"""
Verify that build_instruction fills every placeholder for every parameter combination.

Run from the repo root:  python tests/check_instructions.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data_Collection"))

from scenario_templates import (  # noqa: E402
    SCENARIO_TEMPLATES,
    GROUP_SIZES,
    CLARITY_LEVELS,
    AUTHORITY_PRESENT_OPTIONS,
    BYSTANDER_REACTION_OPTIONS,
    build_instruction,
)


def main() -> None:
    count = 0
    for scenario_type in SCENARIO_TEMPLATES:
        for g in [0] + GROUP_SIZES:
            for clarity in CLARITY_LEVELS:
                for authority in AUTHORITY_PRESENT_OPTIONS:
                    for reaction in BYSTANDER_REACTION_OPTIONS:
                        prompt = build_instruction(scenario_type, g, clarity, authority, reaction)
                        ctx = f"{scenario_type}/{g}/{clarity}/{authority}/{reaction}"
                        assert f"group_size ={g} bystanders" in prompt, f"group size missing: {ctx}"
                        assert clarity in prompt, f"clarity missing: {ctx}"
                        assert "{{" not in prompt, f"unescaped braces left: {ctx}"
                        count += 1
    print(f"{count:,} prompts OK")


if __name__ == "__main__":
    main()
