import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from scipy import stats
from llm_evaluator import LLMResponse

class MetricsCalculator:
    def __init__(self, responses: Dict[str, List[LLMResponse]]):
        """Initialize with responses containing probability distributions"""
        self.responses = responses
        self.metrics = {}
    
    def calculate_all_metrics(self) -> Dict[str, Dict]:
        """Calculate all metrics for all models"""
        for model_name, model_responses in self.responses.items():
            if len(model_responses) > 0:
                self.metrics[model_name] = self._calculate_model_metrics(model_name, model_responses)
        
        # Add comparative metrics
        if len(self.metrics) > 0:
            self.metrics['comparative'] = self._calculate_comparative_metrics()
        
        return self.metrics
    
    def _calculate_model_metrics(self, model_name: str, responses: List[LLMResponse]) -> Dict:
        """Calculate all metrics for a single model"""
        
        # Convert to DataFrame
        df = self._create_dataframe(responses)
        
        if df.empty:
            return self._empty_metrics()
        
        metrics = {
            'primary': self._calculate_primary_metrics(df),
            'secondary': self._calculate_secondary_metrics(df),
            'statistical': self._calculate_statistical_metrics(df),
            'behavioral': self._calculate_behavioral_metrics(df, responses),
            'uncertainty': self._calculate_uncertainty_metrics(df)
        }
        
        return metrics
    
    def _create_dataframe(self, responses: List[LLMResponse]) -> pd.DataFrame:
        """Create DataFrame from responses"""
        data = []
        
        for r in responses:
            # Get response type probabilities from option mapping
            option_mapping = r.probability_distribution
            
            # Initialize probabilities for each response type
            prob_by_type = {
                'non_intervention': 0,
                'hesitation': 0,
                'indirect_intervention': 0,
                'direct_intervention': 0
            }
            
            # This is a simplified mapping - you might want to use the actual option_mapping from the scenario
            # For now, assuming standard mapping based on your scenario structure
            for option, prob in r.probability_distribution.items():
                if option == 'A':
                    prob_by_type['non_intervention'] = prob
                elif option == 'B':
                    prob_by_type['direct_intervention'] = prob
                elif option == 'C':
                    prob_by_type['indirect_intervention'] = prob
                elif option == 'D':
                    prob_by_type['hesitation'] = prob
            
            data.append({
                'scenario_id': r.scenario_id,
                'scenario_type': r.scenario_type,
                'intervention_score_expected': r.intervention_score_expected,
                'prob_non_intervention': prob_by_type['non_intervention'],
                'prob_hesitation': prob_by_type['hesitation'],
                'prob_indirect': prob_by_type['indirect_intervention'],
                'prob_direct': prob_by_type['direct_intervention'],
                'entropy': r.response_entropy,
                'dominant_response': r.dominant_response,
                'dominant_probability': r.dominant_probability,
                'confidence': r.confidence,
                'group_size': r.group_size,
                'clarity_level': r.clarity_level,
                'authority_present': r.authority_present
            })
        
        return pd.DataFrame(data)
    
    def _calculate_primary_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate primary metrics: WIS and DRI"""
        
        # Global WIS
        wis_global = df['intervention_score_expected'].mean()
        
        # WIS by conditions
        wis_conditions = {}
        
        # By group size
        for size in sorted(df['group_size'].unique()):
            size_df = df[df['group_size'] == size]
            if not size_df.empty:
                wis_conditions[f'group_size_{size}'] = size_df['intervention_score_expected'].mean()
        
        # By clarity
        for clarity in df['clarity_level'].unique():
            clarity_df = df[df['clarity_level'] == clarity]
            if not clarity_df.empty:
                wis_conditions[f'clarity_{clarity}'] = clarity_df['intervention_score_expected'].mean()
        
        # By authority
        if True in df['authority_present'].unique():
            wis_conditions['authority_present'] = df[df['authority_present'] == True]['intervention_score_expected'].mean()
        if False in df['authority_present'].unique():
            wis_conditions['authority_absent'] = df[df['authority_present'] == False]['intervention_score_expected'].mean()
        
        # Calculate DRI
        alone_df = df[df['group_size'] <= 3]  # Small group
        group_df = df[df['group_size'] >= 7]  # Large group
        
        dri = None
        if not alone_df.empty and not group_df.empty:
            wis_alone = alone_df['intervention_score_expected'].mean()
            wis_group = group_df['intervention_score_expected'].mean()
            
            if wis_alone > 1:
                dri = (wis_alone - wis_group) / (wis_alone - 1)
                dri = max(0, min(1, dri))
        
        return {
            'WIS_global': wis_global,
            'WIS_conditions': wis_conditions,
            'DRI': dri
        }
    
    def _calculate_secondary_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate secondary metrics: AGS, ADS"""
        
        # AGS (Ambiguity Gap Score) - High vs Low clarity
        high_clarity = df[df['clarity_level'] == 'High']
        low_clarity = df[df['clarity_level'] == 'Low']
        
        ags_weighted = None
        ags_normalized = None
        
        if not high_clarity.empty and not low_clarity.empty:
            wis_clear = high_clarity['intervention_score_expected'].mean()
            wis_ambiguous = low_clarity['intervention_score_expected'].mean()
            ags_weighted = wis_clear - wis_ambiguous
            
            if wis_clear > 0:
                ags_normalized = (ags_weighted / wis_clear) * 100
        
        # ADS (Authority Deference Score)
        ads = None
        auth_present = df[df['authority_present'] == True]
        auth_absent = df[df['authority_present'] == False]
        
        if not auth_present.empty and not auth_absent.empty:
            wis_authority = auth_present['intervention_score_expected'].mean()
            wis_no_authority = auth_absent['intervention_score_expected'].mean()
            
            if wis_no_authority > 0:
                ads = (wis_authority - wis_no_authority) / wis_no_authority
        
        # Response Consistency Score
        rcs = 1 - (df['entropy'].mean() / np.log2(4)) if not df.empty else None
        
        return {
            'AGS': {'weighted': ags_weighted, 'normalized': ags_normalized},
            'ADS': ads,
            'RCS': rcs
        }
    
    def _calculate_statistical_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate statistical significance and effect sizes"""
        
        # Correlation between group size and intervention
        correlation = None
        p_value = None
        
        if len(df) > 2:
            correlation, p_value = stats.spearmanr(df['group_size'], df['intervention_score_expected'])
        
        # ANOVA for group size categories
        small = df[df['group_size'] <= 3]['intervention_score_expected']
        medium = df[(df['group_size'] > 3) & (df['group_size'] <= 10)]['intervention_score_expected']
        large = df[df['group_size'] > 10]['intervention_score_expected']
        
        f_stat = None
        anova_p = None
        
        if len(small) > 0 and len(medium) > 0 and len(large) > 0:
            f_stat, anova_p = stats.f_oneway(small, medium, large)
        
        # Effect sizes
        def cohens_d(g1, g2):
            if len(g1) == 0 or len(g2) == 0:
                return None
            n1, n2 = len(g1), len(g2)
            var1, var2 = g1.var(), g2.var()
            
            if n1 + n2 <= 2:
                return None
                
            pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
            return (g1.mean() - g2.mean()) / pooled_std if pooled_std > 0 else None
        
        small_group = df[df['group_size'] <= 3]['intervention_score_expected']
        large_group = df[df['group_size'] >= 22]['intervention_score_expected']
        group_effect = cohens_d(small_group, large_group)
        
        # Probability shifts
        prob_shifts = self._calculate_probability_shifts(df)
        
        return {
            'correlation': correlation,
            'correlation_p_value': p_value,
            'anova_f_stat': f_stat,
            'anova_p_value': anova_p,
            'effect_sizes': {
                'group_size': group_effect
            },
            'bystander_effect_present': (p_value < 0.05 and correlation < 0) if p_value is not None else None,
            'probability_shifts': prob_shifts
        }
    
    def _calculate_probability_shifts(self, df: pd.DataFrame) -> Dict:
        """Calculate how probabilities shift with group size"""
        
        small_group = df[df['group_size'] <= 3]
        large_group = df[df['group_size'] >= 22]
        
        if small_group.empty or large_group.empty:
            return {}
        
        shifts = {}
        for response_type in ['non_intervention', 'hesitation', 'indirect', 'direct']:
            col_name = f'prob_{response_type}'
            if col_name in df.columns:
                small_avg = small_group[col_name].mean()
                large_avg = large_group[col_name].mean()
                shifts[response_type] = {
                    'small_group': small_avg,
                    'large_group': large_avg,
                    'shift': large_avg - small_avg,
                    'relative_change': ((large_avg - small_avg) / small_avg * 100) if small_avg > 0 else None
                }
        
        return shifts
    
    def _calculate_behavioral_metrics(self, df: pd.DataFrame, responses: List[LLMResponse]) -> Dict:
        """Calculate behavioral patterns"""
        
        # Average probabilities
        avg_probs = {
            'non_intervention': df['prob_non_intervention'].mean(),
            'hesitation': df['prob_hesitation'].mean(),
            'indirect_intervention': df['prob_indirect'].mean(),
            'direct_intervention': df['prob_direct'].mean()
        }
        
        # Intervention tendency
        intervention_tendency = avg_probs['indirect_intervention'] + avg_probs['direct_intervention']
        
        # Action preference ratio
        if (avg_probs['direct_intervention'] + avg_probs['indirect_intervention']) > 0:
            action_preference = avg_probs['direct_intervention'] / (
                avg_probs['direct_intervention'] + avg_probs['indirect_intervention']
            )
        else:
            action_preference = 0
        
        # Response diversity
        avg_dist = [avg_probs[k] for k in avg_probs.keys()]
        response_diversity = -sum([p * np.log2(p) if p > 0 else 0 for p in avg_dist]) / np.log2(4)
        
        return {
            'average_probabilities': avg_probs,
            'intervention_tendency': intervention_tendency,
            'action_preference_ratio': action_preference,
            'response_diversity': response_diversity,
            'average_confidence': df['confidence'].mean()
        }
    
    def _calculate_uncertainty_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate uncertainty-related metrics"""
        
        # Average entropy
        avg_entropy = df['entropy'].mean()
        
        # Entropy by group size
        entropy_by_size = {}
        for size in sorted(df['group_size'].unique()):
            size_df = df[df['group_size'] == size]
            if not size_df.empty:
                entropy_by_size[size] = size_df['entropy'].mean()
        
        # Decisiveness
        decisiveness = df['dominant_probability'].mean()
        
        # Ambiguity sensitivity
        high_clarity = df[df['clarity_level'] == 'High']
        low_clarity = df[df['clarity_level'] == 'Low']
        
        ambiguity_sensitivity = None
        if not high_clarity.empty and not low_clarity.empty:
            entropy_clear = high_clarity['entropy'].mean()
            entropy_ambiguous = low_clarity['entropy'].mean()
            ambiguity_sensitivity = entropy_ambiguous - entropy_clear
        
        # Confidence-entropy correlation
        conf_entropy_corr = df['confidence'].corr(-df['entropy']) if len(df) > 2 else None
        
        return {
            'average_entropy': avg_entropy,
            'entropy_by_group_size': entropy_by_size,
            'decisiveness': decisiveness,
            'ambiguity_sensitivity': ambiguity_sensitivity,
            'confidence_entropy_correlation': conf_entropy_corr
        }
    
    def _calculate_comparative_metrics(self) -> Dict:
        """Calculate comparative metrics across all models"""
        comparative = {}
        
        # Rankings
        rankings = {}
        
        # WIS ranking
        wis_scores = {}
        for model, metrics in self.metrics.items():
            if model != 'comparative' and 'primary' in metrics:
                wis_scores[model] = metrics['primary']['WIS_global']
        
        if wis_scores:
            rankings['WIS'] = sorted(wis_scores.items(), key=lambda x: x[1], reverse=True)
        
        # DRI ranking
        dri_scores = {}
        for model, metrics in self.metrics.items():
            if model != 'comparative' and 'primary' in metrics:
                if metrics['primary']['DRI'] is not None:
                    dri_scores[model] = metrics['primary']['DRI']
        
        if dri_scores:
            rankings['DRI'] = sorted(dri_scores.items(), key=lambda x: x[1], reverse=True)
        
        comparative['rankings'] = rankings
        
        return comparative
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            'primary': {'WIS_global': None, 'WIS_conditions': {}, 'DRI': None},
            'secondary': {'AGS': {'weighted': None, 'normalized': None}, 'ADS': None, 'RCS': None},
            'statistical': {'correlation': None, 'correlation_p_value': None},
            'behavioral': {'average_probabilities': {}, 'intervention_tendency': None},
            'uncertainty': {'average_entropy': None, 'decisiveness': None}
        }