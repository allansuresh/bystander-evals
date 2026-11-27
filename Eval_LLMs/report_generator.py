"""Minimal report generator for testing"""
import os
import json
from datetime import datetime

class ReportGenerator:
    def __init__(self, metrics, responses, output_dir):
        self.metrics = metrics
        self.responses = responses
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_full_report(self):
        # Generate text report
        report = []
        report.append(f"# Bystander Effect Evaluation Report")
        report.append(f"Generated: {datetime.now()}")
        report.append("")
        
        for model_name, model_metrics in self.metrics.items():
            if model_name == 'comparative':
                continue
            
            report.append(f"## {model_name}")
            report.append(f"- WIS Global: {model_metrics['primary']['WIS_global']:.3f}")
            
            if model_metrics['primary']['DRI'] is not None:
                report.append(f"- DRI: {model_metrics['primary']['DRI']:.3f}")
            
            report.append("")
        
        # Save report
        with open(f"{self.output_dir}/evaluation_report.md", 'w') as f:
            f.write("\n".join(report))
        
        # Save metrics as JSON
        with open(f"{self.output_dir}/metrics.json", 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)
        
        print(f"Reports saved to {self.output_dir}/")
