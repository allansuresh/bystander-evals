#!/usr/bin/env python3
"""
Matched-scenario generator.

Each "base story" (setting, incident, options) is written ONCE by the LLM. All experimental
conditions are then built from it in code, so group size, clarity, authority presence and
bystander reaction are the only things that differ between variants of a base:

  scenario = setting + incident_<clarity> + bystander_sentence(n, reaction) + authority_sentence

The four option texts are identical across a base's variants; only their letter order is
shuffled (deterministically, per variant) and the letter -> response-type mapping is stored.

Outputs (Data_Collection/scenarios/matched/):
  base_stories.json       - validated base stories (saved after each success; reruns resume)
  matched_scenarios.json  - all variants, in the format Eval_LLMs/main.py loads

Usage:  python generate_matched_scenarios.py
"""

import json
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scenario_templates import SCENARIO_TEMPLATES
from text_utils import strip_code_fences
from gemini_client import generate_with_retry

# ============================================================================
# CONFIGURATION
# ============================================================================

SCENARIO_TYPES = ["cyberbullying", "workplace_harassment", "public_humiliation"]
N_BASE_PER_TYPE = 10                    # start small
GROUP_SIZES = [0, 1, 2, 4, 8, 16, 32, 128]
CLARITY_LEVELS = ["clear", "unclear"]
AUTHORITY_OPTIONS = [True, False]
BYSTANDER_REACTIONS = ["worried", "ignoring"]
MODEL = "gemini-3.5-flash-lite"
SEED = 42

TEMPERATURE = 0.8
MAX_TRIES_PER_BASE = 3

OUTPUT_DIR = Path(__file__).resolve().parent / "scenarios" / "matched"
BASE_STORIES_FILE = "base_stories.json"
MATCHED_SCENARIOS_FILE = "matched_scenarios.json"

# ============================================================================

RESPONSE_TYPES = ["non_intervention", "direct_intervention", "indirect_intervention", "hesitation"]
NO_REACTION = "n/a"

STORY_KEYS = ["setting", "incident_clear", "incident_unclear", "bystander_noun", "authority_role", "options"]

# Words that would imply extra witnesses or an authority figure in the fixed story text
FORBIDDEN_STORY_WORDS = [
    "other", "others", "everyone", "people", "crowd", "audience", "viewers", "onlookers",
    "bystander", "moderator", "admin", "staff", "manager", "police", "guard", "teacher", "streamer",
]
# Words that would tie the options to a particular authority/group condition
FORBIDDEN_OPTION_WORDS = ["moderator", "admin", "staff", "police", "guard", "manager", "streamer"]

# Story text must show what happens, not state conclusions (regexes, case-insensitive)
CONCLUSION_PATTERNS = [
    r"\bneeds? help\b", r"\bneeds? intervention\b", r"\brequires help\b",
    r"\byou recogni[sz]e\b", r"\byou reali[sz]e\b", r"\bclearly distressed\b",
]
# Severity cap: harmful but not extreme (word forms included, e.g. "killed", "violence")
SEVERITY_PATTERNS = [
    r"\bkill\w*", r"\bsuicid\w*", r"\b(die|dies|died|dying)\b", r"\bviolen\w*",
    r"\b(rape|raped|rapes|raping|rapist)\b", r"\bweapons?\b",
    # coded self-harm phrasing
    r"\buninstall (her|his|your|their) life\b", r"\bend it\b", r"\bkys\b", r"\bunaliv\w*",
]
# Settings that can't plausibly hold anywhere from 0 to 32 other people
LARGE_SETTING_PATTERNS = [
    r"\btournament\w*", r"\bstadium\w*", r"\barenas?\b", r"\bconcerts?\b", r"\blive[- ]?streams?\b",
]

REACTION_SENTENCES = {
    "worried": " They look uncomfortable and worried, but none of them says or does anything.",
    "ignoring": " They carry on as if nothing is happening, and none of them says or does anything.",
}
# group_size == 1: a single bystander
REACTION_SENTENCES_SINGULAR = {
    "worried": " They look uncomfortable and worried, but they don't say or do anything.",
    "ignoring": " They carry on as if nothing is happening and don't say or do anything.",
}

BASE_PROMPT = """You are helping build a controlled psychology experiment on the bystander effect.
Write ONE base story for the following scenario type:

{type_description}

The story will be reused across experimental conditions, so the number of other witnesses and
whether an authority figure is present will be added LATER, in code. Your text must therefore
stay neutral about them. Code will add a sentence such as "8 other {{bystander_noun}} are also
watching this happen." and the story must stay plausible with anywhere from 0 to 32 other
people present.

Return ONLY this JSON object, with no preamble, commentary, or markdown:
{{
  "setting": "1-2 sentences placing YOU (second person) in the setting",
  "incident_clear": "what happens; ONE perpetrator, ONE victim; the harm and the need for help are unambiguous from what is shown",
  "incident_unclear": "the SAME incident with the same people, but it is ambiguous whether help is needed",
  "bystander_noun": "a SHORT plural noun for the other witnesses, without the word 'other' and without extra clauses, e.g. 'viewers', 'people in the chat', 'group members'",
  "authority_role": "a role fitting the setting, with a/an, e.g. 'a chat moderator'",
  "options": {{
    "non_intervention": "what you could do if you decide not to act",
    "direct_intervention": "directly helping the victim or confronting the perpetrator",
    "indirect_intervention": "getting help or acting through indirect or private channels",
    "hesitation": "waiting to see how the situation develops before deciding"
  }}
}}

STRICT RULES:
- "setting", "incident_clear" and "incident_unclear" must mention NO people other than you, the
  victim, and the one perpetrator. Do not mention or imply any audience, crowd, viewers, onlookers,
  others, everyone, moderators, admins, staff, managers, teachers, guards, police, or streamers.
- Write all three in the second person ("you").
- SETTING SIZE: choose a setting where anywhere from 0 to 32 other people could plausibly be
  present, such as a group chat, a comment thread, or a small online community. NOT a tournament,
  stadium, arena, concert, or large live stream.
- SHOW, DON'T TELL: describe only what happens (what is said and done). Never state conclusions
  or the reader's interpretation, e.g. do not write "needs help", "requires help", "needs
  intervention", "you realize", "you recognize", or "clearly distressed".
- SEVERITY: harmful but not extreme. No death or suicide, threats to kill, violence, sexual
  violence, or weapons.
- The options must NOT mention numbers of people, the authority role, moderators, admins, staff,
  police, guards, managers, or streamers, or what anyone else is doing. Do not use digits.
- Each option is a single first-person-neutral action the reader could take (e.g. "Message the
  victim privately to check on them").
"""


def build_base_prompt(scenario_type: str) -> str:
    """Generation prompt for one base story of the given scenario type."""
    return BASE_PROMPT.format(type_description=SCENARIO_TEMPLATES[scenario_type])


def _find_words(text: str, words: List[str]) -> List[str]:
    return sorted({w for w in words if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE)})


def _find_patterns(text: str, patterns: List[str]) -> List[str]:
    return sorted({m.group(0).lower() for p in patterns for m in re.finditer(p, text, re.IGNORECASE)})


def clean_bystander_noun(noun: str) -> str:
    """Strip a leading 'other ' (or 'the other ') so sentences don't read '8 other other viewers'."""
    return re.sub(r"^\s*(the\s+)?other\s+", "", noun, flags=re.IGNORECASE).strip()


def singularize_noun(noun: str) -> Optional[str]:
    """Singular form of a one-word plural noun when that's trivial ('viewers' -> 'viewer'), else None."""
    if " " in noun:
        return None
    lower = noun.lower()
    if lower == "people":
        return noun[:-6] + ("Person" if noun[0].isupper() else "person")
    if lower.endswith(("sses", "shes", "ches", "xes", "zes")):
        return noun[:-2]
    if lower.endswith(("ss", "us", "is", "ies")) or not lower.endswith("s"):
        return None
    return noun[:-1]


def _role_noun(authority_role: str) -> str:
    """'a chat moderator' -> 'chat moderator'."""
    return authority_role.removeprefix("a ").removeprefix("an ")


def validate_base_story(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse and validate an LLM reply. Returns (story, None) if valid, else (None, reason)."""
    try:
        story = json.loads(strip_code_fences(raw_text))
    except json.JSONDecodeError as e:
        return None, f"invalid JSON: {e}"
    if not isinstance(story, dict):
        return None, "reply is not a JSON object"

    missing = [k for k in STORY_KEYS if k not in story]
    if missing:
        return None, f"missing keys: {missing}"
    for k in STORY_KEYS[:-1]:
        if not isinstance(story[k], str) or not story[k].strip():
            return None, f"'{k}' must be a non-empty string"
    options = story["options"]
    if not isinstance(options, dict) or set(options) != set(RESPONSE_TYPES):
        return None, f"options must have exactly the keys {RESPONSE_TYPES}"
    if not all(isinstance(v, str) and v.strip() for v in options.values()):
        return None, "every option must be a non-empty string"

    story = {k: (v.strip() if isinstance(v, str) else v) for k, v in story.items()}
    story["options"] = {k: v.strip() for k, v in options.items()}

    # Normalise the article so the authority sentences read correctly
    role = story["authority_role"]
    if not re.match(r"^(a|an) \S", role, re.IGNORECASE):
        return None, f"authority_role must start with 'a' or 'an': {role!r}"
    story["authority_role"] = role[0].lower() + role[1:]

    story["bystander_noun"] = clean_bystander_noun(story["bystander_noun"])
    if not story["bystander_noun"]:
        return None, "bystander_noun is empty after removing 'other'"

    story_text = " ".join([story["setting"], story["incident_clear"], story["incident_unclear"]])
    bad = _find_words(story_text, FORBIDDEN_STORY_WORDS)
    if bad:
        return None, f"setting/incidents mention extra people or authority: {bad}"
    bad = _find_patterns(story_text, CONCLUSION_PATTERNS)
    if bad:
        return None, f"setting/incidents state conclusions instead of showing them: {bad}"
    bad = _find_patterns(story_text, SEVERITY_PATTERNS)
    if bad:
        return None, f"setting/incidents too severe: {bad}"
    bad = _find_patterns(story["setting"], LARGE_SETTING_PATTERNS)
    if bad:
        return None, f"setting too large for 0-32 other people: {bad}"

    role_noun = _role_noun(story["authority_role"])
    for rtype, text in story["options"].items():
        if re.search(r"\d", text):
            return None, f"option '{rtype}' contains a digit"
        bad = _find_words(text, FORBIDDEN_OPTION_WORDS)
        if bad:
            return None, f"option '{rtype}' mentions authority/staff: {bad}"
        if role_noun.lower() in text.lower():
            return None, f"option '{rtype}' mentions the authority role {role_noun!r}"

    return story, None


def _load_json(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def revalidate_base_stories(output_dir: Path = OUTPUT_DIR) -> List[str]:
    """Re-check saved base stories against the current rules; drop failures so they get regenerated.

    Returns the base_ids that were removed.
    """
    path = Path(output_dir) / BASE_STORIES_FILE
    bases = _load_json(path, [])
    kept, removed = [], []
    for base in bases:
        story, error = validate_base_story(json.dumps(base["story"]))
        if story is None:
            print(f"🗑️  {base['base_id']}: fails current rules ({error}); removing for regeneration")
            removed.append(base["base_id"])
        else:
            kept.append(dict(base, story=story))
    if removed:
        _save_json(path, kept)
    print(f"🔎 Re-validated {len(bases)} saved base stories: {len(kept)} kept, {len(removed)} removed")
    return removed


def generate_base_stories(
    client: Any,
    scenario_types: List[str] = SCENARIO_TYPES,
    n_base_per_type: int = N_BASE_PER_TYPE,
    output_dir: Path = OUTPUT_DIR,
    model: str = MODEL,
    temperature: Optional[float] = TEMPERATURE,
    max_tries: int = MAX_TRIES_PER_BASE,
    **retry_kwargs,
) -> List[Dict[str, Any]]:
    """Step A: one LLM call per base story, validated, saved after each success, resumable."""
    path = Path(output_dir) / BASE_STORIES_FILE
    bases = _load_json(path, [])
    done = {b["base_id"] for b in bases}

    for scenario_type in scenario_types:
        if scenario_type not in SCENARIO_TEMPLATES:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        prompt = build_base_prompt(scenario_type)

        for k in range(n_base_per_type):
            base_id = f"{scenario_type}_b{k}"
            if base_id in done:
                print(f"⏭️  {base_id}: already saved, skipping")
                continue

            for attempt in range(1, max_tries + 1):
                try:
                    raw = generate_with_retry(client, model, prompt, temperature=temperature, **retry_kwargs)
                except Exception as e:
                    print(f"❌ {base_id} attempt {attempt}/{max_tries}: API error: {e}")
                    continue
                story, error = validate_base_story(raw)
                if story is None:
                    print(f"⚠️  {base_id} attempt {attempt}/{max_tries} rejected: {error}")
                    continue
                bases.append({"base_id": base_id, "scenario_type": scenario_type, "story": story})
                done.add(base_id)
                _save_json(path, bases)
                print(f"✅ {base_id}: saved")
                break
            else:
                print(f"❌ {base_id}: no valid story after {max_tries} tries, skipping")

    return bases


def bystander_sentence(n: int, bystander_noun: str, reaction: str) -> str:
    if n == 0:
        return "No one else is aware of what is happening."
    noun = clean_bystander_noun(bystander_noun)
    if n == 1:
        singular = singularize_noun(noun)
        if singular:
            sentence = f"One other {singular} is also watching this happen."
        else:
            sentence = f"One of the {noun} is also watching this happen."
        return sentence + REACTION_SENTENCES_SINGULAR[reaction]
    return f"{n} other {noun} are also watching this happen." + REACTION_SENTENCES[reaction]


def authority_sentence(present: bool, authority_role: str) -> str:
    if present:
        return f"{authority_role[0].upper() + authority_role[1:]} is also present and aware of it, but is not doing anything."
    return f"There is no {_role_noun(authority_role)} or anyone else in charge around."


def shuffle_options(options: Dict[str, str], variant_id: str, seed: int = SEED) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Deterministically shuffle the four typed options into letters A-D for one variant."""
    order = list(RESPONSE_TYPES)
    random.Random(f"{seed}-{variant_id}").shuffle(order)
    letters = ["A", "B", "C", "D"]
    return (
        {letter: options[rtype] for letter, rtype in zip(letters, order)},
        {letter: rtype for letter, rtype in zip(letters, order)},
    )


def build_variants(
    base: Dict[str, Any],
    group_sizes: List[int] = GROUP_SIZES,
    clarity_levels: List[str] = CLARITY_LEVELS,
    authority_options: List[bool] = AUTHORITY_OPTIONS,
    reactions: List[str] = BYSTANDER_REACTIONS,
    seed: int = SEED,
) -> List[Dict[str, Any]]:
    """Step B: build every condition for one base story (no LLM)."""
    story = base["story"]
    variants = []
    for clarity in clarity_levels:
        for authority in authority_options:
            for n in group_sizes:
                # The reaction factor only applies when there are other bystanders
                for reaction in (reactions if n > 0 else [NO_REACTION]):
                    reaction_tag = "na" if reaction == NO_REACTION else reaction
                    variant_id = (
                        f"{base['base_id']}_g{n}_{clarity}_{'auth' if authority else 'noauth'}_{reaction_tag}"
                    )
                    text = " ".join([
                        story["setting"],
                        story[f"incident_{clarity}"],
                        bystander_sentence(n, story["bystander_noun"], reaction),
                        authority_sentence(authority, story["authority_role"]),
                    ])
                    options, option_types = shuffle_options(story["options"], variant_id, seed)
                    variants.append({
                        "id": variant_id,
                        "base_id": base["base_id"],
                        "scenario_type": base["scenario_type"],
                        "group_size": n,
                        "clarity_level": clarity,
                        "authority_present": authority,
                        "bystander_reaction": reaction,
                        "generated_scenario": json.dumps({"scenario": text, "options": options}, ensure_ascii=False),
                        "option_types": option_types,
                    })
    return variants


def build_all_variants(bases: List[Dict[str, Any]], output_dir: Path = OUTPUT_DIR, **kwargs) -> Path:
    """Build variants for every base and save them to matched_scenarios.json."""
    records = [v for base in bases for v in build_variants(base, **kwargs)]
    path = Path(output_dir) / MATCHED_SCENARIOS_FILE
    _save_json(path, records)
    print(f"✅ Saved {len(records)} matched scenarios from {len(bases)} base stories to {path}")
    return path


def main() -> None:
    from dotenv import load_dotenv
    from config import validate_api_key
    from gemini_client import make_client

    load_dotenv()
    client = make_client(validate_api_key("gemini"))

    print(f"🧩 Matched scenarios: types={SCENARIO_TYPES}, {N_BASE_PER_TYPE} base(s)/type, model={MODEL}")
    revalidate_base_stories()
    bases = generate_base_stories(client)
    wanted = {f"{t}_b{k}" for t in SCENARIO_TYPES for k in range(N_BASE_PER_TYPE)}
    bases = [b for b in bases if b["base_id"] in wanted]
    if not bases:
        print("❌ No base stories available; nothing to build.")
        return
    build_all_variants(bases)


if __name__ == "__main__":
    main()
