from typing import Dict, List
import uuid
import json
from collections import Counter
from pathlib import Path
from src.logic.schema import LegalCase, Person, Object, State, Event, Entity
from src.embeddings.vector_store import LocalVectorStore
from src.logic.ontology_seed import STANDARD_ASSETS, STANDARD_OUTCOMES, STANDARD_EVENTS
from src.utils.toon import ToonEncoder

class Reconciler:
    """
    The 'Brain' of the GSW Architecture.
    Merges 'Local Workspaces' into 'Global Memory'.
    """
    def __init__(self, vector_store: LocalVectorStore):
        self.vector_store = vector_store
        self.global_graph = LegalCase(case_id="GLOBAL_PILOT", title="Australian Family Law Knowledge Graph")
        
    def ingest_chunk(self, new_case: LegalCase):
        """
        Main entry point for the Reconciler.
        """
        if not new_case:
            return

        # 1. Reconcile Persons (Entity Linking)
        # Updated to handle List[Person] instead of Dict
        self._reconcile_entities(new_case.persons, self.global_graph.persons, "Person", new_case.case_id)
        
        # 2. Reconcile Objects
        self._reconcile_entities(new_case.objects, self.global_graph.objects, "Object", new_case.case_id)
        
        # 3. Merge Timeline (Events)
        self.global_graph.timeline.extend(new_case.timeline)
        
        # 4. Merge States (Episodic Logic)
        self._reconcile_states(new_case.states)
        
        # 5. Outcomes
        self.global_graph.outcomes.extend(new_case.outcomes)

    def save_graph(self, filepath: str):
        """
        Persists the Global Knowledge Graph to disk.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        json_str = self.global_graph.model_dump_json(indent=2)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"[Reconciler] Saved Global Graph to {path}")

    def get_current_context(self) -> str:
        """
        Returns the 'Known Legal Context' for the Operator.
        Merges the Static Seed (Prior) with the Dynamic Graph (Posterior).
        Uses TOON (Token-Oriented Object Notation) for compression.
        """
        # 1. Get Dynamic Frequency counts
        asset_counts = Counter([obj.type for obj in self.global_graph.objects if obj.type])
        outcome_counts = Counter([out.type for out in self.global_graph.outcomes if out.type])
        event_counts = Counter([e.type for e in self.global_graph.timeline if e.type])
        
        # 2. Merge with Seed (If term appears > 3 times, add it to suggestions)
        active_assets = set(STANDARD_ASSETS)
        active_outcomes = set(STANDARD_OUTCOMES)
        active_events = set(STANDARD_EVENTS)
        
        for term, count in asset_counts.items():
            if count > 3: active_assets.add(term)
            
        for term, count in outcome_counts.items():
            if count > 3: active_outcomes.add(term)
            
        for term, count in event_counts.items():
            if count > 3: active_events.add(term)
            
        # 3. Get Sample People
        sorted_people = sorted(self.global_graph.persons, key=lambda p: len(p.involved_cases), reverse=True)
        sample_people = [p.name for p in sorted_people[:10]]
        
        # 4. Encode to TOON
        assets_toon = ToonEncoder.encode_list("assets", sorted(list(active_assets)))
        outcomes_toon = ToonEncoder.encode_list("outcomes", sorted(list(active_outcomes)))
        events_toon = ToonEncoder.encode_list("events", sorted(list(active_events)))
        people_toon = ToonEncoder.encode_list("people", sample_people)
        
        summary = f"""
        KNOWN LEGAL CONTEXT (TOON Format):
        Use these Standard Terms if applicable.
        
        {assets_toon}
        
        {outcomes_toon}
        
        {events_toon}
        
        {people_toon}
        """
        return summary

    def load_graph(self, filepath: str):
        """
        Loads the Global Knowledge Graph from disk.
        """
        path = Path(filepath)
        if not path.exists():
            print(f"[Reconciler] No existing graph found at {path}. Starting fresh.")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.global_graph = LegalCase.model_validate(data)
            print(f"[Reconciler] Loaded Global Graph from {path} ({len(self.global_graph.persons)} persons).")
        except Exception as e:
            print(f"[Reconciler] Failed to load graph: {e}. Starting fresh.")
            
    def _reconcile_entities(self, new_entities: List[Entity], global_store: List[Entity], type_label: str, current_case_id: str):
        """
        Matches new entities against the global vector store.
        UPDATED: Handles List input and List global store.
        """
        for entity in new_entities:
            # Generate text rep for vector search
            text_rep = f"{entity.name} {entity.description or ''}"
            
            # 1. Check Vector Store
            match_id = self.vector_store.find_similar_entity(text_rep)
            
            if match_id:
                # LINK FOUND
                # Find the global entity with this ID
                global_entity = next((e for e in global_store if e.id == match_id), None)
                
                if global_entity:
                    # Merge logic: Prefer longer description
                    if entity.description and len(entity.description) > len(global_entity.description or ""):
                        global_entity.description = entity.description
                    
                    # Track Case ID (Cross-Case Tracking)
                    if current_case_id and current_case_id not in global_entity.involved_cases:
                        global_entity.involved_cases.append(current_case_id)

                    # Update the local entity's ID to match global (so linked states works)
                    entity.id = match_id
            else:
                # NEW ENTITY
                # Ensure ID exists (should be covered by Schema validator, but double check)
                if not entity.id:
                    entity.id = str(uuid.uuid4())
                
                # Track Case ID
                if current_case_id:
                    entity.involved_cases.append(current_case_id)

                # Add to Graph
                global_store.append(entity)
                # Add to Vector Store
                self.vector_store.add_entity(entity.id, text_rep)

    def _reconcile_states(self, new_states: List[State]):
        """
        CRITICAL GSW LOGIC:
        Close old states when new conflicting states appear.
        """
        for new_state in new_states:
            # Find states with same Name (e.g. "MaritalStatus") for same Entity
            existing = [
                s for s in self.global_graph.states 
                if s.name == new_state.name and s.entity_id == new_state.entity_id
            ]
            
            # Check for open states
            open_state = next((s for s in existing if s.is_ongoing or s.end_date is None), None)
            
            if open_state:
                # If new state starts AFTER old state (lexical compare for strings works roughly for ISO dates)
                # But we allowed fuzzy dates, so this logic is imperfect. 
                # For Pilot: strict compare if both look like YYYY-MM-DD
                if new_state.start_date and open_state.start_date:
                     if new_state.start_date > open_state.start_date:
                        # Close old state
                        open_state.end_date = new_state.start_date
                        open_state.is_ongoing = False
            
            # Add new state
            self.global_graph.states.append(new_state)
