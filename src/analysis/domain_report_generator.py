"""
Domain Report Generator - Per-Domain Analysis

Generates comprehensive analysis reports for each legal domain,
including statistics, patterns, and GSW preparation recommendations.
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DomainAnalysis:
    """Complete analysis for a single domain."""
    domain_name: str
    total_documents: int = 0

    # Distribution breakdowns
    type_distribution: Dict[str, int] = field(default_factory=dict)
    jurisdiction_distribution: Dict[str, int] = field(default_factory=dict)
    source_distribution: Dict[str, int] = field(default_factory=dict)
    category_breakdown: Dict[str, int] = field(default_factory=dict)

    # Temporal analysis
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    year_distribution: Dict[str, int] = field(default_factory=dict)

    # Text analysis
    text_lengths: List[int] = field(default_factory=list)

    # Citation analysis
    court_codes: Dict[str, int] = field(default_factory=dict)
    sample_citations: List[str] = field(default_factory=list)

    # Legal term frequency
    legal_terms: Dict[str, int] = field(default_factory=dict)

    def get_text_stats(self) -> Dict[str, float]:
        """Calculate text length statistics."""
        if not self.text_lengths:
            return {"min": 0, "max": 0, "mean": 0, "median": 0, "std": 0}

        return {
            "min": min(self.text_lengths),
            "max": max(self.text_lengths),
            "mean": statistics.mean(self.text_lengths),
            "median": statistics.median(self.text_lengths),
            "std": statistics.stdev(self.text_lengths) if len(self.text_lengths) > 1 else 0
        }


# ============================================================================
# REPORT GENERATOR
# ============================================================================

class DomainReportGenerator:
    """Generates analysis reports for each domain."""

    # Legal terms to track frequency
    LEGAL_TERMS = [
        # Family law
        "parenting order", "property settlement", "spousal maintenance",
        "best interests", "custody", "relocation", "family violence",
        # Criminal
        "sentencing", "conviction", "bail", "appeal", "guilty", "acquittal",
        # Administrative
        "judicial review", "procedural fairness", "visa", "migration",
        # Commercial
        "contract", "breach", "damages", "negligence", "liability",
        # General
        "evidence", "costs", "order", "judgment", "appeal"
    ]

    # Court code patterns
    COURT_PATTERNS = [
        (r'\[(\d{4})\]\s*([A-Z]{2,}(?:FC|CA|SC|DC|LC|AT|CAT)?)\s*\d+', 2),
        (r'([A-Z]{2,}(?:FC|CA|SC|DC|LC)?)\s*\d+', 1),
    ]

    def __init__(self, domains_dir: Path, output_dir: Path):
        self.domains_dir = Path(domains_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_domain(self, domain_name: str) -> DomainAnalysis:
        """
        Perform deep analysis on a single domain.

        Streams the domain JSONL file to collect statistics.
        """
        domain_file = self.domains_dir / f"{domain_name.lower()}.jsonl"

        if not domain_file.exists():
            print(f"[Warning] Domain file not found: {domain_file}")
            return DomainAnalysis(domain_name=domain_name)

        analysis = DomainAnalysis(domain_name=domain_name)

        print(f"[Analyzing] {domain_name}...")

        with open(domain_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    doc = json.loads(line)
                    self._analyze_document(doc, analysis, line_num)
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    if line_num < 10:  # Only log first few errors
                        print(f"  Error at line {line_num}: {e}")

                if line_num % 10000 == 0 and line_num > 0:
                    print(f"  Processed {line_num:,} documents...", end='\r')

        print(f"  Completed: {analysis.total_documents:,} documents")
        return analysis

    def _analyze_document(
        self,
        doc: Dict[str, Any],
        analysis: DomainAnalysis,
        line_num: int
    ) -> None:
        """Analyze a single document and update analysis."""
        analysis.total_documents += 1

        # Type distribution
        doc_type = doc.get('type', 'unknown')
        analysis.type_distribution[doc_type] = \
            analysis.type_distribution.get(doc_type, 0) + 1

        # Jurisdiction distribution
        jurisdiction = doc.get('jurisdiction', 'unknown')
        analysis.jurisdiction_distribution[jurisdiction] = \
            analysis.jurisdiction_distribution.get(jurisdiction, 0) + 1

        # Source distribution
        source = doc.get('source', 'unknown')
        analysis.source_distribution[source] = \
            analysis.source_distribution.get(source, 0) + 1

        # Category (from classification metadata)
        classification = doc.get('_classification', {})
        category = classification.get('primary_category', 'unknown')
        analysis.category_breakdown[category] = \
            analysis.category_breakdown.get(category, 0) + 1

        # Date analysis
        date = doc.get('date', '')
        if date and len(date) >= 4:
            # Update date range
            if analysis.date_min is None or date < analysis.date_min:
                analysis.date_min = date
            if analysis.date_max is None or date > analysis.date_max:
                analysis.date_max = date

            # Year distribution
            year = date[:4]
            analysis.year_distribution[year] = \
                analysis.year_distribution.get(year, 0) + 1

        # Text length (sample every 50th doc to save memory)
        if line_num % 50 == 0:
            text = doc.get('text', '')
            analysis.text_lengths.append(len(text) if text else 0)

        # Citation analysis
        citation = doc.get('citation', '')
        if citation:
            # Extract court codes
            for pattern, group in self.COURT_PATTERNS:
                match = re.search(pattern, citation)
                if match:
                    code = match.group(group)
                    analysis.court_codes[code] = \
                        analysis.court_codes.get(code, 0) + 1
                    break

            # Sample citations
            if len(analysis.sample_citations) < 20:
                analysis.sample_citations.append(citation)

        # Legal term frequency (sample every 100th doc)
        if line_num % 100 == 0:
            text_lower = (doc.get('text', '') or '').lower()
            for term in self.LEGAL_TERMS:
                if term in text_lower:
                    analysis.legal_terms[term] = \
                        analysis.legal_terms.get(term, 0) + 1

    def generate_markdown_report(self, analysis: DomainAnalysis) -> str:
        """Generate Markdown report for a domain."""
        text_stats = analysis.get_text_stats()

        # Calculate percentages for distributions
        total = analysis.total_documents or 1

        report = f"""# Domain Analysis: {analysis.domain_name}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Documents** | {analysis.total_documents:,} |
| **Date Range** | {analysis.date_min or 'N/A'} to {analysis.date_max or 'N/A'} |
| **Avg Text Length** | {text_stats['mean']:,.0f} characters |
| **Median Text Length** | {text_stats['median']:,.0f} characters |

---

## 2. Document Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
"""
        for doc_type, count in sorted(
            analysis.type_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            pct = (count / total) * 100
            report += f"| {doc_type} | {count:,} | {pct:.1f}% |\n"

        report += """
---

## 3. Jurisdiction Distribution

| Jurisdiction | Count | Percentage |
|--------------|-------|------------|
"""
        for jurisdiction, count in sorted(
            analysis.jurisdiction_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:15]:
            pct = (count / total) * 100
            report += f"| {jurisdiction} | {count:,} | {pct:.1f}% |\n"

        report += """
---

## 4. Source Distribution

| Source | Count | Percentage |
|--------|-------|------------|
"""
        for source, count in sorted(
            analysis.source_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]:
            pct = (count / total) * 100
            report += f"| {source} | {count:,} | {pct:.1f}% |\n"

        report += """
---

## 5. Category Breakdown

| Category | Count | Percentage |
|----------|-------|------------|
"""
        for category, count in sorted(
            analysis.category_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )[:15]:
            pct = (count / total) * 100
            report += f"| {category} | {count:,} | {pct:.1f}% |\n"

        report += """
---

## 6. Temporal Distribution (by Year)

| Year | Count |
|------|-------|
"""
        for year in sorted(analysis.year_distribution.keys(), reverse=True)[:20]:
            count = analysis.year_distribution[year]
            report += f"| {year} | {count:,} |\n"

        report += """
---

## 7. Court Distribution

| Court Code | Count |
|------------|-------|
"""
        for code, count in sorted(
            analysis.court_codes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:15]:
            report += f"| {code} | {count:,} |\n"

        report += """
---

## 8. Text Characteristics

| Statistic | Value |
|-----------|-------|
"""
        report += f"| Minimum Length | {text_stats['min']:,} chars |\n"
        report += f"| Maximum Length | {text_stats['max']:,} chars |\n"
        report += f"| Mean Length | {text_stats['mean']:,.0f} chars |\n"
        report += f"| Median Length | {text_stats['median']:,.0f} chars |\n"
        report += f"| Std Deviation | {text_stats['std']:,.0f} chars |\n"

        report += """
---

## 9. Common Legal Terms

| Term | Frequency |
|------|-----------|
"""
        for term, count in sorted(
            analysis.legal_terms.items(),
            key=lambda x: x[1],
            reverse=True
        )[:15]:
            report += f"| {term} | {count:,} |\n"

        report += """
---

## 10. Sample Citations

"""
        for citation in analysis.sample_citations[:10]:
            report += f"- {citation}\n"

        report += """
---

## 11. GSW Processing Recommendations

"""
        # Generate recommendations based on analysis
        recommendations = self._generate_recommendations(analysis)
        for rec in recommendations:
            report += f"- {rec}\n"

        return report

    def _generate_recommendations(self, analysis: DomainAnalysis) -> List[str]:
        """Generate GSW processing recommendations based on analysis."""
        recommendations = []

        # Volume-based recommendations
        if analysis.total_documents > 50000:
            recommendations.append(
                f"**High Volume Domain** ({analysis.total_documents:,} docs): "
                "Consider batch processing with checkpointing"
            )
        elif analysis.total_documents < 1000:
            recommendations.append(
                f"**Low Volume Domain** ({analysis.total_documents:,} docs): "
                "Suitable for full extraction in single batch"
            )

        # Text length recommendations
        text_stats = analysis.get_text_stats()
        if text_stats['mean'] > 50000:
            recommendations.append(
                "**Long Documents**: Enable text chunking in Operator"
            )

        # Court-specific recommendations
        if 'FamCA' in analysis.court_codes or 'FamCAFC' in analysis.court_codes:
            recommendations.append(
                "**Family Court Cases**: Use family-specific ontology seeds"
            )

        if 'NSWCCA' in analysis.court_codes:
            recommendations.append(
                "**Criminal Appeals**: Track sentencing and appeal outcomes"
            )

        # Category-specific recommendations
        if 'Admin_Migration' in analysis.category_breakdown:
            recommendations.append(
                "**Migration Cases**: Track visa types and tribunal decisions"
            )

        return recommendations or ["No specific recommendations"]

    def generate_json_data(self, analysis: DomainAnalysis) -> Dict[str, Any]:
        """Generate JSON data for visualization/programmatic use."""
        return {
            "domain_name": analysis.domain_name,
            "total_documents": analysis.total_documents,
            "date_range": {
                "min": analysis.date_min,
                "max": analysis.date_max
            },
            "type_distribution": analysis.type_distribution,
            "jurisdiction_distribution": analysis.jurisdiction_distribution,
            "source_distribution": analysis.source_distribution,
            "category_breakdown": analysis.category_breakdown,
            "year_distribution": analysis.year_distribution,
            "court_codes": analysis.court_codes,
            "text_stats": analysis.get_text_stats(),
            "legal_terms": analysis.legal_terms,
            "sample_citations": analysis.sample_citations,
            "generated_at": datetime.now().isoformat()
        }

    def analyze_all_domains(self) -> Dict[str, DomainAnalysis]:
        """Analyze all domain files in the domains directory."""
        analyses = {}

        # Find all domain files
        domain_files = list(self.domains_dir.glob("*.jsonl"))

        print(f"Found {len(domain_files)} domain files")

        for domain_file in domain_files:
            domain_name = domain_file.stem.title()
            analysis = self.analyze_domain(domain_file.stem)
            analyses[domain_name] = analysis

            # Generate and save reports
            self._save_domain_reports(analysis)

        return analyses

    def _save_domain_reports(self, analysis: DomainAnalysis) -> None:
        """Save reports for a single domain."""
        domain_dir = self.output_dir / "per_domain"
        domain_dir.mkdir(parents=True, exist_ok=True)

        # Markdown report
        md_path = domain_dir / f"{analysis.domain_name.lower()}_analysis.md"
        md_content = self.generate_markdown_report(analysis)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # JSON data
        json_path = domain_dir / f"{analysis.domain_name.lower()}_data.json"
        json_content = self.generate_json_data(analysis)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2)

        print(f"  Saved reports to {domain_dir}")


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate domain analysis reports")
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
    parser.add_argument(
        "--domain",
        type=str,
        help="Analyze single domain (e.g., 'family')"
    )

    args = parser.parse_args()

    generator = DomainReportGenerator(args.domains_dir, args.output_dir)

    if args.domain:
        analysis = generator.analyze_domain(args.domain)
        generator._save_domain_reports(analysis)
    else:
        generator.analyze_all_domains()


if __name__ == "__main__":
    main()
