import os
import json
import argparse
import sys
from datetime import datetime
from config import Config
from llm_evaluator import (
    DEFAULT_RPM, RESPONSES_JSONL, LLMEvaluator, Scenario, LLMResponse, load_responses_jsonl, summarize_run,
)
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
    parser.add_argument('--models', nargs='+', required=True,
                       help='Models to evaluate, e.g. gemini-3.5-flash-lite claude-... gpt-...')
    parser.add_argument('--output-dir', type=str,
                       help='Output directory for results (default: evaluation_<timestamp>)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of scenarios to evaluate (for testing)')
    parser.add_argument('--resume', metavar='OUTPUT_DIR', type=str,
                       help=f'Continue a previous run in OUTPUT_DIR: skip (model, scenario) pairs '
                            f'already in its {RESPONSES_JSONL} and evaluate the rest')
    parser.add_argument('--rpm', type=float, default=DEFAULT_RPM,
                       help=f'Max requests per minute per model (client-side; default {DEFAULT_RPM}; 0 = unlimited)')
    
    args = parser.parse_args()

    if args.resume:
        if not os.path.isdir(args.resume):
            parser.error(f"--resume: output directory not found: {args.resume}")
        if args.output_dir and os.path.abspath(args.output_dir) != os.path.abspath(args.resume):
            parser.error("--resume already sets the output directory; drop --output-dir or make them match")
        output_dir = args.resume
    else:
        output_dir = args.output_dir or f'evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    # Initialize configuration
    config = Config()
    config.MODELS_TO_EVALUATE = args.models
    config.OUTPUT_DIR = output_dir
    config.RPM = args.rpm
    
    print("=" * 60)
    print("BYSTANDER EFFECT LLM EVALUATION")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"- Output directory: {config.OUTPUT_DIR}")
    print(f"- Models: {', '.join(config.MODELS_TO_EVALUATE)}")
    print(f"- Temperature: {config.TEMPERATURE}")
    print(f"- Rate limit: {config.RPM:g} requests/min per model" if config.RPM else "- Rate limit: none")
    
    # Load scenarios
    scenarios = load_scenarios(args.scenarios_file)
    
    if args.limit:
        scenarios = scenarios[:args.limit]
        print(f"⚠ Limited to {args.limit} scenarios for testing")
    
    # Resume: load responses already saved in the output dir's JSONL
    existing = None
    jsonl_path = os.path.join(config.OUTPUT_DIR, RESPONSES_JSONL)
    if args.resume:
        existing = load_responses_jsonl(jsonl_path)
        n_saved = sum(len(v) for v in existing.values())
        if n_saved:
            print(f"\n✓ Resuming from {jsonl_path} ({n_saved} saved responses)")
        else:
            print(f"\n⚠ No saved responses in {jsonl_path}; evaluating everything")

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
              f"--models {' '.join(config.MODELS_TO_EVALUATE)} --resume {config.OUTPUT_DIR}"
              + (f" --limit {args.limit}" if args.limit else "")
              + (f" --rpm {args.rpm:g}" if args.rpm != DEFAULT_RPM else ""))
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