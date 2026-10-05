# """
# Fixed Report Generator - UTF-8 Encoding & Error Handling
# Handles unicode characters and special symbols properly
# """

# import json
# import csv
# from pathlib import Path
# from typing import Dict, List, Any
# from datetime import datetime
# import logging

# logger = logging.getLogger(__name__)


# class ReportGenerator:
#     """Generate reports in multiple formats with proper UTF-8 encoding"""
    
#     def __init__(self):
#         self.risk_thresholds = {
#             (0, 30): "Strong Buy",
#             (30, 50): "Buy",
#             (50, 70): "Hold",
#             (70, 85): "Cautious Hold",
#             (85, 100): "Avoid"
#         }
    
#     def calculate_risk_score(self, analysis_results: List[Dict]) -> int:
#         """Calculate overall risk score (0-100)"""
#         if not analysis_results:
#             return 50
        
#         # Count compliance levels
#         compliant = len([r for r in analysis_results if r.get('compliant') == 'Yes'])
#         partial = len([r for r in analysis_results if r.get('compliant') == 'Partial'])
#         non_compliant = len([r for r in analysis_results if r.get('compliant') == 'No'])
#         unknown = len([r for r in analysis_results if r.get('compliant') in ['Unknown', None]])
        
#         total = len(analysis_results)
        
#         # Risk calculation: higher compliance = lower risk
#         # Negative covenants (restrictions) that are non-compliant increase risk
#         # Positive covenants (requirements) that are non-compliant increase risk
        
#         negative_impact = non_compliant * 1.5  # Breaking rules is worse
#         partial_impact = partial * 0.5
#         unknown_impact = unknown * 0.3
        
#         risk_score = int((negative_impact + partial_impact + unknown_impact) / total * 100)
#         risk_score = max(0, min(100, risk_score))  # Clamp 0-100
        
#         return risk_score
    
#     def get_recommendation(self, risk_score: int) -> str:
#         """Convert risk score to investment recommendation"""
#         for (low, high), recommendation in self.risk_thresholds.items():
#             if low <= risk_score < high:
#                 return recommendation
#         return "Avoid"
    
#     def aggregate_results(self, analysis_results: List[Dict]) -> Dict[str, Any]:
#         """Aggregate individual covenant analyses"""
        
#         if not analysis_results:
#             return self._empty_aggregation()
        
#         compliant_count = len([r for r in analysis_results if r.get('compliant') == 'Yes'])
#         non_compliant_count = len([r for r in analysis_results if r.get('compliant') == 'No'])
#         partial_count = len([r for r in analysis_results if r.get('compliant') == 'Partial'])
#         unknown_count = len(analysis_results) - (compliant_count + non_compliant_count + partial_count)
        
#         positive_covenants = len([r for r in analysis_results if r.get('is_positive') == True])
#         negative_covenants = len([r for r in analysis_results if r.get('is_positive') == False])
        
#         confidences = [r.get('confidence', 0) for r in analysis_results 
#                       if isinstance(r.get('confidence'), (int, float))]
#         avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
#         risk_levels = [r.get('risk_level') for r in analysis_results]
#         high_risk = len([r for r in risk_levels if r == 'High'])
#         medium_risk = len([r for r in risk_levels if r == 'Medium'])
#         low_risk = len([r for r in risk_levels if r == 'Low'])
        
#         risk_score = self.calculate_risk_score(analysis_results)
#         recommendation = self.get_recommendation(risk_score)
        
#         return {
#             "summary": {
#                 "total_analyzed": len(analysis_results),
#                 "compliant": compliant_count,
#                 "non_compliant": non_compliant_count,
#                 "partial_compliance": partial_count,
#                 "unknown": unknown_count,
#                 "positive_covenants": positive_covenants,
#                 "negative_covenants": negative_covenants,
#                 "compliance_rate": round(compliant_count / len(analysis_results) * 100, 1) if analysis_results else 0,
#                 "avg_confidence": round(avg_confidence, 1),
#                 "high_risk_covenants": high_risk,
#                 "medium_risk_covenants": medium_risk,
#                 "low_risk_covenants": low_risk,
#                 "risk_score": risk_score,
#                 "recommendation": recommendation,
#                 "analysis_date": datetime.now().isoformat()
#             },
#             "covenants": analysis_results
#         }
    
#     def _empty_aggregation(self) -> Dict[str, Any]:
#         """Return empty aggregation structure"""
#         return {
#             "summary": {
#                 "total_analyzed": 0,
#                 "compliant": 0,
#                 "non_compliant": 0,
#                 "partial_compliance": 0,
#                 "unknown": 0,
#                 "positive_covenants": 0,
#                 "negative_covenants": 0,
#                 "compliance_rate": 0,
#                 "avg_confidence": 0,
#                 "high_risk_covenants": 0,
#                 "medium_risk_covenants": 0,
#                 "low_risk_covenants": 0,
#                 "risk_score": 50,
#                 "recommendation": "Hold",
#                 "analysis_date": datetime.now().isoformat()
#             },
#             "covenants": []
#         }
    
#     def generate_json_report(self, aggregated_results: Dict[str, Any], output_path: Path) -> None:
#         """Generate JSON report - UTF-8 encoded"""
#         try:
#             output_path.parent.mkdir(parents=True, exist_ok=True)
            
#             # Write with explicit UTF-8 encoding and proper indentation
#             with open(output_path, 'w', encoding='utf-8') as f:
#                 json.dump(aggregated_results, f, ensure_ascii=False, indent=2)
            
#             logger.info(f"✅ JSON report saved: {output_path}")
        
#         except Exception as e:
#             logger.error(f"❌ Failed to generate JSON report: {e}")
#             raise
    
#     def generate_markdown_report(self, aggregated_results: Dict[str, Any], output_path: Path) -> None:
#         """Generate Markdown report - UTF-8 encoded with safe characters"""
#         try:
#             output_path.parent.mkdir(parents=True, exist_ok=True)
            
#             summary = aggregated_results.get('summary', {})
#             covenants = aggregated_results.get('covenants', [])
            
#             # Build markdown with safe characters
#             lines = [
#                 "# Bond Covenant Analysis Report",
#                 "",
#                 f"**Analysis Date:** {summary.get('analysis_date', 'N/A')}",
#                 "",
#                 "## Executive Summary",
#                 "",
#                 f"**Investment Recommendation:** `{summary.get('recommendation', 'Hold')}`",
#                 "",
#                 f"**Overall Risk Score:** {summary.get('risk_score', 0)}/100",
#                 "",
#                 "### Key Metrics",
#                 "",
#                 f"| Metric | Value |",
#                 f"|--------|-------|",
#                 f"| Total Covenants Analyzed | {summary.get('total_analyzed', 0)} |",
#                 f"| Compliant | {summary.get('compliant', 0)} ({summary.get('compliance_rate', 0)}%) |",
#                 f"| Non-Compliant | {summary.get('non_compliant', 0)} |",
#                 f"| Partial Compliance | {summary.get('partial_compliance', 0)} |",
#                 f"| Unknown/Error | {summary.get('unknown', 0)} |",
#                 f"| Average Confidence | {summary.get('avg_confidence', 0)}% |",
#                 "",
#                 "### Risk Breakdown",
#                 "",
#                 f"| Risk Level | Count |",
#                 f"|------------|-------|",
#                 f"| High Risk | {summary.get('high_risk_covenants', 0)} |",
#                 f"| Medium Risk | {summary.get('medium_risk_covenants', 0)} |",
#                 f"| Low Risk | {summary.get('low_risk_covenants', 0)} |",
#                 "",
#                 "### Covenant Summary",
#                 "",
#                 f"| Category | Count |",
#                 f"|----------|-------|",
#                 f"| Positive Covenants | {summary.get('positive_covenants', 0)} |",
#                 f"| Negative Covenants | {summary.get('negative_covenants', 0)} |",
#                 "",
#                 "## Detailed Covenant Analysis",
#                 "",
#             ]
            
#             # Sort covenants by compliance status for better readability
#             compliant_covenants = [c for c in covenants if c.get('compliant') == 'Yes']
#             partial_covenants = [c for c in covenants if c.get('compliant') == 'Partial']
#             non_compliant_covenants = [c for c in covenants if c.get('compliant') == 'No']
#             unknown_covenants = [c for c in covenants if c.get('compliant') not in ['Yes', 'Partial', 'No']]
            
#             # Compliant covenants
#             if compliant_covenants:
#                 lines.extend([
#                     "### Compliant Covenants (Positive)",
#                     "",
#                 ])
#                 for cov in compliant_covenants[:10]:  # Show first 10
#                     lines.extend([
#                         f"**{cov.get('covenant_name', 'Unknown')}** (ID: {cov.get('covenant_id', 'N/A')})",
#                         f"- Status: ✅ Compliant",
#                         f"- Confidence: {cov.get('confidence', 0)}%",
#                         f"- Risk Level: {cov.get('risk_level', 'N/A')}",
#                         f"- Impact: {cov.get('investor_impact', 'N/A')}",
#                         "",
#                     ])
#                 if len(compliant_covenants) > 10:
#                     lines.append(f"... and {len(compliant_covenants) - 10} more compliant covenants\n")
            
#             # Partial compliance
#             if partial_covenants:
#                 lines.extend([
#                     "### Partial Compliance Covenants",
#                     "",
#                 ])
#                 for cov in partial_covenants[:5]:
#                     lines.extend([
#                         f"**{cov.get('covenant_name', 'Unknown')}** (ID: {cov.get('covenant_id', 'N/A')})",
#                         f"- Status: ⚠️ Partial Compliance",
#                         f"- Confidence: {cov.get('confidence', 0)}%",
#                         f"- Risk Level: {cov.get('risk_level', 'N/A')}",
#                         f"- Impact: {cov.get('investor_impact', 'N/A')}",
#                         "",
#                     ])
#                 if len(partial_covenants) > 5:
#                     lines.append(f"... and {len(partial_covenants) - 5} more partial compliance covenants\n")
            
#             # Non-compliant
#             if non_compliant_covenants:
#                 lines.extend([
#                     "### Non-Compliant Covenants (Risk)",
#                     "",
#                 ])
#                 for cov in non_compliant_covenants[:5]:
#                     lines.extend([
#                         f"**{cov.get('covenant_name', 'Unknown')}** (ID: {cov.get('covenant_id', 'N/A')})",
#                         f"- Status: ❌ Non-Compliant",
#                         f"- Confidence: {cov.get('confidence', 0)}%",
#                         f"- Risk Level: {cov.get('risk_level', 'N/A')}",
#                         f"- Impact: {cov.get('investor_impact', 'N/A')}",
#                         "",
#                     ])
#                 if len(non_compliant_covenants) > 5:
#                     lines.append(f"... and {len(non_compliant_covenants) - 5} more non-compliant covenants\n")
            
#             # Unknown
#             if unknown_covenants:
#                 lines.append(f"\n### Unclear/Error Covenants ({len(unknown_covenants)} total)\n")
            
#             # Recommendation logic
#             lines.extend([
#                 "## Investment Recommendation",
#                 "",
#                 f"### Overall Assessment: **{summary.get('recommendation', 'Hold').upper()}**",
#                 "",
#             ])
            
#             if summary.get('risk_score', 50) < 30:
#                 lines.append("This bond demonstrates strong covenant compliance with minimal risk factors.")
#             elif summary.get('risk_score', 50) < 50:
#                 lines.append("This bond shows good compliance with manageable risk levels.")
#             elif summary.get('risk_score', 50) < 70:
#                 lines.append("This bond has moderate covenant compliance with acceptable risk levels.")
#             elif summary.get('risk_score', 50) < 85:
#                 lines.append("This bond shows concerns regarding covenant compliance and elevated risk.")
#             else:
#                 lines.append("This bond has significant covenant compliance issues with high risk.")
            
#             lines.extend([
#                 "",
#                 f"**Risk Score:** {summary.get('risk_score', 0)}/100",
#                 f"**Compliance Rate:** {summary.get('compliance_rate', 0)}%",
#                 f"**Average Analysis Confidence:** {summary.get('avg_confidence', 0)}%",
#                 "",
#                 "---",
#                 "",
#                 f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
#             ])
            
#             report = "\n".join(lines)
            
#             # Write with explicit UTF-8 encoding
#             with open(output_path, 'w', encoding='utf-8') as f:
#                 f.write(report)
            
#             logger.info(f"✅ Markdown report saved: {output_path}")
        
#         except Exception as e:
#             logger.error(f"❌ Failed to generate Markdown report: {e}")
#             raise
    
#     def generate_csv_report(self, aggregated_results: Dict[str, Any], output_path: Path) -> None:
#         """Generate CSV report - UTF-8 encoded"""
#         try:
#             output_path.parent.mkdir(parents=True, exist_ok=True)
            
#             covenants = aggregated_results.get('covenants', [])
            
#             if not covenants:
#                 logger.warning("No covenants to export to CSV")
#                 return
            
#             # Prepare CSV rows
#             rows = []
#             for cov in covenants:
#                 rows.append({
#                     'Covenant ID': cov.get('covenant_id', 'N/A'),
#                     'Covenant Name': cov.get('covenant_name', 'N/A'),
#                     'Type': 'Positive' if cov.get('is_positive') else 'Negative',
#                     'Compliant': cov.get('compliant', 'Unknown'),
#                     'Confidence %': cov.get('confidence', 0),
#                     'Risk Level': cov.get('risk_level', 'N/A'),
#                     'Investor Impact': cov.get('investor_impact', 'N/A'),
#                     'Analysis': cov.get('analysis', 'N/A')
#                 })
            
#             # Write with explicit UTF-8 encoding
#             with open(output_path, 'w', encoding='utf-8', newline='') as f:
#                 writer = csv.DictWriter(f, fieldnames=rows[0].keys())
#                 writer.writeheader()
#                 writer.writerows(rows)
            
#             logger.info(f"✅ CSV report saved: {output_path}")
        
#         except Exception as e:
#             logger.error(f"❌ Failed to generate CSV report: {e}")
#             raise
    
#     def generate_all_reports(self, 
#                            analysis_results: List[Dict[str, Any]], 
#                            output_dir: Path) -> Dict[str, Path]:
#         """Generate all reports at once"""
        
#         output_dir.mkdir(parents=True, exist_ok=True)
        
#         # Aggregate results first
#         aggregated_results = self.aggregate_results(analysis_results)
        
#         # Generate reports
#         json_path = output_dir / "covenant_analysis_report.json"
#         md_path = output_dir / "covenant_analysis_report.md"
#         csv_path = output_dir / "covenant_summary.csv"
        
#         self.generate_json_report(aggregated_results, json_path)
#         self.generate_markdown_report(aggregated_results, md_path)
#         self.generate_csv_report(aggregated_results, csv_path)
        
#         logger.info(f"\n✅ All reports generated in: {output_dir}")
        
#         return {
#             "json": json_path,
#             "markdown": md_path,
#             "csv": csv_path
#         }

"""
Professional Report Generator for Kaggle Covenant Analysis
Formats output like your Gemini free tier report
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ProfessionalReportGenerator:
    """
    Generates professional reports from Kaggle covenant analysis
    Matches Gemini report format with detailed explanations
    """
    
    def __init__(self, output_dir: Path = None):
        """Initialize report generator"""
        self.output_dir = Path(output_dir) if output_dir else Path("phase3_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_markdown_report(self, analysis_results: List[Dict], 
                                bond_issuer: str = "Bond") -> Path:
        """Generate Markdown report matching Gemini format"""
        
        stats = self._calculate_stats(analysis_results)
        risk_score = self._calculate_risk_score(stats)
        recommendation = self._get_recommendation(risk_score)
        
        lines = []
        
        # Title and metadata
        lines.append("# BOND COVENANT ANALYSIS REPORT\n")
        lines.append(f"**Generated:** {datetime.now().isoformat()}\n")
        lines.append(f"**Bond Issuer:** {bond_issuer}\n")
        
        # Executive Summary
        lines.append("\n## EXECUTIVE SUMMARY\n")
        lines.append(f"Overall Risk Score: **{risk_score}/100**\n")
        lines.append(f"Investment Recommendation: **{recommendation}**\n")
        
        # Key Metrics
        lines.append("\n### Key Metrics\n\n")
        lines.append(f"- **Total Covenants Analyzed:** {stats['total']}\n")
        lines.append(f"- **Compliant:** {stats['compliant']} ({stats['compliant_pct']:.1f}%)\n")
        lines.append(f"- **Non-Compliant:** {stats['non_compliant']} ({stats['non_compliant_pct']:.1f}%)\n")
        lines.append(f"- **Partial Compliance:** {stats['partial']} ({stats['partial_pct']:.1f}%)\n")
        lines.append(f"- **Unclear Covenants:** {stats['unknown']} ({stats['unknown_pct']:.1f}%)\n")
        
        # Risk Assessment
        lines.append("\n### Risk Assessment\n\n")
        lines.append(f"- **High Risk Covenants:** {stats['high_risk']}\n")
        lines.append(f"- **Medium Risk Covenants:** {stats['medium_risk']}\n")
        lines.append(f"- **Low Risk Covenants:** {stats['low_risk']}\n")
        
        # Investment Recommendation
        lines.append("\n## INVESTMENT RECOMMENDATION\n\n")
        
        if recommendation == "STRONG BUY":
            lines.append("The bond demonstrates excellent covenant compliance. ")
            lines.append(f"{stats['compliant_pct']:.0f}% of covenants are satisfied with strong investor protections. ")
            lines.append("This is an excellent investment for conservative investors.\n")
        elif recommendation == "BUY":
            lines.append("The bond demonstrates solid covenant compliance. ")
            lines.append(f"{stats['compliant_pct']:.0f}% of covenants are satisfied with good investor protections. ")
            lines.append("This is a suitable investment for moderate risk appetite.\n")
        elif recommendation == "HOLD":
            lines.append("The bond shows mixed covenant compliance with moderate risk factors. ")
            lines.append("Investors should monitor closely for any deterioration.\n")
        else:
            lines.append("The bond shows concerning covenant compliance. ")
            lines.append("Exercise caution and monitor closely.\n")
        
        # Positive Findings
        compliant_covs = [r for r in analysis_results if r.get('status') == 'Compliant']
        if compliant_covs:
            lines.append("\n## POSITIVE FINDINGS\n\n")
            
            for i, cov in enumerate(compliant_covs[:8], 1):
                lines.append(f"\n{i}. **{cov['covenant_name']}**\n")
                lines.append(f"   - Status: Yes\n")
                lines.append(f"   - Confidence: {cov.get('confidence', 0)}%\n")
                
                explanation = cov.get('explanation', 'Covenant is satisfied')
                lines.append(f"   - Impact: {explanation[:180]}...\n")
        
        # Partial Compliance Findings
        partial_covs = [r for r in analysis_results if r.get('status') == 'Partial']
        if partial_covs:
            lines.append("\n## PARTIAL COMPLIANCE FINDINGS\n\n")
            
            for i, cov in enumerate(partial_covs[:5], 1):
                lines.append(f"\n{i}. **{cov['covenant_name']}**\n")
                lines.append(f"   - Status: Partial\n")
                lines.append(f"   - Confidence: {cov.get('confidence', 0)}%\n")
                
                explanation = cov.get('explanation', 'Partial compliance noted')
                lines.append(f"   - Explanation: {explanation[:180]}...\n")
        
        # Negative Findings
        non_compliant = [r for r in analysis_results if r.get('status') == 'Non-Compliant']
        if non_compliant:
            lines.append("\n## NEGATIVE FINDINGS\n\n")
            
            for i, cov in enumerate(non_compliant[:5], 1):
                lines.append(f"\n{i}. **{cov['covenant_name']}**\n")
                lines.append(f"   - Status: No\n")
                lines.append(f"   - Confidence: {cov.get('confidence', 0)}%\n")
                lines.append(f"   - Risk Level: {cov.get('risk_level', 'High')}\n")
                
                explanation = cov.get('explanation', 'Non-compliance noted')
                lines.append(f"   - Explanation: {explanation[:180]}...\n")
        
        # Key Risk Factors
        lines.append("\n## KEY RISK FACTORS\n\n")
        
        high_risk_covs = [r for r in analysis_results if r.get('risk_level') == 'High']
        if high_risk_covs:
            for cov in high_risk_covs[:5]:
                lines.append(f"- {cov['covenant_name']} ({cov.get('status', 'Unknown')})\n")
        else:
            lines.append("No high-risk covenants identified.\n")
        
        # Save
        report_path = self.output_dir / "covenant_analysis_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        logger.info(f"✅ Markdown report saved")
        return report_path
    
    def generate_json_report(self, analysis_results: List[Dict]) -> Path:
        """Generate JSON report"""
        
        stats = self._calculate_stats(analysis_results)
        risk_score = self._calculate_risk_score(stats)
        
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_covenants": stats['total']
            },
            "summary": {
                "risk_score": risk_score,
                "recommendation": self._get_recommendation(risk_score),
                "compliant": stats['compliant'],
                "non_compliant": stats['non_compliant'],
                "partial": stats['partial'],
                "unknown": stats['unknown'],
                "avg_confidence": stats['avg_confidence']
            },
            "covenants": [
                {
                    "id": r.get('covenant_id'),
                    "name": r.get('covenant_name'),
                    "status": r.get('status'),
                    "confidence": r.get('confidence'),
                    "risk_level": r.get('risk_level'),
                    "explanation": r.get('explanation', ''),
                    "investor_impact": r.get('investor_impact', ''),
                    "type": "positive" if r.get('is_positive') else "negative"
                }
                for r in analysis_results
            ]
        }
        
        report_path = self.output_dir / "covenant_analysis_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ JSON report saved")
        return report_path
    
    def generate_csv_report(self, analysis_results: List[Dict]) -> Path:
        """Generate CSV report"""
        
        report_path = self.output_dir / "covenant_summary.csv"
        
        with open(report_path, 'w', encoding='utf-8', newline='') as f:
            f.write("Covenant_ID,Name,Status,Confidence,Risk_Level,Type,Explanation\n")
            
            for r in analysis_results:
                covenant_id = r.get('covenant_id', '').replace(',', ';')
                name = r.get('covenant_name', '').replace(',', ';')
                status = r.get('status', '')
                confidence = r.get('confidence', 0)
                risk_level = r.get('risk_level', '')
                cov_type = 'Positive' if r.get('is_positive') else 'Negative'
                explanation = r.get('explanation', '').replace(',', ';')[:100]
                
                f.write(f'"{covenant_id}","{name}","{status}",{confidence},"{risk_level}","{cov_type}","{explanation}"\n')
        
        logger.info(f"✅ CSV report saved")
        return report_path
    
    def generate_all_reports(self, analysis_results: List[Dict], 
                            bond_issuer: str = "Bond") -> Dict[str, Path]:
        """Generate all reports"""
        
        logger.info("\n[STEP 6] GENERATING REPORTS")
        logger.info("-" * 70)
        
        try:
            markdown = self.generate_markdown_report(analysis_results, bond_issuer)
            json_file = self.generate_json_report(analysis_results)
            csv_file = self.generate_csv_report(analysis_results)
            
            logger.info(f"✅ All reports generated successfully")
            
            return {
                "markdown": markdown,
                "json": json_file,
                "csv": csv_file
            }
        
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            raise
    
    def _calculate_stats(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics"""
        
        total = len(results)
        
        compliant = len([r for r in results if r.get('status') == 'Compliant'])
        non_compliant = len([r for r in results if r.get('status') == 'Non-Compliant'])
        partial = len([r for r in results if r.get('status') == 'Partial'])
        unknown = total - (compliant + non_compliant + partial)
        
        confidences = [r.get('confidence', 0) for r in results if r.get('confidence', 0) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        high_risk = len([r for r in results if r.get('risk_level') == 'High'])
        medium_risk = len([r for r in results if r.get('risk_level') == 'Medium'])
        low_risk = len([r for r in results if r.get('risk_level') == 'Low'])
        
        return {
            'total': total,
            'compliant': compliant,
            'compliant_pct': (compliant / total * 100) if total > 0 else 0,
            'non_compliant': non_compliant,
            'non_compliant_pct': (non_compliant / total * 100) if total > 0 else 0,
            'partial': partial,
            'partial_pct': (partial / total * 100) if total > 0 else 0,
            'unknown': unknown,
            'unknown_pct': (unknown / total * 100) if total > 0 else 0,
            'avg_confidence': avg_confidence,
            'high_risk': high_risk,
            'medium_risk': medium_risk,
            'low_risk': low_risk
        }
    
    def _calculate_risk_score(self, stats: Dict) -> int:
        """Calculate risk score 0-100"""
        
        total = stats['total']
        if total == 0:
            return 50
        
        # Non-compliant = high risk
        non_compliant_score = (stats['non_compliant'] / total) * 50
        
        # Partial = medium risk
        partial_score = (stats['partial'] / total) * 20
        
        # High risk covenants
        high_risk_score = (stats['high_risk'] / total) * 20
        
        # Medium risk covenants
        medium_risk_score = (stats['medium_risk'] / total) * 10
        
        total_score = non_compliant_score + partial_score + high_risk_score + medium_risk_score
        
        return int(min(100, max(0, total_score)))
    
    def _get_recommendation(self, risk_score: int) -> str:
        """Get recommendation based on risk score"""
        
        if risk_score < 20:
            return "STRONG BUY"
        elif risk_score < 40:
            return "BUY"
        elif risk_score < 60:
            return "HOLD"
        elif risk_score < 80:
            return "SELL"
        else:
            return "AVOID"