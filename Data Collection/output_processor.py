"""
Handle output processing, file I/O, and format conversion
"""

import json
from typing import List, Dict, Any

class OutputProcessor:
    """Handles saving results and format conversion"""
    
    @staticmethod
    def save_batch_results(
        batch_results: List[Dict[str, Any]], 
        batch_num: int
    ) -> str:
        """Save intermediate batch results"""
        filename = f"bystander_scenarios_batch_{batch_num}.json"
        
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(batch_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Intermediate results saved: {filename}")
        return filename
    
    @staticmethod
    def save_combined_results(all_results: List[Dict[str, Any]]) -> str:
        """Save all combined results"""
        filename = "bystander_scenarios_all_batches.json"
        
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"✅ All results saved: {filename}")
        return filename
    
    @staticmethod
    def convert_for_inspect(results_list: List[Dict[str, Any]]) -> str:
        """Convert generated scenarios to AISI Inspect format"""
        scenarios_for_inspect = []

        for record in results_list:
            scenario_id = record.get("id", f"scenario_{len(scenarios_for_inspect)}")
            scenario_text = record.get("generated_scenario", "")
            
            # Parse the generated scenario if it's JSON
            try:
                parsed_scenario = json.loads(scenario_text)
                scenario_text_content = parsed_scenario.get("scenario", scenario_text)
                options_content = parsed_scenario.get("options", {})
            except json.JSONDecodeError:
                # If not valid JSON, use raw text
                scenario_text_content = scenario_text
                options_content = {}

            # Create metadata
            metadata = {
                "scenario_type": record.get("scenario_type"),
                "group_size": record.get("group_size"),
                "clarity_level": record.get("clarity_level"),
                "authority_present": record.get("authority_present"),
                "generated": True
            }

            scenarios_for_inspect.append({
                "id": scenario_id,
                "input": scenario_text_content,
                "options": options_content,
                "metadata": metadata
            })

        # Save for AISI Inspect
        filename = "bystander_scenarios_inspect.json"
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(scenarios_for_inspect, f, indent=2, ensure_ascii=False)

        print(f"✅ Converted {len(scenarios_for_inspect)} scenarios for AISI Inspect")
        print(f"📁 File saved: {filename}")

        # Print sample for verification
        if scenarios_for_inspect:
            sample = scenarios_for_inspect[0]
            print(f"\n📋 Sample scenario preview:")
            print(f"ID: {sample['id']}")
            print(f"Type: {sample['metadata']['scenario_type']}")
            print(f"Text: {sample['input'][:200]}...")
            print(f"Options: {sample['options']}")
        
        return filename
    
    @staticmethod
    def print_generation_statistics(results: List[Dict[str, Any]]):
        """Print statistics about generated scenarios"""
        print(f"\n📈 Generation statistics:")
        scenario_counts = {}
        
        for result in results:
            scenario_type = result.get('scenario_type', 'unknown')
            scenario_counts[scenario_type] = scenario_counts.get(scenario_type, 0) + 1
        
        for scenario_type, count in scenario_counts.items():
            print(f"   {scenario_type}: {count} scenarios")