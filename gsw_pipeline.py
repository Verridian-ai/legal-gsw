"""
GSW Pipeline - Main Orchestrator

Complete pipeline for Legal Global Semantic Workspace:
1. Domain Extraction - Split corpus into legal domains
2. GSW Processing - Extract actors, roles, states, verbs, questions
3. Analysis - Generate reports and statistics

Usage:
    # Extract domains from corpus
    python gsw_pipeline.py extract --input ../corpus.jsonl

    # Process a domain with GSW
    python gsw_pipeline.py process --domain family --limit 10

    # Generate analysis reports
    python gsw_pipeline.py analyze

    # Run full pipeline
    python gsw_pipeline.py full --input ../corpus.jsonl --domain family
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.logic.gsw_schema import GlobalWorkspace, ChunkExtraction
from src.gsw.legal_operator import LegalOperator, chunk_legal_text
from src.gsw.legal_spacetime import LegalSpacetime
from src.gsw.legal_reconciler import LegalReconciler
from src.gsw.workspace import WorkspaceManager
from src.gsw.legal_summary import LegalSummary


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_INPUT = PROJECT_ROOT.parent / "corpus.jsonl"
DOMAINS_DIR = PROJECT_ROOT / "data" / "processed" / "domains"
WORKSPACES_DIR = PROJECT_ROOT / "data" / "processed" / "workspaces"
REPORTS_DIR = PROJECT_ROOT / "reports" / "domain_analysis"


# ============================================================================
# DOMAIN EXTRACTION
# ============================================================================

def run_domain_extraction(
    input_path: Path,
    output_dir: Path = DOMAINS_DIR,
    progress_interval: int = 5000,
    resume: bool = False
) -> None:
    """Run domain extraction on the corpus."""
    from src.ingestion.corpus_domain_extractor import CorpusDomainExtractor

    print("=" * 60)
    print("PHASE 1: Domain Extraction")
    print("=" * 60)

    extractor = CorpusDomainExtractor(
        input_path=input_path,
        output_dir=output_dir
    )

    extractor.extract_all(
        progress_interval=progress_interval,
        resume=resume
    )


# ============================================================================
# GSW PROCESSING
# ============================================================================

def run_gsw_processing(
    domain: str,
    limit: Optional[int] = None,
    batch_size: int = 10,
    calibration: bool = False,
    resume: bool = False
) -> GlobalWorkspace:
    """
    Run GSW processing on a domain.

    Args:
        domain: Domain name (e.g., "family")
        limit: Maximum documents to process
        batch_size: Documents per batch
        calibration: If True, don't save results (test mode)
        resume: Resume from checkpoint
    """
    print("=" * 60)
    print(f"PHASE 2: GSW Processing - {domain.title()}")
    print("=" * 60)

    # Paths
    domain_file = DOMAINS_DIR / f"{domain.lower()}.jsonl"
    workspace_file = WORKSPACES_DIR / f"{domain.lower()}_workspace.json"
    state_file = WORKSPACES_DIR / f"{domain.lower()}_state.json"

    if not domain_file.exists():
        print(f"[Error] Domain file not found: {domain_file}")
        print("Run domain extraction first: python gsw_pipeline.py extract")
        sys.exit(1)

    # Initialize components
    print("[Init] Loading components...")

    try:
        operator = LegalOperator()
        print("  - LegalOperator: OK")
    except Exception as e:
        print(f"  - LegalOperator: FAILED ({e})")
        print("  Using mock operator for testing")
        operator = None

    try:
        spacetime = LegalSpacetime()
        print("  - LegalSpacetime: OK")
    except:
        spacetime = None

    reconciler = LegalReconciler()
    print("  - LegalReconciler: OK")

    # Load or create workspace
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

    if resume and workspace_file.exists():
        manager = WorkspaceManager.load(workspace_file)
        workspace = manager.workspace
        print(f"[Resume] Loaded workspace with {len(workspace.actors)} actors")
    else:
        workspace = GlobalWorkspace(domain=domain)
        manager = WorkspaceManager(workspace, workspace_file)
        print("[New] Created fresh workspace")

    # Load processing state
    start_line = 0
    if resume and state_file.exists():
        with open(state_file, 'r') as f:
            state = json.load(f)
            start_line = state.get("last_line", 0)
        print(f"[Resume] Starting from line {start_line}")

    # Process documents
    print(f"\n[Processing] Domain: {domain}")
    print(f"[Processing] Limit: {limit or 'All'}")
    print("-" * 40)

    processed = 0
    errors = 0

    with open(domain_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            # Skip if resuming
            if line_num < start_line:
                continue

            # Check limit
            if limit and processed >= limit:
                break

            try:
                doc = json.loads(line)

                # Extract with Operator
                if operator:
                    text = doc.get('text', '')[:30000]
                    citation = doc.get('citation', '')

                    extraction = operator.extract(
                        text=text,
                        situation=f"Legal case: {citation}",
                        background_context=f"Domain: {domain}, Type: {doc.get('type', '')}",
                        document_id=doc.get('version_id', str(line_num))
                    )

                    # Add spatio-temporal links
                    if spacetime and extraction.actors:
                        links = spacetime.link_entities(extraction, text)
                        extraction.spatio_temporal_links.extend(links)

                    # Reconcile with workspace
                    extraction, log = reconciler.reconcile(
                        extraction, workspace, text
                    )

                    processed += 1

                    # Progress
                    if processed % 10 == 0:
                        print(f"  Processed: {processed} | Actors: {len(workspace.actors)} | "
                              f"Questions: {len(workspace.questions)}", end='\r')

                else:
                    # Mock processing for testing without API
                    processed += 1
                    if processed % 100 == 0:
                        print(f"  [Mock] Processed: {processed}", end='\r')

            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"\n  [Error] Line {line_num}: {e}")

            # Save checkpoint every batch
            if processed % batch_size == 0 and not calibration:
                _save_checkpoint(manager, state_file, line_num, processed)

    print(f"\n\n[Complete] Processed: {processed} | Errors: {errors}")
    print(f"[Workspace] Actors: {len(workspace.actors)} | "
          f"Questions: {len(workspace.questions)} | "
          f"Answered: {len(workspace.get_answered_questions())}")

    # Save final state
    if not calibration:
        manager.save()
        _save_checkpoint(manager, state_file, line_num, processed)
        print(f"[Saved] Workspace: {workspace_file}")
    else:
        print("[Calibration] Results NOT saved")

    return workspace


def _save_checkpoint(
    manager: WorkspaceManager,
    state_file: Path,
    line_num: int,
    processed: int
) -> None:
    """Save processing checkpoint."""
    manager.save()

    state = {
        "last_line": line_num + 1,
        "processed": processed,
        "timestamp": datetime.now().isoformat()
    }

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


# ============================================================================
# ANALYSIS
# ============================================================================

def run_analysis(domains_dir: Path = DOMAINS_DIR) -> None:
    """Generate analysis reports."""
    print("=" * 60)
    print("PHASE 3: Analysis Reports")
    print("=" * 60)

    from src.analysis.domain_report_generator import DomainReportGenerator
    from src.analysis.master_domain_report import MasterDomainReport

    if not domains_dir.exists():
        print(f"[Error] Domains directory not found: {domains_dir}")
        print("Run domain extraction first")
        return

    # Per-domain reports
    print("\n[Generating] Per-domain reports...")
    generator = DomainReportGenerator(domains_dir, REPORTS_DIR)
    analyses = generator.analyze_all_domains()

    # Master report
    print("\n[Generating] Master report...")
    master = MasterDomainReport(domains_dir, REPORTS_DIR)
    master.generate_master_report(analyses)

    print(f"\n[Complete] Reports saved to {REPORTS_DIR}")


# ============================================================================
# SUMMARY GENERATION
# ============================================================================

def run_summaries(domain: str) -> None:
    """Generate entity summaries for a domain workspace."""
    print("=" * 60)
    print(f"PHASE 4: Summary Generation - {domain.title()}")
    print("=" * 60)

    workspace_file = WORKSPACES_DIR / f"{domain.lower()}_workspace.json"

    if not workspace_file.exists():
        print(f"[Error] Workspace not found: {workspace_file}")
        print("Run GSW processing first")
        return

    manager = WorkspaceManager.load(workspace_file)
    workspace = manager.workspace

    print(f"[Loaded] {len(workspace.actors)} actors")

    try:
        summarizer = LegalSummary()
        print("[Generating] Entity summaries...")

        summaries = summarizer.generate_all_summaries(
            workspace,
            actor_types=["person"]  # Only summarize people
        )

        print(f"[Complete] Generated {len(summaries)} summaries")

        # Save updated workspace
        manager.save()

    except Exception as e:
        print(f"[Error] Summary generation failed: {e}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Legal GSW Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract domains from corpus
  python gsw_pipeline.py extract --input ../corpus.jsonl

  # Process family law domain (first 10 docs)
  python gsw_pipeline.py process --domain family --limit 10

  # Generate analysis reports
  python gsw_pipeline.py analyze

  # Run full pipeline
  python gsw_pipeline.py full --domain family --limit 100
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract domains from corpus")
    extract_parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT,
                                help="Path to corpus.jsonl")
    extract_parser.add_argument("--output", "-o", type=Path, default=DOMAINS_DIR,
                                help="Output directory for domains")
    extract_parser.add_argument("--progress", "-p", type=int, default=5000,
                                help="Progress interval")
    extract_parser.add_argument("--resume", "-r", action="store_true",
                                help="Resume from checkpoint")

    # Process command
    process_parser = subparsers.add_parser("process", help="Process domain with GSW")
    process_parser.add_argument("--domain", "-d", required=True,
                                help="Domain to process (e.g., family)")
    process_parser.add_argument("--limit", "-l", type=int,
                                help="Maximum documents to process")
    process_parser.add_argument("--batch", "-b", type=int, default=10,
                                help="Batch size for checkpointing")
    process_parser.add_argument("--calibration", "-c", action="store_true",
                                help="Calibration mode (don't save)")
    process_parser.add_argument("--resume", "-r", action="store_true",
                                help="Resume from checkpoint")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Generate analysis reports")
    analyze_parser.add_argument("--domains-dir", type=Path, default=DOMAINS_DIR,
                                help="Domains directory")

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Generate entity summaries")
    summary_parser.add_argument("--domain", "-d", required=True,
                                help="Domain to summarize")

    # Full command
    full_parser = subparsers.add_parser("full", help="Run full pipeline")
    full_parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT,
                             help="Path to corpus.jsonl")
    full_parser.add_argument("--domain", "-d", default="family",
                             help="Domain to process")
    full_parser.add_argument("--limit", "-l", type=int, default=10,
                             help="Documents to process")

    args = parser.parse_args()

    if args.command == "extract":
        run_domain_extraction(
            args.input, args.output, args.progress, args.resume
        )

    elif args.command == "process":
        run_gsw_processing(
            args.domain, args.limit, args.batch,
            args.calibration, args.resume
        )

    elif args.command == "analyze":
        run_analysis(args.domains_dir)

    elif args.command == "summary":
        run_summaries(args.domain)

    elif args.command == "full":
        print("FULL PIPELINE")
        print("=" * 60)

        # Step 1: Extract (if needed)
        if not DOMAINS_DIR.exists() or not list(DOMAINS_DIR.glob("*.jsonl")):
            run_domain_extraction(args.input)

        # Step 2: Process
        run_gsw_processing(args.domain, args.limit)

        # Step 3: Analyze
        run_analysis()

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
