"""
Configuration settings for scenario generation
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class GenerationConfig:
    """Configuration for scenario generation"""
    batch_size: int = 8
    limit_scenarios: Optional[int] = None
    priority_mode: bool = False
    model: str = "claude-3-haiku-20240307"
    batch_delay_seconds: int = 10
    retry_delay_seconds: int = 60
    temperature: float = 0.8
    max_tokens: int = 1200

def validate_api_key() -> str:
    """Validate that required API key is available"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Please set it in your .env file or environment."
        )
    print("✅ Anthropic API key found")
    return api_key

def estimate_generation_time(total_scenarios: int, batch_size: int) -> float:
    """Estimate generation time in minutes"""
    return (total_scenarios / batch_size) * 2  # ~2 minutes per batch with delays

def estimate_cost(total_scenarios: int) -> float:
    """Rough cost estimation"""
    return total_scenarios * 0.01  # Very rough estimate