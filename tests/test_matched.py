"""
Tests for the matched-scenario generator and the evaluator's use of option_types.
No API calls: the Gemini client is stubbed.

Run from the repo root with either:
    python3 tests/test_matched.py
    pytest tests/test_matched.py
"""

import importlib.util
import json
import math
import os
import sys
import tempfile
import types
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_COLLECTION = REPO / "Data_Collection"
EVAL_LLMS = REPO / "Eval_LLMs"

# output_processor creates ./scenarios on import; keep that out of the repo
_WORKDIR = tempfile.mkdtemp(prefix="matched_tests_")
os.chdir(_WORKDIR)


def _stub_if_missing(name: str, **attrs) -> None:
    """Install a minimal stand-in for a third-party module only if it isn't installed."""
    try:
        importlib.import_module(name)
        return
    except ImportError:
        pass
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    parent, _, child = name.rpartition(".")
    if parent:
        _stub_if_missing(parent)
        setattr(sys.modules[parent], child, module)


class _Dummy:
    def __init__(self, *a, **k):
        pass


_stub_if_missing("dotenv", load_dotenv=lambda *a, **k: None)
_stub_if_missing("numpy", log2=math.log2, mean=lambda xs: sum(xs) / len(xs))
_stub_if_missing("pandas")
_stub_if_missing("tqdm", tqdm=lambda it, **k: it)
_stub_if_missing("openai", OpenAI=_Dummy)
_stub_if_missing("anthropic", Anthropic=_Dummy)
_stub_if_missing("google.generativeai", configure=lambda **k: None, GenerativeModel=_Dummy)

sys.path.insert(0, str(DATA_COLLECTION))
import generate_matched_scenarios as gms  # noqa: E402
from gemini_client import generate_with_retry  # noqa: E402


def _load_eval_module(name: str):
    """Import an Eval_LLMs module (its `config` differs from Data_Collection's)."""
    if str(EVAL_LLMS) not in sys.path:
        sys.path.insert(0, str(EVAL_LLMS))
    cached = sys.modules.get("config")
    if cached is not None and Path(getattr(cached, "__file__", "")).parent != EVAL_LLMS:
        del sys.modules["config"]
    spec = importlib.util.spec_from_file_location(f"eval_{name}", EVAL_LLMS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STORY_1 = {
    "setting": "You are scrolling through a class group chat late in the evening.",
    "incident_clear": "Jordan posts an edited photo of Sam with a cruel caption and keeps adding insults; Sam replies asking them to stop and says they feel humiliated.",
    "incident_unclear": "Jordan posts an edited photo of Sam with a caption that could be a joke; Sam reacts with a single laughing emoji and then goes quiet.",
    "bystander_noun": "people in the chat",
    "authority_role": "A chat moderator",
    "options": {
        "non_intervention": "Keep scrolling and say nothing.",
        "direct_intervention": "Reply in the chat telling Jordan to delete the photo.",
        "indirect_intervention": "Message Sam privately to check on them and offer support.",
        "hesitation": "Wait a while to see how the conversation develops.",
    },
}

STORY_2 = {
    "setting": "You are reading replies under a post in a small hobby forum for model-train builders.",
    "incident_clear": "A user named Rex replies to Mia's first build photo calling her stupid and ugly, then posts the same insult under three more of her posts; Mia writes that she is leaving the forum.",
    "incident_unclear": "A user named Rex replies to Mia's first build photo with a blunt comment that her work looks sloppy; Mia does not reply.",
    "bystander_noun": "other forum members",   # leading "other" must be stripped
    "authority_role": "an assistant moderator for the forum",
    "options": {
        "non_intervention": "Close the thread and move on.",
        "direct_intervention": "Reply to Rex telling him to stop insulting Mia.",
        "indirect_intervention": "Use the report button on Rex's replies.",
        "hesitation": "Keep reading to see whether it continues.",
    },
}

INVALID_STORY = dict(STORY_1, setting="You and dozens of viewers are watching a live stream.")


class FakeModels:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if not self.replies:
            raise AssertionError("unexpected extra generate_content call")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return types.SimpleNamespace(text=reply)


class FakeClient:
    def __init__(self, replies):
        self.models = FakeModels(replies)


def _generate(tmp: Path, replies):
    client = FakeClient(replies)
    bases = gms.generate_base_stories(
        client, scenario_types=["cyberbullying"], n_base_per_type=2, output_dir=tmp,
        temperature=None, sleep=lambda s: None,
    )
    return client, bases


def _replies():
    return [
        json.dumps(INVALID_STORY),                               # b0 try 1: mentions "viewers" -> rejected
        "```json\n" + json.dumps(STORY_1, indent=2) + "\n```",  # b0 try 2: fenced, valid
        json.dumps(STORY_2),                                     # b1: plain, valid
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_invalid_story_rejected_and_regenerated():
    story, error = gms.validate_base_story(json.dumps(INVALID_STORY))
    assert story is None and "viewers" in error, error

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        client, bases = _generate(tmp, _replies())
        assert len(client.models.calls) == 3, "invalid story should trigger one regeneration"
        assert [b["base_id"] for b in bases] == ["cyberbullying_b0", "cyberbullying_b1"]
        assert bases[0]["story"]["setting"] == STORY_1["setting"]   # the fenced reply, not the invalid one
        assert bases[0]["story"]["authority_role"] == "a chat moderator"  # article normalised
        assert bases[1]["story"]["bystander_noun"] == "forum members"      # leading "other" stripped
        saved = json.loads((tmp / gms.BASE_STORIES_FILE).read_text())
        assert [b["base_id"] for b in saved] == ["cyberbullying_b0", "cyberbullying_b1"]

        # Resume: both bases are already saved, so no further API calls
        client2, bases2 = _generate(tmp, [])
        assert client2.models.calls == [] and len(bases2) == 2


def test_option_validation():
    bad_digit = json.loads(json.dumps(STORY_1))
    bad_digit["options"]["hesitation"] = "Wait 5 minutes."
    assert gms.validate_base_story(json.dumps(bad_digit))[0] is None

    bad_role = json.loads(json.dumps(STORY_2))
    bad_role["options"]["indirect_intervention"] = "Tell the assistant moderator for the channel."
    assert gms.validate_base_story(json.dumps(bad_role))[0] is None


def _with(story, **changes):
    out = json.loads(json.dumps(story))
    out.update(changes)
    return json.dumps(out)


def test_story_content_rules():
    cases = {
        "conclusion": _with(STORY_1, incident_clear="Jordan insults Sam and you realize Sam needs help."),
        "conclusion2": _with(STORY_1, incident_clear="Jordan insults Sam, who is clearly distressed."),
        "conclusion3": _with(STORY_1, incident_unclear="It is unclear whether Sam requires help."),
        "severity": _with(STORY_1, incident_clear="Jordan tells Sam to kill himself."),
        "severity2": _with(STORY_1, incident_clear="Jordan posts violent threats at Sam."),
        "severity3": _with(STORY_1, incident_clear="Jordan says Sam should die."),
        "large": _with(STORY_1, setting="You are competing in an online gaming tournament."),
        "large2": _with(STORY_1, setting="You are watching a livestream on your phone."),
    }
    for name, raw in cases.items():
        story, error = gms.validate_base_story(raw)
        assert story is None, f"{name} should be rejected"
    # Words that only look similar must not trigger the severity rules
    ok = _with(STORY_1, incident_unclear="Jordan posts a photo of Sam's diet plan with a skill-related joke.")
    assert gms.validate_base_story(ok)[0] is not None


def test_bystander_sentences():
    w = gms.REACTION_SENTENCES["worried"]
    assert gms.bystander_sentence(0, "viewers", "n/a") == "No one else is aware of what is happening."
    assert gms.bystander_sentence(1, "viewers", "worried") == "One other viewer is also watching this happen." + w
    assert gms.bystander_sentence(1, "people", "worried") == "One other person is also watching this happen." + w
    assert gms.bystander_sentence(1, "witnesses", "worried") == "One other witness is also watching this happen." + w
    assert gms.bystander_sentence(1, "people in the chat", "worried") == (
        "One of the people in the chat is also watching this happen." + w)
    assert gms.bystander_sentence(8, "viewers", "worried") == "8 other viewers are also watching this happen." + w
    # Defensive: a leading "other" is stripped even if it reaches bystander_sentence
    assert gms.bystander_sentence(8, "other channel viewers", "worried") == (
        "8 other channel viewers are also watching this happen." + w)
    assert gms.bystander_sentence(1, "Other viewers", "worried").startswith("One other viewer ")


def _built(tmp: Path):
    _, bases = _generate(tmp, _replies())
    path = gms.build_all_variants(bases, output_dir=tmp)
    return bases, json.loads(path.read_text()), path


def test_variants_are_matched():
    with tempfile.TemporaryDirectory() as d:
        bases, records, _ = _built(Path(d))
        n_sizes = len(gms.GROUP_SIZES)
        expected_per_base = (
            len(gms.CLARITY_LEVELS) * len(gms.AUTHORITY_OPTIONS)
            * (1 + (n_sizes - 1) * len(gms.BYSTANDER_REACTIONS))
        )

        for base in bases:
            story = base["story"]
            variants = [r for r in records if r["base_id"] == base["base_id"]]
            assert len(variants) == expected_per_base, (len(variants), expected_per_base)

            assert not any("other other" in v["generated_scenario"].lower() for v in variants)
            option_sets = {frozenset(json.loads(v["generated_scenario"])["options"].values()) for v in variants}
            assert option_sets == {frozenset(story["options"].values())}

            # Group by everything except group size; within a group, only the bystander sentence may differ
            groups = defaultdict(list)
            for v in variants:
                assert v["generated_scenario"]
                text = json.loads(v["generated_scenario"])["scenario"]
                prefix = f"{story['setting']} {story['incident_' + v['clarity_level']]} "
                suffix = " " + gms.authority_sentence(v["authority_present"], story["authority_role"])
                assert text.startswith(prefix) and text.endswith(suffix), v["id"]
                middle = text[len(prefix):len(text) - len(suffix)]
                assert middle == gms.bystander_sentence(
                    v["group_size"], story["bystander_noun"], v["bystander_reaction"]
                ), v["id"]
                groups[(v["clarity_level"], v["authority_present"])].append((v, prefix, suffix))

            for (clarity, authority), members in groups.items():
                assert len({p for _, p, _ in members}) == 1 and len({s for _, _, s in members}) == 1
                zero = [v for v, _, _ in members if v["group_size"] == 0]
                assert len(zero) == 1 and zero[0]["bystander_reaction"] == "n/a", (clarity, authority)
                for n in gms.GROUP_SIZES[1:]:
                    reactions = sorted(v["bystander_reaction"] for v, _, _ in members if v["group_size"] == n)
                    assert reactions == sorted(gms.BYSTANDER_REACTIONS)


def test_options_shuffled_and_typed():
    with tempfile.TemporaryDirectory() as d:
        bases, records, _ = _built(Path(d))
        story_options = {b["base_id"]: b["story"]["options"] for b in bases}
        a_types = set()
        for r in records:
            options = json.loads(r["generated_scenario"])["options"]
            assert sorted(options) == ["A", "B", "C", "D"]
            assert sorted(r["option_types"]) == ["A", "B", "C", "D"]
            assert sorted(r["option_types"].values()) == sorted(gms.RESPONSE_TYPES)
            for letter, rtype in r["option_types"].items():
                assert options[letter] == story_options[r["base_id"]][rtype]
            a_types.add(r["option_types"]["A"])
        assert a_types != {"non_intervention"}, "option A should not always be non-intervention"
        assert len(a_types) > 1

        # Deterministic: rebuilding gives identical output
        again = [v for b in bases for v in gms.build_variants(b)]
        assert again == records


def test_retry_backoff():
    sleeps = []
    client = FakeClient([RuntimeError("503 UNAVAILABLE"), RuntimeError("429 RESOURCE_EXHAUSTED"), "ok"])
    assert generate_with_retry(client, "m", "p", sleep=sleeps.append) == "ok"
    assert sleeps == [10, 20]

    client = FakeClient([RuntimeError("400 INVALID_ARGUMENT")])
    try:
        generate_with_retry(client, "m", "p", sleep=sleeps.append)
        raise AssertionError("non-retryable error should be raised")
    except RuntimeError as e:
        assert "400" in str(e)

    sleeps = []
    client = FakeClient([TimeoutError("read timed out")] * 5)
    try:
        generate_with_retry(client, "m", "p", sleep=sleeps.append)
        raise AssertionError("should give up after 5 attempts")
    except TimeoutError:
        pass
    assert sleeps == [10, 20, 40, 80] and len(client.models.calls) == 5


def test_evaluator_loads_and_scores_with_option_types():
    eval_main = _load_eval_module("main")
    llm_evaluator = sys.modules["llm_evaluator"]

    with tempfile.TemporaryDirectory() as d:
        _, records, path = _built(Path(d))
        scenarios = eval_main.load_scenarios(str(path))
        assert len(scenarios) == len(records)
        s = scenarios[0]
        assert s.base_id == records[0]["base_id"] and s.option_types == records[0]["option_types"]
        assert s.bystander_reaction == records[0]["bystander_reaction"]

        # The model puts all probability on A and (wrongly) labels A as direct intervention.
        # The score must come from option_types, not the model's label.
        letter_a_type = s.option_types["A"]
        reply = {
            "option_evaluations": {
                letter: {"probability": 100 if letter == "A" else 0,
                         "response_type": "direct_intervention", "reasoning": ""}
                for letter in "ABCD"
            },
            "confidence": 7,
            "key_factors": [],
        }
        evaluator = object.__new__(llm_evaluator.LLMEvaluator)
        evaluator._get_model_response = lambda model_name, prompt: json.dumps(reply)
        response = evaluator.evaluate_scenario("fake-model", s)

        scores = {"non_intervention": 1, "hesitation": 2, "indirect_intervention": 3, "direct_intervention": 4}
        assert response.intervention_score_expected == scores[letter_a_type]
        assert response.model_response_types == {letter: "direct_intervention" for letter in "ABCD"}
        assert response.option_types == s.option_types and response.base_id == s.base_id


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"PASS {name}")
    print(f"\n{len(tests)} tests passed")
