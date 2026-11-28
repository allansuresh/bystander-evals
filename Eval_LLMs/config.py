import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List

env_path = Path(__file__).parent.parent / '.env'  # Goes up two levels from config.py
load_dotenv(dotenv_path=env_path)

@dataclass
class Config:
    """Configuration for the evaluation"""
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Models to evaluate: set with --models (required)
    MODELS_TO_EVALUATE: List[str] = field(default_factory=list)
    
    # Evaluation settings
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 500
    USE_LOGPROBS: bool = True  # Use logprobs for OpenAI models when available
    PROBABILITY_SAMPLES: int = 5  # Number of samples for logprob estimation
    
    # Output settings
    OUTPUT_DIR: str = "evaluation_results"
    SAVE_RAW_RESPONSES: bool = True
    RPM: float = 14  # Client-side max requests per minute per model (--rpm)