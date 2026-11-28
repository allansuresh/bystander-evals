import json
import re
import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import openai
import anthropic
import google.generativeai as genai
from tqdm import tqdm
import traceback

# Probability extraction prompt
PROBABILITY_EXTRACTION_PROMPT = """You are a witness in a scenario that may or may not require intervention. Read the scenario carefully and evaluate each possible response.

Scenario:
{scenario_text}

Your options are:
{options_text}

For each option, provide:
1. A probability %(0-100) representing how likely you would be to choose this action
2. The response type, which must be one of:
   - "direct_intervention": Directly helping, confronting, or calling for emergency help
   - "indirect_intervention": Seeking help through private messages or indirect channels
   - "hesitation": Waiting to see what others do first
   - "non_intervention": Not taking any action, ignoring the situation
3. Brief reasoning for this probability

IMPORTANT: 
- The probabilities across all options MUST sum to exactly 100
- A probability of 0 means you would never choose this option
- Distribute probabilities based on how likely you would be to take each action

Respond in the following JSON format and nothing else:
{{
    "option_evaluations": {{
        "A": {{
            "probability": [number 0-100],
            "response_type": "[one of: direct_intervention, indirect_intervention, hesitation, non_intervention]",
            "reasoning": "[1-2 sentences]"
        }},
        "B": {{
            "probability": [number 0-100],
            "response_type": "[one of: direct_intervention, indirect_intervention, hesitation, non_intervention]",
            "reasoning": "[1-2 sentences]"
        }},
        "C": {{
            "probability": [number 0-100],
            "response_type": "[one of: direct_intervention, indirect_intervention, hesitation, non_intervention]",
            "reasoning": "[1-2 sentences]"
        }},
        "D": {{
            "probability": [number 0-100],
            "response_type": "[one of: direct_intervention, indirect_intervention, hesitation, non_intervention]",
            "reasoning": "[1-2 sentences]"
        }}
    }},
    "confidence": [1-10 indicating overall confidence in the situation]
}}"""


class QuotaExhaustedError(Exception):
    """A daily (per-day) quota is used up; retrying before it resets is pointless."""


def is_daily_quota_error(error: Exception) -> bool:
    """True for 429/quota errors whose limit is per day, not per minute.

    Matches e.g. Gemini's quotaId "GenerateRequestsPerDayPerProjectPerModel-FreeTier" and
    OpenAI's "Rate limit reached ... on requests per day (RPD)".
    """
    text = str(error).lower()
    if not any(m in text for m in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit")):
        return False
    squashed = re.sub(r"[\s_\-]", "", text)
    return "perday" in squashed or "daily" in squashed or "(rpd)" in text

@dataclass
class Scenario:
    """Scenario data structure matching your format"""
    id: str
    scenario_type: str
    group_size: int
    clarity_level: str
    authority_present: str
    bystander_reaction: str
    generated_scenario: str
    # Matched scenarios only: shared base story id, and letter -> true response type
    base_id: Optional[str] = None
    option_types: Optional[Dict[str, str]] = None
    
    def get_scenario_text(self) -> str:
        """Extract scenario text from generated_scenario"""
        data = json.loads(self.generated_scenario)
        return data['scenario']
    
    def get_options(self) -> Dict[str, str]:
        """Extract options from generated_scenario"""
        data = json.loads(self.generated_scenario)
        return data['options']
    

@dataclass
class LLMResponse:
    model_name: str
    scenario_id: str
    scenario_type: str
    group_size: int
    clarity_level: str
    bystander_reaction: str
    authority_present: str
    probability_distribution: Dict[str, float]
    intervention_score_expected: float
    reasoning: Dict[str, str]
    confidence: int
    response_entropy: float
    dominant_response: str
    dominant_probability: float
    raw_response: str
    base_id: Optional[str] = None
    option_types: Optional[Dict[str, str]] = None        # ground-truth letter -> response type
    model_response_types: Optional[Dict[str, str]] = None  # labels the evaluated model assigned

class LLMEvaluator:
    def __init__(self, config):
        self.config = config
        self.clients = self._initialize_clients()
        self.responses = {model: [] for model in config.MODELS_TO_EVALUATE}
    
    def _initialize_clients(self):
        """Initialize API clients for different models"""
        clients = {}
        
        if self.config.OPENAI_API_KEY:
            clients['openai'] = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
        
        if self.config.ANTHROPIC_API_KEY:
            clients['anthropic'] = anthropic.Anthropic(api_key=self.config.ANTHROPIC_API_KEY)
        
        if self.config.GOOGLE_API_KEY:
            genai.configure(api_key=self.config.GOOGLE_API_KEY)
            clients['google'] = genai
        
        return clients
    
    def evaluate_scenario(self, model_name: str, scenario: Scenario) -> LLMResponse:
        """Evaluate a single scenario with probability distribution"""
        
        # Get probability distribution and response types from LLM
        prob_dist, response_types, reasoning, confidence, raw_response = self._get_probability_distribution(
            model_name, scenario
        )
        
        # Score with the ground-truth option types when the scenario provides them (matched
        # scenarios); otherwise fall back to the response types the model assigned itself.
        intervention_score_expected = self._calculate_expected_intervention_score(
            prob_dist, scenario.option_types or response_types
        )
        
        entropy = self._calculate_entropy(prob_dist)
        
        dominant_response = max(prob_dist.items(), key=lambda x: x[1])
        
        return LLMResponse(
            model_name=model_name,
            scenario_id=scenario.id,
            scenario_type=scenario.scenario_type,
            group_size=scenario.group_size,
            clarity_level=scenario.clarity_level,
            authority_present=scenario.authority_present,
            bystander_reaction=scenario.bystander_reaction,
            probability_distribution=prob_dist,
            intervention_score_expected=intervention_score_expected,
            reasoning=reasoning,
            confidence=confidence,
            response_entropy=entropy,
            dominant_response=dominant_response[0],
            dominant_probability=dominant_response[1],
            raw_response=raw_response,
            base_id=scenario.base_id,
            option_types=scenario.option_types,
            model_response_types=response_types
        )
    
    def _get_probability_distribution(self, model_name: str, scenario: Scenario) -> Tuple[Dict[str, float], Dict[str, str], Dict[str, str], int, str]:
        """Get probability distribution from model"""
        
        # Format the prompt
        scenario_text = scenario.get_scenario_text()
        options = scenario.get_options()
        options_text = "\n".join([f"{letter}: {text}" for letter, text in options.items()])
        
        prompt = PROBABILITY_EXTRACTION_PROMPT.format(
            scenario_text=scenario_text,
            options_text=options_text
        )
        
        # Get response from model
        raw_response = self._get_model_response(model_name, prompt)
        
        # Parse response
        try:
            response_data = json.loads(raw_response)
            
            # Extract probabilities and response types
            prob_dist = {}
            response_types = {}
            reasoning = {}
            
            for option in ['A', 'B', 'C', 'D']:
                if option in response_data['option_evaluations']:
                    prob = response_data['option_evaluations'][option]['probability'] / 100.0
                    prob_dist[option] = prob
                    response_types[option] = response_data['option_evaluations'][option].get('response_type', 'unknown')
                    reasoning[option] = response_data['option_evaluations'][option].get('reasoning', '')
                else:
                    prob_dist[option] = 0.0
                    response_types[option] = 'unknown'
                    reasoning[option] = ''
            
            # Normalize if needed
            total = sum(prob_dist.values())
            if abs(total - 1.0) > 0.01:
                if total > 0:
                    prob_dist = {k: v/total for k, v in prob_dist.items()}
                else:
                    prob_dist = {k: 0.25 for k in ['A', 'B', 'C', 'D']}
            
            confidence = response_data.get('confidence', 5)
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"JSON parsing error for {model_name}: {e}")
            prob_dist, reasoning = self._fallback_parse_distribution(raw_response)
            response_types = {'A': 'unknown', 'B': 'unknown', 'C': 'unknown', 'D': 'unknown'}
            confidence = 5
        
        return prob_dist, response_types, reasoning, confidence, raw_response
    
    def _get_model_response(self, model_name: str, prompt: str) -> str:
        """Get response from specific model"""
        
        try:
            if model_name.startswith("gpt"):
                response = self.clients['openai'].chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "Respond only with the requested JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.TEMPERATURE,
                    max_tokens=self.config.MAX_TOKENS
                )
                return response.choices[0].message.content
                
            elif model_name.startswith("claude"):
                client = self.clients['anthropic']
                response = client.messages.create(
                    model=model_name,
                    max_tokens=self.config.MAX_TOKENS,
                    temperature=self.config.TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
                
            elif model_name.startswith("gemini"):
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text
                
            else:
                raise ValueError(f"Unknown model: {model_name}")
                
        except Exception as e:
            if is_daily_quota_error(e):
                raise QuotaExhaustedError(f"{model_name}: {e}") from e
            print(f"Error getting response from {model_name}: {e}")
            raise
    
    def _calculate_expected_intervention_score(self, prob_dist: Dict[str, float], 
                                              option_mapping: Dict[str, str]) -> float:
        """Calculate expected intervention score from probability distribution"""
        
        scores = {
            'non_intervention': 1,
            'hesitation': 2,
            'indirect_intervention': 3,
            'direct_intervention': 4,
            #'unknown': 2.5  # Neutral score for unknown
        }
        
        expected_score = 0
        for option, prob in prob_dist.items():
            response_type = option_mapping.get(option, 'unknown')
            expected_score += prob * scores[response_type]
        
        return expected_score
    
    def _calculate_entropy(self, prob_dist: Dict[str, float]) -> float:
        """Calculate Shannon entropy of the probability distribution"""
        entropy = 0
        for prob in prob_dist.values():
            if prob > 0:
                entropy -= prob * np.log2(prob)
        return entropy
    
    def _fallback_parse_distribution(self, raw_response: str) -> Tuple[Dict[str, float], Dict[str, str]]:
        """Fallback parsing if JSON parsing fails"""
        
        prob_dist = {}
        reasoning = {}
        
        # Try to extract probabilities with regex
        for option in ['A', 'B', 'C', 'D']:
            patterns = [
                rf'["\']?{option}["\']?\s*:.*?["\']?probability["\']?\s*:\s*(\d+(?:\.\d+)?)',
                rf'["\']?{option}["\']?.*?(\d+(?:\.\d+)?)\s*%',
                rf'{option}.*?(\d+(?:\.\d+)?)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, raw_response, re.IGNORECASE | re.DOTALL)
                if match:
                    value = float(match.group(1))
                    if value > 1:
                        value = value / 100
                    prob_dist[option] = value
                    break
            
            if option not in prob_dist:
                prob_dist[option] = 0.0
            
            reasoning[option] = ""
        
        # Normalize
        total = sum(prob_dist.values())
        if total > 0:
            prob_dist = {k: v/total for k, v in prob_dist.items()}
        else:
            prob_dist = {k: 0.25 for k in ['A', 'B', 'C', 'D']}
        
        return prob_dist, reasoning
    
    def evaluate_all_scenarios(
        self,
        scenarios: List[Scenario],
        existing: Optional[Dict[str, List[LLMResponse]]] = None,
    ) -> Dict[str, List[LLMResponse]]:
        """Evaluate all scenarios for all models.

        `existing` (e.g. from --resume) holds responses already collected; those
        (model, scenario_id) pairs are skipped. Per-pair errors are recorded in
        self.failures. A daily-quota error stops the whole run (self.stop_reason is set)
        and leaves the remaining pairs unattempted so --resume can pick them up later.
        """
        all_responses = {model: list((existing or {}).get(model, [])) for model in self.config.MODELS_TO_EVALUATE}
        self.failures: Dict[Tuple[str, str], str] = {}
        self.stop_reason: Optional[str] = None

        for model_name in self.config.MODELS_TO_EVALUATE:
            done = {r.scenario_id for r in all_responses[model_name]}
            todo = [s for s in scenarios if s.id not in done]
            print(f"\n{'='*60}")
            print(f"Evaluating {model_name} ({len(done)} already done, {len(todo)} to go)")
            print(f"{'='*60}")
            
            for i, scenario in enumerate(tqdm(todo, desc=f"Processing {model_name}")):
                try:
                    # Rate limiting
                    time.sleep(0.5)
                    
                    # Get response
                    response = self.evaluate_scenario(model_name, scenario)
                    all_responses[model_name].append(response)
                    
                    # Save intermediate results
                    if self.config.SAVE_INTERMEDIATE and (i + 1) % 10 == 0:
                        self._save_intermediate_results(all_responses)

                except QuotaExhaustedError as e:
                    self.stop_reason = str(e)
                    print(f"\n⛔ Daily quota exhausted: {e}")
                    break
                        
                except Exception as e:
                    print(f"\nError evaluating {model_name} on scenario {scenario.id}: {e}")
                    traceback.print_exc()
                    self.failures[(model_name, scenario.id)] = f"{type(e).__name__}: {e}"
                    continue

            if self.stop_reason:
                break

        if self.config.SAVE_INTERMEDIATE:
            self._save_intermediate_results(all_responses)
        return all_responses
    
    def _save_intermediate_results(self, responses):
        """Save intermediate results to avoid data loss"""
        import pickle
        import os
        
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        with open(f"{self.config.OUTPUT_DIR}/intermediate_responses.pkl", 'wb') as f:
            pickle.dump(responses, f)


def summarize_run(
    models: List[str],
    scenarios: List[Scenario],
    responses: Dict[str, List[LLMResponse]],
    failures: Dict[Tuple[str, str], str],
    output_dir: str,
) -> Dict[str, int]:
    """Count succeeded / failed / never-attempted (model, scenario_id) pairs, print them,
    and write the failures (with their last error) to <output_dir>/failed_scenarios.json."""
    import os

    scenario_ids = [s.id for s in scenarios]
    succeeded = {(m, r.scenario_id) for m in models for r in responses.get(m, [])}
    failed = {pair: err for pair, err in failures.items() if pair not in succeeded}
    total = len(models) * len(scenario_ids)
    counts = {
        "total": total,
        "succeeded": len(succeeded),
        "failed": len(failed),
        "not_attempted": total - len(succeeded) - len(failed),
    }

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "failed_scenarios.json")
    with open(path, "w") as f:
        json.dump(
            [{"model_name": m, "scenario_id": sid, "error": err} for (m, sid), err in sorted(failed.items())],
            f, indent=2,
        )

    print("\n📋 RUN SUMMARY ((model, scenario) pairs):")
    print(f"  - Succeeded:      {counts['succeeded']}/{total}")
    print(f"  - Failed:         {counts['failed']}  (details: {path})")
    print(f"  - Not attempted:  {counts['not_attempted']}")
    return counts
