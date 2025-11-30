# Quick Reference: generate_custom_scenarios.py

## Quick Start

1. **Set your API key:**
   ```bash
   $env:GOOGLE_API_KEY="your-api-key"
   ```

2. **Open `generate_custom_scenarios.py` and modify the CONFIGURATION section**

3. **Run the script:**
   ```bash
   python generate_custom_scenarios.py
   ```

## Configuration Variables

### Scenario Selection
- **`SCENARIO_TYPE`**: The type of scenario to generate
  - Options: `medical_emergency`, `workplace_harassment`, `public_humiliation`, `discrimination`, `cyberbullying`, `sexual_harassment`, `depression`, `crime`, `breaking_rules`, `dependent_neglect`, `bullying`, `safety_hazard`, `public_intoxication`, `domestic_conflict`, `deceptive_business`, `fake_news`, `unauthorized_surveillance`, `hoarding`, `financial_fraud`, `event_disruption`

### Quantity Control
- **`LIMIT_SCENARIOS`**: Total number of scenarios to generate
  - `None` = Generate all possible combinations
  - `20` = Generate exactly 20 scenarios
  - Maximum for single type: 64 (8×2×2×2)

### Filter Variables (set to `None` to use all options)
- **`GROUP_SIZES_FILTER`**: Filter group sizes
  - `None` = All sizes [1,2,3,4,5,6,7,8]
  - `[1, 2, 3]` = Only small groups
  - `[5, 6, 7, 8]` = Only large groups

- **`CLARITY_LEVELS_FILTER`**: Filter clarity levels
  - `None` = Both ['clear', 'unclear']
  - `['clear']` = Only clear scenarios
  - `['unclear']` = Only unclear scenarios

- **`AUTHORITY_OPTIONS_FILTER`**: Filter authority presence
  - `None` = Both [True, False]
  - `[True]` = Only with authority
  - `[False]` = Only without authority

- **`BYSTANDER_REACTIONS_FILTER`**: Filter bystander reactions
  - `None` = Both ['worried', 'ignoring']
  - `['worried']` = Only worried bystanders
  - `['ignoring']` = Only ignoring bystanders

### Generation Parameters
- **`BATCH_SIZE`**: Scenarios per batch (1-20 recommended, default: 8)
- **`TEMPERATURE`**: Creativity level (0.0-1.0, default: 0.8)
- **`MAX_TOKENS`**: Max tokens per scenario (default: 1200)
- **`MODEL`**: Gemini model name (default: "gemini-2.5-flash")
- **`BATCH_DELAY_SECONDS`**: Delay between batches (default: 10)

## Example Configurations

### Example 1: Generate 20 medical emergency scenarios
```python
SCENARIO_TYPE = "medical_emergency"
LIMIT_SCENARIOS = 20
GROUP_SIZES_FILTER = None  # Use all
CLARITY_LEVELS_FILTER = None  # Use all
AUTHORITY_OPTIONS_FILTER = None  # Use all
BYSTANDER_REACTIONS_FILTER = None  # Use all
```

### Example 2: Generate all clear workplace harassment scenarios (no authority)
```python
SCENARIO_TYPE = "workplace_harassment"
LIMIT_SCENARIOS = None  # All combinations
GROUP_SIZES_FILTER = None
CLARITY_LEVELS_FILTER = ['clear']  # Only clear
AUTHORITY_OPTIONS_FILTER = [False]  # No authority
BYSTANDER_REACTIONS_FILTER = None
```

### Example 3: Generate 12 cyberbullying scenarios with small groups only
```python
SCENARIO_TYPE = "cyberbullying"
LIMIT_SCENARIOS = 12
GROUP_SIZES_FILTER = [1, 2, 3]  # Small groups only
CLARITY_LEVELS_FILTER = None
AUTHORITY_OPTIONS_FILTER = None
BYSTANDER_REACTIONS_FILTER = None
```

### Example 4: Generate all 64 combinations for a single type
```python
SCENARIO_TYPE = "discrimination"
LIMIT_SCENARIOS = None  # All combinations
GROUP_SIZES_FILTER = None
CLARITY_LEVELS_FILTER = None
AUTHORITY_OPTIONS_FILTER = None
BYSTANDER_REACTIONS_FILTER = None
# This will generate: 8 × 2 × 2 × 2 = 64 scenarios
```

## Calculation Formula

**Maximum scenarios per type:**
```
Total = Group Sizes × Clarity Levels × Authority Options × Bystander Reactions
```

**Examples:**
- All options: 8 × 2 × 2 × 2 = **64 scenarios**
- Only group sizes [1,2,3]: 3 × 2 × 2 × 2 = **24 scenarios**
- Only clear + no authority: 8 × 1 × 1 × 2 = **16 scenarios**
- Only clear + no authority + worried: 8 × 1 × 1 × 1 = **8 scenarios**

## Output Files

The script generates:
- `scenarios/bystander_scenarios_all_batches.json` - Combined results
- `scenarios/bystander_scenarios_inspect.json` - AISI Inspect format
- `scenarios/batches/bystander_scenarios_batch_*.json` - Individual batches

## Troubleshooting

1. **API Key Error**: Set `$env:GOOGLE_API_KEY="your-key"`
2. **Rate Limits**: Increase `BATCH_DELAY_SECONDS` or decrease `BATCH_SIZE`
3. **Invalid Scenario Type**: Check spelling against available types
4. **Too Many Scenarios**: Set `LIMIT_SCENARIOS` to a smaller number

