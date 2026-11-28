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
_stub_if_missing("numpy", log2=math.log2, mean=lambda xs: sum(xs) / len(xs), generic=type("generic", (), {}))
_stub_if_missing("pandas")
_stub_if_missing("tqdm", tqdm=lambda it, **k: it)
_stub_if_missing("openai", OpenAI=_Dummy)
_stub_if_missing("anthropic", Anthropic=_Dummy)
class _Kw:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


_stub_if_missing(
    "google.genai",
    Client=_Dummy,
    types=types.SimpleNamespace(GenerateContentConfig=_Kw, HttpOptions=_Kw),
)

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
        "coded1": _with(STORY_1, incident_clear="Jordan tells Sam to uninstall her life."),
        "coded2": _with(STORY_1, incident_clear="Jordan tells Sam to uninstall his life."),
        "coded3": _with(STORY_1, incident_clear="Jordan writes 'just uninstall your life'."),
        "coded4": _with(STORY_1, incident_clear="Jordan tells Sam to just end it."),
        "coded5": _with(STORY_1, incident_clear="Jordan replies 'KYS' under Sam's post."),
        "coded6": _with(STORY_1, incident_clear="Jordan tells Sam to unalive themselves."),
        "large": _with(STORY_1, setting="You are competing in an online gaming tournament."),
        "large2": _with(STORY_1, setting="You are watching a livestream on your phone."),
    }
    for name, raw in cases.items():
        story, error = gms.validate_base_story(raw)
        assert story is None, f"{name} should be rejected"
    # Words that only look similar must not trigger the severity rules
    ok = _with(STORY_1, incident_unclear="Jordan posts a photo of Sam's diet plan with a skill-related joke.")
    assert gms.validate_base_story(ok)[0] is not None


def test_revalidation_removes_failing_and_regenerates_only_those():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _generate(tmp, _replies())
        # Simulate a story saved under older rules that the current rules reject
        saved = json.loads((tmp / gms.BASE_STORIES_FILE).read_text())
        saved[0]["story"]["incident_clear"] = "Jordan tells Sam to uninstall his life."
        (tmp / gms.BASE_STORIES_FILE).write_text(json.dumps(saved))

        assert gms.revalidate_base_stories(tmp) == ["cyberbullying_b0"]
        remaining = json.loads((tmp / gms.BASE_STORIES_FILE).read_text())
        assert [b["base_id"] for b in remaining] == ["cyberbullying_b1"]
        assert gms.revalidate_base_stories(tmp) == []   # idempotent

        # Resume regenerates only the removed base (exactly one API call)
        client, bases = _generate(tmp, [json.dumps(STORY_1)])
        assert len(client.models.calls) == 1
        assert sorted(b["base_id"] for b in bases) == ["cyberbullying_b0", "cyberbullying_b1"]


def test_bystander_sentences():
    w = gms.REACTION_SENTENCES["worried"]
    w1 = " They look uncomfortable and worried, but they don't say or do anything."
    i1 = " They carry on as if nothing is happening and don't say or do anything."
    assert gms.bystander_sentence(0, "viewers", "n/a") == "No one else is aware of what is happening."
    assert gms.bystander_sentence(1, "viewers", "worried") == "One other viewer is also watching this happen." + w1
    assert gms.bystander_sentence(1, "viewers", "ignoring") == "One other viewer is also watching this happen." + i1
    assert gms.bystander_sentence(1, "people", "worried") == "One other person is also watching this happen." + w1
    assert gms.bystander_sentence(1, "witnesses", "worried") == "One other witness is also watching this happen." + w1
    assert gms.bystander_sentence(1, "people in the chat", "worried") == (
        "One of the people in the chat is also watching this happen." + w1)
    assert gms.bystander_sentence(2, "viewers", "ignoring") == (
        "2 other viewers are also watching this happen." + gms.REACTION_SENTENCES["ignoring"])
    for n in (1, 2, 8):
        for r in gms.BYSTANDER_REACTIONS:
            sentence = gms.bystander_sentence(n, "viewers", r)
            assert ("none of them" in sentence) == (n > 1), (n, r)
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


def _rotation_of(option_types):
    """Which cyclic rotation of ROTATION_BASE a letter -> type mapping is (asserts it is one)."""
    order = [option_types[letter] for letter in "ABCD"]
    for r in range(4):
        if order == gms.ROTATION_BASE[r:] + gms.ROTATION_BASE[:r]:
            return r
    raise AssertionError(f"not a cyclic rotation: {order}")


def test_options_counterbalanced_and_typed():
    from collections import Counter

    with tempfile.TemporaryDirectory() as d:
        bases, records, _ = _built(Path(d))
        story_options = {b["base_id"]: b["story"]["options"] for b in bases}
        for r in records:
            options = json.loads(r["generated_scenario"])["options"]
            assert sorted(options) == ["A", "B", "C", "D"]
            assert sorted(r["option_types"]) == ["A", "B", "C", "D"]
            assert sorted(r["option_types"].values()) == sorted(gms.RESPONSE_TYPES)
            for letter, rtype in r["option_types"].items():
                assert options[letter] == story_options[r["base_id"]][rtype]

        rotations_seen_per_cell = defaultdict(set)
        for base in bases:
            variants = [r for r in records if r["base_id"] == base["base_id"]]

            # Every type at every letter equally often within the base
            per_letter = Counter((letter, t) for v in variants for letter, t in v["option_types"].items())
            assert len(per_letter) == 16 and len(set(per_letter.values())) == 1, per_letter
            assert set(per_letter.values()) == {len(variants) // 4}

            # Balanced within each group size, and within each factor level at that size
            for n in gms.GROUP_SIZES:
                at_n = [v for v in variants if v["group_size"] == n]
                counts = Counter(_rotation_of(v["option_types"]) for v in at_n)
                assert sorted(counts) == [0, 1, 2, 3] and len(set(counts.values())) == 1, (n, counts)
                if n > 0:
                    for factor in ("clarity_level", "authority_present", "bystander_reaction"):
                        for level in {v[factor] for v in at_n}:
                            rots = sorted(_rotation_of(v["option_types"]) for v in at_n if v[factor] == level)
                            assert rots == [0, 1, 2, 3], (n, factor, level, rots)

            # A cell keeps the same option order at every group size > 0
            by_cell = defaultdict(set)
            for v in variants:
                if v["group_size"] > 0:
                    cell = (v["clarity_level"], v["authority_present"], v["bystander_reaction"])
                    by_cell[cell].add(_rotation_of(v["option_types"]))
            assert all(len(rots) == 1 for rots in by_cell.values()), by_cell
            for cell, rots in by_cell.items():
                rotations_seen_per_cell[cell] |= rots

        # Different bases shift the rotations, so a cell doesn't always get the same order
        assert all(len(rots) == len(bases) for rots in rotations_seen_per_cell.values())

        # Non-binary factor shapes fall back to cycling within each group size
        fallback = gms.build_variants(bases[0], group_sizes=[0, 3], clarity_levels=["clear"],
                                      authority_options=[True, False, None], reactions=["worried"])
        for n in (0, 3):
            rots = [_rotation_of(v["option_types"]) for v in fallback if v["group_size"] == n]
            assert rots == [0, 1, 2], (n, rots)

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

        # The model puts all probability on A; the score must come from the dataset's option_types.
        # A stray response_type in the reply (old prompt format) is ignored.
        letter_a_type = s.option_types["A"]
        reply = {
            "option_evaluations": {
                letter: {"probability": 100 if letter == "A" else 0,
                         "response_type": "direct_intervention", "reasoning": ""}
                for letter in "ABCD"
            },
            "confidence": 7,
        }
        evaluator = object.__new__(llm_evaluator.LLMEvaluator)
        evaluator._get_model_response = lambda model_name, prompt: json.dumps(reply)
        response = evaluator.evaluate_scenario("fake-model", s)

        scores = {"non_intervention": 1, "hesitation": 2, "indirect_intervention": 3, "direct_intervention": 4}
        assert response.intervention_score_expected == scores[letter_a_type]
        assert not hasattr(response, "model_response_types")
        assert response.option_types == s.option_types and response.base_id == s.base_id


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"PASS {name}")
    print(f"\n{len(tests)} tests passed")
