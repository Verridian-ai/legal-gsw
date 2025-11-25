"""
Corpus Domain Extractor

Streams the Australian Legal Corpus and classifies documents into 14 legal domains.
This is the preprocessing step before GSW extraction.

Usage:
    python -m src.ingestion.corpus_domain_extractor --input corpus.jsonl --output data/processed/domains

Features:
- Streaming extraction (RAM-safe for 8.8GB+)
- Enhanced classification with citation/jurisdiction boosts
- Multi-domain tracking in metadata
- Checkpoint/resume support
- Statistics collection during extraction
"""

import json
import re
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, TextIO, Any
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion.classification_config import CLASSIFICATION_MAP, DOMAIN_MAPPING


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = BASE_DIR.parent / "corpus.jsonl"
DEFAULT_OUTPUT = BASE_DIR / "data" / "processed" / "domains"
STATE_FILE = BASE_DIR / "data" / "processed" / "extraction_state.json"

# All broad domains we'll create files for
ALL_DOMAINS = list(DOMAIN_MAPPING.keys()) + ["Legislation_Other", "Unclassified"]


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DomainStats:
    """Statistics collected for a single domain during extraction."""
    document_count: int = 0
    by_type: Dict[str, int] = field(default_factory=Counter)
    by_jurisdiction: Dict[str, int] = field(default_factory=Counter)
    by_source: Dict[str, int] = field(default_factory=Counter)
    by_category: Dict[str, int] = field(default_factory=Counter)
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    text_lengths: List[int] = field(default_factory=list)
    sample_citations: List[str] = field(default_factory=list)

    def update_date_range(self, date_str: Optional[str]) -> None:
        """Update min/max date range."""
        if not date_str or len(date_str) < 4:
            return
        if self.date_min is None or date_str < self.date_min:
            self.date_min = date_str
        if self.date_max is None or date_str > self.date_max:
            self.date_max = date_str

    def add_sample_citation(self, citation: str, max_samples: int = 10) -> None:
        """Add a sample citation if we don't have enough."""
        if len(self.sample_citations) < max_samples and citation:
            self.sample_citations.append(citation)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_count": self.document_count,
            "by_type": dict(self.by_type),
            "by_jurisdiction": dict(self.by_jurisdiction),
            "by_source": dict(self.by_source),
            "by_category": dict(self.by_category),
            "date_range": {"min": self.date_min, "max": self.date_max},
            "text_length_stats": self._calc_text_stats(),
            "sample_citations": self.sample_citations
        }

    def _calc_text_stats(self) -> Dict[str, float]:
        """Calculate text length statistics."""
        if not self.text_lengths:
            return {"min": 0, "max": 0, "mean": 0, "count": 0}
        lengths = self.text_lengths
        return {
            "min": min(lengths),
            "max": max(lengths),
            "mean": sum(lengths) / len(lengths),
            "count": len(lengths)
        }


@dataclass
class ExtractionState:
    """Checkpoint state for resumable extraction."""
    last_line: int = 0
    total_processed: int = 0
    started_at: str = ""
    domain_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionState":
        return cls(**data)


@dataclass
class OverlapStats:
    """Statistics about multi-domain classification."""
    single_domain_count: int = 0
    multi_domain_count: int = 0
    domain_pairs: Dict[str, int] = field(default_factory=Counter)

    def record(self, domains: List[str]) -> None:
        """Record domain matches for a document."""
        if len(domains) <= 1:
            self.single_domain_count += 1
        else:
            self.multi_domain_count += 1
            # Record all pairs
            for i, d1 in enumerate(domains):
                for d2 in domains[i+1:]:
                    pair = tuple(sorted([d1, d2]))
                    self.domain_pairs[str(pair)] += 1


# ============================================================================
# CLASSIFICATION ENGINE
# ============================================================================

class DomainClassifier:
    """Enhanced document classifier with weighted scoring."""

    def __init__(self):
        # Pre-compile regex patterns for performance
        self.patterns: Dict[str, re.Pattern] = {}
        for category, keywords in CLASSIFICATION_MAP.items():
            pattern_str = "|".join([re.escape(k) for k in keywords])
            self.patterns[category] = re.compile(pattern_str, re.IGNORECASE)

        # Build category -> domain lookup
        self.category_to_domain: Dict[str, str] = {}
        for broad, granular_list in DOMAIN_MAPPING.items():
            for granular in granular_list:
                self.category_to_domain[granular] = broad

    def classify(self, doc: Dict[str, Any]) -> Tuple[str, str, List[Tuple[str, int]]]:
        """
        Classify a document into domains.

        Returns:
            (primary_domain, primary_category, all_matches)
            where all_matches is [(category, score), ...]
        """
        doc_type = doc.get('type', '')
        citation = doc.get('citation', '') or ''
        text = doc.get('text', '') or ''
        jurisdiction = (doc.get('jurisdiction', '') or '').lower()

        # Different strategies for legislation vs decisions
        if doc_type in ['primary_legislation', 'secondary_legislation', 'bill']:
            return self._classify_legislation(citation, jurisdiction)
        else:
            return self._classify_decision(citation, text, jurisdiction)

    def _classify_legislation(
        self,
        citation: str,
        jurisdiction: str
    ) -> Tuple[str, str, List[Tuple[str, int]]]:
        """Classify legislation using citation/title only."""
        scores = Counter()
        citation_lower = citation.lower()

        for category, pattern in self.patterns.items():
            if pattern.search(citation_lower):
                scores[category] = 10  # High weight for title match

        if not scores:
            return "Legislation_Other", "Legislation_Other", []

        all_matches = scores.most_common()
        best_category = all_matches[0][0]
        best_domain = self.category_to_domain.get(best_category, "Legislation_Other")

        return best_domain, best_category, all_matches

    def _classify_decision(
        self,
        citation: str,
        text: str,
        jurisdiction: str
    ) -> Tuple[str, str, List[Tuple[str, int]]]:
        """Classify court decisions with enhanced scoring."""
        scores = Counter()

        # Build searchable text (citation + first 15000 chars)
        search_text = f"{citation} {text[:15000]}".lower()
        citation_lower = citation.lower()

        for category, pattern in self.patterns.items():
            matches = pattern.findall(search_text)
            if not matches:
                continue

            base_score = len(matches)

            # BOOST 1: Citation match (strong indicator)
            if pattern.search(citation_lower):
                base_score += 10

            # BOOST 2: Jurisdiction alignment
            if "Family" in category:
                if "family" in jurisdiction or "family court" in search_text[:1000]:
                    base_score += 20

            if "Migration" in category or "Admin_Migration" in category:
                if "refugee" in search_text or "visa" in search_text or "migration" in jurisdiction:
                    base_score += 15

            if "Criminal" in category:
                if "criminal" in jurisdiction or "crime" in jurisdiction:
                    base_score += 15

            scores[category] = base_score

        if not scores:
            return "Unclassified", "Unclassified", []

        all_matches = scores.most_common()
        best_category = all_matches[0][0]
        best_domain = self.category_to_domain.get(best_category, "Unclassified")

        return best_domain, best_category, all_matches


# ============================================================================
# FILE MANAGER
# ============================================================================

class DomainFileManager:
    """Manages output file handles for all domain files."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.handles: Dict[str, TextIO] = {}

    def __enter__(self) -> "DomainFileManager":
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for domain in ALL_DOMAINS:
            path = self.output_dir / f"{domain.lower()}.jsonl"
            self.handles[domain] = open(path, 'w', encoding='utf-8')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for handle in self.handles.values():
            handle.close()

    def write(self, domain: str, doc: Dict[str, Any]) -> None:
        """Write document to appropriate domain file."""
        if domain in self.handles:
            self.handles[domain].write(json.dumps(doc, ensure_ascii=False) + '\n')
        else:
            # Fallback to Unclassified
            self.handles["Unclassified"].write(json.dumps(doc, ensure_ascii=False) + '\n')


# ============================================================================
# MAIN EXTRACTOR
# ============================================================================

class CorpusDomainExtractor:
    """
    Main extraction class for domain classification.

    Streams the corpus.jsonl file, classifies each document,
    and writes to domain-specific output files.
    """

    def __init__(
        self,
        input_path: Path,
        output_dir: Path,
        state_path: Optional[Path] = None
    ):
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.state_path = Path(state_path) if state_path else STATE_FILE

        self.classifier = DomainClassifier()
        self.stats: Dict[str, DomainStats] = defaultdict(DomainStats)
        self.overlap_stats = OverlapStats()

    def extract_all(
        self,
        progress_interval: int = 5000,
        resume: bool = False
    ) -> Dict[str, DomainStats]:
        """
        Process entire corpus with streaming.

        Args:
            progress_interval: Print progress every N documents
            resume: Whether to resume from checkpoint

        Returns:
            Dictionary of domain -> DomainStats
        """
        start_line = 0
        if resume:
            state = self._load_checkpoint()
            if state:
                start_line = state.last_line
                print(f"[Resume] Starting from line {start_line}")

        print(f"[Extractor] Input: {self.input_path}")
        print(f"[Extractor] Output: {self.output_dir}")
        print(f"[Extractor] Domains: {len(ALL_DOMAINS)}")
        print("-" * 60)

        start_time = datetime.now()

        with DomainFileManager(self.output_dir) as file_manager:
            with open(self.input_path, 'r', encoding='utf-8') as infile:
                for line_num, line in enumerate(infile):
                    # Skip lines if resuming
                    if line_num < start_line:
                        continue

                    try:
                        doc = json.loads(line)
                        self._process_document(doc, file_manager, line_num)

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"\n[Error] Line {line_num}: {e}")
                        continue

                    # Progress reporting
                    if line_num % progress_interval == 0 and line_num > 0:
                        self._print_progress(line_num, start_time)
                        # Save checkpoint
                        self._save_checkpoint(line_num)

        elapsed = datetime.now() - start_time
        print(f"\n[Complete] Processed {sum(s.document_count for s in self.stats.values())} documents in {elapsed}")

        # Save final statistics
        self._save_statistics()

        return dict(self.stats)

    def _process_document(
        self,
        doc: Dict[str, Any],
        file_manager: DomainFileManager,
        line_num: int
    ) -> None:
        """Process a single document."""
        # Classify
        primary_domain, primary_category, all_matches = self.classifier.classify(doc)

        # Track overlap statistics
        all_domains = list(set([
            self.classifier.category_to_domain.get(cat, "Unclassified")
            for cat, _ in all_matches
        ]))
        self.overlap_stats.record(all_domains)

        # Inject classification metadata
        doc['_classification'] = {
            'primary_domain': primary_domain,
            'primary_category': primary_category,
            'all_matches': [(cat, score) for cat, score in all_matches[:5]],  # Top 5
            'match_count': len(all_matches),
            'line_number': line_num
        }

        # Write to primary domain file
        file_manager.write(primary_domain, doc)

        # Collect statistics
        stats = self.stats[primary_domain]
        stats.document_count += 1
        stats.by_type[doc.get('type', 'unknown')] += 1
        stats.by_jurisdiction[doc.get('jurisdiction', 'unknown')] += 1
        stats.by_source[doc.get('source', 'unknown')] += 1
        stats.by_category[primary_category] += 1
        stats.update_date_range(doc.get('date'))

        # Sample text lengths (every 100th doc to save memory)
        if stats.document_count % 100 == 0:
            text = doc.get('text', '')
            stats.text_lengths.append(len(text) if text else 0)

        # Sample citations
        stats.add_sample_citation(doc.get('citation', ''))

    def _print_progress(self, line_num: int, start_time: datetime) -> None:
        """Print progress update."""
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = line_num / elapsed if elapsed > 0 else 0

        # Top domains by count
        top_domains = sorted(
            [(d, s.document_count) for d, s in self.stats.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        top_str = " | ".join([f"{d}:{c}" for d, c in top_domains])
        print(f"\r[Progress] {line_num:,} docs | {rate:.0f}/sec | {top_str}", end="", flush=True)

    def _save_checkpoint(self, line_num: int) -> None:
        """Save extraction state for resume."""
        state = ExtractionState(
            last_line=line_num,
            total_processed=sum(s.document_count for s in self.stats.values()),
            started_at=datetime.now().isoformat(),
            domain_counts={d: s.document_count for d, s in self.stats.items()}
        )

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, indent=2)

    def _load_checkpoint(self) -> Optional[ExtractionState]:
        """Load previous extraction state."""
        if not self.state_path.exists():
            return None

        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ExtractionState.from_dict(data)
        except Exception as e:
            print(f"[Warning] Could not load checkpoint: {e}")
            return None

    def _save_statistics(self) -> None:
        """Save extraction statistics to JSON."""
        stats_path = self.output_dir / "extraction_statistics.json"

        output = {
            "extraction_completed": datetime.now().isoformat(),
            "total_documents": sum(s.document_count for s in self.stats.values()),
            "domain_stats": {d: s.to_dict() for d, s in self.stats.items()},
            "overlap_stats": {
                "single_domain": self.overlap_stats.single_domain_count,
                "multi_domain": self.overlap_stats.multi_domain_count,
                "top_pairs": dict(Counter(self.overlap_stats.domain_pairs).most_common(20))
            }
        }

        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        print(f"[Stats] Saved to {stats_path}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract and classify Australian Legal Corpus into domains"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to corpus.jsonl"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory for domain files"
    )
    parser.add_argument(
        "--progress", "-p",
        type=int,
        default=5000,
        help="Progress reporting interval"
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume from checkpoint"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"[Error] Input file not found: {args.input}")
        sys.exit(1)

    extractor = CorpusDomainExtractor(
        input_path=args.input,
        output_dir=args.output
    )

    extractor.extract_all(
        progress_interval=args.progress,
        resume=args.resume
    )


if __name__ == "__main__":
    main()
