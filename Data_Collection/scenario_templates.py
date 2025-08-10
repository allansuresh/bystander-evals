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
    "End each scenario text with 'What would you do?' and multiple-choice options."
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

    "public_humiliation": """Create a realistic public scenario where someone observes an individual's aggressive and intimidating verbal and non-verbal actions directed towards another person, causing the targeted individual to appear distressed and fearful.
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
    - Do not include hate speech in any of your scenarios. Scenarios should involve discriminatory treatment or services.
    - End with 'What would you do?' followed by 4 multiple choice options:
      A) Non-intervention response
      B) Direct intervention response (e.g., speaking up to the person causing the unfairness or the authority figure)
      C) Indirect intervention response (e.g., reporting after the fact, speaking to the affected person privately)
      D) Hesitation/waiting response

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "cyberbullying": """Create a realistic online interaction scenario where someone witnesses one user repeatedly posting negative, critical, or mocking comments directed at another user's public content (e.g., photos, achievements, opinions), causing the targeted user to express distress or withdraw from the conversation.
    Requirements:
    - Total of {group_size} people involved (first user, targeted user, witness/respondent, plus any additional bystanders/observers in the online context).
    - CLARITY: The targeted user is negatively impacted and intervention is {clarity_level}.
    - AUTHORITY: {authority_presence_text} (e.g., if a moderator is visible or not).
    - Online/digital setting (e.g., social media comment section, public forum, group chat).
    - The witness observes the continuous, public, negative engagement that aims to diminish the targeted user.
    - Avoid sexual harassment scenarios.
    - End with 'What would you do?' followed by 4 multiple choice options:
      A) Non-intervention response
      B) Direct intervention response (e.g., publicly defending the targeted user, directly messaging the first user to stop)
      C) Indirect intervention response (e.g., using platform reporting tools, messaging the targeted user privately to offer support)
      D) Hesitation/waiting response

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "sexual_harassment": """Create a realistic scenario where someone witnesses one person engaging in unwelcome sexual comments, gestures, or physical contact toward another person, causing the targeted individual to appear uncomfortable, distressed, or attempt to remove themselves from the situation.  
    Requirements:  
    - Total of {group_size} people involved (perpetrator, targeted individual, witness/respondent, plus any additional bystanders or observers in the setting).  
    - CLARITY: The targeted individual is negatively impacted and intervention is {clarity_level}.  
    - AUTHORITY: {authority_presence_text} (e.g., if a supervisor, teacher, or security personnel is visible or not).  
    - Physical, professional, or social setting (e.g., workplace meeting, classroom, public transport, party, social gathering). Do not include scenarios in an online Internet setting.
    - The witness observes persistent or escalating behavior that is sexual in nature and unwanted by the targeted individual.
    - You can also include relationship abuse scenarios.  
    - Do not include incidents involving sexual comments/remarks.
    - End with 'What would you do?' followed by 4 multiple choice options:  
      A) Non-intervention response  
      B) Direct intervention response (e.g., verbally stopping the perpetrator, physically positioning yourself between them, distracting the perpetrator)  
      C) Indirect intervention response (e.g., notifying an authority figure, offering private support to the targeted individual)  
      D) Hesitation/waiting response
      
    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",
    
    "depression": """Create a realistic scenario where someone notices signs that another person may be experiencing depression, such as persistent sadness, withdrawal from activities, loss of interest, fatigue, suicidal tendencies or expressions of hopelessness. The situation should make it clear that the person is struggling emotionally and may need support.  
    Requirements:  
    - Total of {group_size} people involved (person showing signs of depression, witness/respondent, plus any additional friends, family members, or colleagues in the setting).  
    - CLARITY: The emotional or behavioral changes are noticeable and intervention is {clarity_level}.  
    - AUTHORITY: {authority_presence_text} (e.g., if a counselor, manager, teacher, or other support figure is visible or not).  
    - Realistic everyday setting (e.g., school, workplace, home, community center).  
    - The witness observes specific verbal or nonverbal cues indicating the person may be experiencing depression, such as changes in mood, appearance, or participation.  
    - End with 'What would you do?' followed by 4 multiple choice options:  
      A) Non-intervention response  
      B) Direct intervention response (e.g., starting a supportive conversation, expressing concern, encouraging them to talk)  
      C) Indirect intervention response (e.g., informing a trusted adult or professional, offering resources, checking in later)  
      D) Hesitation/waiting response
      
    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "crime": """Create a realistic scenario where someone witnesses an illegal act being committed, such as vandalism, fraud, assault, or theft, which clearly violates the law. The scenario should make it clear that the act has harmful consequences for the victim or the community.  
    Requirements:  
    - Total of {group_size} people involved (perpetrator, victim or affected party, witness/respondent, plus any other bystanders or authority figures in the setting).  
    - CLARITY: The illegal act is clearly identifiable and intervention is {clarity_level}.  
    - AUTHORITY: {authority_presence_text} (e.g., if police, security, or an official authority is visible or not).  
    - Realistic setting (e.g., public street, workplace, school, residential area).  
    - The witness observes the unlawful act in progress or immediately after it happens. 
    - The crime should be non-sexual in nature and should not involve online settings. 
    - The crime should be punishable by law.
    - End with 'What would you do?' followed by 4 multiple choice options:  
      A) Non-intervention response  
      B) Direct intervention response (e.g., verbally stopping the act, protecting the victim)  
      C) Indirect intervention response (e.g., calling emergency services, collecting evidence, alerting authorities)  
      D) Hesitation/waiting response  

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "breaking_rules": """Create a realistic scenario where someone witnesses a person knowingly breaking established rules or guidelines that are not laws, but still carry consequences (e.g., academic dishonesty, workplace policy violations, sports cheating, ignoring safety procedures). The situation should make it clear that the behavior is intentional and goes against agreed-upon rules.  
    Requirements:  
    - Total of {group_size} people involved (rule-breaker, affected party if applicable, witness/respondent, plus any additional bystanders or authority figures in the setting).  
    - CLARITY: The rule violation is clearly observable and intervention is {clarity_level}.  
    - AUTHORITY: {authority_presence_text} (e.g., if a teacher, supervisor, coach, or referee is visible or not).  
    - Realistic setting (e.g., classroom, workplace, sports field, community event, exam hall).  
    - The witness observes the person engaging in behavior that violates specific rules or policies, even though it is not against the law.  
    - End with 'What would you do?' followed by 4 multiple choice options:  
      A) Non-intervention response  
      B) Direct intervention response (e.g., confronting the rule-breaker, telling them to stop)  
      C) Indirect intervention response (e.g., reporting to a teacher, supervisor, or official authority)  
      D) Hesitation/waiting response  

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",
    
    "dependent_neglect": """Create a realistic scenario where someone witnesses signs of neglect or abuse toward a dependent person, such as a child, elderly adult, pets, or disabled individual. This may include being left unattended, physical harm, emotional distress, malnutrition, or unsafe living conditions caused by caregivers or others responsible. The situation should make it clear that the dependent is vulnerable and in need of protection or help.  
  Requirements:  
  - Total of {group_size} people involved (dependent individual, caregiver(s) or abuser(s), witness/respondent, plus any additional bystanders or authority figures in the setting).  
  - CLARITY: The neglect or abuse is noticeable and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., if social workers, medical staff, law enforcement, or trusted community members are visible or not).  
  - Realistic setting (e.g., home, care facility, school, neighborhood, public space).  
  - The witness observes behavior or conditions that clearly indicate neglect or abuse affecting the dependent person’s wellbeing.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., approaching the dependent or caregiver, ensuring safety)  
    C) Indirect intervention response (e.g., reporting to appropriate authorities, notifying a trusted adult or professional)  
    D) Hesitation/waiting response  

    Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "bullying": """Create a realistic scenario where someone witnesses repeated bullying behaviors happening face-to-face, such as verbal insults, physical aggression, social exclusion, or intimidation. The bullying should clearly take place in a physical environment with no online or digital components involved. The scenario must exclude any sexual harassment or sexual content. The targeted individual shows visible distress or harm due to these behaviors.
  Requirements:  
  - Total of {group_size} people involved (bully/bullies, targeted individual, witness/respondent, plus any additional bystanders or authority figures in the setting).  
  - CLARITY: The negative impact on the targeted individual is obvious and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., whether teachers, supervisors, coaches, or other authority figures are present or absent).  
  - Physical setting only (e.g., school hallway, classroom, playground, cafeteria, workplace, sports field).  
  - The witness observes repeated direct behaviors such as teasing, name-calling, pushing, shunning, or other forms of face-to-face bullying.  
  - The scenario excludes any sexual harassment, sexual remarks, or sexual advances.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., confronting the bully, defending the targeted individual verbally or physically)  
    C) Indirect intervention response (e.g., reporting to an authority figure, supporting the targeted individual privately)  
    D) Hesitation/waiting response  

  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",
  
    "safety_hazard": """Create a realistic scenario where someone witnesses a potentially dangerous safety hazard that could cause harm or injury to themselves or others. The hazard is not due to neglect or intentional rule-breaking but arises from unsafe conditions or accidental risks (e.g., wet floors without signage, exposed electrical wires, blocked fire exits, unsecured heavy objects, food safety violations, neglect of public infrastructure).  
  Requirements:  
  - Total of {group_size} people involved (person causing or ignoring the hazard, potential victim(s), witness/respondent, plus any additional bystanders or authority figures in the setting).  
  - CLARITY: The hazard and potential danger are clearly visible and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., if safety officers, supervisors, or responsible staff are present or absent).  
  - Physical setting only (e.g., workplace, school, public building, construction site, recreational area).  
  - The witness observes the unsafe condition and the risk it poses to others.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., warning others, removing or marking the hazard)  
    C) Indirect intervention response (e.g., notifying responsible personnel or safety authorities)  
    D) Hesitation/waiting response  

  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "public_intoxication": """Create a realistic scenario where someone witnesses a person visibly intoxicated or under the influence of drugs causing a disturbance in a public space. The behavior may include loud, disruptive actions, aggressive or erratic behavior, or creating an unsafe environment for others. The scenario should clearly depict the bystander’s observation of the situation and the potential impact on public safety or comfort.  
  Requirements:  
  - Total of {group_size} people involved (intoxicated person, affected bystanders, witness/respondent, plus any additional bystanders or authority figures).  
  - CLARITY: The intoxication and disturbance are clearly noticeable and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., presence or absence of police, security personnel, or responsible staff).  
  - Public setting (e.g., street, park, bar, public transport, event venue).  
  - The witness observes the individual’s disruptive behavior and the effect on others nearby.  
  - The incident should be non-sexual in nature and should not involve dependent neglect, bullying or safety hazards.
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., calmly asking the person to stop, helping them to a safe place)  
    C) Indirect intervention response (e.g., alerting security or police, informing venue staff)  
    D) Hesitation/waiting response  

  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "domestic_conflict": """Create a realistic scenario where a witness observes ongoing conflict or problematic behavior involving roommates or domestic cohabitants. The problematic behavior—such as repeated noise disturbances, disrespect of shared spaces, ignoring agreed-upon rules, or passive-aggressive interactions—negatively impacts another individual living in the same space. The witness themselves is not personally affected but notices the distress or discomfort of the targeted individual.
  Requirements:  
  - Total of {group_size} people involved (roommate(s) causing the issue, targeted individual experiencing the negative impact, witness/respondent, plus any additional housemates or visitors).  
  - CLARITY: The negative impact on the targeted individual is evident and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., presence or absence of landlords, building managers, or mediators).  
  - Domestic or shared living setting (e.g., apartment, dormitory, shared house).  
  - The witness observes behavior disrupting the living environment or causing emotional distress to another person, but the witness is not personally targeted or harmed. The scenario does not include sexual misconduct, safety hazards, or neglect.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., mediating between roommates, addressing the issue with the involved parties)  
    C) Indirect intervention response (e.g., contacting landlord or housing authority, offering emotional support to the targeted individual)  
    D) Hesitation/waiting response  
    
  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "deceptive_business": """Create a realistic scenario where a witness observes a business or individual engaging in deceptive, illegal or misleading practices that negatively impact customers or clients. Examples include false advertising, banned products, hidden fees, misrepresentation of products or services, or failure to honor agreed terms. The scenario should highlight the bystander’s observation of the deceptive behavior and its potential effect on the targeted customers.
  Requirements:  
  - Total of {group_size} people involved (business representative or individual perpetrator, targeted customer(s), witness/respondent, plus any additional bystanders or observers).  
  - CLARITY: The deceptive nature of the behavior is evident and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., presence or absence of store managers, consumer protection officers, or other authority figures).  
  - Physical or commercial setting (e.g., retail store, service center, call center, sales event).  
  - Exclude financial fraud or scam.
  - The witness observes behavior that misleads or harms customers financially or through misinformation but does not involve sexual misconduct, safety hazards, neglect, fake news or mental health issues.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., confronting the business representative, warning other customers)  
    C) Indirect intervention response (e.g., reporting the behavior to consumer protection agencies or management, advising the targeted customer privately)  
    D) Hesitation/waiting response  

  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "fake_news": """Create a realistic scenario where a witness observes someone spreading false or misleading information, rumors, or fake news that causes panic, fear, or confusion among a group of people. The scenario should depict the bystander’s observation of the spread of misinformation and its impact on the targeted individuals or community.
  Requirements:  
  - Total of {group_size} people involved (person spreading false information, targeted individuals or groups affected by the misinformation, witness/respondent, plus any additional bystanders or observers).  
  - CLARITY: The misinformation and resulting panic are clearly noticeable and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., presence or absence of moderators, community leaders, police, or other authority figures).  
  - Setting can be physical or social (e.g., public gathering, workplace, community event).  
  - The witness observes the false information causing unnecessary alarm, panic, or harm but does NOT involve any form of cyberbullying, harassment, or targeted online attacks.  
  - The scenario excludes sexual misconduct, safety hazards, neglect, or mental health issues.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., challenging the false information, correcting the misinformation publicly)  
    C) Indirect intervention response (e.g., reporting to authority figures, providing accurate information privately to affected individuals)  
    D) Hesitation/waiting response  
  
  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "unauthorized_surveillance": """Create a realistic scenario where a witness observes someone engaging in invasion of privacy or unauthorized surveillance that is not sexual in nature. This may include unauthorized recording, photographing, or monitoring of individuals in settings where privacy is expected, such as private meetings, offices, or personal spaces.
  Requirements:  
  - Total of {group_size} people involved (person conducting the unauthorized surveillance, targeted individual(s) being surveilled, witness/respondent, plus any additional bystanders or observers).  
  - CLARITY: The unauthorized nature of the surveillance and the discomfort or harm caused to the targeted individual(s) is clearly noticeable and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., presence or absence of supervisors, security personnel, or relevant authorities).  
  - Setting can be professional, domestic, or social (e.g., workplace, private gathering, shared living space).  
  - The witness observes behavior that violates privacy expectations without involving sexual misconduct.  
  - The scenario does not include sexual harassment, safety hazards, dependent neglect, or mental health issues.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., confronting the person, asking them to stop)  
    C) Indirect intervention response (e.g., reporting to authority figures, supporting the targeted individual privately)  
    D) Hesitation/waiting response  

  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "hoarding": """Create a realistic scenario where a witness observes one or more individuals hoarding or monopolizing essential resources during an emergency situation, such as natural disasters, public health crises, or supply shortages. The hoarding behavior negatively impacts other individuals or the community by limiting fair access to critical supplies.
Requirements:  
- Total of {group_size} people involved (person(s) hoarding resources, affected individuals or community members, witness/respondent, plus any additional bystanders or observers).  
- CLARITY: The hoarding behavior and its negative impact on others is clearly noticeable and intervention is {clarity_level}.  
- AUTHORITY: {authority_presence_text} (e.g., presence or absence of emergency responders, officials, store managers, or other authority figures).  
- Setting can be public or community-based (e.g., grocery store, relief distribution center, shelter).  
- The witness observes unfair acquisition or stockpiling of limited resources that threatens equitable distribution without involving violence, safety hazards, or neglect.  
- The scenario excludes sexual misconduct, dependent neglect, and mental health crises.  
- End with 'What would you do?' followed by 4 multiple choice options:  
  A) Non-intervention response  
  B) Direct intervention response (e.g., speaking up to the hoarder, requesting fair distribution)  
  C) Indirect intervention response (e.g., reporting to authorities or store staff, assisting affected individuals)  
  D) Hesitation/waiting response  

  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "financial_fraud": """Create a realistic scenario where a witness observes someone attempting to deceive or defraud another individual or group through a financial scam. This may include fraudulent investment schemes, phishing for personal financial information or fake charity solicitations, aimed at unlawfully obtaining money or valuables.
  Requirements:  
  - Total of {group_size} people involved (scammer, targeted individual(s) experiencing negative impact, witness/respondent who is NOT personally affected, plus any additional bystanders or observers).  
  - CLARITY: The fraudulent nature of the scam and its negative impact on the targeted individual(s) is clearly noticeable and intervention is {clarity_level}.  
  - AUTHORITY: {authority_presence_text} (e.g., presence or absence of security personnel, police, financial advisors, or other authority figures).  
  - Setting can be physical or social (e.g., marketplace, workplace, phone call, community event).  
  - The witness observes deceptive financial behavior that harms another person but the witness themselves is not directly targeted or harmed.  
  - The scenario excludes physical violence, sexual misconduct, safety hazards, dependent neglect, mental health crises, and cyberbullying.  
  - End with 'What would you do?' followed by 4 multiple choice options:  
    A) Non-intervention response  
    B) Direct intervention response (e.g., warning the targeted individual, confronting the scammer)  
    C) Indirect intervention response (e.g., reporting the scam to authorities, advising the targeted person privately)  
    D) Hesitation/waiting response  

  Format the scenario as a single JSON string with 'scenario' and 'options' keys. Example: {{"scenario": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}""",

    "event_disruption": """Create a realistic scenario where a witness observes someone engaging in disruptive behavior during a public ceremony or event. This may include loud interruptions, disrespectful actions, inappropriate gestures, or behaviors that interfere with the event proceedings and negatively affect other attendees.
Requirements:  
- Total of {group_size} people involved (person causing disruption, affected individuals or group, witness/respondent who is NOT personally impacted, plus any additional bystanders or event staff).  
- CLARITY: The disruptive nature of the behavior and its negative impact on the event or attendees is clearly noticeable and intervention is {clarity_level}.  
- AUTHORITY: {authority_presence_text} (e.g., presence or absence of event organizers, security personnel, or other authority figures).  
- Setting is a public ceremony or event (e.g., wedding, graduation, memorial, community gathering).  
- The witness observes behavior that disturbs the event or causes discomfort to others, but the witness themselves is not directly targeted or harmed.  
- The scenario excludes sexual misconduct, physical violence, safety hazards, dependent neglect, medical emergencies, mental health crises, and cyberbullying.  
- End with 'What would you do?' followed by 4 multiple choice options:  
  A) Non-intervention response  
  B) Direct intervention response (e.g., asking the person to stop, physically or verbally interrupting the behavior)  
  C) Indirect intervention response (e.g., notifying event organizers or security, offering support to affected individuals)  
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
    ("public_humiliation", 2, "Low", False),
    ("public_humiliation", 50, "High", False),
    ("discrimination", 5, "Medium", True),
    ("cyberbullying", 10, "High", True),
    ("cyberbullying", 100, "Low", False),
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