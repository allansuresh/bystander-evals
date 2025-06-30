"""
Distilabel pipeline execution with rate limiting and batch processing
"""

import os
import time
from typing import List, Dict, Any
from distilabel.pipeline import Pipeline
from distilabel.llms import AnthropicLLM
from distilabel.steps import LoadDataFromDicts, KeepColumns
from distilabel.steps.tasks import TextGeneration

class PipelineRunner:
    """Handles Distilabel pipeline execution with rate limiting"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key
        self.model = model
    
    def run_batch(
        self, 
        scenarios_batch: List[Dict[str, Any]], 
        batch_num: int, 
        total_batches: int
    ) -> List[Dict[str, Any]]:
        """Run scenario generation for a single batch with rate limiting"""
        
        print(f"🔄 Processing batch {batch_num}/{total_batches} ({len(scenarios_batch)} scenarios)")
        
        # Create and run pipeline
        with Pipeline(
            name=f"bystander_scenario_generation_batch_{batch_num}", 
            description=f"Generate bystander effect scenarios batch {batch_num}/{total_batches}"
        ) as pipeline:
            
            # Load scenario data for this batch
            load_scenarios = LoadDataFromDicts(
                name="load_base_scenarios",
                data=scenarios_batch
            )
            
            # Generate scenarios using Claude
            generate_scenarios = TextGeneration(
                name="generate_scenarios",
                llm=AnthropicLLM(
                    model=self.model,
                    api_key=self.api_key,
                ),
                input_mappings={"instruction": "instruction"},
                output_mappings={"generation": "generated_scenario"}
            )
            
            # Keep relevant columns
            keep_columns = KeepColumns(
                name="keep_relevant_data",
                columns=[
                    "id",
                    "scenario_type",
                    "group_size", 
                    "clarity_level",
                    "authority_present",
                    "generated_scenario"
                ]
            )
            
            # Connect pipeline steps
            load_scenarios >> generate_scenarios >> keep_columns
        
        # Run the pipeline
        try:
            print(f"🚀 Starting batch {batch_num} generation...")
            distiset = pipeline.run(
                parameters={
                    "generate_scenarios": {
                        "llm": {
                            "generation_kwargs": {
                                "temperature": 0.8,
                                "max_tokens": 1200
                            }
                        }
                    }
                },
                use_cache=False
            )
            
            print(f"✅ Batch {batch_num} completed!")
            return distiset["default"]["train"].to_list()
            
        except Exception as e:
            return self._handle_batch_error(e, batch_num, scenarios_batch)
    
    def _handle_batch_error(
        self, 
        error: Exception, 
        batch_num: int, 
        scenarios_batch: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Handle batch processing errors with retry logic"""
        print(f"❌ Batch {batch_num} failed: {error}")
        
        if "rate_limit" in str(error).lower() or "429" in str(error):
            print(f"⏳ Rate limit hit on batch {batch_num}. Waiting 60 seconds...")
            time.sleep(60)
            
            # Retry once
            try:
                return self._retry_batch(batch_num, scenarios_batch)
            except Exception as retry_error:
                print(f"❌ Batch {batch_num} failed on retry: {retry_error}")
                return []
        else:
            print(f"❌ Non-rate-limit error in batch {batch_num}: {error}")
            return []
    
    def _retry_batch(self, batch_num: int, scenarios_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retry a failed batch"""
        with Pipeline(
            name=f"bystander_scenario_generation_batch_{batch_num}_retry", 
            description=f"Retry batch {batch_num}"
        ) as pipeline:
            
            load_scenarios = LoadDataFromDicts(
                name="load_base_scenarios",
                data=scenarios_batch
            )
            
            generate_scenarios = TextGeneration(
                name="generate_scenarios",
                llm=AnthropicLLM(
                    model=self.model,
                    api_key=self.api_key,
                ),
                input_mappings={"instruction": "instruction"},
                output_mappings={"generation": "generated_scenario"}
            )
            
            keep_columns = KeepColumns(
                name="keep_relevant_data",
                columns=[
                    "id", "scenario_type", "group_size", 
                    "clarity_level", "authority_present", "generated_scenario"
                ]
            )
            
            load_scenarios >> generate_scenarios >> keep_columns
        
        distiset = pipeline.run(
            parameters={
                "generate_scenarios": {
                    "llm": {
                        "generation_kwargs": {
                            "temperature": 0.8,
                            "max_tokens": 1200
                        }
                    }
                }
            },
            use_cache=False
        )
        
        print(f"✅ Batch {batch_num} completed on retry!")
        return distiset["default"]["train"].to_list()