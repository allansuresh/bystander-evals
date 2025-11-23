# Provider Switching Guide

This guide explains how to switch between Claude and Gemini APIs, and how to control the number of scenarios generated.

## Switching Between Claude and Gemini

### Method 1: Environment Variable (Recommended)

Set the `LLM_PROVIDER` environment variable before running the script:

**For Claude (default):**
```bash
# Windows PowerShell
$env:LLM_PROVIDER="claude"
python main.py

# Windows CMD
set LLM_PROVIDER=claude
python main.py

# Linux/Mac
export LLM_PROVIDER=claude
python main.py
```

**For Gemini:**
```bash
# Windows PowerShell
$env:LLM_PROVIDER="gemini"
python main.py

# Windows CMD
set LLM_PROVIDER=gemini
python main.py

# Linux/Mac
export LLM_PROVIDER=gemini
python main.py
```

### Method 2: Modify main.py

Edit the `main()` function in `main.py` and change the provider:

```python
# In main.py, around line 109
provider = "gemini"  # Change from "claude" to "gemini" or vice versa
```

## API Keys Setup

### Claude API Key
Set the `ANTHROPIC_API_KEY` environment variable:
```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY="your-anthropic-api-key"

# Linux/Mac
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

Or add it to your `.env` file:
```
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Gemini API Key
Set the `GOOGLE_API_KEY` or `GEMINI_API_KEY` environment variable:
```bash
# Windows PowerShell
$env:GOOGLE_API_KEY="your-google-api-key"

# Linux/Mac
export GOOGLE_API_KEY="your-google-api-key"
```

Or add it to your `.env` file:
```
GOOGLE_API_KEY=your-google-api-key
```

## Installing Required Packages

### For Claude (default):
```bash
pip install distilabel anthropic python-dotenv
```

### For Gemini:
```bash
pip install google-genai python-dotenv
```

## Controlling the Number of Scenarios Generated

### Key Parameters in `main.py`

Edit the `GenerationConfig` in the `main()` function:

```python
config = GenerationConfig(
    batch_size=8,                    # Number of scenarios per batch
    limit_scenarios=None,            # Total number of scenarios (None = all)
    priority_mode=False,              # Use priority combinations only
    provider="claude",               # "claude" or "gemini"
    model="claude-3-haiku-20240307", # Model name
    batch_delay_seconds=10,          # Delay between batches
    temperature=0.8,                 # Generation temperature
    max_tokens=1200                  # Maximum tokens per scenario
)
```

### Parameters Explained

1. **`limit_scenarios`**: 
   - `None` = Generate all possible scenarios (default: 256 scenarios)
   - `10` = Generate only 10 scenarios
   - `100` = Generate 100 scenarios
   - **This is the main parameter to control total scenario count**

2. **`batch_size`**: 
   - Number of scenarios processed in each batch
   - Smaller batches = more API calls but better rate limit handling
   - Larger batches = fewer API calls but higher risk of rate limits
   - Default: 8

3. **`priority_mode`**: 
   - `False` = Generate all combinations
   - `True` = Generate only priority combinations (5 predefined scenarios × 2 bystander reactions = 10 scenarios)
   - Useful for quick testing

4. **`batch_delay_seconds`**: 
   - Delay between batches to avoid rate limits
   - Default: 10 seconds

### Example Configurations

**Generate 20 scenarios for testing:**
```python
config = GenerationConfig(
    batch_size=5,
    limit_scenarios=20,
    priority_mode=False,
    provider="gemini",
    model="gemini-1.5-flash"
)
```

**Generate only priority scenarios (10 total):**
```python
config = GenerationConfig(
    batch_size=5,
    limit_scenarios=None,  # Not used in priority mode
    priority_mode=True,    # This limits to ~10 scenarios
    provider="claude",
    model="claude-3-haiku-20240307"
)
```

**Generate all scenarios (256 total):**
```python
config = GenerationConfig(
    batch_size=8,
    limit_scenarios=None,  # None = all scenarios
    priority_mode=False,
    provider="claude",
    model="claude-3-haiku-20240307"
)
```

## Model Options

### Claude Models:
- `claude-3-haiku-20240307` (fastest, cheapest)
- `claude-3-sonnet-20240229` (balanced)
- `claude-3-opus-20240229` (most capable)

### Gemini Models:
- `gemini-2.5-flash` (fastest, recommended, default)
- `gemini-1.5-flash` (alternative)
- `gemini-1.5-pro` (more capable)

## Total Scenario Calculation

The total number of possible scenarios is calculated as:
```
Total = (Number of scenario types) × (Group sizes) × (Clarity levels) × 
        (Authority options) × (Bystander reactions)
```

Currently:
- 20 scenario types
- 8 group sizes (1-8)
- 2 clarity levels (clear, unclear)
- 2 authority options (present, not present)
- 2 bystander reactions (worried, ignoring)

**Total = 20 × 8 × 2 × 2 × 2 = 1,280 scenarios**

Use `limit_scenarios` to generate fewer scenarios for testing.

## Troubleshooting

### Gemini Issues:
1. **Import Error**: Install `google-genai`: `pip install google-genai`
2. **API Key Error**: Make sure `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set
3. **Rate Limits**: Reduce `batch_size` and increase `batch_delay_seconds`

### Claude Issues:
1. **API Key Error**: Make sure `ANTHROPIC_API_KEY` is set
2. **Rate Limits**: Reduce `batch_size` and increase `batch_delay_seconds`

## Quick Start Examples

**Test with 5 scenarios using Gemini:**
```bash
$env:LLM_PROVIDER="gemini"
$env:GOOGLE_API_KEY="your-key"
# Then edit main.py: limit_scenarios=5
python main.py
```

**Generate 50 scenarios with Claude:**
```bash
$env:LLM_PROVIDER="claude"
$env:ANTHROPIC_API_KEY="your-key"
# Then edit main.py: limit_scenarios=50
python main.py
```

