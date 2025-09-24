"""
Core scenario generation logic using Distilabel
"""

from typing import List, Dict, Any, Optional, Tuple
from scenario_templates import (
    SCENARIO_TEMPLATES, 
    GROUP_SIZES, 
    CLARITY_LEVELS, 
    AUTHORITY_PRESENT_OPTIONS,
    BYSTANDER_REACTION_OPTIONS,
    PRIORITY_COMBINATIONS,
    COMMON_SYSTEM_MESSAGE_PREFIX,
    get_authority_presence_text,
    get_bystander_reaction_text
)

class ScenarioGenerator:
    """Handles creation of scenario variations for bystander effect research"""
    
    def __init__(self):
        self.scenario_id_counter = 0
    
    def create_base_scenarios(
        self, 
        # limit_scenarios: Optional[int] = None,
        limit_scenarios: Optional[int] = 10,
        priority_combinations: Optional[List[Tuple[str, int, str, bool]]] = None
    ) -> List[Dict[str, Any]]:
        """Create base scenario templates with proper variation parameters
        
        Args:
            limit_scenarios: If set, limits total scenarios generated
            priority_combinations: List of (scenario_type, group_size, clarity, authority) tuples to prioritize
        """
        generated_scenarios = []
        
        # Use priority combinations if specified
        if priority_combinations:
            return self._generate_priority_scenarios(priority_combinations, limit_scenarios)
        
        # Generate all combinations
        return self._generate_all_scenarios(limit_scenarios)
    
    def _generate_priority_scenarios(
        self, 
        priority_combinations: List[Tuple[str, int, str, bool]], 
        limit_scenarios: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Generate scenarios from priority combinations"""
        generated_scenarios = []
        
        for scenario_type, group_size, clarity_level, authority_present in priority_combinations:
            if scenario_type in SCENARIO_TEMPLATES:
                # Generate scenarios for both bystander reaction options
                for bystander_reaction in BYSTANDER_REACTION_OPTIONS:
                    scenario = self._create_single_scenario(
                        scenario_type, group_size, clarity_level, authority_present, bystander_reaction
                    )
                    generated_scenarios.append(scenario)
                    
                    if limit_scenarios and len(generated_scenarios) >= limit_scenarios:
                        break
                
                if limit_scenarios and len(generated_scenarios) >= limit_scenarios:
                    break
        
        print(f"Generated {len(generated_scenarios)} priority scenarios.")
        return generated_scenarios
    
    def _generate_all_scenarios(self, limit_scenarios: Optional[int]) -> List[Dict[str, Any]]:
        """Generate all possible scenario combinations"""
        generated_scenarios = []
        
        for scenario_type in SCENARIO_TEMPLATES.keys():
            for group_size in GROUP_SIZES:
                for clarity_level in CLARITY_LEVELS:
                    for authority_present in AUTHORITY_PRESENT_OPTIONS:
                        for bystander_reaction in BYSTANDER_REACTION_OPTIONS:
                            scenario = self._create_single_scenario(
                                scenario_type, group_size, clarity_level, authority_present, bystander_reaction
                            )
                            generated_scenarios.append(scenario)
                            
                            if limit_scenarios and len(generated_scenarios) >= limit_scenarios:
                                print(f"Reached scenario limit of {limit_scenarios}")
                                return generated_scenarios
        
        print(f"Generated {len(generated_scenarios)} unique scenario variations.")
        return generated_scenarios
    
    def _create_single_scenario(
        self, 
        scenario_type: str, 
        group_size: int, 
        clarity_level: str, 
        authority_present: bool,
        bystander_reaction: str
    ) -> Dict[str, Any]:
        """Create a single scenario configuration"""
        template_instruction = SCENARIO_TEMPLATES[scenario_type]
        authority_presence_text = get_authority_presence_text(authority_present)
        bystander_reaction_text = get_bystander_reaction_text(bystander_reaction)
        
        # Fill in template placeholders
        instruction_filled = template_instruction.format(
            group_size=group_size,
            clarity_level=clarity_level,
            authority_presence_text=authority_presence_text,
            bystander_reaction_text=bystander_reaction_text
        )
        
        # Create unique ID
        scenario_id = f"{scenario_type}_{group_size}p_{clarity_level}clarity_{'auth' if authority_present else 'noauth'}_{bystander_reaction}_{self.scenario_id_counter}"
        self.scenario_id_counter += 1
        
        return {
            "id": scenario_id,
            "scenario_type": scenario_type,
            "group_size": group_size,
            "clarity_level": clarity_level,
            "authority_present": authority_present,
            "bystander_reaction": bystander_reaction,
            "instruction": COMMON_SYSTEM_MESSAGE_PREFIX + instruction_filled
        }