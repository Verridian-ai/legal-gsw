"""
Legal Spacetime - Spatio-Temporal Entity Linking

This component links entities that share the same spatial or temporal context.
It's a critical part of the GSW model - binding WHO, WHAT, WHEN, and WHERE together.

In the brain, this is analogous to:
- Parahippocampal Place Area (spatial encoding)
- Entorhinal Cortex (temporal encoding)

Based on: GSW_prompt_spacetime.pdf
Adapted for: Australian Legal Domain
"""

import json
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.logic.gsw_schema import (
    Actor, SpatioTemporalLink, LinkType, ChunkExtraction
)


# ============================================================================
# SPACETIME PROMPT
# ============================================================================

SPACETIME_SYSTEM_PROMPT = """You are an expert at understanding spatio-temporal relationships in legal documents.

Your task is to identify groups of entities that share the same:
- TEMPORAL context (same date, time period, or event)
- SPATIAL context (same location, court, or address)

This binding is crucial for understanding legal narratives:
- "On 15 March 2020, the husband, wife, and children were at the matrimonial home"
  → All 4 entities share both temporal (15 March 2020) and spatial (matrimonial home) context

- "The hearing was held at Sydney Family Court"
  → The judge, parties, and hearing all share spatial context
"""

SPACETIME_USER_PROMPT = """
Analyze this text and the extracted entities to identify spatio-temporal links.

## Extracted Entities
{entities_json}

## Original Text
{input_text}

## Instructions

1. Find groups of entities that share TEMPORAL context:
   - Same specific date (e.g., "15 March 2020")
   - Same event (e.g., "the hearing", "the separation")
   - Same time period (e.g., "during the marriage")

2. Find groups of entities that share SPATIAL context:
   - Same location (e.g., "Sydney", "123 Smith Street")
   - Same court (e.g., "Family Court of Australia")
   - Same property (e.g., "the matrimonial home")

## Output Format

Return a JSON object:
```json
{{
    "spatio_temporal_links": [
        {{
            "linked_entity_ids": ["actor_001", "actor_002", "actor_005"],
            "tag_type": "temporal",
            "tag_value": "2020-03-15",
            "context_description": "Date of separation"
        }},
        {{
            "linked_entity_ids": ["actor_001", "actor_002", "actor_003"],
            "tag_type": "spatial",
            "tag_value": "123 Smith Street, Parramatta",
            "context_description": "Matrimonial home location"
        }}
    ]
}}
```

IMPORTANT:
- Only create links when entities CLEARLY share the same time/space
- Use specific values when mentioned (actual dates, addresses)
- Use null for tag_value if the context is implied but not explicitly stated
- Include context_description to explain why entities are linked
"""


# ============================================================================
# SPACETIME LINKER CLASS
# ============================================================================

class LegalSpacetime:
    """
    Links entities by shared spatio-temporal context.

    This is crucial for the GSW model because it creates the "bindings"
    that make episodic memory coherent. Just like the hippocampus binds
    together the what, where, and when of an experience.
    """

    def __init__(
        self,
        model: str = "google/gemini-2.0-flash-001",
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
        """Setup the LLM client."""
        if self.use_openrouter:
            import httpx
            self.client = httpx.Client(
                base_url="https://openrouter.ai/api/v1",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )

    def link_entities(
        self,
        extraction: ChunkExtraction,
        original_text: str
    ) -> List[SpatioTemporalLink]:
        """
        Analyze extracted entities and create spatio-temporal links.

        Args:
            extraction: The ChunkExtraction from the Operator
            original_text: The original text for context

        Returns:
            List of SpatioTemporalLink objects
        """
        if not extraction.actors:
            return []

        # Build entities JSON for prompt
        entities_data = []
        for actor in extraction.actors:
            entities_data.append({
                "id": actor.id,
                "name": actor.name,
                "type": actor.actor_type.value,
                "roles": actor.roles,
                "states": [{"name": s.name, "value": s.value} for s in actor.states]
            })

        entities_json = json.dumps(entities_data, indent=2)

        # Call LLM
        user_prompt = SPACETIME_USER_PROMPT.format(
            entities_json=entities_json,
            input_text=original_text[:10000]
        )

        try:
            response = self._call_llm(user_prompt)
            links = self._parse_response(response, extraction.chunk_id)
            return links
        except Exception as e:
            print(f"[Spacetime Error] {e}")
            # Fall back to rule-based linking
            return self._rule_based_linking(extraction)

    def _call_llm(self, user_prompt: str) -> str:
        """Call the LLM."""
        if self.use_openrouter:
            response = self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SPACETIME_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4000
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise NotImplementedError("Direct Google API not implemented")

    def _repair_json(self, text: str) -> str:
        """Attempt to repair common JSON issues."""
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

    def _parse_response(
        self,
        response: str,
        chunk_id: str
    ) -> List[SpatioTemporalLink]:
        """Parse LLM response into links."""
        # Clean markdown
        cleaned = response.strip()
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

        links = []
        for link_data in data.get("spatio_temporal_links", []):
            tag_type_str = link_data.get("tag_type", "temporal").lower()
            try:
                tag_type = LinkType(tag_type_str)
            except ValueError:
                tag_type = LinkType.TEMPORAL

            link = SpatioTemporalLink(
                id=f"link_{uuid4().hex[:8]}",
                linked_entity_ids=link_data.get("linked_entity_ids", []),
                tag_type=tag_type,
                tag_value=link_data.get("tag_value"),
                source_chunk_id=chunk_id,
                metadata={
                    "context_description": link_data.get("context_description", "")
                }
            )
            links.append(link)

        return links

    def _rule_based_linking(
        self,
        extraction: ChunkExtraction
    ) -> List[SpatioTemporalLink]:
        """
        Fallback rule-based linking when LLM is unavailable.

        Uses simple heuristics to link entities.
        """
        links = []

        # Find temporal entities
        temporal_actors = [
            a for a in extraction.actors
            if a.actor_type.value == "temporal"
        ]

        # Find location entities
        location_actors = [
            a for a in extraction.actors
            if a.actor_type.value == "location"
        ]

        # Link all person actors to temporal entities
        person_ids = [
            a.id for a in extraction.actors
            if a.actor_type.value == "person"
        ]

        for temporal in temporal_actors:
            if person_ids:
                link = SpatioTemporalLink(
                    id=f"link_{uuid4().hex[:8]}",
                    linked_entity_ids=person_ids + [temporal.id],
                    tag_type=LinkType.TEMPORAL,
                    tag_value=temporal.name,
                    source_chunk_id=extraction.chunk_id,
                    metadata={"method": "rule_based"}
                )
                links.append(link)

        for location in location_actors:
            if person_ids:
                link = SpatioTemporalLink(
                    id=f"link_{uuid4().hex[:8]}",
                    linked_entity_ids=person_ids + [location.id],
                    tag_type=LinkType.SPATIAL,
                    tag_value=location.name,
                    source_chunk_id=extraction.chunk_id,
                    metadata={"method": "rule_based"}
                )
                links.append(link)

        return links


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_dates_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract dates from legal text using regex patterns.

    Returns list of {"date": "...", "context": "..."}
    """
    patterns = [
        # Full dates: 15 March 2020, March 15, 2020
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
        # ISO format: 2020-03-15
        r'(\d{4}-\d{2}-\d{2})',
        # Short format: 15/03/2020
        r'(\d{1,2}/\d{1,2}/\d{4})',
    ]

    dates = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get surrounding context
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()

            dates.append({
                "date": match.group(1),
                "context": context
            })

    return dates


def extract_locations_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract locations from legal text.

    Returns list of {"location": "...", "context": "..."}
    """
    patterns = [
        # Street addresses
        r'(\d+\s+[A-Z][a-z]+\s+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Court|Ct|Place|Pl)[,\s]+[A-Z][a-z]+)',
        # Court names
        r'((?:Family|Federal|Supreme|District|Local)\s+Court\s+(?:of\s+)?(?:Australia|NSW|Victoria|Queensland)?)',
        # Suburbs/Cities
        r'(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    ]

    locations = []
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end].strip()

            locations.append({
                "location": match.group(1),
                "context": context
            })

    return locations


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    sample_text = """
    The parties married on 10 June 2010 in Sydney. They separated on
    1 March 2020 at the matrimonial home located at 123 Smith Street,
    Parramatta. The hearing was held at the Family Court of Australia
    in Sydney on 15 March 2024.
    """

    print("Extracting dates...")
    dates = extract_dates_from_text(sample_text)
    for d in dates:
        print(f"  - {d['date']}")

    print("\nExtracting locations...")
    locations = extract_locations_from_text(sample_text)
    for loc in locations:
        print(f"  - {loc['location']}")
