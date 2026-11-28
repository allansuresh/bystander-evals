"""
Stubbed tests for the evaluator run (no API calls): retry/backoff, fence stripping, JSONL
resume, the client-side rate limiter, failure reporting and the daily-quota stop.

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
    "quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier. Please retry in 37.2s."
)
MODEL = "gemini-fake"


def _reply(fenced: bool = False) -> str:
    body = json.dumps({
        "option_evaluations": {
            "A": {"probability": 70, "reasoning": "a"},
            "B": {"probability": 10, "reasoning": "b"},
            "C": {"probability": 10, "reasoning": "c"},
            "D": {"probability": 10, "reasoning": "d"},
        },
        "confidence": 6,
    }, indent=2)
    return f"```json\n{body}\n```" if fenced else body


class FakeGemini:
    """Stands in for a google-genai Client. `script` maps call index -> Exception or reply text."""

    def __init__(self, script=None, default=None):
        self.script = dict(script or {})
        self.default = default or _reply()
        self.calls = []
        self.models = self

    def generate_content(self, model, contents, config=None):
        i = len(self.calls)
        self.calls.append({"model": model, "config": config})
        out = self.script.get(i, self.default)
        if isinstance(out, Exception):
            raise out
        return types.SimpleNamespace(text=out)


class RecordingLimiter:
    def __init__(self):
        self.keys = []

    def wait(self, key):
        self.keys.append(key)


def _evaluator(tmp: Path, client=None, models=(MODEL,), clients=None):
    ev = object.__new__(llm_evaluator.LLMEvaluator)
    ev.config = types.SimpleNamespace(
        MODELS_TO_EVALUATE=list(models), OUTPUT_DIR=str(tmp), TEMPERATURE=0.7, MAX_TOKENS=500,
    )
    ev.clients = clients if clients is not None else {"google": client or FakeGemini()}
    ev.rate_limiter = RecordingLimiter()
    ev.sleeps = []
    ev.retry_sleep = ev.sleeps.append
    return ev


def _scenarios(tmp: Path, n: int):
    _, _, path = tm._built(tmp)
    return eval_main.load_scenarios(str(path))[:n], path


@contextlib.contextmanager
def _quiet():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def test_prompt_has_no_key_factors():
    prompt = llm_evaluator.PROBABILITY_EXTRACTION_PROMPT
    assert "key_factors" not in prompt
    for leak in ("group size", "clarity", "authority"):
        assert leak not in prompt.lower(), leak
    assert "key_factors" not in llm_evaluator.LLMResponse.__dataclass_fields__
    prompt.format(scenario_text="s", options_text="o")  # still formats


def test_prompt_does_not_define_response_types():
    prompt = llm_evaluator.PROBABILITY_EXTRACTION_PROMPT
    for term in ("response_type", "response type", "direct_intervention", "indirect_intervention",
                 "hesitation", "non_intervention", "Waiting to see what others do first"):
        assert term.lower() not in prompt.lower(), term
    assert '"probability"' in prompt and '"reasoning"' in prompt
    assert "model_response_types" not in llm_evaluator.LLMResponse.__dataclass_fields__


def test_load_scenarios_requires_option_types():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _, _, path = tm._built(tmp)
        records = json.loads(path.read_text())
        records[3].pop("option_types")
        legacy = tmp / "legacy.json"
        legacy.write_text(json.dumps(records))
        with _quiet():
            try:
                eval_main.load_scenarios(str(legacy))
                raise AssertionError("expected ValueError for missing option_types")
            except ValueError as e:
                assert "option_types" in str(e) and records[3]["id"] in str(e)


def test_old_jsonl_lines_with_model_response_types_still_load():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        scenarios, _ = _scenarios(tmp, 1)
        ev = _evaluator(tmp)
        with _quiet():
            r = ev.evaluate_scenario(MODEL, scenarios[0])
        line = llm_evaluator.response_to_dict(r)
        line["model_response_types"] = {k: "hesitation" for k in "ABCD"}  # written by the old code
        line["key_factors"] = []
        path = tmp / "old.jsonl"
        path.write_text(json.dumps(line) + "\n")
        loaded = llm_evaluator.load_responses_jsonl(str(path))
        assert loaded[MODEL][0].scenario_id == r.scenario_id


# ---------------------------------------------------------------------------
# Retry / backoff
# ---------------------------------------------------------------------------

def test_retry_transient_errors_with_backoff():
    with tempfile.TemporaryDirectory() as d:
        client = FakeGemini({0: RuntimeError("503 UNAVAILABLE"), 1: RuntimeError("504 DEADLINE_EXCEEDED")})
        ev = _evaluator(Path(d), client)
        with _quiet():
            assert ev._get_model_response(MODEL, "p") == _reply()
        assert len(client.calls) == 3 and ev.sleeps == [10, 20]
        # temperature is passed through GenerateContentConfig
        assert client.calls[0]["config"].temperature == 0.7
        # every attempt (incl. retries) goes through the rate limiter
        assert ev.rate_limiter.keys == [MODEL] * 3


def test_retry_honours_please_retry_in():
    with tempfile.TemporaryDirectory() as d:
        client = FakeGemini({0: RuntimeError(GEMINI_PER_MINUTE)})
        ev = _evaluator(Path(d), client)
        with _quiet():
            ev._get_model_response(MODEL, "p")
        assert ev.sleeps == [37.2], ev.sleeps


def test_retry_gives_up_after_five_attempts():
    with tempfile.TemporaryDirectory() as d:
        client = FakeGemini(default=None)
        client.script = {i: TimeoutError("read timed out") for i in range(10)}
        ev = _evaluator(Path(d), client)
        with _quiet():
            try:
                ev._get_model_response(MODEL, "p")
                raise AssertionError("should give up")
            except TimeoutError:
                pass
        assert len(client.calls) == 5 and ev.sleeps == [10, 20, 40, 80]


def test_backoff_caps_at_120s():
    sleeps = []
    attempts = iter(range(100))

    def always_fail():
        next(attempts)
        raise RuntimeError("503 UNAVAILABLE")

    with _quiet():
        try:
            llm_evaluator.call_with_retry(always_fail, max_attempts=7, sleep=sleeps.append)
        except RuntimeError:
            pass
    assert sleeps == [10, 20, 40, 80, 120, 120]


def test_no_retry_on_daily_quota_or_bad_request():
    with tempfile.TemporaryDirectory() as d:
        client = FakeGemini({0: RuntimeError(GEMINI_DAILY)})
        ev = _evaluator(Path(d), client)
        with _quiet():
            try:
                ev._get_model_response(MODEL, "p")
                raise AssertionError("expected QuotaExhaustedError")
            except llm_evaluator.QuotaExhaustedError:
                pass
        assert len(client.calls) == 1 and ev.sleeps == []

        client = FakeGemini({0: ValueError("400 INVALID_ARGUMENT")})
        ev = _evaluator(Path(d), client)
        with _quiet():
            try:
                ev._get_model_response(MODEL, "p")
                raise AssertionError("expected ValueError")
            except ValueError:
                pass
        assert len(client.calls) == 1 and ev.sleeps == []


def test_retry_covers_openai_and_anthropic():
    class APITimeoutError(Exception):
        pass

    openai_calls = []

    def openai_create(**kw):
        openai_calls.append(kw)
        if len(openai_calls) == 1:
            raise APITimeoutError("Request timed out.")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok-gpt"))])

    anthropic_calls = []

    def anthropic_create(**kw):
        anthropic_calls.append(kw)
        if len(anthropic_calls) == 1:
            raise RuntimeError("Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error'}}")
        return types.SimpleNamespace(content=[types.SimpleNamespace(text="ok-claude")])

    clients = {
        "openai": types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=openai_create))),
        "anthropic": types.SimpleNamespace(messages=types.SimpleNamespace(create=anthropic_create)),
    }
    with tempfile.TemporaryDirectory() as d:
        ev = _evaluator(Path(d), clients=clients)
        with _quiet():
            assert ev._get_model_response("gpt-fake", "p") == "ok-gpt"
            assert ev._get_model_response("claude-fake", "p") == "ok-claude"
        assert len(openai_calls) == 2 and len(anthropic_calls) == 2 and ev.sleeps == [10, 10]


def test_daily_quota_detection():
    assert llm_evaluator.is_daily_quota_error(RuntimeError(GEMINI_DAILY))
    assert llm_evaluator.is_daily_quota_error(RuntimeError(
        "Rate limit reached for gpt-4o on requests per day (RPD): Limit 10000, Used 10000."))
    assert not llm_evaluator.is_daily_quota_error(RuntimeError(GEMINI_PER_MINUTE))
    assert not llm_evaluator.is_daily_quota_error(RuntimeError("503 UNAVAILABLE"))
    assert not llm_evaluator.is_daily_quota_error(ValueError("the daily special is soup"))


# ---------------------------------------------------------------------------
# Fence stripping
# ---------------------------------------------------------------------------

def test_fenced_reply_is_parsed():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        scenarios, _ = _scenarios(tmp, 1)
        ev = _evaluator(tmp, FakeGemini(default=_reply(fenced=True)))
        with _quiet():
            r = ev.evaluate_scenario(MODEL, scenarios[0])
        assert r.probability_distribution == {"A": 0.7, "B": 0.1, "C": 0.1, "D": 0.1}
        assert r.reasoning == {"A": "a", "B": "b", "C": "c", "D": "d"}, "fallback parser gives empty reasoning"
        assert r.confidence == 6


# ---------------------------------------------------------------------------
# JSONL persistence + resume
# ---------------------------------------------------------------------------

def test_jsonl_written_per_response_and_resume_skips_done_pairs():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        scenarios, _ = _scenarios(tmp, 8)
        jsonl = tmp / llm_evaluator.RESPONSES_JSONL

        # call 0 ok, call 1 fails (bad request), call 2 ok, call 3 daily quota -> stop
        client = FakeGemini({1: ValueError("400 INVALID_ARGUMENT"), 3: RuntimeError(GEMINI_DAILY)})
        ev = _evaluator(tmp, client)

        lines_seen = []
        real_append = llm_evaluator.append_response_jsonl

        def spy(path, r):
            real_append(path, r)
            lines_seen.append(len(Path(path).read_text().splitlines()))  # on disk immediately

        llm_evaluator.append_response_jsonl = spy
        try:
            with _quiet():
                responses = ev.evaluate_all_scenarios(scenarios)
        finally:
            llm_evaluator.append_response_jsonl = real_append

        assert lines_seen == [1, 2]
        assert len(client.calls) == 4 and ev.stop_reason and "PerDay" in ev.stop_reason
        assert list(ev.failures) == [(MODEL, scenarios[1].id)]
        assert not (tmp / "intermediate_responses.pkl").exists()

        saved = [json.loads(line) for line in jsonl.read_text().splitlines()]
        assert [s["scenario_id"] for s in saved] == [scenarios[0].id, scenarios[2].id]
        assert "raw_response" in saved[0] and "key_factors" not in saved[0]

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            counts = llm_evaluator.summarize_run([MODEL], scenarios, responses, ev.failures, d)
        assert counts == {"total": 8, "succeeded": 2, "failed": 1, "not_attempted": 5}, counts
        assert json.loads((tmp / "failed_scenarios.json").read_text()) == [
            {"model_name": MODEL, "scenario_id": scenarios[1].id, "error": "ValueError: 400 INVALID_ARGUMENT"}]

        # A partial last line (crash mid-write) must not break resume
        with open(jsonl, "a") as f:
            f.write('{"model_name": "gemini-fake", "scenario_id": "trunc')

        with _quiet():
            existing = llm_evaluator.load_responses_jsonl(str(jsonl))
        assert sorted(r.scenario_id for r in existing[MODEL]) == sorted([scenarios[0].id, scenarios[2].id])
        assert existing[MODEL][0].probability_distribution == responses[MODEL][0].probability_distribution

        client2 = FakeGemini()
        ev2 = _evaluator(tmp, client2)
        with _quiet():
            responses2 = ev2.evaluate_all_scenarios(scenarios, existing=existing)
            counts2 = llm_evaluator.summarize_run([MODEL], scenarios, responses2, ev2.failures, d)
        assert len(client2.calls) == 6, "only the failed + unattempted pairs are re-evaluated"
        assert counts2 == {"total": 8, "succeeded": 8, "failed": 0, "not_attempted": 0}
        with _quiet():
            reloaded = llm_evaluator.load_responses_jsonl(str(jsonl))
        assert len(reloaded[MODEL]) == 8


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        assert seconds > 0
        self.now += seconds


def test_rate_limiter_spaces_calls():
    clock = FakeClock()
    limiter = llm_evaluator.RateLimiter(rpm=14, clock=clock, sleep=clock.sleep)
    times = []
    for _ in range(50):
        limiter.wait("m")
        times.append(clock.now)
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert all(60 / 14 <= g <= 60 / 14 + 0.1 for g in gaps), gaps[:3]
    # No 60-second window contains more than 14 calls
    for i, t in enumerate(times):
        assert sum(1 for u in times[i:] if u < t + 60) <= 14

    # Separate models are limited independently
    t0 = clock.now
    limiter.wait("other-model")
    assert clock.now == t0

    # Slow callers are not delayed further
    clock.now += 100
    t1 = clock.now
    limiter.wait("m")
    assert clock.now == t1

    # rpm=0 disables limiting
    off = llm_evaluator.RateLimiter(rpm=0, clock=clock, sleep=clock.sleep)
    t2 = clock.now
    for _ in range(5):
        off.wait("m")
    assert clock.now == t2


def test_no_fixed_sleep_in_run_loop():
    import inspect
    assert "time.sleep(0.5)" not in inspect.getsource(llm_evaluator.LLMEvaluator.evaluate_all_scenarios)


# ---------------------------------------------------------------------------
# main.py end to end
# ---------------------------------------------------------------------------

def _run_main(argv):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["main.py"] + argv
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            eval_main.main()
    except SystemExit as e:
        code = e.code
    finally:
        sys.argv = saved
    return code, out.getvalue()


@contextlib.contextmanager
def _patched_clients(client):
    saved = llm_evaluator.LLMEvaluator._initialize_clients
    llm_evaluator.LLMEvaluator._initialize_clients = lambda self: {"google": client}
    try:
        yield
    finally:
        llm_evaluator.LLMEvaluator._initialize_clients = saved


def test_models_required():
    code, out = _run_main(["--scenarios-file", "x.json"])
    assert code == 2 and "--models" in out
    assert eval_main.Config().MODELS_TO_EVALUATE == []


def test_main_stops_cleanly_then_resumes():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _, path = _scenarios(tmp, 0)
        outdir = tmp / "run"
        base = ["--scenarios-file", str(path), "--models", MODEL, "--limit", "5", "--rpm", "0"]

        client = FakeGemini({2: RuntimeError(GEMINI_DAILY)})
        with _patched_clients(client):
            code, out = _run_main(base + ["--output-dir", str(outdir)])
        assert code == 3, out
        assert "daily quota exhausted" in out.lower() and f"--resume {outdir}" in out
        assert "Traceback" not in out
        assert len((outdir / "responses.jsonl").read_text().splitlines()) == 2
        assert len(json.loads((outdir / "raw_responses.json").read_text())[MODEL]) == 2
        assert json.loads((outdir / "failed_scenarios.json").read_text()) == []

        client2 = FakeGemini(default=_reply(fenced=True))
        with _patched_clients(client2):
            code, out = _run_main(base + ["--resume", str(outdir)])
        assert code == 0, out
        assert len(client2.calls) == 3, "resume should evaluate only the 3 remaining scenarios"
        raw = json.loads((outdir / "raw_responses.json").read_text())[MODEL]
        assert len(raw) == 5 and all("key_factors" not in r for r in raw)
        assert len((outdir / "responses.jsonl").read_text().splitlines()) == 5
        assert "EVALUATION COMPLETE" in out and "Succeeded:      5/5" in out

        # --resume needs an existing directory
        code, out = _run_main(base + ["--resume", str(tmp / "missing")])
        assert code == 2 and "not found" in out


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"PASS {name}")
    print(f"\n{len(tests)} tests passed")
