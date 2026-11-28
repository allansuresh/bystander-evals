import os
import json
import argparse
import pickle
import sys
from datetime import datetime
from config import Config
from llm_evaluator import LLMEvaluator, Scenario, LLMResponse, summarize_run
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
            bystander_reaction=s.get('bystander_reaction'),
            generated_scenario=s['generated_scenario'],
            base_id=s.get('base_id'),
            option_types=s.get('option_types')
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
                       help='Resume from intermediate results in --output-dir: keep saved responses '
                            'and evaluate only the (model, scenario) pairs not yet done')
    
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
    existing = None
    intermediate_path = f"{config.OUTPUT_DIR}/intermediate_responses.pkl"
    if args.resume:
        if os.path.exists(intermediate_path):
            with open(intermediate_path, 'rb') as f:
                existing = pickle.load(f)
            n_saved = sum(len(v) for v in existing.values())
            print(f"\n✓ Resuming from {intermediate_path} ({n_saved} saved responses)")
        else:
            print(f"\n⚠ --resume given but {intermediate_path} not found; starting fresh")

    # Evaluate LLMs (skips pairs already in `existing`)
    print(f"\n2. Evaluating {len(config.MODELS_TO_EVALUATE)} models on {len(scenarios)} scenarios...")
    evaluator = LLMEvaluator(config)
    responses = evaluator.evaluate_all_scenarios(scenarios, existing=existing)
    
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
                    'base_id': r.base_id,
                    'scenario_type': r.scenario_type,
                    'group_size': r.group_size,
                    'clarity_level': r.clarity_level,
                    'authority_present': r.authority_present,
                    'bystander_reaction': r.bystander_reaction,
                    'option_types': r.option_types,
                    'model_response_types': r.model_response_types,
                    'probability_distribution': r.probability_distribution,
                    'intervention_score_expected': r.intervention_score_expected,
                    'reasoning': r.reasoning,
                    'confidence': r.confidence,
                    'response_entropy': r.response_entropy,
                    'dominant_response': r.dominant_response,
                    'dominant_probability': r.dominant_probability
                }
                for r in model_responses
            ]
        
        with open(f"{config.OUTPUT_DIR}/raw_responses.json", 'w') as f:
            json.dump(serializable_responses, f, indent=2)
        print(f"✓ Saved raw responses to {config.OUTPUT_DIR}/raw_responses.json")

    # Report succeeded / failed / not-attempted pairs and write failed_scenarios.json
    summarize_run(config.MODELS_TO_EVALUATE, scenarios, responses, evaluator.failures, config.OUTPUT_DIR)

    if evaluator.stop_reason:
        print("\n" + "=" * 60)
        print("RUN STOPPED: daily quota exhausted")
        print(f"  {evaluator.stop_reason}")
        print("  Progress is saved. After the quota resets, rerun with:")
        print(f"    python main.py --scenarios-file {args.scenarios_file} "
              f"--output-dir {config.OUTPUT_DIR} --resume"
              + (f" --models {' '.join(config.MODELS_TO_EVALUATE)}" if args.models else "")
              + (f" --limit {args.limit}" if args.limit else ""))
        print("=" * 60)
        sys.exit(3)
    
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