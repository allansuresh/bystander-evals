"""
Gemini API pipeline execution with rate limiting and batch processing
Uses Google's Generative AI SDK directly
"""

import os
import time
import json
from typing import List, Dict, Any

from output_processor import strip_code_fences
from gemini_client import make_client, generate_with_retry

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  Warning: google-genai not installed. Install with: pip install google-genai")


class PipelineRunnerGemini:
    """Handles scenario generation with Gemini API and rate limiting"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", temperature: float = 0.8, max_tokens: int = 1200):
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "Google Generative AI library not installed. "
                "Install with: pip install google-genai"
            )
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize the Gemini client (with HTTP timeout; see gemini_client.py)
        self.client = make_client(api_key)
    
    def run_batch(
        self, 
        scenarios_batch: List[Dict[str, Any]], 
        batch_num: int, 
        total_batches: int
    ) -> List[Dict[str, Any]]:
        """Run scenario generation for a single batch with rate limiting"""
        
        print(f"🔄 Processing batch {batch_num}/{total_batches} ({len(scenarios_batch)} scenarios)")
        print(f"🚀 Starting batch {batch_num} generation with Gemini...")
        
        results = []
        
        for idx, scenario in enumerate(scenarios_batch, 1):
            try:
                # Generate scenario using Gemini
                instruction = scenario.get("instruction", "")
                
                # Retries transient errors (429/503/504/timeouts) with exponential backoff
                generated_text = generate_with_retry(
                    self.client, self.model, instruction, temperature=self.temperature
                )
                generated_text = strip_code_fences(generated_text)
                
                # Create result in the same format as distilabel output
                result = {
                    "id": scenario.get("id"),
                    "scenario_type": scenario.get("scenario_type"),
                    "group_size": scenario.get("group_size"),
                    "clarity_level": scenario.get("clarity_level"),
                    "authority_present": scenario.get("authority_present"),
                    "bystander_reaction": scenario.get("bystander_reaction"),
                    "generated_scenario": generated_text
                }
                
                results.append(result)
                print(f"  ✓ Generated scenario {idx}/{len(scenarios_batch)}")
                
                # Small delay between requests to avoid rate limits
                if idx < len(scenarios_batch):
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"  ❌ Failed to generate scenario {idx}: {e}")
                # Continue with next scenario
                continue
        
        if results:
            print(f"✅ Batch {batch_num} completed! Generated {len(results)}/{len(scenarios_batch)} scenarios")
        else:
            print(f"⚠️  Batch {batch_num} generated no results")
        
        return results
    
    def _handle_batch_error(
        self, 
        error: Exception, 
        batch_num: int, 
        scenarios_batch: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Handle batch processing errors with retry logic"""
        print(f"❌ Batch {batch_num} failed: {error}")
        
        if "rate_limit" in str(error).lower() or "429" in str(error) or "quota" in str(error).lower():
            print(f"⏳ Rate limit/quota hit on batch {batch_num}. Waiting 60 seconds...")
            time.sleep(60)
            
            # Retry once
            try:
                return self.run_batch(scenarios_batch, batch_num, 1)
            except Exception as retry_error:
                print(f"❌ Batch {batch_num} failed on retry: {retry_error}")
                return []
        else:
            print(f"❌ Non-rate-limit error in batch {batch_num}: {error}")
            return []
