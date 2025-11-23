"""
Main entry point for bystander effect scenario generation
"""

import os
import sys
import time
import multiprocessing
from dotenv import load_dotenv

# Set encoding for Windows compatibility
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Important: Set multiprocessing method for Windows
if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)

load_dotenv()

from scenario_generator import ScenarioGenerator
from pipeline_runner import PipelineRunner
from pipeline_runner_gemini import PipelineRunnerGemini
from output_processor import OutputProcessor
from config import GenerationConfig, validate_api_key, estimate_generation_time, estimate_cost
from scenario_templates import calculate_total_scenarios, PRIORITY_COMBINATIONS

class BystanderScenarioGenerator:
    """Main orchestrator for scenario generation"""
    
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.api_key = validate_api_key(config.provider)
        self.scenario_generator = ScenarioGenerator()
        
        # Select pipeline runner based on provider
        if config.provider == "gemini":
            self.pipeline_runner = PipelineRunnerGemini(
                self.api_key, 
                config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        else:  # claude
            self.pipeline_runner = PipelineRunner(self.api_key, config.model)
        
        self.output_processor = OutputProcessor()
    
    def run_generation(self) -> list:
        """Run the complete scenario generation process"""
        # Create base scenarios
        base_scenarios = self._create_scenarios()
        print(f"Created {len(base_scenarios)} base scenario templates")
        
        # Process in batches
        all_results = self._process_batches(base_scenarios)
        
        # Save and convert results
        if all_results:
            self._save_results(all_results)
            return all_results
        else:
            print("❌ No scenarios were successfully generated")
            return []
    
    def _create_scenarios(self) -> list:
        """Create scenario configurations"""
        if self.config.priority_mode:
            return self.scenario_generator.create_base_scenarios(
                limit_scenarios=self.config.limit_scenarios,
                priority_combinations=PRIORITY_COMBINATIONS
            )
        else:
            return self.scenario_generator.create_base_scenarios(
                limit_scenarios=self.config.limit_scenarios
            )
    
    def _process_batches(self, base_scenarios: list) -> list:
        """Process scenarios in batches with rate limiting"""
        all_results = []
        total_batches = (len(base_scenarios) + self.config.batch_size - 1) // self.config.batch_size
        
        for i in range(0, len(base_scenarios), self.config.batch_size):
            batch = base_scenarios[i:i + self.config.batch_size]
            batch_num = (i // self.config.batch_size) + 1
            
            # Add delay between batches
            if i > 0:
                print(f"⏳ Waiting {self.config.batch_delay_seconds} seconds between batches...")
                time.sleep(self.config.batch_delay_seconds)
            
            # Process batch
            batch_results = self.pipeline_runner.run_batch(batch, batch_num, total_batches)
            
            if batch_results:
                all_results.extend(batch_results)
                self.output_processor.save_batch_results(batch_results, batch_num)
            else:
                print(f"⚠️ Batch {batch_num} returned no results or failed entirely.")
        
        return all_results
    
    def _save_results(self, all_results: list):
        """Save final results and convert formats"""
        print(f"\n✅ All batches completed! Total scenarios generated: {len(all_results)}")
        
        # Save combined results
        self.output_processor.save_combined_results(all_results)
        
        # Convert for AISI Inspect
        self.output_processor.convert_for_inspect(all_results)
        
        # Print statistics
        self.output_processor.print_generation_statistics(all_results)

def main():
    """Main execution function"""
    print("=== Bystander Effect Scenario Generation (Rate-Limited) ===")
    
    # Get provider from environment or default to claude
    provider = os.getenv("LLM_PROVIDER", "claude").lower()
    if provider not in ["claude", "gemini"]:
        print(f"⚠️  Invalid provider '{provider}', defaulting to 'claude'")
        provider = "claude"
    
    # Set default model based on provider
    from config import get_default_model
    default_model = get_default_model(provider)
    
    if provider == "gemini":
        print("Using Google Gemini API")
    else:
        print("Using Distilabel framework with Anthropic Claude")
    
    # Configuration
    config = GenerationConfig(
        batch_size=8,
        limit_scenarios=None,  # Generate all scenarios
        priority_mode=False,
        provider=provider,
        model=default_model
    )
    
    # Calculate totals and estimates
    total_possible = calculate_total_scenarios()
    estimated_time = estimate_generation_time(total_possible, config.batch_size)
    estimated_cost = estimate_cost(total_possible)
    
    print(f"📊 Total possible scenarios: {total_possible}")
    print(f"\n🔧 Configuration:")
    print(f"   Provider: {config.provider}")
    print(f"   Model: {config.model}")
    print(f"   Batch size: {config.batch_size}")
    print(f"   Total scenarios limit: {config.limit_scenarios}")
    print(f"   Priority mode: {config.priority_mode}")
    print(f"   Estimated batches: {(total_possible + config.batch_size - 1) // config.batch_size}")
    print(f"   Estimated time: {estimated_time:.1f} minutes ({estimated_time/60:.1f} hours)")
    print(f"   Estimated cost: ~${estimated_cost:.2f} (very rough estimate)")
    
    print(f"\n⚠️  WARNING: This will generate {total_possible} scenarios!")
    print(f"   Make sure you have sufficient API credits and time.")
    
    # Ask for confirmation
    response = input("\nDo you want to proceed with generating ALL scenarios? (y/N): ")
    if response.lower() != 'y':
        print("Generation cancelled.")
        return
    
    try:
        # Run generation
        generator = BystanderScenarioGenerator(config)
        results = generator.run_generation()
        
        if results:
            print(f"\n🎉 Generation complete!")
            print(f"📊 Generated {len(results)} scenarios")
            print(f"📁 Files created:")
            print(f"   - bystander_scenarios_all_batches.json (Combined results)")
            print(f"   - bystander_scenarios_inspect.json (AISI Inspect format)")
            print(f"   - bystander_scenarios_batch_*.json (Individual batches)")
            
            print(f"\n🔄 Next steps:")
            print(f"1. Review generated scenarios for quality")
            print(f"2. If satisfied, increase limit_scenarios and re-run")
            print(f"3. Run AISI Inspect evaluation with the generated data")
            print(f"4. Analyze results for bystander effect patterns")
        else:
            print("\n❌ No scenarios generated. Check API key and rate limits.")
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        print("\nTroubleshooting tips:")
        if config.provider == "gemini":
            print("1. Check your GOOGLE_API_KEY or GEMINI_API_KEY is set correctly")
            print("2. Ensure you have sufficient API credits/quota")
            print("3. Install google-generativeai: pip install google-generativeai")
        else:
            print("1. Check your ANTHROPIC_API_KEY is set correctly")
            print("2. Ensure you have sufficient API credits")
        print("4. Reduce batch_size and limit_scenarios in config")
        print("5. Check your rate limit tier in the API console")
        print("6. Try switching providers by setting LLM_PROVIDER environment variable")

if __name__ == "__main__":
    main()