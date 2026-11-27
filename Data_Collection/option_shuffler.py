"""
Option shuffling utilities for preventing LLM pattern recognition
"""

import random
from typing import Dict, Tuple, Any

def shuffle_options_and_create_mapping(options: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Shuffle options and create a mapping to track original positions.
    
    This function takes a dictionary of options (A, B, C, D) and shuffles them
    to prevent LLMs from recognizing patterns in option ordering.
    
    Args:
        options: Dictionary with keys 'A', 'B', 'C', 'D' and their corresponding option texts
        
    Returns:
        tuple: (shuffled_options, option_mapping) where:
            - shuffled_options: New options with shuffled order
            - option_mapping: Maps new position to original position (e.g., {'A': 'C', 'B': 'A', ...})
    """
    # Extract option texts without letter prefixes
    option_texts = []
    original_keys = []
    
    for key in ['A', 'B', 'C', 'D']:
        if key in options:
            # Remove any existing letter prefixes (A., B., C., D.) if present
            text = options[key]
            if text.startswith(f"{key}. "):
                text = text[3:]  # Remove "A. ", "B. ", etc.
            option_texts.append(text)
            original_keys.append(key)
    
    # Shuffle the options
    shuffled_data = list(zip(option_texts, original_keys))
    random.shuffle(shuffled_data)
    
    # Create new shuffled options
    shuffled_options = {}
    option_mapping = {}
    
    new_keys = ['A', 'B', 'C', 'D']
    for new_key, (text, original_key) in zip(new_keys, shuffled_data):
        shuffled_options[new_key] = text
        option_mapping[new_key] = original_key
    
    return shuffled_options, option_mapping

def format_prompt_with_shuffled_options(
    scenario_data: Dict[str, Any], 
    prompt_template: str
) -> Tuple[Dict[str, str], str]:
    """
    Format a prompt with shuffled options to prevent LLM pattern recognition.
    
    This is similar to your format_prompt_4 function but adapted for the current codebase.
    
    Args:
        scenario_data: Dictionary containing scenario data with options
        prompt_template: Template string for the prompt
        
    Returns:
        tuple: (option_mapping, formatted_prompt) where:
            - option_mapping: Maps new position to original position
            - formatted_prompt: The formatted prompt with shuffled options
    """
    # Extract options from scenario data
    options = scenario_data.get('options', {})
    
    # Shuffle options and get mapping
    shuffled_options, option_mapping = shuffle_options_and_create_mapping(options)
    
    # Format the prompt with shuffled options
    formatted_prompt = prompt_template.format(
        story=scenario_data.get('scenario', ''),
        question=scenario_data.get('question', ''),
        choice_a=shuffled_options.get('A', ''),
        choice_b=shuffled_options.get('B', ''),
        choice_c=shuffled_options.get('C', ''),
        choice_d=shuffled_options.get('D', '')
    )
    
    return option_mapping, formatted_prompt

def reverse_option_mapping(option_mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Reverse the option mapping to go from original position to new position.
    
    Args:
        option_mapping: Maps new position to original position
        
    Returns:
        Dict mapping original position to new position
    """
    return {v: k for k, v in option_mapping.items()}

def get_correct_answer_with_mapping(
    original_correct_answer: str, 
    option_mapping: Dict[str, str]
) -> str:
    """
    Get the correct answer in the new shuffled position.
    
    Args:
        original_correct_answer: The correct answer in original position (A, B, C, or D)
        option_mapping: Maps new position to original position
        
    Returns:
        The correct answer in the new shuffled position
    """
    reverse_mapping = reverse_option_mapping(option_mapping)
    return reverse_mapping.get(original_correct_answer, original_correct_answer) 