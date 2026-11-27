import os
import json
import argparse
import pickle
from datetime import datetime
from config import Config
from llm_evaluator import LLMEvaluator, Scenario, LLMResponse
from metrics_calculator import MetricsCalculator

def load_scenarios(scenarios_file: str) -> list[Scenario]:
    """Load scenarios from JSON file"""
    print(f"Loading scenarios from {scenarios_file}...")
    
    with open(scenarios_file, 'r') as f:
        scenarios_data = json.load(f)
    
    scenarios = []
    for s in scenarios_data:
        scenario = Scenario(
            id=s['id'],
            scenario_type=s['scenario_type'],
            group_size=s['group_size'],
            clarity_level=s['clarity_level'],
            authority_present=s['authority_present'],
            bystander_reaction=s['bystander_reaction'],
            generated_scenario=s['generated_scenario']
        )
        scenarios.append(scenario)
    
    print(f"✓ Loaded {len(scenarios)} scenarios")
    return scenarios

def main():
    parser = argparse.ArgumentParser(description='Evaluate LLMs for Bystander Effect')
    parser.add_argument('--scenarios-file', type=str, required=True,
                       help='Path to scenarios JSON file')
    parser.add_argument('--models', nargs='+',
                       help='Models to evaluate (overrides config)')
    parser.add_argument('--output-dir', type=str,
                       default=f'evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                       help='Output directory for results')
    parser.add_argument('--limit', type=int,
                       help='Limit number of scenarios to evaluate (for testing)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from intermediate results')
    
    args = parser.parse_args()
    
    # Initialize configuration
    config = Config()
    if args.models:
        config.MODELS_TO_EVALUATE = args.models
    config.OUTPUT_DIR = args.output_dir
    
    print("=" * 60)
    print("BYSTANDER EFFECT LLM EVALUATION")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"- Output directory: {config.OUTPUT_DIR}")
    print(f"- Models: {', '.join(config.MODELS_TO_EVALUATE)}")
    print(f"- Temperature: {config.TEMPERATURE}")
    
    # Load scenarios
    scenarios = load_scenarios(args.scenarios_file)
    
    if args.limit:
        scenarios = scenarios[:args.limit]
        print(f"⚠ Limited to {args.limit} scenarios for testing")
    
    # Check for intermediate results
    if args.resume and os.path.exists(f"{config.OUTPUT_DIR}/intermediate_responses.pkl"):
        print("\n✓ Resuming from intermediate results...")
        with open(f"{config.OUTPUT_DIR}/intermediate_responses.pkl", 'rb') as f:
            responses = pickle.load(f)
    else:
        # Evaluate LLMs
        print(f"\n2. Evaluating {len(config.MODELS_TO_EVALUATE)} models on {len(scenarios)} scenarios...")
        
        evaluator = LLMEvaluator(config)
        responses = evaluator.evaluate_all_scenarios(scenarios)
    
    # Save raw responses
    if config.SAVE_RAW_RESPONSES:
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        
        # Convert responses to serializable format
        serializable_responses = {}
        for model, model_responses in responses.items():
            serializable_responses[model] = [
                {
                    'model_name': r.model_name,
                    'scenario_id': r.scenario_id,
                    'scenario_type': r.scenario_type,
                    'group_size': r.group_size,
                    'clarity_level': r.clarity_level,
                    'authority_present': r.authority_present,
                    'probability_distribution': r.probability_distribution,
                    'intervention_score_expected': r.intervention_score_expected,
                    'reasoning': r.reasoning,
                    'confidence': r.confidence,
                    'key_factors': r.key_factors,
                    'response_entropy': r.response_entropy,
                    'dominant_response': r.dominant_response,
                    'dominant_probability': r.dominant_probability
                }
                for r in model_responses
            ]
        
        with open(f"{config.OUTPUT_DIR}/raw_responses.json", 'w') as f:
            json.dump(serializable_responses, f, indent=2)
        print(f"✓ Saved raw responses to {config.OUTPUT_DIR}/raw_responses.json")
    
    # Calculate metrics
    print("\n3. Calculating metrics...")
    calculator = MetricsCalculator(responses)
    metrics = calculator.calculate_all_metrics()
    

    
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print(f"Results saved to: {config.OUTPUT_DIR}/")
    print("=" * 60)
    
    # Print summary
    print("\n📊 QUICK SUMMARY:")
    for model_name, model_metrics in metrics.items():
        if model_name == 'comparative':
            continue
        
        primary = model_metrics.get('primary', {})
        statistical = model_metrics.get('statistical', {})
        behavioral = model_metrics.get('behavioral', {})
        
        print(f"\n{model_name}:")
        print(f"  - WIS: {primary.get('WIS_global', 'N/A'):.3f}" if primary.get('WIS_global') else "  - WIS: N/A")
        print(f"  - DRI: {primary.get('DRI', 'N/A'):.3f}" if primary.get('DRI') else "  - DRI: N/A")
        print(f"  - Bystander Effect: {'Present ✓' if statistical.get('bystander_effect_present') else 'Not detected ✗'}")
        intervention_tendency = behavioral.get('intervention_tendency')
        if intervention_tendency is not None:
            print(f"  - Intervention Tendency: {intervention_tendency:.1%}")
        else:
            print(f"  - Intervention Tendency: N/A")
            
if __name__ == "__main__":
    main()