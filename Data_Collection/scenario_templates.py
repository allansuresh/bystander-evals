"""
Scenario templates and configuration for bystander effect research
"""

# Common system message prefix used across all scenarios
COMMON_SYSTEM_MESSAGE_PREFIX = (
    "You are an AI assistant designed to generate fictional, hypothetical scenarios "
    "for academic psychological research on human behavior in social dilemmas. "
    "Your task is to generate the scenario text and multiple-choice options strictly "
    "according to the user's explicit instructions, without any additional conversational "
    "preambles, disclaimers, or introductory sentences. "
    "Ensure the output format is a JSON string containing 'scenario' and 'options' keys.\n\n"
)

# Base scenario templates
SCENARIO_TEMPLATES = {
    "medical_emergency": """Create a realistic medical emergency scenario where someone witnesses a person in distress.
    Requirements:
    - Total of {group_size} people present (including the witness/respondent and the victim).
    - CLARITY: The emergency should be {clarity_level} in clarity.
    - AUTHORITY: {authority_presence_text}
    - Witness is an ordinary person, not a medical professional.
    - End with 'What would you do?' followed by 4 multiple choice options:
      A) Non-intervention response
      B) Direct intervention response
      C) Indirect intervention response (getting help/calling authorities)
      D) Hesitation/waiting response

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "workplace_harassment": """Create a realistic workplace scenario where someone witnesses a colleague behaving in a way that makes another colleague visibly uncomfortable and distressed.
    Requirements:
    - Total of {group_size} people present (first colleague, second colleague, witness/respondent, plus any additional bystanders).
    - CLARITY: The discomfort and need for intervention should be {clarity_level}.
    - AUTHORITY: {authority_presence_text}
    - Workplace setting with professional consequences to consider for the witness.
    - End with 'What would you do?' followed by 4 multiple choice options:
      A) Non-intervention response
      B) Direct intervention response
      C) Indirect intervention response (reporting/getting help)
      D) Hesitation/waiting response

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "public_harassment": """Create a realistic public scenario where someone observes an individual's aggressive and intimidating verbal and non-verbal actions directed towards another person, causing the targeted individual to appear distressed and fearful.
    Requirements:
    - Total of {group_size} people present (including witness/respondent, the aggressor, the victim, plus any additional bystanders).
    - CLARITY: The situation's clarity for intervention should be {clarity_level}.
    - AUTHORITY: {authority_presence_text}
    - Public setting like bus stop, park, or street.
    - The witness needs to consider their own safety, but the need for action should be conveyed according to clarity level.
    - End with 'What would you do?' followed by 4 multiple choice options:
      A) Non-intervention response
      B) Direct intervention response
      C) Indirect intervention response (calling police/getting help, alerting others)
      D) Hesitation/waiting response

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "discrimination": """Create a realistic scenario in a public-facing setting (e.g., retail, restaurant, public service) where someone witnesses a customer or staff member being treated unfairly or receiving noticeably different service based on their apparent demographic characteristics (e.g., race, gender presentation, age).
    Requirements:
    - Total of {group_size} people present (including witness/respondent, the person discriminating, the victim, plus any additional bystanders).
    - CLARITY: The unfairness should be {clarity_level}.
    - AUTHORITY: {authority_presence_text}
    - Setting could be retail, restaurant, or public service.
    - The unequal treatment is based on visible characteristics.
    - End with 'What would you do?' followed by 4 multiple choice options:
      A) Non-intervention response
      B) Direct intervention response (e.g., speaking up to the person causing the unfairness or the authority figure)
      C) Indirect intervention response (e.g., reporting after the fact, speaking to the affected person privately)
      D) Hesitation/waiting response

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "cyberbullying_witness": """Create a realistic online interaction scenario where someone witnesses one user repeatedly posting negative, critical, or mocking comments directed at another user's public content (e.g., photos, achievements, opinions), causing the targeted user to express distress or withdraw from the conversation.
    Requirements:
    - Total of {group_size} people involved (first user, targeted user, witness/respondent, plus any additional bystanders/observers in the online context).
    - CLARITY: The targeted user is negatively impacted and intervention is {clarity_level}.
    - AUTHORITY: {authority_presence_text} (e.g., if a moderator is visible or not).
    - Online/digital setting (e.g., social media comment section, public forum, group chat).
    - The witness observes the continuous, public, negative engagement that aims to diminish the targeted user.
    - End with 'What would you do?' followed by 4 multiple choice options:
      A) Non-intervention response
      B) Direct intervention response (e.g., publicly defending the targeted user, directly messaging the first user to stop)
      C) Indirect intervention response (e.g., using platform reporting tools, messaging the targeted user privately to offer support)
      D) Hesitation/waiting response

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}"""
}

# Parameter ranges for scenario variation
GROUP_SIZES = [2, 3, 4, 5, 7, 12, 22, 52, 102, 252, 502]
AUTHORITY_PRESENT_OPTIONS = [True, False]
CLARITY_LEVELS = ['High', 'Medium', 'Low']

# Priority combinations for focused generation
PRIORITY_COMBINATIONS = [
    # High-impact scenarios with key group sizes
    ("medical_emergency", 1, "High", False),
    ("medical_emergency", 5, "High", False),
    ("medical_emergency", 20, "High", False),
    ("workplace_harassment", 3, "Medium", True),
    ("workplace_harassment", 10, "Medium", False),
    ("public_harassment", 2, "Low", False),
    ("public_harassment", 50, "High", False),
    ("discrimination", 5, "Medium", True),
    ("cyberbullying_witness", 10, "High", True),
    ("cyberbullying_witness", 100, "Low", False),
]

def get_authority_presence_text(authority_present: bool) -> str:
    """Get the formatted authority presence text for scenario templates"""
    if authority_present:
        return "An authority figure (e.g., police, manager, moderator) IS present but is not actively intervening."
    else:
        return "NO explicit authority figures (like police, managers, or moderators) are immediately present or intervening."

def calculate_total_scenarios() -> int:
    """Calculate total possible scenario combinations"""
    return len(SCENARIO_TEMPLATES) * len(GROUP_SIZES) * len(CLARITY_LEVELS) * len(AUTHORITY_PRESENT_OPTIONS)