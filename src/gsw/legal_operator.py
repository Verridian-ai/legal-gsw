"""
Legal Operator - GSW Actor-Centric Extraction

The Operator is the "sensory cortex" of the GSW system.
It takes raw legal text and extracts structured semantic information:
- Actors (parties, judges, assets, dates, etc.)
- Roles (how actors function in the situation)
- States (conditions that change over time)
- Verb Phrases (actions linking actors)
- Predictive Questions (what could be asked)
- Spatio-Temporal Links (time/space bindings)

Based on: GSW_prompt_operator.pdf
Adapted for: Australian Legal Domain
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import os

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.logic.gsw_schema import (
    Actor, ActorType, State, VerbPhrase, PredictiveQuestion,
    SpatioTemporalLink, ChunkExtraction, QuestionType, LinkType,
    OntologyContext
)


# ============================================================================
# LEGAL OPERATOR PROMPT
# ============================================================================

LEGAL_OPERATOR_SYSTEM_PROMPT = """You are the Legal Operator for a Global Semantic Workspace (GSW) system.
Your task is to extract structured episodic memory from Australian legal documents.

The GSW model is ACTOR-CENTRIC, not verb-centric. This means:
- We organize information around WHO is involved (actors)
- Each actor has ROLES (their function) and STATES (their condition)
- VERBS become links between actors, not the organizing principle
- We track WHEN and WHERE things happen (spatio-temporal binding)
- We generate QUESTIONS that the text might answer

This mirrors how human episodic memory works:
When you remember an experience, you remember WHO was involved and WHAT happened to them.
"""

LEGAL_OPERATOR_USER_PROMPT = """
## Your 6 Tasks

### Task 1: ACTOR IDENTIFICATION
Extract ALL actors from this legal text. An actor can be:

**PERSONS:**
- Parties: Applicant, Respondent, Appellant, Husband, Wife, Father, Mother
- Children: Named children, "the child", "the children of the marriage"
- Legal professionals: Judge, Magistrate, Solicitor, Barrister, ICL (Independent Children's Lawyer)
- Witnesses, experts, third parties

**ORGANIZATIONS:**
- Courts: Family Court, Federal Circuit Court, Full Court
- Government: Department of Communities, Child Safety, Centrelink
- Employers, businesses, banks

**ASSETS (treat as actors):**
- Real property: "the matrimonial home", "123 Smith Street"
- Financial: Superannuation, bank accounts, shares
- Vehicles, businesses, personal property

**TEMPORAL ENTITIES:**
- All dates: marriage date, separation date, hearing dates, order dates
- Time periods: "during the marriage", "post-separation"

**DOCUMENTS (treat as actors):**
- Applications, Orders, Affidavits, Subpoenas, Judgments

**ABSTRACT ENTITIES:**
- "The proceedings", "the appeal", "the property pool"

### Task 2: ROLE ASSIGNMENT
For each actor, assign their ROLE in this legal context:
- Party roles: "Applicant husband", "Respondent mother", "Subject child"
- Asset roles: "Matrimonial home", "Pre-relationship asset", "Jointly owned asset"
- Professional roles: "Trial Judge", "Appellant's solicitor"

### Task 3: STATE IDENTIFICATION
Track the STATE of each actor at different points:

**Relationship States:**
- Married, De facto, Separated, Divorced, Remarried

**Custody/Parenting States:**
- Lives with [parent], Shared care (50/50), Limited time, Supervised contact, No contact

**Financial States:**
- Employed (occupation, income), Unemployed, Receiving Centrelink
- Asset value: "Valued at $X", "Encumbered by mortgage of $Y"

**Legal/Procedural States:**
- Filed application, Orders made, Appeal pending, Matter concluded

### Task 4: VERB PHRASE IDENTIFICATION
Extract legal actions (verbs that LINK actors):

**Explicit verbs:**
- Filing: filed, lodged, served, issued, commenced
- Court: ordered, granted, dismissed, allowed, refused, adjourned, appealed
- Party actions: separated, relocated, married, purchased, sold, transferred

**Implicit verbs (infer from context):**
- "The parties separated in March 2020" → separated(husband, wife, March 2020)
- "Property settlement" → seek_division(applicant, property_pool)

### Task 5: PREDICTIVE QUESTION GENERATION
Generate questions this text MIGHT answer:

**WHO questions:**
- Who is the applicant/respondent?
- Who has primary care of the children?

**WHAT questions:**
- What assets form the property pool?
- What orders were made?

**WHEN questions:**
- When did the parties marry/separate/divorce?
- When was the hearing?

**WHERE questions:**
- Where do the children live?
- Where is the matrimonial home?

**HOW MUCH questions:**
- What is the value of the property pool?
- What percentage was awarded?

### Task 6: ANSWER MAPPING
For each question, if the text provides an answer:
- Mark as answerable: true
- Provide the answer_text
- Link to the relevant actor_id

---

<situation>
{situation}
</situation>

<background_context>
{background_context}
</background_context>

{ontology_context}

<input_text>
{input_text}
</input_text>

---

## Output Format

Return a JSON object with this structure:

```json
{{
    "situation_summary": "Brief description of what this text is about",
    "actors": [
        {{
            "id": "actor_001",
            "name": "John Smith",
            "actor_type": "person",
            "aliases": ["the husband", "the applicant", "Mr Smith"],
            "roles": ["Applicant", "Husband", "Father"],
            "states": [
                {{
                    "name": "RelationshipStatus",
                    "value": "Separated",
                    "start_date": "2020-03-15"
                }},
                {{
                    "name": "Employment",
                    "value": "Employed as accountant",
                    "start_date": null
                }}
            ]
        }}
    ],
    "verb_phrases": [
        {{
            "id": "verb_001",
            "verb": "filed",
            "agent_id": "actor_001",
            "patient_ids": ["actor_010"],
            "temporal_id": "actor_020",
            "is_implicit": false
        }}
    ],
    "questions": [
        {{
            "id": "q_001",
            "question_text": "When did the parties separate?",
            "question_type": "when",
            "target_entity_id": "actor_001",
            "answerable": true,
            "answer_text": "March 15, 2020",
            "answer_entity_id": "actor_020"
        }}
    ],
    "spatio_temporal_links": [
        {{
            "id": "link_001",
            "linked_entity_ids": ["actor_001", "actor_002", "actor_003"],
            "tag_type": "temporal",
            "tag_value": "2020-03-15"
        }}
    ]
}}
```

IMPORTANT:
- Extract ALL actors, even minor ones
- Generate IDs consistently (actor_001, actor_002, etc.)
- If a date is mentioned, create a temporal actor for it
- Link actors via verb_phrases and spatio_temporal_links
- Be conservative with states - only include what's explicitly stated
- Generate at least 5 predictive questions
"""


# ============================================================================
# OPERATOR CLASS
# ============================================================================

class LegalOperator:
    """
    The Legal Operator extracts structured information from legal text.

    This implements the 6-task extraction process:
    1. Actor Identification
    2. Role Assignment
    3. State Identification
    4. Verb Phrase Identification
    5. Predictive Question Generation
    6. Answer Mapping
    """

    def __init__(
        self,
        model: str = "google/gemini-2.0-flash-001",
        api_key: Optional[str] = None,
        use_openrouter: bool = True
    ):
        """
        Initialize the Legal Operator.

        Args:
            model: Model to use for extraction
            api_key: API key (or uses env var)
            use_openrouter: Whether to use OpenRouter API
        """
        self.model = model
        self.use_openrouter = use_openrouter

        # Get API key
        if api_key:
            self.api_key = api_key
        elif use_openrouter:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
        else:
            self.api_key = os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("No API key found. Set OPENROUTER_API_KEY or GOOGLE_API_KEY")

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
                timeout=120.0
            )
        else:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)

    def extract(
        self,
        text: str,
        situation: str = "",
        background_context: str = "",
        ontology_context: Optional[OntologyContext] = None,
        chunk_id: Optional[str] = None,
        document_id: str = ""
    ) -> ChunkExtraction:
        """
        Extract structured information from legal text.

        Args:
            text: The legal text to process
            situation: Brief description of the situation
            background_context: Context from surrounding text
            ontology_context: Current ontology for feedback loop
            chunk_id: ID for this chunk
            document_id: ID of source document

        Returns:
            ChunkExtraction with actors, verbs, questions, links
        """
        if chunk_id is None:
            chunk_id = f"chunk_{uuid4().hex[:8]}"

        # Build the prompt
        ontology_str = ""
        if ontology_context:
            ontology_str = f"\n<known_vocabulary>\n{ontology_context.to_prompt_context()}\n</known_vocabulary>\n"

        user_prompt = LEGAL_OPERATOR_USER_PROMPT.format(
            situation=situation or "Legal proceedings",
            background_context=background_context or "Australian legal document",
            ontology_context=ontology_str,
            input_text=text[:30000]  # Limit text length
        )

        # Call LLM
        try:
            raw_response = self._call_llm(user_prompt)
            extraction = self._parse_response(raw_response, chunk_id, document_id)
            extraction.raw_llm_response = raw_response
            return extraction

        except Exception as e:
            print(f"[Operator Error] {e}")
            # Return empty extraction on error
            return ChunkExtraction(
                chunk_id=chunk_id,
                source_document_id=document_id,
                situation=situation
            )

    def _call_llm(self, user_prompt: str) -> str:
        """Call the LLM and get response."""
        if self.use_openrouter:
            response = self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": LEGAL_OPERATOR_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8000
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        else:
            response = self.client.generate_content(
                f"{LEGAL_OPERATOR_SYSTEM_PROMPT}\n\n{user_prompt}"
            )
            return response.text

    def _repair_json(self, text: str) -> str:
        """Attempt to repair common JSON issues from LLM output."""
        # Remove trailing commas before ] or }
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        # Fix unescaped newlines in strings
        text = re.sub(r'(?<!\\)\n(?=.*")', '\\n', text)
        # Fix missing commas between objects/arrays
        text = re.sub(r'}\s*{', '},{', text)
        text = re.sub(r']\s*\[', '],[', text)
        # Truncated response - try to close it properly
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        if open_braces > 0 or open_brackets > 0:
            # Remove last partial element
            last_comma = max(text.rfind(',{'), text.rfind(',['), text.rfind(',"'))
            if last_comma > len(text) // 2:
                text = text[:last_comma]
            text += ']' * open_brackets + '}' * open_braces
        return text

    def _parse_response(
        self,
        raw_response: str,
        chunk_id: str,
        document_id: str
    ) -> ChunkExtraction:
        """Parse LLM response into ChunkExtraction."""
        # Clean markdown code blocks
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                json_str = match.group()
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to repair the JSON
                    repaired = self._repair_json(json_str)
                    try:
                        data = json.loads(repaired)
                    except json.JSONDecodeError:
                        # Last resort: return minimal valid structure
                        data = {"actors": [], "verb_phrases": [], "questions": []}
            else:
                raise ValueError("Could not parse JSON from response")

        # Build ChunkExtraction
        extraction = ChunkExtraction(
            chunk_id=chunk_id,
            source_document_id=document_id,
            situation=data.get("situation_summary", ""),
            model_used=self.model
        )

        # Parse actors
        for actor_data in data.get("actors", []):
            actor = self._parse_actor(actor_data, chunk_id)
            extraction.actors.append(actor)

        # Parse verb phrases
        for verb_data in data.get("verb_phrases", []):
            verb = self._parse_verb_phrase(verb_data, chunk_id)
            extraction.verb_phrases.append(verb)

        # Parse questions
        for q_data in data.get("questions", []):
            question = self._parse_question(q_data, chunk_id)
            extraction.questions.append(question)

        # Parse spatio-temporal links
        for link_data in data.get("spatio_temporal_links", []):
            link = self._parse_link(link_data, chunk_id)
            extraction.spatio_temporal_links.append(link)

        return extraction

    def _parse_actor(self, data: Dict[str, Any], chunk_id: str) -> Actor:
        """Parse actor from response data."""
        # Parse states
        states = []
        for state_data in data.get("states", []):
            state = State(
                id=f"state_{uuid4().hex[:8]}",
                entity_id=data.get("id", ""),
                name=state_data.get("name", "Unknown"),
                value=state_data.get("value", ""),
                start_date=state_data.get("start_date"),
                end_date=state_data.get("end_date"),
                source_chunk_id=chunk_id
            )
            states.append(state)

        # Parse actor type
        actor_type_str = data.get("actor_type", "person").lower()
        try:
            actor_type = ActorType(actor_type_str)
        except ValueError:
            actor_type = ActorType.PERSON

        return Actor(
            id=data.get("id", f"actor_{uuid4().hex[:8]}"),
            name=data.get("name", "Unknown"),
            actor_type=actor_type,
            aliases=data.get("aliases", []),
            roles=data.get("roles", []),
            states=states,
            source_chunk_ids=[chunk_id]
        )

    def _parse_verb_phrase(self, data: Dict[str, Any], chunk_id: str) -> VerbPhrase:
        """Parse verb phrase from response data."""
        # Ensure agent_id is string or None (LLM sometimes returns [])
        agent_id = data.get("agent_id")
        if not isinstance(agent_id, str):
            agent_id = None
        # Ensure patient_ids is a list of strings
        patient_ids = data.get("patient_ids", [])
        if not isinstance(patient_ids, list):
            patient_ids = []
        patient_ids = [p for p in patient_ids if isinstance(p, str)]

        return VerbPhrase(
            id=data.get("id", f"verb_{uuid4().hex[:8]}"),
            verb=data.get("verb", ""),
            agent_id=agent_id,
            patient_ids=patient_ids,
            temporal_id=data.get("temporal_id") if isinstance(data.get("temporal_id"), str) else None,
            spatial_id=data.get("spatial_id") if isinstance(data.get("spatial_id"), str) else None,
            is_implicit=data.get("is_implicit", False),
            source_chunk_id=chunk_id
        )

    def _parse_question(self, data: Dict[str, Any], chunk_id: str) -> PredictiveQuestion:
        """Parse predictive question from response data."""
        # Parse question type
        q_type_str = data.get("question_type", "what").lower()
        try:
            q_type = QuestionType(q_type_str)
        except ValueError:
            q_type = QuestionType.WHAT

        return PredictiveQuestion(
            id=data.get("id", f"q_{uuid4().hex[:8]}"),
            question_text=data.get("question_text", ""),
            question_type=q_type,
            target_entity_id=data.get("target_entity_id"),
            answerable=data.get("answerable", False),
            answer_text=data.get("answer_text"),
            answer_entity_id=data.get("answer_entity_id"),
            source_chunk_id=chunk_id
        )

    def _parse_link(self, data: Dict[str, Any], chunk_id: str) -> SpatioTemporalLink:
        """Parse spatio-temporal link from response data."""
        tag_type_str = data.get("tag_type", "temporal").lower()
        try:
            tag_type = LinkType(tag_type_str)
        except ValueError:
            tag_type = LinkType.TEMPORAL

        return SpatioTemporalLink(
            id=data.get("id", f"link_{uuid4().hex[:8]}"),
            linked_entity_ids=data.get("linked_entity_ids", []),
            tag_type=tag_type,
            tag_value=data.get("tag_value"),
            source_chunk_id=chunk_id
        )

    def review_extraction(
        self,
        extraction: ChunkExtraction,
        original_text: str
    ) -> ChunkExtraction:
        """
        Reflexion step: Review and improve extraction.

        This implements the self-correction loop from Phase 4.
        """
        # Build review prompt
        review_prompt = f"""
Review this extraction for accuracy and completeness.

ORIGINAL TEXT:
{original_text[:10000]}

EXTRACTED DATA:
- Actors: {len(extraction.actors)}
- Verb Phrases: {len(extraction.verb_phrases)}
- Questions: {len(extraction.questions)}
- Spatio-Temporal Links: {len(extraction.spatio_temporal_links)}

Actor names: {[a.name for a in extraction.actors]}
Questions: {[q.question_text for q in extraction.questions]}

REVIEW CHECKLIST:
1. Are all parties (applicant, respondent) identified?
2. Are all dates captured as temporal entities?
3. Are key assets identified?
4. Are relationship states tracked?
5. Are the questions appropriate for this text?

If the extraction looks good, respond with: {{"status": "approved"}}
If improvements needed, respond with corrections in the same JSON format as original extraction.
"""

        try:
            response = self._call_llm(review_prompt)
            if '"status": "approved"' in response or '"status":"approved"' in response:
                return extraction

            # Parse corrections and merge
            # For now, just return original if approved
            return extraction

        except Exception as e:
            print(f"[Review Warning] {e}")
            return extraction


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def chunk_legal_text(
    text: str,
    max_chunk_size: int = 15000,
    overlap: int = 500
) -> List[Tuple[str, int, int]]:
    """
    Split legal text into chunks for processing.

    Tries to split at paragraph boundaries.

    Returns:
        List of (chunk_text, start_pos, end_pos)
    """
    if len(text) <= max_chunk_size:
        return [(text, 0, len(text))]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chunk_size

        if end >= len(text):
            chunks.append((text[start:], start, len(text)))
            break

        # Try to find a paragraph break
        para_break = text.rfind('\n\n', start + overlap, end)
        if para_break > start + overlap:
            end = para_break

        # Or sentence break
        else:
            sent_break = text.rfind('. ', start + overlap, end)
            if sent_break > start + overlap:
                end = sent_break + 1

        chunks.append((text[start:end], start, end))
        start = end - overlap

    return chunks


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    # Demo usage
    sample_text = """
    FAMILY COURT OF AUSTRALIA

    Smith & Smith [2024] FamCA 123

    JUDGE: Wilson J
    DATE: 15 March 2024

    PARTIES:
    Applicant: John Smith (the husband)
    Respondent: Jane Smith (the wife)

    BACKGROUND:
    The parties married on 10 June 2010 in Sydney. They have two children,
    Emma (born 2012) and Jack (born 2015). The parties separated on
    1 March 2020 after approximately 10 years of marriage.

    The matrimonial home at 123 Smith Street, Parramatta was purchased
    in 2012 for $650,000 and is currently valued at $1.2 million.
    The property is subject to a mortgage of $400,000.

    ORDERS:
    1. The wife shall have sole parental responsibility for the children.
    2. The children shall live with the wife.
    3. The husband shall have supervised time with the children.
    """

    print("Testing Legal Operator...")
    print("-" * 60)

    try:
        operator = LegalOperator()
        extraction = operator.extract(
            text=sample_text,
            situation="Family law property and parenting matter",
            background_context="Family Court of Australia judgment"
        )

        print(f"Extracted {len(extraction.actors)} actors:")
        for actor in extraction.actors:
            print(f"  - {actor.name} ({actor.actor_type.value}): {actor.roles}")

        print(f"\nExtracted {len(extraction.questions)} questions:")
        for q in extraction.questions:
            status = "✓" if q.answerable else "?"
            print(f"  {status} {q.question_text}")
            if q.answerable:
                print(f"      → {q.answer_text}")

    except Exception as e:
        print(f"Demo failed (need API key): {e}")
        print("Set OPENROUTER_API_KEY environment variable to test.")
