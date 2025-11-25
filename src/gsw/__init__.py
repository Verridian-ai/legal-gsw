"""
GSW - Global Semantic Workspace for Legal AI

An actor-centric episodic memory system for legal document understanding,
based on the research paper arXiv:2511.07587.

Components:
-----------
LegalOperator
    Extracts actors, roles, states, verbs, and predictive questions
    from legal text using the 6-task extraction process.

LegalSpacetime
    Links entities that share the same temporal or spatial context.
    Binds WHO, WHAT, WHEN, and WHERE together.

LegalReconciler
    Merges entities across chunks and answers pending questions.
    Implements entity resolution and conflict handling.

WorkspaceManager
    Persistence and operations for the Global Workspace.
    Save/load, statistics, ontology context extraction.

LegalSummary
    Generates coherent narrative summaries for entities.
    Used for QA and human-readable reports.

Pipeline:
---------
1. Text → LegalOperator → ChunkExtraction (actors, verbs, questions, links)
2. ChunkExtraction → LegalSpacetime → Enhanced spatio-temporal links
3. ChunkExtraction → LegalReconciler → Merged into GlobalWorkspace
4. GlobalWorkspace → LegalSummary → Entity narratives
5. GlobalWorkspace → QA Pipeline → Grounded answers

Usage:
------
```python
from src.gsw import LegalOperator, LegalReconciler, WorkspaceManager
from src.logic.gsw_schema import GlobalWorkspace

# Initialize components
operator = LegalOperator()
reconciler = LegalReconciler()
workspace = GlobalWorkspace(domain="family")

# Process a document
extraction = operator.extract(legal_text, situation="Family law matter")
extraction, log = reconciler.reconcile(extraction, workspace, legal_text)

# Save workspace
manager = WorkspaceManager(workspace, Path("workspace.json"))
manager.save()
```
"""

from src.gsw.legal_operator import LegalOperator, chunk_legal_text
from src.gsw.legal_spacetime import LegalSpacetime, extract_dates_from_text, extract_locations_from_text
from src.gsw.legal_reconciler import LegalReconciler
from src.gsw.workspace import WorkspaceManager, merge_workspaces
from src.gsw.legal_summary import LegalSummary

__all__ = [
    # Core components
    "LegalOperator",
    "LegalSpacetime",
    "LegalReconciler",
    "WorkspaceManager",
    "LegalSummary",

    # Utilities
    "chunk_legal_text",
    "extract_dates_from_text",
    "extract_locations_from_text",
    "merge_workspaces",
]

__version__ = "2.0.0"
__author__ = "Legal GSW Project"
