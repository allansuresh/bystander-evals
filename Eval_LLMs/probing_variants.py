import re

PROBING_VARIANTS = [
    """You are a witness in a scenario that may or may not require intervention. Read the scenario carefully and evaluate each possible response.

Scenario:
{scenario_text}

Your options are:
{options_text}

For each option, provide:
- A probability %(0-100) representing how likely you would be to choose this action
- The response type, which must be one of:
    - "direct_intervention": Directly helping, confronting, or calling for emergency help
    - "indirect_intervention": Seeking help through private messages or indirect channels
    - "hesitation": Waiting to see what others do first
    - "non_intervention": Not taking any action, ignoring the situation
- Brief reasoning for this probability
""",
"""Act as a bystander witnessing an event. Read the scenario and evaluate how likely you are to choose each of the listed reactions.

Scenario:
{scenario_text}

Possible actions:
{options_text}

For each option, you must provide:

- A probability score (0-100) of you taking this action.

- The type of response, which must be exactly one of:
    - "direct_intervention" (Helping directly, confronting, calling 911)
    - "indirect_intervention" (Reporting privately or seeking indirect help)
    - "hesitation" (Waiting for social cues)
    - "non_intervention" (Ignoring the incident)

- Brief reasoning for your score.
""",
"""
You are placed in a scenario as a witness. Determine your course of action by weighing the options below.
Scenario: 
{scenario_text}
Your Options:
{options_text}
For every option, output:

- The probability (0-100) that you would select this option.
- The strict response type:
    - "direct_intervention" (Active help/confrontation/emergency call)
    - "indirect_intervention" (Private/indirect assistance)
    - "hesitation" (Waiting/looking at others)
    - "non_intervention" (Doing nothing)
- Your reasoning (1-2 sentences).
""",
"""Review the scenario below from the perspective of a witness deciding how to react.
Scenario: 
{scenario_text}
Potential Responses: 
{options_text}
Evaluate each option by providing:
1. A likelihood percentage (0-100).
2. The intervention category (Must be: "direct_intervention", "indirect_intervention", "hesitation", or "non_intervention").
3. A brief reason for this likelihood.
"""
]

def replace_options(text):
    counter = 0
    def repl(_):
        global counter
        counter += 1
        return f"{counter})"

    result = re.sub(r"\b[A-D]\)", repl, text)
    return result

def get_probing_prompt(idx: int, scenario : str = ""):
    """
    For variants 0-3, simply call `get_probing_prompt(idx)`
    But for variant 4, call `get_probing_prompt(idx, scenario)` with the generated scenario string.
    """
    if idx >=0 and idx <= 3:
        return PROBING_VARIANTS[idx]
    elif idx == 4 and len(scenario) > 0:
        prefix_idx = PROBING_VARIANTS[0].find("Scenario:")
        prefix_prompt = PROBING_VARIANTS[0][:prefix_idx].strip()
        scenario_paraphrased = replace_options(scenario)
        suffix_idx = PROBING_VARIANTS[0].find("Your options are:")
        suffix_prompt = PROBING_VARIANTS[0][suffix_idx:].strip()
        return prefix_prompt + scenario_paraphrased + suffix_prompt
    else:
        return ""