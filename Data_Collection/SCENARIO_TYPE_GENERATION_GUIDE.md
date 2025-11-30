# Generating Data for a Specific Scenario Type with Gemini

This guide explains all variables you can modify to control scenario generation and how to generate data for a specific scenario type only.

## All Variables You Can Change

### 1. **Scenario Type** (Primary Filter)
Available scenario types in `scenario_templates.py`:
- `medical_emergency`
- `workplace_harassment`
- `public_humiliation`
- `discrimination`
- `cyberbullying`
- `sexual_harassment`
- `depression`
- `crime`
- `breaking_rules`
- `dependent_neglect`
- `bullying`
- `safety_hazard`
- `public_intoxication`
- `domestic_conflict`
- `deceptive_business`
- `fake_news`
- `unauthorized_surveillance`
- `hoarding`
- `financial_fraud`
- `event_disruption`

### 2. **Number of Datapoints** (`limit_scenarios`)
- Controls total number of scenarios to generate
- `None` = Generate all combinations for selected filters
- `10` = Generate exactly 10 scenarios
- `50` = Generate 50 scenarios
- **Formula for single scenario type**: `GROUP_SIZES × CLARITY_LEVELS × AUTHORITY_OPTIONS × BYSTANDER_REACTIONS = 8 × 2 × 2 × 2 = 64 scenarios max per type`

### 3. **Group Sizes** (`GROUP_SIZES` in `scenario_templates.py`)
- Default: `[1, 2, 3, 4, 5, 6, 7, 8]`
- Number of bystanders (excluding victim and perpetrator)
- Can modify in `scenario_templates.py` to filter specific sizes

### 4. **Clarity Levels** (`CLARITY_LEVELS` in `scenario_templates.py`)
- Default: `['clear', 'unclear']`
- Whether help requirement is clear or unclear
- Can modify to `['clear']` or `['unclear']` for single option

### 5. **Authority Presence** (`AUTHORITY_PRESENT_OPTIONS` in `scenario_templates.py`)
- Default: `[True, False]`
- Whether authority figure is present
- Can modify to `[True]` or `[False]` for single option

### 6. **Bystander Reactions** (`BYSTANDER_REACTION_OPTIONS` in `scenario_templates.py`)
- Default: `['worried', 'ignoring']`
- How other bystanders react
- Can modify to `['worried']` or `['ignoring']` for single option

### 7. **Batch Size** (`batch_size` in `main.py`)
- Default: `8`
- Number of scenarios processed per batch
- Smaller = more API calls but better rate limit handling
- Larger = fewer calls but higher rate limit risk

### 8. **Temperature** (`temperature` in `main.py`)
- Default: `0.8`
- Range: `0.0` (deterministic) to `1.0` (creative)
- Controls randomness in generation

### 9. **Max Tokens** (`max_tokens` in `main.py`)
- Default: `1200`
- Maximum tokens per generated scenario
- Increase for longer scenarios

### 10. **Model** (`model` in `main.py`)
- Gemini default: `gemini-2.5-flash`
- Alternatives: `gemini-1.5-flash`, `gemini-1.5-pro`

### 11. **Provider** (`provider` in `main.py` or `LLM_PROVIDER` env var)
- `"gemini"` or `"claude"`

### 12. **Batch Delay** (`batch_delay_seconds` in `main.py`)
- Default: `10`
- Seconds to wait between batches
- Increase if hitting rate limits

## Method 1: Quick Method - Modify main.py Directly

Edit `main.py` and modify the `GenerationConfig` and add scenario type filtering:

```python
# In main.py, around line 136-142, modify:

config = GenerationConfig(
    batch_size=8,
    limit_scenarios=64,  # Max for single scenario type (8×2×2×2)
    priority_mode=False,
    provider="gemini",  # Use Gemini
    model="gemini-2.5-flash",
    temperature=0.8,
    max_tokens=1200,
    batch_delay_seconds=10
)

# Then modify scenario_generator.py's _generate_all_scenarios method
# OR create a custom filter after generation
```

**Command:**
```bash
# Set Gemini API key
$env:GOOGLE_API_KEY="your-api-key"
$env:LLM_PROVIDER="gemini"

# Run (after modifying main.py)
python main.py
```

## Method 2: Filter by Scenario Type (Recommended)

Create a new script or modify `scenario_generator.py` to add a `scenario_type_filter` parameter:

**Option A: Create a new script `generate_single_type.py`:**

```python
# generate_single_type.py
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from scenario_generator import ScenarioGenerator
from pipeline_runner_gemini import PipelineRunnerGemini
from output_processor import OutputProcessor
from config import GenerationConfig, validate_api_key
from scenario_templates import (
    SCENARIO_TEMPLATES, GROUP_SIZES, CLARITY_LEVELS,
    AUTHORITY_PRESENT_OPTIONS, BYSTANDER_REACTION_OPTIONS,
    COMMON_SYSTEM_MESSAGE_PREFIX,
    get_authority_presence_text, get_bystander_reaction_text
)

def generate_single_scenario_type(
    scenario_type: str,
    limit_scenarios: int = None,
    group_sizes: list = None,
    clarity_levels: list = None,
    authority_options: list = None,
    bystander_reactions: list = None,
    batch_size: int = 8,
    temperature: float = 0.8,
    max_tokens: int = 1200,
    model: str = "gemini-2.5-flash"
):
    """Generate scenarios for a single scenario type with custom filters"""
    
    # Validate scenario type
    if scenario_type not in SCENARIO_TEMPLATES:
        raise ValueError(f"Invalid scenario type: {scenario_type}. Available: {list(SCENARIO_TEMPLATES.keys())}")
    
    # Use defaults if not specified
    group_sizes = group_sizes or GROUP_SIZES
    clarity_levels = clarity_levels or CLARITY_LEVELS
    authority_options = authority_options or AUTHORITY_PRESENT_OPTIONS
    bystander_reactions = bystander_reactions or BYSTANDER_REACTION_OPTIONS
    
    # Generate scenario configurations
    scenarios = []
    scenario_id_counter = 0
    
    for group_size in group_sizes:
        for clarity_level in clarity_levels:
            for authority_present in authority_options:
                for bystander_reaction in bystander_reactions:
                    # Create scenario
                    template_instruction = SCENARIO_TEMPLATES[scenario_type]
                    authority_presence_text = get_authority_presence_text(authority_present)
                    bystander_reaction_text = get_bystander_reaction_text(bystander_reaction)
                    
                    instruction_filled = template_instruction.format(
                        group_size=group_size,
                        clarity_level=clarity_level,
                        authority_presence_text=authority_presence_text,
                        bystander_reaction_text=bystander_reaction_text
                    )
                    
                    scenario_id = f"{scenario_type}_{group_size}p_{clarity_level}clarity_{'auth' if authority_present else 'noauth'}_{bystander_reaction}_{scenario_id_counter}"
                    scenario_id_counter += 1
                    
                    scenarios.append({
                        "id": scenario_id,
                        "scenario_type": scenario_type,
                        "group_size": group_size,
                        "clarity_level": clarity_level,
                        "authority_present": authority_present,
                        "bystander_reaction": bystander_reaction,
                        "instruction": COMMON_SYSTEM_MESSAGE_PREFIX + instruction_filled
                    })
                    
                    if limit_scenarios and len(scenarios) >= limit_scenarios:
                        break
                if limit_scenarios and len(scenarios) >= limit_scenarios:
                    break
            if limit_scenarios and len(scenarios) >= limit_scenarios:
                break
        if limit_scenarios and len(scenarios) >= limit_scenarios:
            break
    
    print(f"Generated {len(scenarios)} scenario configurations for '{scenario_type}'")
    
    # Initialize pipeline runner
    api_key = validate_api_key("gemini")
    pipeline_runner = PipelineRunnerGemini(api_key, model, temperature, max_tokens)
    output_processor = OutputProcessor()
    
    # Process in batches
    all_results = []
    total_batches = (len(scenarios) + batch_size - 1) // batch_size
    
    import time
    for i in range(0, len(scenarios), batch_size):
        batch = scenarios[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        if i > 0:
            print(f"⏳ Waiting 10 seconds between batches...")
            time.sleep(10)
        
        batch_results = pipeline_runner.run_batch(batch, batch_num, total_batches)
        
        if batch_results:
            all_results.extend(batch_results)
            output_processor.save_batch_results(batch_results, batch_num)
    
    # Save results
    if all_results:
        output_processor.save_combined_results(all_results)
        output_processor.convert_for_inspect(all_results)
        print(f"\n✅ Generated {len(all_results)} scenarios for '{scenario_type}'")
    
    return all_results

if __name__ == "__main__":
    # Example usage
    generate_single_scenario_type(
        scenario_type="medical_emergency",
        limit_scenarios=32,  # Generate 32 scenarios
        group_sizes=[1, 2, 3, 4],  # Only these group sizes
        clarity_levels=['clear'],  # Only clear scenarios
        authority_options=[False],  # No authority present
        bystander_reactions=['worried', 'ignoring'],  # Both reactions
        batch_size=8,
        temperature=0.8,
        max_tokens=1200,
        model="gemini-2.5-flash"
    )
```

**Command:**
```bash
# Set API key
$env:GOOGLE_API_KEY="your-api-key"

# Run the script (after creating it)
python generate_single_type.py
```

## Method 3: Command-Line Arguments (Most Flexible)

Modify `main.py` to accept command-line arguments:

**Add to main.py:**
```python
import argparse

def main():
    parser = argparse.ArgumentParser(description='Generate bystander effect scenarios')
    parser.add_argument('--scenario-type', type=str, default=None, 
                       help='Generate only this scenario type')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of scenarios')
    parser.add_argument('--group-sizes', nargs='+', type=int, default=None,
                       help='Filter group sizes (e.g., --group-sizes 1 2 3)')
    parser.add_argument('--clarity', nargs='+', default=None,
                       choices=['clear', 'unclear'],
                       help='Filter clarity levels')
    parser.add_argument('--authority', nargs='+', type=bool, default=None,
                       help='Filter authority presence (True/False)')
    parser.add_argument('--batch-size', type=int, default=8,
                       help='Batch size')
    parser.add_argument('--temperature', type=float, default=0.8,
                       help='Generation temperature')
    parser.add_argument('--max-tokens', type=int, default=1200,
                       help='Max tokens per scenario')
    parser.add_argument('--model', type=str, default=None,
                       help='Model name')
    
    args = parser.parse_args()
    
    # Use args to configure generation...
```

**Commands:**
```bash
# Set API key
$env:GOOGLE_API_KEY="your-api-key"
$env:LLM_PROVIDER="gemini"

# Generate 20 medical_emergency scenarios
python main.py --scenario-type medical_emergency --limit 20

# Generate workplace_harassment with specific filters
python main.py --scenario-type workplace_harassment --group-sizes 2 3 4 --clarity clear --limit 12

# Generate all combinations for a single type (64 scenarios)
python main.py --scenario-type cyberbullying --limit 64
```

## Quick Reference: Variable Summary

| Variable | Location | Default | Options |
|----------|----------|---------|---------|
| **Scenario Type** | `scenario_templates.py` | All 20 types | Any from SCENARIO_TEMPLATES |
| **Number of Datapoints** | `main.py` config | `None` (all) | Any integer |
| **Group Sizes** | `scenario_templates.py` | `[1-8]` | Any subset of `[1,2,3,4,5,6,7,8]` |
| **Clarity Levels** | `scenario_templates.py` | `['clear','unclear']` | `['clear']`, `['unclear']`, or both |
| **Authority Presence** | `scenario_templates.py` | `[True, False]` | `[True]`, `[False]`, or both |
| **Bystander Reactions** | `scenario_templates.py` | `['worried','ignoring']` | `['worried']`, `['ignoring']`, or both |
| **Batch Size** | `main.py` | `8` | Any integer (1-20 recommended) |
| **Temperature** | `main.py` | `0.8` | `0.0` to `1.0` |
| **Max Tokens** | `main.py` | `1200` | Any integer (500-2000 recommended) |
| **Model** | `main.py` | `gemini-2.5-flash` | `gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-1.5-pro` |
| **Provider** | `main.py` or env | `claude` | `gemini` or `claude` |
| **Batch Delay** | `main.py` | `10` | Any integer (seconds) |

## Example Commands for Common Use Cases

### Generate 50 medical emergency scenarios with all variations:
```bash
$env:GOOGLE_API_KEY="your-key"
$env:LLM_PROVIDER="gemini"
# Modify main.py: limit_scenarios=50, add scenario_type filter
python main.py
```

### Generate all 64 combinations for workplace_harassment:
```bash
$env:GOOGLE_API_KEY="your-key"
# Use Method 2 script with limit_scenarios=None
python generate_single_type.py
```

### Generate 20 scenarios with only clear, no authority, worried bystanders:
```bash
$env:GOOGLE_API_KEY="your-key"
# Use Method 2 script with:
# - scenario_type="medical_emergency"
# - limit_scenarios=20
# - clarity_levels=['clear']
# - authority_options=[False]
# - bystander_reactions=['worried']
python generate_single_type.py
```

## Calculation: Max Scenarios Per Type

For a single scenario type:
- Group sizes: 8 options
- Clarity levels: 2 options
- Authority: 2 options
- Bystander reactions: 2 options

**Total = 8 × 2 × 2 × 2 = 64 scenarios maximum per scenario type**

If you filter any dimension, multiply accordingly:
- Only group sizes [1,2,3] = 3 × 2 × 2 × 2 = 24 scenarios
- Only clear scenarios = 8 × 1 × 2 × 2 = 32 scenarios
- Only clear + no authority = 8 × 1 × 1 × 2 = 16 scenarios

