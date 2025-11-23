"""
Configuration settings for scenario generation
"""

import os
from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class GenerationConfig:
    """Configuration for scenario generation"""
    batch_size: int = 8
    limit_scenarios: Optional[int] = None
    priority_mode: bool = False
    provider: Literal["claude", "gemini"] = "claude"
    model: str = "claude-3-haiku-20240307"  # Default Claude model
    batch_delay_seconds: int = 10
    retry_delay_seconds: int = 60
    temperature: float = 0.8
    max_tokens: int = 1200

def validate_api_key(provider: str = "claude") -> str:
    """Validate that required API key is available for the specified provider"""
    if provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY environment variable is required for Gemini. "
                "Please set it in your .env file or environment."
            )
        print("✅ Google/Gemini API key found")
        return api_key
    else:  # claude
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        print("✅ Anthropic API key found")
        return api_key

def get_default_model(provider: str) -> str:
    """Get default model name for the specified provider"""
    if provider == "gemini":
        return "gemini-2.5-flash"
    else:  # claude
        return "claude-3-haiku-20240307"

def estimate_generation_time(total_scenarios: int, batch_size: int) -> float:
    """Estimate generation time in minutes"""
    return (total_scenarios / batch_size) * 2  # ~2 minutes per batch with delays

def estimate_cost(total_scenarios: int) -> float:
    """Rough cost estimation"""
    return total_scenarios * 0.01  # Very rough estimate