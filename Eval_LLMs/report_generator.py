import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, Any
import numpy as np

class ReportGenerator:
    def __init__(self, metrics: Dict[str, Dict], responses: Dict, output_dir: str):
        self.metrics = metrics
        self.responses = responses
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
    
    def generate_full_report(self):
        """Generate complete report with visualizations"""
        
        print("\nGenerating reports and visualizations...")
        
        # Generate text report
        self._generate_text_report()
        
        # Generate visualizations
        self._generate_visualizations()
        
        # Generate JSON report
        self._generate_json_report()
        
        # Generate CSV summaries
        self._generate_csv_summaries()
        
        print(f"✓ Report generated in {self.output_dir}/")
    
    def _generate_text_report(self):
        """Generate markdown text report"""
        report = []
        report.append(f"# Bystander Effect LLM Evaluation Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Executive Summary
        report.append("## Executive Summary\n")
        report.append(self._generate_executive_summary())
        
        # Individual Model Analysis
        report.append("\n## Individual Model Analysis\n")
        for model_name, metrics in self.metrics.items():
            if model_name == 'comparative':
                continue
            report.append(self._generate_model_section(model_name, metrics))
        
        # Comparative Analysis
        report.append("\n## Comparative Analysis\n")
        report.append(self._generate_comparative_section())
        
        # Save report
        with open(f"{self.output_dir}/evaluation_report.md", 'w') as f:
            f.write('\n'.join(report))
    
    def _generate_executive_summary(self) -> str:
        """Generate executive summary"""
        summary = []
        
        # Count models showing bystander effect
        models_with_effect = 0
        for model, metrics in self.metrics.items():
            if model != 'comparative':
                if metrics.get('statistical', {}).get('bystander_effect_present', False):
                    models_with_effect += 1
        
        total_models = len([m for m in self.metrics.keys() if m != 'comparative'])
        
        summary.append(f"- **Models Evaluated**: {total_models}")
        summary.append(f"- **Models Showing Bystander Effect**: {models_with_effect}/{total_models}")
        
        # Find strongest and weakest effect
        dri_scores = {}
        for model, metrics in self.metrics.items():
            if model != 'comparative' and metrics.get('primary', {}).get('DRI') is not None:
                dri_scores[model] = metrics['primary']['DRI']
        
        if dri_scores:
            strongest = max(dri_scores.items(), key=lambda x: x[1])
            weakest = min(dri_scores.items(), key=lambda x: x[1])
            summary.append(f"- **Strongest Bystander Effect**: {strongest[0]} (DRI: {strongest[1]:.3f})")
            summary.append(f"- **Weakest Bystander Effect**: {weakest[0]} (DRI: {weakest[1]:.3f})")
        
        return '\n'.join(summary)
    
    def _generate_model_section(self, model_name: str, metrics: Dict) -> str:
        """Generate report section for individual model"""
        section = [f"### {model_name}\n"]
        
        # Primary Metrics
        section.append("**Primary Metrics:**")
        primary = metrics.get('primary', {})
        if primary.get('WIS_global') is not None:
            section.append(f"- Weighted Intervention Score (WIS): {primary['WIS_global']:.3f}")
        if primary.get('DRI') is not None:
            section.append(f"- Diffusion of Responsibility Index (DRI): {primary['DRI']:.3f}")
        
        # Secondary Metrics
        section.append("\n**Secondary Metrics:**")
        secondary = metrics.get('secondary', {})
        ags = secondary.get('AGS', {})
        if ags.get('normalized') is not None:
            section.append(f"- Ambiguity Gap Score: {ags['normalized']:.1f}%")
        if secondary.get('ADS') is not None:
            section.append(f"- Authority Deference Score: {secondary['ADS']:.3f}")
        if secondary.get('RCS') is not None:
            section.append(f"- Response Consistency Score: {secondary['RCS']:.3f}")
        
        # Statistical Analysis
        section.append("\n**Statistical Analysis:**")
        stat = metrics.get('statistical', {})
        if stat.get('bystander_effect_present') is not None:
            section.append(f"- Bystander Effect Present: {'✓' if stat['bystander_effect_present'] else '✗'}")
        if stat.get('correlation') is not None and stat.get('correlation_p_value') is not None:
            section.append(f"- Group Size Correlation: {stat['correlation']:.3f} (p={stat['correlation_p_value']:.4f})")
        
        # Behavioral Patterns
        section.append("\n**Behavioral Patterns:**")
        behavioral = metrics.get('behavioral', {})
        if behavioral.get('intervention_tendency') is not None:
            section.append(f"- Intervention Tendency: {behavioral['intervention_tendency']:.1%}")
        if behavioral.get('average_confidence') is not None:
            section.append(f"- Average Confidence: {behavioral['average_confidence']:.1f}/10")
        
        # Uncertainty Metrics
        section.append("\n**Uncertainty Analysis:**")
        uncertainty = metrics.get('uncertainty', {})
        if uncertainty.get('average_entropy') is not None:
            section.append(f"- Average Decision Entropy: {uncertainty['average_entropy']:.3f}")
        if uncertainty.get('decisiveness') is not None:
            section.append(f"- Decisiveness: {uncertainty['decisiveness']:.1%}")
        
        return '\n'.join(section) + '\n'
    
    def _generate_comparative_section(self) -> str:
        """Generate comparative analysis section"""
        section = []
        
        if 'comparative' in self.metrics:
            comp = self.metrics['comparative']
            
            if 'rankings' in comp:
                section.append("### Model Rankings\n")
                
                if 'WIS' in comp['rankings']:
                    section.append("**By Weighted Intervention Score (WIS):**")
                    for i, (model, score) in enumerate(comp['rankings']['WIS'], 1):
                        section.append(f"{i}. {model}: {score:.3f}")
                
                if 'DRI' in comp['rankings']:
                    section.append("\n**By Diffusion of Responsibility Index (DRI):**")
                    for i, (model, score) in enumerate(comp['rankings']['DRI'], 1):
                        section.append(f"{i}. {model}: {score:.3f}")
        
        return '\n'.join(section)
    
    def _generate_visualizations(self):
        """Generate all visualizations"""
        
        # 1. Bystander Effect Curves
        self._plot_bystander_curves()
        
        # 2. Probability Distributions
        self._plot_probability_distributions()
        
        # 3. Metric Comparison Heatmap
        self._plot_metric_heatmap()
        
        # 4. Entropy Analysis
        self._plot_entropy_analysis()
    
    def _plot_bystander_curves(self):
        """Plot intervention rate vs group size for all models"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        for model_name, metrics in self.metrics.items():
            if model_name == 'comparative':
                continue
            
            wis_conditions = metrics.get('primary', {}).get('WIS_conditions', {})
            if not wis_conditions:
                continue
            
            # Extract group sizes and scores
            group_data = []
            for key, value in wis_conditions.items():
                if key.startswith('group_size_') and value is not None:
                    size = int(key.replace('group_size_', ''))
                    group_data.append((size, value))
            
            if group_data:
                group_data.sort()
                sizes, scores = zip(*group_data)
                ax.plot(sizes, scores, marker='o', label=model_name, linewidth=2)
        
        ax.set_xscale('log')
        ax.set_xlabel('Group Size (log scale)', fontsize=12)
        ax.set_ylabel('Weighted Intervention Score', fontsize=12)
        ax.set_title('Bystander Effect Curves: Intervention vs Group Size', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/bystander_curves.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_probability_distributions(self):
        """Plot probability distributions for each model"""
        models = [m for m in self.metrics.keys() if m != 'comparative']
        n_models = len(models)
        
        if n_models == 0:
            return
        
        # Determine subplot layout
        cols = 3
        rows = (n_models + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 5*rows))
        if rows == 1:
            axes = axes.reshape(1, -1)
        elif cols == 1:
            axes = axes.reshape(-1, 1)
        
        response_types = ['non_intervention', 'hesitation', 'indirect_intervention', 'direct_intervention']
        colors = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4']
        labels = ['Non-Int', 'Hesitate', 'Indirect', 'Direct']
        
        for idx, model in enumerate(models):
            row = idx // cols
            col = idx % cols
            ax = axes[row, col]
            
            avg_probs = self.metrics[model].get('behavioral', {}).get('average_probabilities', {})
            if avg_probs:
                values = [avg_probs.get(rt, 0) for rt in response_types]
                
                bars = ax.bar(range(len(labels)), values, color=colors)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45)
                ax.set_ylabel('Probability')
                ax.set_title(f'{model}')
                ax.set_ylim(0, 1)
                
                # Add value labels
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{value:.1%}', ha='center', va='bottom')
        
        # Remove unused subplots
        for idx in range(n_models, rows * cols):
            row = idx // cols
            col = idx % cols
            fig.delaxes(axes[row, col])
        
        fig.suptitle('Average Response Probability Distributions', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/probability_distributions.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_metric_heatmap(self):
        """Plot heatmap of all metrics across models"""
        models = [m for m in self.metrics.keys() if m != 'comparative']
        
        if not models:
            return
        
        metric_names = ['WIS', 'DRI', 'AGS_norm', 'ADS', 'RCS']
        
        data = []
        for model in models:
            row = []
            m = self.metrics[model]
            
            # WIS
            wis = m.get('primary', {}).get('WIS_global')
            row.append(wis if wis is not None else 0)
            
            # DRI
            dri = m.get('primary', {}).get('DRI')
            row.append(dri if dri is not None else 0)
            
            # AGS normalized
            ags = m.get('secondary', {}).get('AGS', {}).get('normalized')
            row.append(ags/100 if ags is not None else 0)  # Normalize to 0-1
            
            # ADS
            ads = m.get('secondary', {}).get('ADS')
            row.append(abs(ads) if ads is not None else 0)
            
            # RCS
            rcs = m.get('secondary', {}).get('RCS')
            row.append(rcs if rcs is not None else 0)
            
            data.append(row)
        
        if data:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(data, annot=True, fmt='.2f', xticklabels=metric_names,
                       yticklabels=models, cmap='YlOrRd', cbar_kws={'label': 'Score'})
            ax.set_title('Metric Comparison Across Models', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/metric_heatmap.png", dpi=300, bbox_inches='tight')
            plt.close()
    
    def _plot_entropy_analysis(self):
        """Plot entropy-based analysis"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # 1. Entropy by group size
        ax1 = axes[0]
        
        for model_name, metrics in self.metrics.items():
            if model_name == 'comparative':
                continue
            
            entropy_by_size = metrics.get('uncertainty', {}).get('entropy_by_group_size', {})
            if entropy_by_size:
                sizes = sorted(entropy_by_size.keys())
                entropies = [entropy_by_size[s] for s in sizes]
                ax1.plot(sizes, entropies, marker='o', label=model_name)
        
        ax1.set_xscale('log')
        ax1.set_xlabel('Group Size (log scale)')
        ax1.set_ylabel('Response Entropy')
        ax1.set_title('Decision Uncertainty vs Group Size')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Decisiveness vs Intervention Tendency
        ax2 = axes[1]
        
        for model_name, metrics in self.metrics.items():
            if model_name == 'comparative':
                continue
            
            decisiveness = metrics.get('uncertainty', {}).get('decisiveness')
            intervention = metrics.get('behavioral', {}).get('intervention_tendency')
            
            if decisiveness is not None and intervention is not None:
                ax2.scatter(decisiveness, intervention, s=100, label=model_name)
                ax2.annotate(model_name, (decisiveness, intervention),
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        ax2.set_xlabel('Decisiveness (Avg Dominant Probability)')
        ax2.set_ylabel('Intervention Tendency')
        ax2.set_title('Model Decisiveness vs Intervention Tendency')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/entropy_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_json_report(self):
        """Save metrics as JSON for further analysis"""
        # Convert numpy types to native Python types for JSON serialization
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(v) for v in obj]
            else:
                return obj
        
        serializable_metrics = convert_to_serializable(self.metrics)
        
        with open(f"{self.output_dir}/metrics.json", 'w') as f:
            json.dump(serializable_metrics, f, indent=2, default=str)
    
    def _generate_csv_summaries(self):
        """Generate CSV summaries for easy analysis"""
        summary_data = []
        
        for model_name, metrics in self.metrics.items():
            if model_name == 'comparative':
                continue
            
            row = {
                'Model': model_name,
                'WIS_Global': metrics.get('primary', {}).get('WIS_global'),
                'DRI': metrics.get('primary', {}).get('DRI'),
                'AGS_Normalized': metrics.get('secondary', {}).get('AGS', {}).get('normalized'),
                'ADS': metrics.get('secondary', {}).get('ADS'),
                'RCS': metrics.get('secondary', {}).get('RCS'),
                'Bystander_Effect': metrics.get('statistical', {}).get('bystander_effect_present'),
                'Avg_Confidence': metrics.get('behavioral', {}).get('average_confidence'),
                'Avg_Entropy': metrics.get('uncertainty', {}).get('average_entropy'),
                'Decisiveness': metrics.get('uncertainty', {}).get('decisiveness')
            }
            summary_data.append(row)
        
        if summary_data:
            df = pd.DataFrame(summary_data)
            df.to_csv(f"{self.output_dir}/summary_metrics.csv", index=False)