import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List

load_dotenv()

@dataclass
class Config:
    """Configuration for the evaluation"""
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Models to evaluate
    MODELS_TO_EVALUATE: List[str] = [
        "gpt-4",
        "gpt-3.5-turbo",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "gemini-pro"
    ]
    
    # Evaluation settings
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 500
    USE_LOGPROBS: bool = True  # Use logprobs for OpenAI models when available
    PROBABILITY_SAMPLES: int = 5  # Number of samples for logprob estimation
    
    # Output settings
    OUTPUT_DIR: str = "evaluation_results"
    SAVE_RAW_RESPONSES: bool = True
    SAVE_INTERMEDIATE: bool = True  # Save after every 10 scenarios