"""
Global Workspace Manager - Persistence and Operations

The Global Semantic Workspace is the central "memory" of the system.
This module provides persistence (save/load) and high-level operations.

Analogous to:
- Hippocampal Complex: Central integration point
- Long-term memory consolidation
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.logic.gsw_schema import (
    GlobalWorkspace, Actor, State, VerbPhrase, PredictiveQuestion,
    SpatioTemporalLink, ChunkExtraction, OntologyContext, ActorType,
    QuestionType, LinkType
)


# ============================================================================
# WORKSPACE MANAGER
# ============================================================================

class WorkspaceManager:
    """
    Manages the Global Semantic Workspace.

    Provides:
    - Persistence (save/load to JSON)
    - Statistics and reporting
    - Ontology context extraction
    - Querying capabilities
    """

    def __init__(
        self,
        workspace: Optional[GlobalWorkspace] = None,
        storage_path: Optional[Path] = None
    ):
        self.workspace = workspace or GlobalWorkspace()
        self.storage_path = storage_path

    @classmethod
    def load(cls, path: Path) -> "WorkspaceManager":
        """Load workspace from JSON file."""
        if not path.exists():
            print(f"[Workspace] No existing workspace at {path}, creating new")
            return cls(storage_path=path)

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        workspace = cls._deserialize_workspace(data)
        manager = cls(workspace=workspace, storage_path=path)

        print(f"[Workspace] Loaded: {len(workspace.actors)} actors, "
              f"{len(workspace.questions)} questions")

        return manager

    def save(self, path: Optional[Path] = None) -> None:
        """Save workspace to JSON file."""
        save_path = path or self.storage_path
        if not save_path:
            raise ValueError("No storage path specified")

        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = self._serialize_workspace(self.workspace)

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[Workspace] Saved to {save_path}")

    def get_ontology_context(self) -> OntologyContext:
        """
        Extract current ontology context from workspace.

        This is used for the self-improving feedback loop (Phase 4.5).
        The ontology context is injected into the Operator prompt.
        """
        from collections import Counter

        context = OntologyContext()

        # Count actor types
        for actor in self.workspace.actors.values():
            context.actor_types[actor.actor_type.value] = \
                context.actor_types.get(actor.actor_type.value, 0) + 1

            # Count roles
            for role in actor.roles:
                context.role_types[role] = context.role_types.get(role, 0) + 1

            # Count state names
            for state in actor.states:
                context.state_names[state.name] = \
                    context.state_names.get(state.name, 0) + 1

        # Count verb types
        for verb in self.workspace.verb_phrases.values():
            context.verb_types[verb.verb] = \
                context.verb_types.get(verb.verb, 0) + 1

        return context

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive workspace statistics."""
        stats = self.workspace.get_statistics()

        # Add additional analytics
        stats["actors_by_type"] = {}
        for actor in self.workspace.actors.values():
            t = actor.actor_type.value
            stats["actors_by_type"][t] = stats["actors_by_type"].get(t, 0) + 1

        stats["questions_by_type"] = {}
        for q in self.workspace.questions.values():
            t = q.question_type.value
            stats["questions_by_type"][t] = stats["questions_by_type"].get(t, 0) + 1

        return stats

    def query_actors_by_role(self, role: str) -> List[Actor]:
        """Find all actors with a specific role."""
        role_lower = role.lower()
        return [
            actor for actor in self.workspace.actors.values()
            if any(role_lower in r.lower() for r in actor.roles)
        ]

    def query_actors_by_state(self, state_name: str, state_value: str = None) -> List[Actor]:
        """Find actors with a specific state."""
        results = []
        for actor in self.workspace.actors.values():
            for state in actor.states:
                if state.name.lower() == state_name.lower():
                    if state_value is None or state.value.lower() == state_value.lower():
                        results.append(actor)
                        break
        return results

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of events."""
        events = []

        # Gather all dated items
        for verb in self.workspace.verb_phrases.values():
            if verb.temporal_id:
                # Look up temporal entity
                temporal = self.workspace.actors.get(verb.temporal_id)
                if temporal:
                    events.append({
                        "date": temporal.name,
                        "type": "action",
                        "verb": verb.verb,
                        "agent": self.workspace.actors.get(verb.agent_id, {}).get("name", "Unknown"),
                        "id": verb.id
                    })

        # Sort by date string (works for ISO dates)
        events.sort(key=lambda x: x.get("date", ""))

        return events

    @staticmethod
    def _serialize_workspace(workspace: GlobalWorkspace) -> Dict[str, Any]:
        """Serialize workspace to JSON-compatible dict."""
        return {
            "metadata": {
                "created_at": workspace.created_at,
                "last_updated": workspace.last_updated,
                "chunk_count": workspace.chunk_count,
                "document_count": workspace.document_count,
                "domain": workspace.domain
            },
            "actors": {
                aid: {
                    "id": a.id,
                    "name": a.name,
                    "actor_type": a.actor_type.value,
                    "aliases": a.aliases,
                    "roles": a.roles,
                    "states": [
                        {
                            "id": s.id,
                            "entity_id": s.entity_id,
                            "name": s.name,
                            "value": s.value,
                            "start_date": s.start_date,
                            "end_date": s.end_date,
                            "source_chunk_id": s.source_chunk_id
                        }
                        for s in a.states
                    ],
                    "spatio_temporal_link_ids": a.spatio_temporal_link_ids,
                    "involved_cases": a.involved_cases,
                    "source_chunk_ids": a.source_chunk_ids
                }
                for aid, a in workspace.actors.items()
            },
            "verb_phrases": {
                vid: {
                    "id": v.id,
                    "verb": v.verb,
                    "agent_id": v.agent_id,
                    "patient_ids": v.patient_ids,
                    "temporal_id": v.temporal_id,
                    "spatial_id": v.spatial_id,
                    "is_implicit": v.is_implicit,
                    "source_chunk_id": v.source_chunk_id
                }
                for vid, v in workspace.verb_phrases.items()
            },
            "questions": {
                qid: {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type.value,
                    "target_entity_id": q.target_entity_id,
                    "answerable": q.answerable,
                    "answer_text": q.answer_text,
                    "answer_entity_id": q.answer_entity_id,
                    "source_chunk_id": q.source_chunk_id,
                    "answered_in_chunk_id": q.answered_in_chunk_id
                }
                for qid, q in workspace.questions.items()
            },
            "spatio_temporal_links": {
                lid: {
                    "id": l.id,
                    "linked_entity_ids": l.linked_entity_ids,
                    "tag_type": l.tag_type.value,
                    "tag_value": l.tag_value,
                    "source_chunk_id": l.source_chunk_id
                }
                for lid, l in workspace.spatio_temporal_links.items()
            },
            "entity_summaries": workspace.entity_summaries
        }

    @staticmethod
    def _deserialize_workspace(data: Dict[str, Any]) -> GlobalWorkspace:
        """Deserialize workspace from JSON dict."""
        workspace = GlobalWorkspace()

        # Metadata
        meta = data.get("metadata", {})
        workspace.created_at = meta.get("created_at", datetime.now().isoformat())
        workspace.last_updated = meta.get("last_updated", datetime.now().isoformat())
        workspace.chunk_count = meta.get("chunk_count", 0)
        workspace.document_count = meta.get("document_count", 0)
        workspace.domain = meta.get("domain", "")

        # Actors
        for aid, adata in data.get("actors", {}).items():
            states = []
            for sdata in adata.get("states", []):
                states.append(State(
                    id=sdata["id"],
                    entity_id=sdata.get("entity_id", aid),
                    name=sdata["name"],
                    value=sdata["value"],
                    start_date=sdata.get("start_date"),
                    end_date=sdata.get("end_date"),
                    source_chunk_id=sdata.get("source_chunk_id", "")
                ))

            actor = Actor(
                id=adata["id"],
                name=adata["name"],
                actor_type=ActorType(adata.get("actor_type", "person")),
                aliases=adata.get("aliases", []),
                roles=adata.get("roles", []),
                states=states,
                spatio_temporal_link_ids=adata.get("spatio_temporal_link_ids", []),
                involved_cases=adata.get("involved_cases", []),
                source_chunk_ids=adata.get("source_chunk_ids", [])
            )
            workspace.actors[aid] = actor

        # Verb phrases
        for vid, vdata in data.get("verb_phrases", {}).items():
            workspace.verb_phrases[vid] = VerbPhrase(
                id=vdata["id"],
                verb=vdata["verb"],
                agent_id=vdata.get("agent_id"),
                patient_ids=vdata.get("patient_ids", []),
                temporal_id=vdata.get("temporal_id"),
                spatial_id=vdata.get("spatial_id"),
                is_implicit=vdata.get("is_implicit", False),
                source_chunk_id=vdata.get("source_chunk_id", "")
            )

        # Questions
        for qid, qdata in data.get("questions", {}).items():
            workspace.questions[qid] = PredictiveQuestion(
                id=qdata["id"],
                question_text=qdata["question_text"],
                question_type=QuestionType(qdata.get("question_type", "what")),
                target_entity_id=qdata.get("target_entity_id"),
                answerable=qdata.get("answerable", False),
                answer_text=qdata.get("answer_text"),
                answer_entity_id=qdata.get("answer_entity_id"),
                source_chunk_id=qdata.get("source_chunk_id", ""),
                answered_in_chunk_id=qdata.get("answered_in_chunk_id")
            )

        # Spatio-temporal links
        for lid, ldata in data.get("spatio_temporal_links", {}).items():
            workspace.spatio_temporal_links[lid] = SpatioTemporalLink(
                id=ldata["id"],
                linked_entity_ids=ldata.get("linked_entity_ids", []),
                tag_type=LinkType(ldata.get("tag_type", "temporal")),
                tag_value=ldata.get("tag_value"),
                source_chunk_id=ldata.get("source_chunk_id", "")
            )

        # Entity summaries
        workspace.entity_summaries = data.get("entity_summaries", {})

        return workspace


# ============================================================================
# WORKSPACE OPERATIONS
# ============================================================================

def merge_workspaces(ws1: GlobalWorkspace, ws2: GlobalWorkspace) -> GlobalWorkspace:
    """Merge two workspaces together."""
    merged = GlobalWorkspace()
    merged.domain = ws1.domain or ws2.domain

    # Merge actors (simple: just combine, no deduplication)
    merged.actors.update(ws1.actors)
    merged.actors.update(ws2.actors)

    # Merge other components
    merged.verb_phrases.update(ws1.verb_phrases)
    merged.verb_phrases.update(ws2.verb_phrases)

    merged.questions.update(ws1.questions)
    merged.questions.update(ws2.questions)

    merged.spatio_temporal_links.update(ws1.spatio_temporal_links)
    merged.spatio_temporal_links.update(ws2.spatio_temporal_links)

    merged.entity_summaries.update(ws1.entity_summaries)
    merged.entity_summaries.update(ws2.entity_summaries)

    merged.chunk_count = ws1.chunk_count + ws2.chunk_count
    merged.document_count = ws1.document_count + ws2.document_count
    merged.touch()

    return merged


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    from pathlib import Path

    print("Testing WorkspaceManager...")

    # Create a workspace
    workspace = GlobalWorkspace(domain="family")

    # Add some test data
    actor = Actor(
        id="test_001",
        name="John Smith",
        actor_type=ActorType.PERSON,
        roles=["Applicant", "Husband"]
    )
    workspace.add_actor(actor)

    question = PredictiveQuestion(
        id="q_001",
        question_text="When did the parties separate?",
        question_type=QuestionType.WHEN,
        answerable=False
    )
    workspace.questions[question.id] = question

    # Create manager
    manager = WorkspaceManager(workspace)

    # Get statistics
    stats = manager.get_statistics()
    print(f"\nWorkspace stats:")
    print(f"  - Actors: {stats['total_actors']}")
    print(f"  - Questions: {stats['total_questions']}")
    print(f"  - Unanswered: {stats['unanswered_questions']}")

    # Get ontology context
    context = manager.get_ontology_context()
    print(f"\nOntology context:")
    print(f"  - Role types: {context.role_types}")

    # Test save/load
    test_path = Path("test_workspace.json")
    manager.save(test_path)

    loaded = WorkspaceManager.load(test_path)
    print(f"\nLoaded workspace: {len(loaded.workspace.actors)} actors")

    # Cleanup
    test_path.unlink()
    print("\nTest complete!")
