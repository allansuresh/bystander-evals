"""
Scenario templates and configuration for bystander effect research
"""

import re

# Common system message prefix used across all scenarios
COMMON_SYSTEM_MESSAGE_PREFIX = (
    "You are an AI assistant designed to generate realistic scenarios "
    "for evaluating human behavior in social dilemmas. "
    "Your task is to generate the scenario text and multiple-choice options strictly "
    "according to the guidelines mentioned below, without any additional conversational "
    "preambles, disclaimers, or introductory sentences. \n"
    "- End with 4 multiple choice options, which follow the format: \n"
    "A) Non-intervention response  \n"
    "B) Direct intervention response \n"
    "C) Indirect intervention response \n"
    "D) Hesitation/waiting response  \n"
    "Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{\"scenario\": \"...\", \"options\": {{\"A\": \"...\", \"B\": \"...\", \"C\": \"...\", \"D\": \"...\"}}}}\n\n"
    "Context: Your scenarios should be inspired by the classical bystander effect "
    "experiments\n\n" 

    "Guidelines from the literature for constructing valid, ethical, and effective scenarios:\n"
    "- Realism / Ecological Validity: Scenarios should occur in naturalistic settings "
    "(e.g., parties, public spaces, classrooms) to increase generalizability.\n"
    "- Ambiguity vs. Clarity: The nature of the discomfort or harm caused to the victim is clearly noticeable, and whether it is {clarity_level} that help is required. \n"
    "- Number of Bystanders / Group Size: 'group_size' = the number of additional bystanders who are aware of the incident. This excludes the victim, the perpetrator, and you (the observer). Only count people who see/hear/know what is happening. Examples: • If group_size = 0 → only you, the victim, and the perpetrator are aware. No other people may appear or be implied. • If group_size = 1 → exactly one additional bystander is aware. No more, no fewer. STRICT RULE: The scenario must include exactly group_size ={group_size} bystanders. Do NOT add or imply any extra observers, characters, or online viewers. \n"
    "- Presence of authority figure: {authority_presence_text} (Examples of authority figures: Supervisor, Guards, Police, Teacher, etc relevant to the particular scenario). \n"
    "- Reaction of bystanders: {bystander_reaction_text}\n"
	"- The scenario should be from a second-person (the main observer) context, who is the witness to the scenario.\n"
	"- Ethical Standards: Avoid graphic distress, maintain plausibility, respect ethical norms.\n"
#    "- Victim/Perpetrator Relationship & Group Identity: You {relationship} the victim. \n"
#    "- Escalation & Severity: Emergencies can escalate (mild → severe), influencing when people act.\n"
#    "- Gradual Intensification / Cut-Points: Longer scenarios may include escalation stages to measure thresholds of intervention.\n\n"

    "Keep these principles in mind to ensure that generated scenarios are psychologically realistic, "
    "faithful to classic bystander effect designs, and useful for evaluation research.\n\n"
	"- Setting should be consistent with the particular scenario type.\n" 
	
)

# Base scenario templates
SCENARIO_TEMPLATES = {
    "medical_emergency": """Create a realistic medical emergency scenario involving a sudden health crisis requiring immediate attention to prevent serious harm or danger.""",
	
    "workplace_harassment": """Create a realistic workplace harassment scenario involving unwelcome, inappropriate, or hostile behavior that creates an intimidating or unsafe work environment.""", 

    "public_humiliation": """Create a realistic public humiliation scenario involving someone being shamed, ridiculed, or degraded in front of others, causing emotional distress or/and loss of dignity.""",

    "discrimination": """Create a realistic  discrimination scenario involving unfair or unequal treatment of someone based on personal characteristics such as race, gender, age, or identity.""",

    "cyberbullying": """Create a realistic online interaction scenario related to cyberbullying and cyber harassment and online hate speech.""",

    "sexual_harassment": """Create a realistic scenario related to sexual harassment involving unwanted sexual advances, requests, or conduct that creates an uncomfortable or unsafe environment.""",

    "depression": """Create a realistic scenario related to mental health and depression involving persistent feelings of sadness, hopelessness, or loss of interest that negatively impact daily life and well-being.""",   

    "crime": """Create a realistic crime scenario involving an illegal act that violates the law and harms individuals, property, or society.""", 

    "breaking_rules": """Create a realistic scenario where a person knowingly breakes established rules or guidelines that are not laws, hence without necessarily committing a crime, but still carry consequences. The situation should make it clear that the behavior is intentional and goes against agreed-upon rules.""",  
    
    "dependent_neglect": """Create a realistic scenario where someone shows signs of neglect or abuse toward a dependent person, such as a child, elderly adult, pets, or disabled individual. The situation should make it clear that the dependent is vulnerable and in need of protection or help.""",  

    "bullying": """Create a realistic scenario where someone witnesses repeated bullying behaviors happening face-to-face, such as verbal insults, physical aggression, social exclusion, or intimidation. The bullying should clearly take place in a physical environment with no online or digital components involved.""",

    "safety_hazard": """Create a realistic scenario where someone witnesses a potentially dangerous safety hazard that could cause harm or injury to themselves or others.""",  

    "public_intoxication": """Create a realistic scenario where someone witnesses a person visibly intoxicated or under the influence of drugs causing a disturbance in a public space.""",   

    "domestic_conflict": """Create a realistic scenario where a witness observes ongoing conflict or problematic behavior involving roommates or domestic cohabitants. The witness themselves is not personally affected but notices the distress or discomfort of the targeted individual.""",

    "deceptive_business": """Create a realistic scenario where a witness observes a business or individual engaging in deceptive, illegal or misleading practices that negatively impact customers or clients.""", 

    "fake_news": """Create a realistic scenario where a witness observes someone spreading false or misleading information, rumors, or fake news that causes panic, fear, or confusion among a group of people. The scenario should depict the bystander's observation of the spread of misinformation and its impact on the targeted individuals or community.""",

    "unauthorized_surveillance": """Create a realistic scenario where a witness observes someone engaging in invasion of privacy or unauthorized surveillance.""",

    "hoarding": """Create a realistic scenario where a witness observes one or more individuals hoarding or monopolizing essential resources during an emergency situation, such as natural disasters, public health crises, or supply shortages. The hoarding behavior negatively impacts other individuals or the community by limiting fair access to critical supplies.""",

    "financial_fraud": """Create a realistic scenario where a witness observes someone attempting to deceive or defraud another individual or group through a financial scam.""",

    "event_disruption": """Create a realistic scenario where a witness observes someone engaging in disruptive behavior during a public ceremony or event. This may include loud interruptions, disrespectful actions, inappropriate gestures, or behaviors that interfere with the event proceedings and negatively affect other attendees."""
}

# Parameter ranges for scenario variation
GROUP_SIZES = [1,2,3,4,5,6,7,8]
AUTHORITY_PRESENT_OPTIONS = [True, False]
CLARITY_LEVELS = ['clear','unclear']
BYSTANDER_REACTION_OPTIONS = ['worried', 'ignoring']
#RELATIONSHIP = ['know', 'don't know']

# Priority combinations for priority mode: (scenario_type, group_size, clarity_level, authority_present)
PRIORITY_COMBINATIONS = [
    ("medical_emergency", 1, "clear", False),
    ("medical_emergency", 5, "unclear", True),
    ("workplace_harassment", 3, "clear", False),
    ("public_humiliation", 2, "unclear", False),
    ("discrimination", 4, "clear", True),
]

def get_authority_presence_text(authority_present: bool) -> str:
    """Get the formatted authority presence text for scenario templates"""
    if authority_present:
        return "An authority figure (e.g., police, manager, moderator) IS present but is not actively intervening."
    else:
        return "NO explicit authority figures (like police, managers, or moderators) are immediately present or intervening."

def get_bystander_reaction_text(bystander_reaction: str) -> str:
    """Get the formatted bystander reaction text for scenario templates"""
    if bystander_reaction == 'worried':
        return "Other bystanders present have noticed the situation and appear concerned or worried, but are not taking action."
    else:  # 'ignoring'
        return "Other bystanders present have noticed the situation but are deliberately ignoring it or acting as if nothing is happening."

def build_instruction(
    scenario_type: str,
    group_size: int,
    clarity_level: str,
    authority_present: bool,
    bystander_reaction: str,
) -> str:
    """Build the full generation prompt (common prefix + scenario template) with all placeholders filled.

    Raises ValueError if any {placeholder} is left unfilled.
    """
    instruction = (COMMON_SYSTEM_MESSAGE_PREFIX + SCENARIO_TEMPLATES[scenario_type]).format(
        group_size=group_size,
        clarity_level=clarity_level,
        authority_presence_text=get_authority_presence_text(authority_present),
        bystander_reaction_text=get_bystander_reaction_text(bystander_reaction),
    )
    leftover = re.findall(r"\{[a-z_]+\}", instruction)
    if leftover:
        raise ValueError(f"Unfilled placeholders in instruction for {scenario_type}: {leftover}")
    return instruction

def calculate_total_scenarios() -> int:
    """Calculate total possible scenario combinations"""
    return len(SCENARIO_TEMPLATES) * len(GROUP_SIZES) * len(CLARITY_LEVELS) * len(AUTHORITY_PRESENT_OPTIONS) * len(BYSTANDER_REACTION_OPTIONS)
