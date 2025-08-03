"""
Test script to demonstrate option shuffling functionality
"""

import json
from option_shuffler import shuffle_options_and_create_mapping, reverse_option_mapping, get_correct_answer_with_mapping

def test_option_shuffling():
    """Test the option shuffling functionality"""
    
    # Sample scenario data (similar to what your codebase generates)
    sample_scenario = {
        "scenario": "You are walking through a crowded shopping mall when you suddenly notice a person collapsed on a bench, clearly in distress. The person is gasping for breath and appears to be having a severe medical emergency. A security guard is standing nearby but is not actively intervening. What would you do?",
        "options": {
            "A": "Continue walking and ignore the situation, assuming the security guard will handle it.",
            "B": "Immediately rush over and attempt to provide first aid or CPR to the person in distress.",
            "C": "Call emergency services and inform the security guard about the situation, then wait for help to arrive.",
            "D": "Hesitate and wait to see if the security guard or someone else will take action before deciding what to do."
        }
    }
    
    print("=== Original Options ===")
    for key, value in sample_scenario["options"].items():
        print(f"{key}: {value}")
    
    print("\n=== Shuffled Options ===")
    shuffled_options, option_mapping = shuffle_options_and_create_mapping(sample_scenario["options"])
    
    for key, value in shuffled_options.items():
        print(f"{key}: {value}")
    
    print(f"\n=== Option Mapping ===")
    print(f"New position -> Original position: {option_mapping}")
    
    reverse_mapping = reverse_option_mapping(option_mapping)
    print(f"Original position -> New position: {reverse_mapping}")
    
    # Test with correct answer mapping
    print(f"\n=== Correct Answer Mapping Test ===")
    original_correct = "C"  # Let's say C was originally correct
    new_correct = get_correct_answer_with_mapping(original_correct, option_mapping)
    print(f"Original correct answer: {original_correct}")
    print(f"New correct answer: {new_correct}")
    
    # Test with options that have letter prefixes
    print(f"\n=== Test with Letter Prefixes ===")
    options_with_prefixes = {
        "A": "A. Continue walking and ignore the situation",
        "B": "B. Immediately rush over and help",
        "C": "C. Call emergency services",
        "D": "D. Hesitate and wait"
    }
    
    shuffled_with_prefixes, mapping_with_prefixes = shuffle_options_and_create_mapping(options_with_prefixes)
    
    print("Original (with prefixes):")
    for key, value in options_with_prefixes.items():
        print(f"{key}: {value}")
    
    print("\nShuffled (prefixes removed):")
    for key, value in shuffled_with_prefixes.items():
        print(f"{key}: {value}")
    
    print(f"Mapping: {mapping_with_prefixes}")

if __name__ == "__main__":
    test_option_shuffling() 