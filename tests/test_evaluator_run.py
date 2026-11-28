"""
Tests for the evaluator's run bookkeeping: no key_factors in the prompt, failure reporting,
daily-quota stop, and --resume continuing where a run stopped. No API calls.

Run from the repo root with either:
    python3 tests/test_evaluator_run.py
    pytest tests/test_evaluator_run.py
"""

import contextlib
import io
import json
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_matched as tm  # noqa: E402  (installs module stand-ins, builds fixtures)

eval_main = tm._load_eval_module("main")
llm_evaluator = sys.modules["llm_evaluator"]

GEMINI_DAILY = (
    "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota. "
    "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, "
    "limit: 20', 'details': [{'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]}]}}"
)
GEMINI_PER_MINUTE = (
    "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: generate_content_free_tier_requests, "
    "quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
)


def _good_reply(prompt: str) -> str:
    return json.dumps({
        "option_evaluations": {
            letter: {"probability": 25, "response_type": "hesitation", "reasoning": ""} for letter in "ABCD"
        },
        "confidence": 6,
    })


class FakeGenai:
    """Stands in for google.generativeai; `script` maps call index -> Exception to raise."""

    def __init__(self, script=None):
        self.script = dict(script or {})
        self.calls = 0

    def configure(self, **k):
        pass

    def GenerativeModel(self, name):
        outer = self

        class _Model:
            def generate_content(self, prompt):
                i = outer.calls
                outer.calls += 1
                if i in outer.script:
                    raise outer.script[i]
                return types.SimpleNamespace(text=_good_reply(prompt))

        return _Model()


@contextlib.contextmanager
def fake_gemini(script=None):
    fake = FakeGenai(script)
    saved_genai, saved_sleep = llm_evaluator.genai, llm_evaluator.time.sleep
    llm_evaluator.genai = fake
    llm_evaluator.time.sleep = lambda s: None
    try:
        yield fake
    finally:
        llm_evaluator.genai, llm_evaluator.time.sleep = saved_genai, saved_sleep


def _scenarios(tmp: Path, n: int):
    _, _, path = tm._built(tmp)
    return eval_main.load_scenarios(str(path))[:n], path


def _evaluator(tmp: Path, models=("gemini-fake",)):
    ev = object.__new__(llm_evaluator.LLMEvaluator)
    ev.config = types.SimpleNamespace(MODELS_TO_EVALUATE=list(models), SAVE_INTERMEDIATE=True, OUTPUT_DIR=str(tmp))
    return ev


def test_prompt_has_no_key_factors():
    prompt = llm_evaluator.PROBABILITY_EXTRACTION_PROMPT
    assert "key_factors" not in prompt
    for leak in ("group size", "clarity", "authority"):
        assert leak not in prompt.lower(), leak
    assert "key_factors" not in llm_evaluator.LLMResponse.__dataclass_fields__
    prompt.format(scenario_text="s", options_text="o")  # still formats


def test_daily_quota_detection():
    assert llm_evaluator.is_daily_quota_error(RuntimeError(GEMINI_DAILY))
    assert llm_evaluator.is_daily_quota_error(RuntimeError(
        "Rate limit reached for gpt-4o on requests per day (RPD): Limit 10000, Used 10000."))
    assert not llm_evaluator.is_daily_quota_error(RuntimeError(GEMINI_PER_MINUTE))
    assert not llm_evaluator.is_daily_quota_error(RuntimeError("503 UNAVAILABLE"))
    assert not llm_evaluator.is_daily_quota_error(ValueError("the daily special is soup"))


def test_failures_reported_and_quota_stops_run():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        scenarios, _ = _scenarios(tmp, 8)
        ev = _evaluator(tmp)
        # call 0 ok, call 1 per-minute 429 (ordinary failure), call 2 ok, call 3 daily quota -> stop
        with fake_gemini({1: RuntimeError(GEMINI_PER_MINUTE), 3: RuntimeError(GEMINI_DAILY)}) as fake, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            responses = ev.evaluate_all_scenarios(scenarios)
        assert fake.calls == 4, "must stop at the daily-quota error instead of continuing"
        assert ev.stop_reason and "PerDay" in ev.stop_reason
        assert [r.scenario_id for r in responses["gemini-fake"]] == [scenarios[0].id, scenarios[2].id]
        assert list(ev.failures) == [("gemini-fake", scenarios[1].id)]
        assert (tmp / "intermediate_responses.pkl").exists(), "progress must be saved on stop"

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            counts = llm_evaluator.summarize_run(ev.config.MODELS_TO_EVALUATE, scenarios, responses, ev.failures, d)
        assert counts == {"total": 8, "succeeded": 2, "failed": 1, "not_attempted": 5}, counts
        assert "Not attempted:  5" in out.getvalue()
        failed = json.loads((tmp / "failed_scenarios.json").read_text())
        assert failed == [{"model_name": "gemini-fake", "scenario_id": scenarios[1].id,
                           "error": "RuntimeError: " + GEMINI_PER_MINUTE}]

        # Resume: only the failed + unattempted pairs are evaluated
        ev2 = _evaluator(tmp)
        with fake_gemini() as fake2, contextlib.redirect_stdout(io.StringIO()):
            responses2 = ev2.evaluate_all_scenarios(scenarios, existing=responses)
            counts2 = llm_evaluator.summarize_run(ev2.config.MODELS_TO_EVALUATE, scenarios, responses2, ev2.failures, d)
        assert fake2.calls == 6 and ev2.stop_reason is None
        assert counts2 == {"total": 8, "succeeded": 8, "failed": 0, "not_attempted": 0}
        assert json.loads((tmp / "failed_scenarios.json").read_text()) == []


def _run_main(argv):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["main.py"] + argv
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            eval_main.main()
    except SystemExit as e:
        code = e.code
    finally:
        sys.argv = saved
    return code, out.getvalue()


def test_main_stops_cleanly_then_resumes():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _, path = _scenarios(tmp, 0)
        outdir = tmp / "run"
        args = ["--scenarios-file", str(path), "--models", "gemini-fake", "--output-dir", str(outdir), "--limit", "5"]

        with fake_gemini({2: RuntimeError(GEMINI_DAILY)}):
            code, out = _run_main(args)
        assert code == 3, out
        assert "daily quota exhausted" in out.lower() and "--resume" in out and str(outdir) in out
        assert "Traceback" not in out
        assert len(json.loads((outdir / "raw_responses.json").read_text())["gemini-fake"]) == 2
        assert json.loads((outdir / "failed_scenarios.json").read_text()) == []

        with fake_gemini() as fake:
            code, out = _run_main(args + ["--resume"])
        assert code == 0, out
        assert fake.calls == 3, "resume should evaluate only the 3 remaining scenarios"
        raw = json.loads((outdir / "raw_responses.json").read_text())["gemini-fake"]
        assert len(raw) == 5 and all("key_factors" not in r for r in raw)
        assert "EVALUATION COMPLETE" in out


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"PASS {name}")
    print(f"\n{len(tests)} tests passed")
