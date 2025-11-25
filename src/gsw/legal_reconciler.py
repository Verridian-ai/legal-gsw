"""
Legal Reconciler - Entity Merging and Question Answering

The Reconciler performs two critical functions:
1. Entity Reconciliation: Merge entities across chunks (e.g., "the husband" = "John Smith")
2. Question Answering: Check if new chunks answer previously unanswered questions

In the brain, this is analogous to:
- CA1: Integrating new information with existing memories
- CA3: Pattern completion (recognizing the same entity)
- DG: Pattern separation (distinguishing similar but different entities)

Based on: GSW_prompt_reconcile.pdf
Adapted for: Australian Legal Domain
"""

import json
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.logic.gsw_schema import (
    Actor, State, PredictiveQuestion, ChunkExtraction, GlobalWorkspace
)
from src.utils.toon import ToonEncoder


# ============================================================================
# RECONCILE PROMPT
# ============================================================================

RECONCILE_SYSTEM_PROMPT = """You are an expert at entity reconciliation and question answering in legal documents.

Your task is to:
1. Identify when entities in a new chunk refer to the SAME entity as one already in the workspace
2. Determine if the new chunk answers any previously unanswered questions

This is crucial for building a coherent knowledge graph across multiple chunks of a legal document.
"""

RECONCILE_USER_PROMPT = """
## Task 1: Entity Reconciliation

Match entities from the new chunk to existing entities in the workspace.

### Existing Entities in Workspace:
{existing_entities}

### New Entities from Current Chunk:
{new_entities}

### Guidelines for Matching:
- Match by NAME: "John Smith" = "Mr Smith" = "the husband" = "the applicant"
- Match by ROLE: If roles align (both "Applicant"), likely same person
- Match by CONTEXT: Same case, same proceedings = likely same entity
- DO NOT match different people who happen to share a name

## Task 2: Question Answering

Check if this chunk answers any unanswered questions.

### Unanswered Questions:
{unanswered_questions}

### Current Chunk Text:
{chunk_text}

## Output Format

```json
{{
    "entity_matches": [
        {{
            "new_entity_id": "actor_005",
            "existing_entity_id": "actor_001",
            "confidence": 0.95,
            "reason": "Same person - 'the husband' refers to John Smith identified earlier"
        }}
    ],
    "answered_questions": [
        {{
            "question_id": "q_001",
            "answer_text": "The parties separated on 1 March 2020",
            "answer_entity_id": "actor_010",
            "confidence": 0.9
        }}
    ],
    "new_entities": [
        "actor_008"
    ]
}}
```

- entity_matches: Links between new and existing entities
- answered_questions: Questions that can now be answered from this chunk
- new_entities: Entity IDs that are genuinely NEW (not matches to existing)
"""


# ============================================================================
# RECONCILER CLASS
# ============================================================================

class LegalReconciler:
    """
    The Reconciler integrates new chunk extractions into the global workspace.

    Key functions:
    1. Entity Reconciliation - Match "the husband" to "John Smith"
    2. Question Answering - Find answers to pending questions
    3. State Updates - Update entity states with new information
    4. Conflict Resolution - Handle contradictory information
    """

    def __init__(
        self,
        model: str = "google/gemini-2.0-flash-001",
        api_key: Optional[str] = None,
        use_openrouter: bool = True,
        similarity_threshold: float = 0.85,
        use_toon: bool = True  # Enable TOON format for ~71% token reduction
    ):
        self.model = model
        self.use_openrouter = use_openrouter
        self.similarity_threshold = similarity_threshold
        self.use_toon = use_toon

        if api_key:
            self.api_key = api_key
        elif use_openrouter:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
        else:
            self.api_key = os.getenv("GOOGLE_API_KEY")

        self._setup_client()

        # Optional: Vector store for entity embeddings
        self.vector_store = None

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

    def _repair_json(self, text: str) -> str:
        """Attempt to repair common JSON issues from LLM output."""
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        text = re.sub(r'}\s*{', '},{', text)
        text = re.sub(r']\s*\[', '],[', text)
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        if open_braces > 0 or open_brackets > 0:
            last_comma = max(text.rfind(',{'), text.rfind(',['), text.rfind(',"'))
            if last_comma > len(text) // 2:
                text = text[:last_comma]
            text += ']' * open_brackets + '}' * open_braces
        return text

    def reconcile(
        self,
        new_extraction: ChunkExtraction,
        workspace: GlobalWorkspace,
        chunk_text: str
    ) -> Tuple[ChunkExtraction, List[Dict[str, Any]]]:
        """
        Reconcile a new chunk extraction with the global workspace.

        Args:
            new_extraction: The ChunkExtraction from the Operator
            workspace: The current GlobalWorkspace
            chunk_text: Original text of the chunk

        Returns:
            Tuple of (updated_extraction, reconciliation_log)
        """
        reconciliation_log = []

        # Step 1: Entity Reconciliation
        entity_matches = self._reconcile_entities(
            new_extraction.actors,
            workspace,
            chunk_text
        )

        # Apply entity matches
        for match in entity_matches:
            new_id = match["new_entity_id"]
            existing_id = match["existing_entity_id"]

            # Find the new actor
            new_actor = next(
                (a for a in new_extraction.actors if a.id == new_id),
                None
            )

            if new_actor and existing_id in workspace.actors:
                existing_actor = workspace.actors[existing_id]

                # Merge information
                self._merge_actors(existing_actor, new_actor)

                # Update references in extraction
                self._update_references(new_extraction, new_id, existing_id)

                reconciliation_log.append({
                    "action": "merged",
                    "new_id": new_id,
                    "existing_id": existing_id,
                    "reason": match.get("reason", "")
                })

        # Step 2: Answer Pending Questions
        answered = self._answer_questions(
            workspace.get_unanswered_questions(),
            chunk_text,
            new_extraction
        )

        for answer in answered:
            q_id = answer["question_id"]
            if q_id in workspace.questions:
                workspace.questions[q_id].answerable = True
                workspace.questions[q_id].answer_text = answer["answer_text"]
                workspace.questions[q_id].answer_entity_id = answer.get("answer_entity_id")
                workspace.questions[q_id].answered_in_chunk_id = new_extraction.chunk_id

                reconciliation_log.append({
                    "action": "answered_question",
                    "question_id": q_id,
                    "answer": answer["answer_text"]
                })

        # Step 3: Add new entities to workspace
        for actor in new_extraction.actors:
            # Check if this actor was matched to an existing one
            was_matched = any(
                m["new_entity_id"] == actor.id for m in entity_matches
            )

            if not was_matched:
                workspace.add_actor(actor)
                reconciliation_log.append({
                    "action": "added_new",
                    "entity_id": actor.id,
                    "name": actor.name
                })

        # Step 4: Add new questions
        for question in new_extraction.questions:
            workspace.questions[question.id] = question

        # Step 5: Add verb phrases and links
        for verb in new_extraction.verb_phrases:
            workspace.verb_phrases[verb.id] = verb

        for link in new_extraction.spatio_temporal_links:
            workspace.spatio_temporal_links[link.id] = link

        # Update workspace metadata
        workspace.chunk_count += 1
        workspace.touch()

        return new_extraction, reconciliation_log

    def _reconcile_entities(
        self,
        new_actors: List[Actor],
        workspace: GlobalWorkspace,
        chunk_text: str
    ) -> List[Dict[str, Any]]:
        """
        Find matches between new actors and existing workspace actors.
        """
        if not workspace.actors or not new_actors:
            return []

        # Try LLM-based reconciliation first
        if self.client:
            try:
                return self._llm_reconcile_entities(new_actors, workspace, chunk_text)
            except Exception as e:
                print(f"[Reconciler Warning] LLM reconciliation failed: {e}")

        # Fall back to rule-based reconciliation
        return self._rule_based_reconciliation(new_actors, workspace)

    def _llm_reconcile_entities(
        self,
        new_actors: List[Actor],
        workspace: GlobalWorkspace,
        chunk_text: str
    ) -> List[Dict[str, Any]]:
        """Use LLM for entity reconciliation."""
        # Build existing entities summary
        existing_summary = []
        for actor in list(workspace.actors.values())[:50]:  # Limit for context
            existing_summary.append({
                "id": actor.id,
                "name": actor.name,
                "aliases": actor.aliases,
                "roles": actor.roles,
                "type": actor.actor_type.value
            })

        # Build new entities summary
        new_summary = []
        for actor in new_actors:
            new_summary.append({
                "id": actor.id,
                "name": actor.name,
                "aliases": actor.aliases,
                "roles": actor.roles,
                "type": actor.actor_type.value
            })

        # Build unanswered questions summary
        unanswered = workspace.get_unanswered_questions()[:20]
        questions_summary = [
            {"id": q.id, "question": q.question_text}
            for q in unanswered
        ]

        # Format entities using TOON (~71% token reduction) or JSON
        if self.use_toon:
            existing_str = self._format_actors_toon(existing_summary)
            new_str = self._format_actors_toon(new_summary)
            questions_str = self._format_questions_toon(questions_summary)
        else:
            existing_str = json.dumps(existing_summary, indent=2)
            new_str = json.dumps(new_summary, indent=2)
            questions_str = json.dumps(questions_summary, indent=2)

        prompt = RECONCILE_USER_PROMPT.format(
            existing_entities=existing_str,
            new_entities=new_str,
            unanswered_questions=questions_str,
            chunk_text=chunk_text[:5000]
        )

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": RECONCILE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            }
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        # Parse response
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                json_str = match.group()
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    repaired = self._repair_json(json_str)
                    try:
                        data = json.loads(repaired)
                    except json.JSONDecodeError:
                        return []
            else:
                return []
        return data.get("entity_matches", [])

    def _rule_based_reconciliation(
        self,
        new_actors: List[Actor],
        workspace: GlobalWorkspace
    ) -> List[Dict[str, Any]]:
        """
        Rule-based entity reconciliation fallback.

        Matches entities based on:
        - Exact name match
        - Alias match
        - Role alignment
        """
        matches = []

        for new_actor in new_actors:
            new_name = new_actor.name.lower().strip()
            new_aliases = [a.lower().strip() for a in new_actor.aliases]

            for existing_id, existing_actor in workspace.actors.items():
                existing_name = existing_actor.name.lower().strip()
                existing_aliases = [a.lower().strip() for a in existing_actor.aliases]

                # Check for name/alias matches
                match_found = False
                reason = ""

                # Exact name match
                if new_name == existing_name:
                    match_found = True
                    reason = f"Exact name match: {new_actor.name}"

                # New name in existing aliases
                elif new_name in existing_aliases:
                    match_found = True
                    reason = f"Name matches alias: {new_actor.name}"

                # Existing name in new aliases
                elif existing_name in new_aliases:
                    match_found = True
                    reason = f"Alias matches name: {existing_actor.name}"

                # Cross-alias match
                elif set(new_aliases) & set(existing_aliases):
                    match_found = True
                    common = list(set(new_aliases) & set(existing_aliases))[0]
                    reason = f"Common alias: {common}"

                # Role-based matching for common legal terms
                if not match_found:
                    # Match "the husband"/"the wife" patterns
                    role_mappings = {
                        "the husband": ["husband", "applicant husband", "respondent husband"],
                        "the wife": ["wife", "applicant wife", "respondent wife"],
                        "the applicant": ["applicant"],
                        "the respondent": ["respondent"],
                        "the child": ["child", "subject child"],
                    }

                    for term, related_roles in role_mappings.items():
                        if new_name == term or term in new_aliases:
                            # Check if existing actor has matching role
                            existing_roles_lower = [r.lower() for r in existing_actor.roles]
                            if any(r in existing_roles_lower for r in related_roles):
                                match_found = True
                                reason = f"Role-based match: {term} -> {existing_actor.name}"
                                break

                if match_found:
                    matches.append({
                        "new_entity_id": new_actor.id,
                        "existing_entity_id": existing_id,
                        "confidence": 0.8,
                        "reason": reason
                    })
                    break  # Only match to one existing entity

        return matches

    def _merge_actors(self, existing: Actor, new: Actor) -> None:
        """Merge information from new actor into existing actor."""
        # Add new aliases
        for alias in new.aliases:
            if alias not in existing.aliases and alias != existing.name:
                existing.aliases.append(alias)

        # Add the new name as alias if different
        if new.name != existing.name and new.name not in existing.aliases:
            existing.aliases.append(new.name)

        # Add new roles
        for role in new.roles:
            if role not in existing.roles:
                existing.roles.append(role)

        # Add new states
        for state in new.states:
            # Check if we already have this state type with same value
            existing_state = next(
                (s for s in existing.states
                 if s.name == state.name and s.value == state.value),
                None
            )
            if not existing_state:
                state.entity_id = existing.id
                existing.states.append(state)

        # Track source chunks
        for chunk_id in new.source_chunk_ids:
            if chunk_id not in existing.source_chunk_ids:
                existing.source_chunk_ids.append(chunk_id)

    def _update_references(
        self,
        extraction: ChunkExtraction,
        old_id: str,
        new_id: str
    ) -> None:
        """Update all references from old_id to new_id in extraction."""
        # Update verb phrase references
        for verb in extraction.verb_phrases:
            if verb.agent_id == old_id:
                verb.agent_id = new_id
            verb.patient_ids = [
                new_id if pid == old_id else pid
                for pid in verb.patient_ids
            ]
            if verb.temporal_id == old_id:
                verb.temporal_id = new_id
            if verb.spatial_id == old_id:
                verb.spatial_id = new_id

        # Update spatio-temporal links
        for link in extraction.spatio_temporal_links:
            link.linked_entity_ids = [
                new_id if eid == old_id else eid
                for eid in link.linked_entity_ids
            ]

        # Update question references
        for q in extraction.questions:
            if q.target_entity_id == old_id:
                q.target_entity_id = new_id
            if q.answer_entity_id == old_id:
                q.answer_entity_id = new_id

    def _answer_questions(
        self,
        questions: List[PredictiveQuestion],
        chunk_text: str,
        extraction: ChunkExtraction
    ) -> List[Dict[str, Any]]:
        """
        Check if the chunk text answers any pending questions.
        """
        if not questions:
            return []

        answered = []
        chunk_lower = chunk_text.lower()

        for q in questions:
            q_text = q.question_text.lower()

            # Simple pattern matching for common question types
            answer_found = None

            # When questions
            if "when" in q_text:
                # Look for dates in the chunk
                date_patterns = [
                    r'(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4})',
                    r'((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4})',
                    r'(\d{4}-\d{2}-\d{2})',
                ]

                # Check if question topic is in chunk
                topic_words = ["separate", "marry", "divorce", "hear", "order", "file"]
                for word in topic_words:
                    if word in q_text and word in chunk_lower:
                        # Find nearby date
                        for pattern in date_patterns:
                            matches = re.findall(pattern, chunk_lower)
                            if matches:
                                answer_found = matches[0]
                                break
                        break

            # Who questions
            elif "who" in q_text:
                # Check if we have new person actors
                for actor in extraction.actors:
                    if actor.actor_type.value == "person":
                        if any(role.lower() in q_text for role in actor.roles):
                            answer_found = actor.name
                            break

            # What questions about value
            elif "value" in q_text or "worth" in q_text:
                # Look for dollar amounts
                money_pattern = r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|m))?'
                matches = re.findall(money_pattern, chunk_lower)
                if matches:
                    answer_found = matches[0]

            if answer_found:
                answered.append({
                    "question_id": q.id,
                    "answer_text": str(answer_found).title(),
                    "answer_entity_id": None,
                    "confidence": 0.7
                })

        return answered

    # =========================================================================
    # TOON Formatting Helpers (~71% token reduction)
    # =========================================================================

    def _format_actors_toon(self, actors: List[Dict]) -> str:
        """
        Format actors in TOON format for compact LLM prompts.

        Example output:
        Actors[3]{id,name,type,aliases,roles}
        actor_001,John Smith,person,the husband|Mr Smith,Applicant|Husband
        actor_002,Jane Smith,person,the wife,Respondent|Wife
        actor_003,Family Court,organization,,Court
        """
        if not actors:
            return "No existing entities."

        headers = ["id", "name", "type", "aliases", "roles"]
        data = []
        for a in actors:
            aliases = a.get("aliases", [])
            aliases_str = "|".join(aliases) if aliases else ""
            roles = a.get("roles", [])
            roles_str = "|".join(roles) if roles else ""

            data.append([
                a.get("id", ""),
                a.get("name", ""),
                a.get("type", ""),
                aliases_str,
                roles_str
            ])

        return ToonEncoder.encode("Actors", headers, data)

    def _format_questions_toon(self, questions: List[Dict]) -> str:
        """
        Format questions in TOON format for compact LLM prompts.

        Example output:
        Questions[2]{id,question}
        q_001,When did the parties separate?
        q_002,What is the value of the matrimonial home?
        """
        if not questions:
            return "No unanswered questions."

        headers = ["id", "question"]
        data = [
            [q.get("id", ""), q.get("question", "")]
            for q in questions
        ]

        return ToonEncoder.encode("Questions", headers, data)


# ============================================================================
# VECTOR-BASED RECONCILIATION (Optional Enhancement)
# ============================================================================

class VectorReconciler:
    """
    Enhanced reconciler using vector embeddings for entity matching.

    Uses the existing vector_store.py for embedding-based similarity.
    """

    def __init__(self, embedding_model: str = "BAAI/bge-m3"):
        self.embedding_model = embedding_model
        self.embeddings: Dict[str, List[float]] = {}

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts."""
        # This would use the sentence-transformers model
        # Placeholder for now
        return 0.0


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Testing Legal Reconciler...")

    # Create a sample workspace
    workspace = GlobalWorkspace(domain="family")

    # Add an existing actor
    existing_actor = Actor(
        id="actor_001",
        name="John Smith",
        actor_type="person",
        aliases=["the husband"],
        roles=["Applicant", "Husband"],
        source_chunk_ids=["chunk_001"]
    )
    workspace.add_actor(existing_actor)

    # Add an unanswered question
    question = PredictiveQuestion(
        id="q_001",
        question_text="When did the parties separate?",
        question_type="when",
        answerable=False,
        source_chunk_id="chunk_001"
    )
    workspace.questions[question.id] = question

    print(f"Workspace has {len(workspace.actors)} actors")
    print(f"Workspace has {len(workspace.get_unanswered_questions())} unanswered questions")

    # Create a new extraction with "the applicant" (should match John Smith)
    new_actor = Actor(
        id="actor_new",
        name="the applicant",
        actor_type="person",
        roles=["Applicant"],
        source_chunk_ids=["chunk_002"]
    )

    new_extraction = ChunkExtraction(
        chunk_id="chunk_002",
        actors=[new_actor]
    )

    chunk_text = "The applicant separated from the respondent on 1 March 2020."

    # Test rule-based reconciliation
    reconciler = LegalReconciler(api_key=None)  # No API key = rule-based only
    matches = reconciler._rule_based_reconciliation(
        new_extraction.actors,
        workspace
    )

    print(f"\nFound {len(matches)} entity matches:")
    for match in matches:
        print(f"  - {match['new_entity_id']} -> {match['existing_entity_id']}")
        print(f"    Reason: {match['reason']}")
