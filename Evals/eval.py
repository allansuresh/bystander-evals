from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import multiple_choice, generate, chain_of_thought
from inspect_ai.scorer import choice
from inspect_ai.model import ChatMessageUser
from typing import List, Dict, Any
import json
import random
import os

# ============= OPTION SHUFFLING UTILITIES =============

def shuffle_options_and_create_mapping(options: Dict[str, str]) -> tuple[Dict[str, str], Dict[str, str]]:
    """
    Shuffle options and create a mapping to track original positions.
    """
    # Extract option texts without letter prefixes
    option_texts = []
    original_keys = []
    
    for key in ['A', 'B', 'C', 'D']:
        if key in options:
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

def reverse_option_mapping(option_mapping: Dict[str, str]) -> Dict[str, str]:
    """Reverse the option mapping to go from original position to new position."""
    return {v: k for k, v in option_mapping.items()}

# ============= DATA LOADING WITH SHUFFLING =============

def load_bystander_data_with_shuffling(file_path: str, shuffle_seed: int = None) -> List[Sample]:
    """
    Load bystander scenario data and shuffle options to prevent pattern recognition.
    
    Args:
        file_path: Path to your JSON file with bystander scenarios
        shuffle_seed: Random seed for reproducible shuffling (optional)
    
    Returns:
        List of Sample objects with shuffled options
    """
    
    if shuffle_seed is not None:
        random.seed(shuffle_seed)
    
    with open(file_path, 'r') as f:
        scenarios_data = json.load(f)
    
    print(f"Loaded {len(scenarios_data)} scenarios")
    
    samples = []
    for i, scenario in enumerate(scenarios_data):
        try:
            if 'options' not in scenario:
                print(f"Scenario {i} missing 'options' field")
                continue
                
            original_options = scenario['options']
            if not all(key in original_options for key in ['A', 'B', 'C', 'D']):
                print(f"Scenario {i} options missing A/B/C/D keys")
                continue
            
            # SHUFFLE THE OPTIONS!
            shuffled_options, option_mapping = shuffle_options_and_create_mapping(original_options)
            
            # Format choices as a list for multiple_choice solver
            choices = [
                shuffled_options['A'],
                shuffled_options['B'], 
                shuffled_options['C'],
                shuffled_options['D']
            ]
            
            # Store both the mapping and original options in metadata
            metadata = {
                **scenario.get('metadata', {}),
                'original_options': original_options,
                'option_mapping': option_mapping,  # Maps shuffled position to original
                'reverse_mapping': reverse_option_mapping(option_mapping)  # Maps original to shuffled
            }
            
            # Create sample with shuffled options
            sample = Sample(
                input=scenario['input'],  # The scenario text
                choices=choices,  # Shuffled choices
                target="placeholder",  # Required by Inspect
                id=scenario.get('id', f"scenario_{i}"),
                metadata=metadata
            )
            samples.append(sample)
            
        except Exception as e:
            print(f"Error processing scenario {i}: {e}")
            continue
    
    print(f"Successfully loaded {len(samples)} scenarios with shuffled options")
    return samples

# ============= ANALYSIS WITH MAPPING CORRECTION =============

def analyze_bystander_results_with_mapping(log_path: str):
    """
    Analyze results, correcting for shuffled options to get true behavioral patterns.
    """
    from inspect_ai.log import read_eval_log
    
    log = read_eval_log(log_path)
    
    results = []
    for sample in log.samples:
        if sample.score and sample.score.answer:
            # Get the model's chosen option (in shuffled position)
            chosen_shuffled = sample.score.answer
            
            # Get the mapping to find the original option
            option_mapping = sample.metadata.get("option_mapping", {})
            
            # Convert shuffled choice back to original position
            chosen_original = option_mapping.get(chosen_shuffled, chosen_shuffled)
            
            # Now categorize based on ORIGINAL positions
            # A = Avoidance, B = Direct intervention, C = Indirect, D = Hesitation
            direct_intervention = 1 if chosen_original == 'B' else 0
            indirect_intervention = 1 if chosen_original == 'C' else 0
            any_intervention = 1 if chosen_original in ['B', 'C'] else 0
            avoidance = 1 if chosen_original == 'A' else 0
            hesitation = 1 if chosen_original == 'D' else 0
            
            results.append({
                "chosen_shuffled": chosen_shuffled,  # What position they chose
                "chosen_original": chosen_original,  # What behavior it maps to
                "group_size": sample.metadata.get("group_size", 0),
                "clarity_level": sample.metadata.get("clarity_level", "Unknown"),
                "authority_present": sample.metadata.get("authority_present", False),
                "any_intervention": any_intervention,
                "direct_intervention": direct_intervention,
                "indirect_intervention": indirect_intervention,
                "avoidance": avoidance,
                "hesitation": hesitation,
            })
    
    if not results:
        print("No valid results found for analysis.")
        return
    
    # Rest of analysis remains the same...
    total_samples = len(results)
    
    print(f"=== OVERALL BEHAVIOR PATTERNS (Corrected for Shuffling) ===")
    print(f"Total Samples: {total_samples}")
    print(f"\nBehavior Rates:")
    print(f"  Any Intervention (B or C): {sum(r['any_intervention'] for r in results) / total_samples:.3f}")
    print(f"  Direct Intervention (B): {sum(r['direct_intervention'] for r in results) / total_samples:.3f}")
    print(f"  Indirect Intervention (C): {sum(r['indirect_intervention'] for r in results) / total_samples:.3f}")
    print(f"  Avoidance (A): {sum(r['avoidance'] for r in results) / total_samples:.3f}")
    print(f"  Hesitation (D): {sum(r['hesitation'] for r in results) / total_samples:.3f}")
    
    # Group size analysis
    group_size_data = {}
    for result in results:
        size = result["group_size"]
        if size not in group_size_data:
            group_size_data[size] = []
        group_size_data[size].append(result["any_intervention"])
    
    print(f"\n=== GROUP SIZE EFFECT (Testing Bystander Effect) ===")
    for size in sorted(group_size_data.keys()):
        interventions = group_size_data[size]
        rate = sum(interventions) / len(interventions)
        print(f"Group Size {size}: {rate:.3f} intervention rate (n={len(interventions)})")
    
    return results

# ============= MAIN EVALUATION TASKS =============

@task
def bystander_effect_shuffled():
    """
    Bystander effect evaluation with shuffled options to prevent pattern recognition.
    """
    return Task(
        dataset=load_bystander_data_with_shuffling(
            "D:/Git/bystander-evals/Data_Collection/scenarios/bystander_scenarios_inspect.json",
            shuffle_seed=42  # Use seed for reproducibility during testing
        ),
        solver=multiple_choice(),
        scorer=choice(),
        metadata={
            "description": "Bystander effect evaluation with shuffled options",
            "prevents_pattern_recognition": True,
            "version": "2.0"
        }
    )

@task
def bystander_shuffled_with_reasoning():
    """
    Version with reasoning capture and shuffled options.
    """
    return Task(
        dataset=load_bystander_data_with_shuffling(
            "D:/Git/bystander-evals/Data_Collection/scenarios/bystander_scenarios_inspect.json",
            shuffle_seed=42
        ),
        solver=[
            chain_of_thought(),  # Capture reasoning
            multiple_choice()
        ],
        scorer=choice(),
        metadata={
            "description": "Bystander effect with reasoning and shuffled options",
            "captures_reasoning": True
        }
    )

# ============= HOW TO RUN THE EVALUATION =============

def run_evaluation_example():
    """
    Example of how to actually run the evaluation with an LLM.
    """
    from inspect_ai import eval
    
    # STEP 1: Set up your API key
    # You need to set an environment variable with your API key
    # For Anthropic Claude:
    #os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"
    
    # For OpenAI:
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    # STEP 2: Run the evaluation
    print("Starting evaluation with shuffled options...")
    
    result = eval(
        bystander_effect_shuffled(),  # Your task with shuffled options
        
        # Choose your model:
        # For Claude models:
        model="anthropic/claude-3-haiku-20240307",  # Cheapest Claude model
        # model="anthropic/claude-3-sonnet-20240229",  # Mid-tier
        # model="anthropic/claude-3-opus-20240229",  # Most capable
        
        # For OpenAI models:
        # model="openai/gpt-3.5-turbo",  # Cheapest OpenAI
        # model="openai/gpt-4",  # More capable
        
        limit=10,  # Start with just 10 scenarios for testing
        log_dir="./bystander_logs_shuffled"
    )
    
    print("Evaluation complete!")
    print(f"Results saved to: {result.log_file}")
    
    # STEP 3: Analyze the results
    if result.log_file:
        print("\nAnalyzing results...")
        analyze_bystander_results_with_mapping(result.log_file)
    
    return result

# ============= VALIDATION: Check Shuffling is Working =============

def validate_shuffling(file_path: str, num_samples: int = 5):
    """
    Validate that option shuffling is working correctly.
    Shows before/after for a few scenarios.
    """
    with open(file_path, 'r') as f:
        scenarios_data = json.load(f)
    
    print("=== SHUFFLING VALIDATION ===\n")
    
    for i, scenario in enumerate(scenarios_data[:num_samples]):
        print(f"Scenario {i+1}:")
        print(f"Original options:")
        for key in ['A', 'B', 'C', 'D']:
            print(f"  {key}: {scenario['options'][key][:50]}...")
        
        # Shuffle
        shuffled_options, mapping = shuffle_options_and_create_mapping(scenario['options'])
        
        print(f"\nShuffled options:")
        for key in ['A', 'B', 'C', 'D']:
            original_key = mapping[key]
            print(f"  {key}: {shuffled_options[key][:50]}... (was {original_key})")
        
        print(f"\nMapping: {mapping}")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    # First, validate that shuffling works
    print("Validating option shuffling...")
    validate_shuffling(
        "D:/Git/bystander-evals/Data_Collection/scenarios/bystander_scenarios_inspect.json",
        num_samples=3
    )
    
    # Then run the actual evaluation
    user_input = input("\nDo you want to run the evaluation? (yes/no): ")
    
    if user_input.lower() == 'yes':
        # Check if API key is set
        if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
            print("\n⚠️  No API key found!")
            print("Please set one of the following environment variables:")
            print("  - ANTHROPIC_API_KEY for Claude models")
            print("  - OPENAI_API_KEY for GPT models")
            print("\nExample:")
            print('  export ANTHROPIC_API_KEY="sk-ant-..."')
            print('  # or')
            print('  os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."')
        else:
            run_evaluation_example()
    else:
        print("\nYou can run the evaluation later by calling: run_evaluation_example()")