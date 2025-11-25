"""
Master Domain Report - Cross-Domain Analysis

Generates a comprehensive report across all legal domains,
including overlap analysis and GSW processing priorities.
"""

import json
import sys
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analysis.domain_report_generator import DomainReportGenerator, DomainAnalysis


# ============================================================================
# MASTER REPORT GENERATOR
# ============================================================================

class MasterDomainReport:
    """Generates cross-domain analysis and master reports."""

    # GSW processing priority factors
    PRIORITY_WEIGHTS = {
        "existing_ontology": 3,      # Domain has existing ontology work
        "legal_importance": 2,       # High legal/social importance
        "volume_moderate": 2,        # Not too large, not too small
        "court_hierarchy": 1,        # High court decisions
        "temporal_coverage": 1,      # Good date range
    }

    # Domains with existing ontology work
    DOMAINS_WITH_ONTOLOGY = ["Family", "Criminal"]

    def __init__(self, domains_dir: Path, output_dir: Path):
        self.domains_dir = Path(domains_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.domain_generator = DomainReportGenerator(domains_dir, output_dir)

    def generate_master_report(
        self,
        analyses: Optional[Dict[str, DomainAnalysis]] = None
    ) -> str:
        """
        Generate the master cross-domain report.

        Args:
            analyses: Pre-computed domain analyses (or will compute)
        """
        if analyses is None:
            analyses = self.domain_generator.analyze_all_domains()

        # Calculate totals
        total_docs = sum(a.total_documents for a in analyses.values())

        # Generate report sections
        report = self._generate_header(total_docs, len(analyses))
        report += self._generate_domain_distribution(analyses, total_docs)
        report += self._generate_overlap_analysis()
        report += self._generate_priority_ranking(analyses)
        report += self._generate_recommendations(analyses)

        # Save report
        report_path = self.output_dir / "MASTER_DOMAIN_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        # Save JSON data
        json_path = self.output_dir / "master_data.json"
        json_data = self._generate_json_data(analyses)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)

        print(f"[Master Report] Saved to {report_path}")
        return report

    def _generate_header(self, total_docs: int, num_domains: int) -> str:
        """Generate report header."""
        return f"""# MASTER DOMAIN ANALYSIS REPORT

## Australian Legal Corpus - Complete Classification

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Documents** | {total_docs:,} |
| **Legal Domains** | {num_domains} |
| **Corpus Size** | ~8.8 GB |

This report provides cross-domain analysis of the Australian Legal Corpus,
identifying patterns, overlaps, and recommendations for GSW processing.

---

"""

    def _generate_domain_distribution(
        self,
        analyses: Dict[str, DomainAnalysis],
        total_docs: int
    ) -> str:
        """Generate domain distribution section."""
        report = """## 1. Domain Distribution

| Domain | Documents | % of Corpus | Primary Type | Date Range |
|--------|-----------|-------------|--------------|------------|
"""
        # Sort by document count
        sorted_domains = sorted(
            analyses.items(),
            key=lambda x: x[1].total_documents,
            reverse=True
        )

        for domain_name, analysis in sorted_domains:
            pct = (analysis.total_documents / total_docs) * 100 if total_docs > 0 else 0

            # Find primary document type
            primary_type = "N/A"
            if analysis.type_distribution:
                primary_type = max(
                    analysis.type_distribution.items(),
                    key=lambda x: x[1]
                )[0]

            date_range = f"{analysis.date_min or 'N/A'} - {analysis.date_max or 'N/A'}"

            report += f"| {domain_name} | {analysis.total_documents:,} | {pct:.1f}% | {primary_type} | {date_range} |\n"

        # Add visualization hint
        report += """
### Domain Size Visualization

```
"""
        max_count = max(a.total_documents for a in analyses.values()) if analyses else 1

        for domain_name, analysis in sorted_domains[:10]:
            bar_length = int((analysis.total_documents / max_count) * 40)
            bar = "█" * bar_length
            report += f"{domain_name:20} {bar} {analysis.total_documents:,}\n"

        report += """```

---

"""
        return report

    def _generate_overlap_analysis(self) -> str:
        """Generate overlap analysis section."""
        # Load overlap data from extraction statistics if available
        stats_path = self.domains_dir / "extraction_statistics.json"

        report = """## 2. Classification Quality Analysis

"""
        if stats_path.exists():
            with open(stats_path, 'r', encoding='utf-8') as f:
                stats = json.load(f)

            overlap = stats.get("overlap_stats", {})
            single = overlap.get("single_domain", 0)
            multi = overlap.get("multi_domain", 0)
            total = single + multi

            if total > 0:
                single_pct = (single / total) * 100
                multi_pct = (multi / total) * 100

                report += f"""### Classification Confidence

| Classification | Count | Percentage |
|----------------|-------|------------|
| Single Domain Match | {single:,} | {single_pct:.1f}% |
| Multi-Domain Match | {multi:,} | {multi_pct:.1f}% |

**Interpretation**: Documents matching multiple domains may require manual review
or represent genuinely cross-cutting legal matters.

"""
                # Top overlap pairs
                top_pairs = overlap.get("top_pairs", {})
                if top_pairs:
                    report += """### Top Domain Overlaps

| Domain Pair | Overlap Count |
|-------------|---------------|
"""
                    for pair, count in list(top_pairs.items())[:10]:
                        report += f"| {pair} | {count:,} |\n"

        else:
            report += """*Note: Run domain extraction to generate overlap statistics.*

"""

        report += """
---

"""
        return report

    def _generate_priority_ranking(
        self,
        analyses: Dict[str, DomainAnalysis]
    ) -> str:
        """Generate GSW processing priority ranking."""
        report = """## 3. GSW Processing Priority Ranking

Based on: existing infrastructure, legal importance, volume, and data quality.

| Rank | Domain | Priority Score | Rationale |
|------|--------|----------------|-----------|
"""
        # Calculate priority scores
        priorities = []

        for domain_name, analysis in analyses.items():
            score = 0
            rationale = []

            # Factor 1: Existing ontology
            if domain_name in self.DOMAINS_WITH_ONTOLOGY:
                score += self.PRIORITY_WEIGHTS["existing_ontology"] * 3
                rationale.append("Existing ontology")

            # Factor 2: Legal importance (Family, Criminal high priority)
            if domain_name in ["Family", "Criminal", "Constitutional"]:
                score += self.PRIORITY_WEIGHTS["legal_importance"] * 2
                rationale.append("High legal importance")

            # Factor 3: Moderate volume (not too big, not too small)
            if 1000 <= analysis.total_documents <= 50000:
                score += self.PRIORITY_WEIGHTS["volume_moderate"] * 2
                rationale.append("Manageable volume")
            elif analysis.total_documents < 1000:
                score += self.PRIORITY_WEIGHTS["volume_moderate"]
                rationale.append("Small volume - quick to process")

            # Factor 4: Court hierarchy (High Court, Full Court)
            high_courts = ['HCA', 'FCAFC', 'FamCAFC', 'NSWCA', 'NSWCCA']
            high_court_count = sum(
                analysis.court_codes.get(c, 0) for c in high_courts
            )
            if high_court_count > 100:
                score += self.PRIORITY_WEIGHTS["court_hierarchy"] * 2
                rationale.append("High court decisions")

            # Factor 5: Good temporal coverage
            if analysis.date_min and analysis.date_max:
                try:
                    year_min = int(analysis.date_min[:4])
                    year_max = int(analysis.date_max[:4])
                    if year_max - year_min > 10:
                        score += self.PRIORITY_WEIGHTS["temporal_coverage"]
                        rationale.append("Good temporal coverage")
                except:
                    pass

            priorities.append({
                "domain": domain_name,
                "score": score,
                "rationale": ", ".join(rationale) or "Standard processing",
                "docs": analysis.total_documents
            })

        # Sort by score
        priorities.sort(key=lambda x: x["score"], reverse=True)

        for rank, p in enumerate(priorities, 1):
            report += f"| {rank} | {p['domain']} | {p['score']} | {p['rationale']} |\n"

        report += """
---

"""
        return report

    def _generate_recommendations(
        self,
        analyses: Dict[str, DomainAnalysis]
    ) -> str:
        """Generate processing recommendations."""
        report = """## 4. Processing Recommendations

### Phase 1: Priority Domains (Immediate)

Focus on domains with existing infrastructure and high legal value:

1. **Family Law**
   - Existing ontology and schema
   - High social importance
   - Well-defined entity types (parties, children, assets)
   - Run full GSW pipeline with Reflexion

2. **Criminal Law**
   - Large volume but well-structured
   - Clear actor types (accused, victim, judge)
   - Track sentencing outcomes
   - Consider sub-domain splitting (Violence, Drugs, etc.)

### Phase 2: High-Volume Domains

3. **Administrative Law**
   - Largest domain - requires batch processing
   - Split into sub-domains (Migration, Social Security, etc.)
   - Migration cases have distinct patterns

4. **Tax Law**
   - Technical but structured
   - Track ATO rulings and tribunal decisions

### Phase 3: Specialized Domains

5. **Commercial/Property/Torts**
   - Moderate complexity
   - Focus on contract and negligence patterns

6. **Other Domains**
   - Constitutional, Procedural, Specialized
   - Lower priority due to volume or specificity

### Technical Recommendations

"""
        # Calculate total volume
        total_docs = sum(a.total_documents for a in analyses.values())
        large_domains = [
            (name, a.total_documents)
            for name, a in analyses.items()
            if a.total_documents > 30000
        ]

        if large_domains:
            report += "**Large Domain Handling**:\n"
            for name, count in large_domains:
                report += f"- {name} ({count:,} docs): Use streaming + checkpointing\n"
            report += "\n"

        report += """**Batch Size Recommendations**:
- Small domains (<5,000 docs): Process in single batch
- Medium domains (5,000-50,000): Batch size of 100-500
- Large domains (>50,000): Batch size of 50-100 with checkpoints

**API Cost Estimation**:
"""
        # Rough cost estimate (assuming ~$0.001 per 1K tokens, ~2K tokens per doc)
        estimated_cost = (total_docs * 2000 * 0.000001)
        report += f"- Estimated total tokens: ~{total_docs * 2000:,}\n"
        report += f"- Estimated API cost: ~${estimated_cost:,.2f} (at $1/1M tokens)\n"

        report += """
---

## 5. Next Steps

1. [ ] Run domain extraction on full corpus
2. [ ] Review per-domain reports for anomalies
3. [ ] Configure domain-specific ontology seeds
4. [ ] Begin Phase 1 GSW processing (Family, Criminal)
5. [ ] Establish evaluation benchmarks
6. [ ] Monitor extraction quality metrics

---

*Generated by Legal GSW Domain Analysis System*
"""
        return report

    def _generate_json_data(
        self,
        analyses: Dict[str, DomainAnalysis]
    ) -> Dict[str, Any]:
        """Generate JSON data for programmatic use."""
        return {
            "generated_at": datetime.now().isoformat(),
            "total_documents": sum(a.total_documents for a in analyses.values()),
            "domain_count": len(analyses),
            "domains": {
                name: {
                    "document_count": a.total_documents,
                    "type_distribution": a.type_distribution,
                    "jurisdiction_distribution": a.jurisdiction_distribution,
                    "date_range": {"min": a.date_min, "max": a.date_max},
                    "court_codes": a.court_codes
                }
                for name, a in analyses.items()
            }
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate master domain report")
    parser.add_argument(
        "--domains-dir", "-d",
        type=Path,
        default=Path("data/processed/domains"),
        help="Directory containing domain JSONL files"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("reports/domain_analysis"),
        help="Output directory for reports"
    )

    args = parser.parse_args()

    generator = MasterDomainReport(args.domains_dir, args.output_dir)
    generator.generate_master_report()


if __name__ == "__main__":
    main()
