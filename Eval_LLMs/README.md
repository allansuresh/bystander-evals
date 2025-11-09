# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API keys
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"

# 3. Run evaluation
python main.py --scenarios-file your_scenarios.json

# 4. Run with specific models
python main.py --scenarios-file scenarios.json --models gpt-4 claude-3-opus-20240229

# 5. Test with limited scenarios
python main.py --scenarios-file scenarios.json --limit 10

# 6. Resume from interruption
python main.py --scenarios-file scenarios.json --resume