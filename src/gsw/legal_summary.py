"""
Legal Summary - Entity-Centric Narrative Generation

Generates coherent narrative summaries for each entity based on their
timeline of roles, states, and actions in the Global Workspace.

Based on: GSW_prompt_summary.pdf
Adapted for: Australian Legal Domain
"""

import json
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.logic.gsw_schema import (
    Actor, GlobalWorkspace, State, VerbPhrase, SpatioTemporalLink
)


# ============================================================================
# SUMMARY PROMPT
# ============================================================================

SUMMARY_SYSTEM_PROMPT = """You are an expert legal narrative summarizer.

Your task is to create concise, chronological summaries about legal entities
based on structured information from a Global Semantic Workspace.

The summary should read like a coherent story of the entity's involvement
in the legal matter, covering:
- Who they are (name, roles)
- Key dates and locations
- What happened to them (states, events)
- Relationships with other entities
"""

SUMMARY_USER_PROMPT = """
Create a summary for this entity:

## Entity Information
Name: {entity_name}
Type: {entity_type}
Roles: {roles}

## States (conditions over time)
{states_info}

## Actions Involving This Entity
{actions_info}

## Spatio-Temporal Context
{spacetime_info}

## Related Entities
{related_entities}

## Instructions
1. Write a single paragraph (3-5 sentences) summarizing the entity
2. Follow chronological order where dates are available
3. Include key dates, locations, and relationships
4. Focus on legally relevant information
5. Be factual - only include what's in the data

Return ONLY the summary paragraph, no markdown or formatting.
"""


# ============================================================================
# SUMMARY GENERATOR
# ============================================================================

class LegalSummary:
    """
    Generates entity-centric narrative summaries.

    These summaries are used for:
    - Question answering (provide context to QA system)
    - Human review (make the knowledge graph readable)
    - Retrieval (search for entities by summary content)
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        use_openrouter: bool = True
    ):
        self.model = model
        self.use_openrouter = use_openrouter

        if api_key:
            self.api_key = api_key
        elif use_openrouter:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
        else:
            self.api_key = os.getenv("GOOGLE_API_KEY")

        self._setup_client()

    def _setup_client(self) -> None:
        """Setup LLM client."""
        if self.use_openrouter and self.api_key:
            import httpx
            self.client = httpx.Client(
                base_url="https://openrouter.ai/api/v1",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )
        else:
            self.client = None

    def generate_summary(
        self,
        actor: Actor,
        workspace: GlobalWorkspace
    ) -> str:
        """
        Generate a narrative summary for an actor.

        Args:
            actor: The actor to summarize
            workspace: The GlobalWorkspace for context

        Returns:
            A narrative summary string
        """
        # Gather information about this actor
        states_info = self._format_states(actor.states)
        actions_info = self._format_actions(actor.id, workspace)
        spacetime_info = self._format_spacetime(actor.id, workspace)
        related_entities = self._find_related_entities(actor.id, workspace)

        # Try LLM generation
        if self.client:
            try:
                return self._llm_generate_summary(
                    actor, states_info, actions_info, spacetime_info, related_entities
                )
            except Exception as e:
                print(f"[Summary Warning] LLM generation failed: {e}")

        # Fallback to template-based summary
        return self._template_summary(
            actor, states_info, actions_info, spacetime_info, related_entities
        )

    def generate_all_summaries(
        self,
        workspace: GlobalWorkspace,
        actor_types: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Generate summaries for all actors in workspace.

        Args:
            workspace: The GlobalWorkspace
            actor_types: Optional filter for actor types (e.g., ["person"])

        Returns:
            Dict of actor_id -> summary
        """
        summaries = {}

        for actor_id, actor in workspace.actors.items():
            # Filter by type if specified
            if actor_types and actor.actor_type.value not in actor_types:
                continue

            try:
                summary = self.generate_summary(actor, workspace)
                summaries[actor_id] = summary
                workspace.entity_summaries[actor_id] = summary
            except Exception as e:
                print(f"[Summary Error] Failed for {actor.name}: {e}")

        return summaries

    def _format_states(self, states: List[State]) -> str:
        """Format states for prompt."""
        if not states:
            return "No states recorded."

        lines = []
        for state in states:
            date_info = ""
            if state.start_date:
                date_info = f" (from {state.start_date}"
                if state.end_date:
                    date_info += f" to {state.end_date}"
                date_info += ")"

            lines.append(f"- {state.name}: {state.value}{date_info}")

        return "\n".join(lines)

    def _format_actions(self, actor_id: str, workspace: GlobalWorkspace) -> str:
        """Format verb phrases involving this actor."""
        actions = []

        for verb in workspace.verb_phrases.values():
            if verb.agent_id == actor_id:
                action = f"- {verb.verb} (as agent)"
                if verb.patient_ids:
                    patients = [
                        workspace.actors.get(pid, {}).name
                        for pid in verb.patient_ids
                        if pid in workspace.actors
                    ]
                    if patients:
                        action += f" affecting {', '.join(patients)}"
                actions.append(action)

            elif actor_id in verb.patient_ids:
                agent_name = "Unknown"
                if verb.agent_id and verb.agent_id in workspace.actors:
                    agent_name = workspace.actors[verb.agent_id].name
                actions.append(f"- Was {verb.verb} by {agent_name}")

        return "\n".join(actions) if actions else "No actions recorded."

    def _format_spacetime(self, actor_id: str, workspace: GlobalWorkspace) -> str:
        """Format spatio-temporal links for this actor."""
        links = []

        for link in workspace.spatio_temporal_links.values():
            if actor_id in link.linked_entity_ids:
                tag_type = link.tag_type.value.title()
                tag_value = link.tag_value or "Unknown"
                links.append(f"- {tag_type}: {tag_value}")

        return "\n".join(links) if links else "No spatio-temporal context."

    def _find_related_entities(
        self,
        actor_id: str,
        workspace: GlobalWorkspace
    ) -> str:
        """Find entities related to this actor via actions or links."""
        related = set()

        # Via verb phrases
        for verb in workspace.verb_phrases.values():
            if verb.agent_id == actor_id:
                related.update(verb.patient_ids)
            elif actor_id in verb.patient_ids:
                if verb.agent_id:
                    related.add(verb.agent_id)

        # Via spatio-temporal links
        for link in workspace.spatio_temporal_links.values():
            if actor_id in link.linked_entity_ids:
                related.update(link.linked_entity_ids)

        related.discard(actor_id)  # Remove self

        # Format as names
        related_names = []
        for rid in related:
            if rid in workspace.actors:
                actor = workspace.actors[rid]
                related_names.append(f"{actor.name} ({actor.actor_type.value})")

        return ", ".join(related_names[:10]) if related_names else "No related entities."

    def _llm_generate_summary(
        self,
        actor: Actor,
        states_info: str,
        actions_info: str,
        spacetime_info: str,
        related_entities: str
    ) -> str:
        """Generate summary using LLM."""
        prompt = SUMMARY_USER_PROMPT.format(
            entity_name=actor.name,
            entity_type=actor.actor_type.value,
            roles=", ".join(actor.roles) if actor.roles else "No roles assigned",
            states_info=states_info,
            actions_info=actions_info,
            spacetime_info=spacetime_info,
            related_entities=related_entities
        )

        response = self.client.post(
            "/chat/completions",
            json={
                "model": f"google/{self.model}",
                "messages": [
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
        )
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"].strip()

    def _template_summary(
        self,
        actor: Actor,
        states_info: str,
        actions_info: str,
        spacetime_info: str,
        related_entities: str
    ) -> str:
        """Generate summary using templates (fallback)."""
        parts = []

        # Identity
        name = actor.name
        actor_type = actor.actor_type.value

        if actor.roles:
            roles_str = " and ".join(actor.roles[:3])
            parts.append(f"{name} is a {actor_type} serving as {roles_str}.")
        else:
            parts.append(f"{name} is a {actor_type} in this matter.")

        # States
        if actor.states:
            current_states = [s for s in actor.states if s.end_date is None]
            if current_states:
                state = current_states[0]
                parts.append(f"Currently, their {state.name} is {state.value}.")

        # Temporal context
        temporal_lines = [l for l in spacetime_info.split('\n') if 'Temporal' in l]
        if temporal_lines:
            date = temporal_lines[0].split(': ')[-1]
            parts.append(f"Key events occurred on {date}.")

        # Related entities
        if related_entities and "No related" not in related_entities:
            parts.append(f"Related to: {related_entities}.")

        return " ".join(parts)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    from src.logic.gsw_schema import ActorType

    print("Testing Legal Summary...")

    # Create test data
    workspace = GlobalWorkspace(domain="family")

    actor = Actor(
        id="actor_001",
        name="John Smith",
        actor_type=ActorType.PERSON,
        roles=["Applicant", "Husband", "Father"],
        states=[
            State(
                id="state_001",
                entity_id="actor_001",
                name="RelationshipStatus",
                value="Separated",
                start_date="2020-03-01"
            ),
            State(
                id="state_002",
                entity_id="actor_001",
                name="Employment",
                value="Accountant earning $120,000"
            )
        ]
    )
    workspace.add_actor(actor)

    # Create summarizer (no API key = template mode)
    summarizer = LegalSummary(api_key=None)

    # Generate summary
    summary = summarizer.generate_summary(actor, workspace)
    print(f"\nGenerated summary:\n{summary}")
