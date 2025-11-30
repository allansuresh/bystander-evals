"""
Custom Scenario Generator - Generate scenarios for a specific scenario type with full control

This script allows you to generate scenarios for a single scenario type with complete control
over all parameters. Simply modify the CONFIGURATION section below and run the script.

Usage:
    1. Set your API key: $env:GOOGLE_API_KEY="your-api-key"
    2. Modify the CONFIGURATION section below
    3. Run: python generate_custom_scenarios.py
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import required modules
from scenario_templates import (
    SCENARIO_TEMPLATES,
    GROUP_SIZES,
    CLARITY_LEVELS,
    AUTHORITY_PRESENT_OPTIONS,
    BYSTANDER_REACTION_OPTIONS,
    COMMON_SYSTEM_MESSAGE_PREFIX,
    get_authority_presence_text,
    get_bystander_reaction_text
)
from pipeline_runner_gemini import PipelineRunnerGemini
from output_processor import OutputProcessor
from config import validate_api_key

# ============================================================================
# CONFIGURATION - MODIFY THESE VALUES TO CUSTOMIZE YOUR GENERATION
# ============================================================================

# Scenario Type Selection
SCENARIO_TYPE = "cyberbullying"  # Choose from: medical_emergency, workplace_harassment, 
                                      # public_humiliation, discrimination, cyberbullying,
                                      # sexual_harassment, depression, crime, breaking_rules,
                                      # dependent_neglect, bullying, safety_hazard,
                                      # public_intoxication, domestic_conflict,
                                      # deceptive_business, fake_news, unauthorized_surveillance,
                                      # hoarding, financial_fraud, event_disruption

# Number of Datapoints
LIMIT_SCENARIOS = None  # Set to None for all combinations, or an integer (e.g., 20, 50, 64)
                        # Max for single type: 64 (8 group sizes × 2 clarity × 2 authority × 2 reactions)

# Group Sizes Filter
GROUP_SIZES_FILTER = [0]  # None = use all [1,2,3,4,5,6,7,8]
                           # Or specify: [1, 2, 3] for only those sizes
                           # Or specify: [5, 6, 7, 8] for larger groups only

# Clarity Levels Filter
CLARITY_LEVELS_FILTER = None  # None = use all ['clear', 'unclear']
                              # Or specify: ['clear'] for only clear scenarios
                              # Or specify: ['unclear'] for only unclear scenarios

# Authority Presence Filter
AUTHORITY_OPTIONS_FILTER = None  # None = use all [True, False]
                                  # Or specify: [True] for only scenarios with authority
                                  # Or specify: [False] for only scenarios without authority

# Bystander Reactions Filter
BYSTANDER_REACTIONS_FILTER = None  # None = use all ['worried', 'ignoring']
                                    # Or specify: ['worried'] for only worried bystanders
                                    # Or specify: ['ignoring'] for only ignoring bystanders

# Generation Parameters
BATCH_SIZE = 8  # Number of scenarios processed per batch (1-20 recommended)
TEMPERATURE = 0.8  # Generation temperature: 0.0 (deterministic) to 1.0 (creative)
MAX_TOKENS = 1200  # Maximum tokens per generated scenario
MODEL = "gemini-2.5-flash"  # Options: gemini-2.5-flash, gemini-1.5-flash, gemini-1.5-pro
BATCH_DELAY_SECONDS = 10  # Seconds to wait between batches (to avoid rate limits)

# Provider Selection
PROVIDER = "gemini"  # "gemini" or "claude" (Note: This script is optimized for Gemini)

# ============================================================================
# END OF CONFIGURATION
# ============================================================================


def validate_scenario_type(scenario_type: str) -> None:
    """Validate that the scenario type exists"""
    if scenario_type not in SCENARIO_TEMPLATES:
        available = ", ".join(SCENARIO_TEMPLATES.keys())
        raise ValueError(
            f"❌ Invalid scenario type: '{scenario_type}'\n"
            f"Available types: {available}"
        )


def calculate_max_scenarios(
    group_sizes: list,
    clarity_levels: list,
    authority_options: list,
    bystander_reactions: list
) -> int:
    """Calculate maximum possible scenarios with given filters"""
    return len(group_sizes) * len(clarity_levels) * len(authority_options) * len(bystander_reactions)


def generate_custom_scenarios():
    """Main function to generate scenarios with custom configuration"""
    
    print("=" * 70)
    print("Custom Scenario Generator")
    print("=" * 70)
    
    # Validate scenario type
    validate_scenario_type(SCENARIO_TYPE)
    print(f"✅ Scenario type: {SCENARIO_TYPE}")
    
    # Apply filters or use defaults
    group_sizes = GROUP_SIZES_FILTER if GROUP_SIZES_FILTER is not None else GROUP_SIZES
    clarity_levels = CLARITY_LEVELS_FILTER if CLARITY_LEVELS_FILTER is not None else CLARITY_LEVELS
    authority_options = AUTHORITY_OPTIONS_FILTER if AUTHORITY_OPTIONS_FILTER is not None else AUTHORITY_PRESENT_OPTIONS
    bystander_reactions = BYSTANDER_REACTIONS_FILTER if BYSTANDER_REACTIONS_FILTER is not None else BYSTANDER_REACTION_OPTIONS
    
    # Calculate maximum scenarios
    max_scenarios = calculate_max_scenarios(group_sizes, clarity_levels, authority_options, bystander_reactions)
    
    print(f"\n📊 Configuration Summary:")
    print(f"   Scenario Type: {SCENARIO_TYPE}")
    print(f"   Group Sizes: {group_sizes}")
    print(f"   Clarity Levels: {clarity_levels}")
    print(f"   Authority Options: {authority_options}")
    print(f"   Bystander Reactions: {bystander_reactions}")
    print(f"   Maximum Possible Scenarios: {max_scenarios}")
    print(f"   Limit Scenarios: {LIMIT_SCENARIOS if LIMIT_SCENARIOS else 'None (all combinations)'}")
    print(f"   Batch Size: {BATCH_SIZE}")
    print(f"   Temperature: {TEMPERATURE}")
    print(f"   Max Tokens: {MAX_TOKENS}")
    print(f"   Model: {MODEL}")
    print(f"   Provider: {PROVIDER}")
    
    # Validate limit
    if LIMIT_SCENARIOS is not None and LIMIT_SCENARIOS > max_scenarios:
        print(f"\n⚠️  Warning: LIMIT_SCENARIOS ({LIMIT_SCENARIOS}) exceeds maximum possible ({max_scenarios})")
        print(f"   Will generate {max_scenarios} scenarios (all combinations)")
        actual_limit = max_scenarios
    else:
        actual_limit = LIMIT_SCENARIOS
    
    # Generate scenario configurations
    print(f"\n🔨 Generating scenario configurations...")
    scenarios = []
    scenario_id_counter = 0
    
    for group_size in group_sizes:
        for clarity_level in clarity_levels:
            for authority_present in authority_options:
                for bystander_reaction in bystander_reactions:
                    # Create scenario configuration
                    template_instruction = SCENARIO_TEMPLATES[SCENARIO_TYPE]
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
                    scenario_id = (
                        f"{SCENARIO_TYPE}_{group_size}p_{clarity_level}clarity_"
                        f"{'auth' if authority_present else 'noauth'}_{bystander_reaction}_{scenario_id_counter}"
                    )
                    scenario_id_counter += 1
                    
                    scenarios.append({
                        "id": scenario_id,
                        "scenario_type": SCENARIO_TYPE,
                        "group_size": group_size,
                        "clarity_level": clarity_level,
                        "authority_present": authority_present,
                        "bystander_reaction": bystander_reaction,
                        "instruction": COMMON_SYSTEM_MESSAGE_PREFIX + instruction_filled
                    })
                    
                    # Check limit
                    if actual_limit and len(scenarios) >= actual_limit:
                        break
                if actual_limit and len(scenarios) >= actual_limit:
                    break
            if actual_limit and len(scenarios) >= actual_limit:
                break
        if actual_limit and len(scenarios) >= actual_limit:
            break
    
    print(f"✅ Generated {len(scenarios)} scenario configurations")
    
    # Ask for confirmation
    print(f"\n⚠️  Ready to generate {len(scenarios)} scenarios using {PROVIDER.upper()}")
    print(f"   Estimated batches: {(len(scenarios) + BATCH_SIZE - 1) // BATCH_SIZE}")
    print(f"   Estimated time: ~{(len(scenarios) / BATCH_SIZE) * (BATCH_DELAY_SECONDS / 60):.1f} minutes")
    
    response = input("\nProceed with generation? (y/N): ")
    if response.lower() != 'y':
        print("❌ Generation cancelled.")
        return
    
    # Initialize API and pipeline
    try:
        api_key = validate_api_key(PROVIDER)
        pipeline_runner = PipelineRunnerGemini(
            api_key,
            MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        output_processor = OutputProcessor()
        
        # Process scenarios in batches
        print(f"\n🚀 Starting generation...")
        all_results = []
        total_batches = (len(scenarios) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(scenarios), BATCH_SIZE):
            batch = scenarios[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            # Add delay between batches
            if i > 0:
                print(f"\n⏳ Waiting {BATCH_DELAY_SECONDS} seconds between batches...")
                time.sleep(BATCH_DELAY_SECONDS)
            
            # Process batch
            batch_results = pipeline_runner.run_batch(batch, batch_num, total_batches)
            
            if batch_results:
                all_results.extend(batch_results)
                output_processor.save_batch_results(batch_results, batch_num)
            else:
                print(f"⚠️  Batch {batch_num} returned no results")
        
        # Save final results
        if all_results:
            print(f"\n✅ Generation complete! Generated {len(all_results)}/{len(scenarios)} scenarios")
            
            # Save combined results
            output_processor.save_combined_results(all_results)
            
            # Convert for AISI Inspect
            output_processor.convert_for_inspect(all_results)
            
            # Print statistics
            output_processor.print_generation_statistics(all_results)
            
            print(f"\n📁 Files saved:")
            print(f"   - scenarios/bystander_scenarios_all_batches.json")
            print(f"   - scenarios/bystander_scenarios_inspect.json")
            print(f"   - scenarios/batches/bystander_scenarios_batch_*.json")
        else:
            print("\n❌ No scenarios were successfully generated")
            print("   Check API key, rate limits, and network connection")
    
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API key is set correctly")
        print("2. Ensure you have sufficient API credits/quota")
        print("3. Verify the scenario type is correct")
        print("4. Check your internet connection")
        print("5. Try reducing BATCH_SIZE or increasing BATCH_DELAY_SECONDS")


if __name__ == "__main__":
    try:
        generate_custom_scenarios()
    except KeyboardInterrupt:
        print("\n\n❌ Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

