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

