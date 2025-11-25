from typing import List, Dict, Optional, Any
from datetime import date
import numpy as np
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from .schema import LegalCase, Person, Object, Entity, State, Event

# Configuration for the Reconciler
SIMILARITY_THRESHOLD = 0.92  # Threshold for merging entities
MODEL_NAME = "BAAI/bge-m3"

class Reconciler:
    """
    The 'Brain' of the GSW Architecture.
    Responsibility:
    1. Vector-based Entity Linking (Identity Resolution).
    2. Temporal State Merging (Episodic Memory Construction).
    3. Coherence Checking (Ensuring new events fit the timeline).
    """
    
    def __init__(self, device: str = "cuda"):
        print(f"Loading Reconciler Model: {MODEL_NAME} on {device}...")
        self.model = SentenceTransformer(MODEL_NAME, device=device)
        self.global_case = None # The 'Global Memory'

    def initialize_case(self, case_id: str, title: str):
        """Starts a new empty Global Memory for a case."""
        self.global_case = LegalCase(case_id=case_id, title=title)

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a name/description."""
        return self.model.encode(text, normalize_embeddings=True)

    def reconcile_chunk(self, local_workspace: LegalCase):
        """
        Merges a 'Local Workspace' (from Operator) into the 'Global Memory'.
        """
        if not self.global_case:
            # First chunk becomes the base
            self.global_case = local_workspace
            return

        # 1. Entity Linking (Persons)
        self._merge_entities(local_workspace.persons, self.global_case.persons)

        # 2. Entity Linking (Objects)
        self._merge_entities(local_workspace.objects, self.global_case.objects)

        # 3. Event Integration (Timeline Construction)
        self._merge_timeline(local_workspace.timeline)
        
        # 4. State Merging (Episodic Updates)
        self._merge_states(local_workspace.states)

        # 5. Outcome Integration
        self.global_case.outcomes.extend(local_workspace.outcomes)

    def _merge_entities(self, new_entities: Dict[str, Entity], global_store: Dict[str, Entity]):
        """
        Uses Vector Similarity to find if 'Mr. Smith' (New) is 'John Smith' (Global).
        """
        # If global store is empty, just add everything
        if not global_store:
            global_store.update(new_entities)
            return

        # Pre-compute global embeddings
        global_ids = list(global_store.keys())
        global_names = [e.name for e in global_store.values()]
        global_embeddings = self.model.encode(global_names, normalize_embeddings=True)

        for new_id, new_entity in new_entities.items():
            # Compute new embedding
            new_emb = self.model.encode(new_entity.name, normalize_embeddings=True)
            
            # Calculate similarities
            scores = global_embeddings @ new_emb.T
            best_idx = np.argmax(scores)
            best_score = scores[best_idx]

            if best_score > SIMILARITY_THRESHOLD:
                # MATCH FOUND: Merge into existing global entity
                global_id = global_ids[best_idx]
                existing_entity = global_store[global_id]
                
                # Logic: Enrich description, don't overwrite name (unless new one is longer/better?)
                # For now, we keep the Global ID as the canonical truth
                # But we must update the new_id in the incoming data to match the global_id
                # (This 're-wiring' is complex, simplified here by assuming we map IDs later)
                print(f"Reconciler: Merged '{new_entity.name}' into '{existing_entity.name}' (Score: {best_score:.4f})")
                
                # Merge static attributes (naive)
                if new_entity.description and not existing_entity.description:
                    existing_entity.description = new_entity.description
                    
            else:
                # NO MATCH: Add as new entity
                print(f"Reconciler: Created new entity '{new_entity.name}'")
                global_store[new_id] = new_entity

    def _merge_timeline(self, new_events: List[Event]):
        """
        Adds new events to the global timeline. 
        Ideally, deduplicates identical events (same date + same description vector).
        """
        # Simplified: Just append for now. 
        # Real GSW would check for duplicates.
        self.global_case.timeline.extend(new_events)
        
        # Sort timeline by date to maintain narrative coherence
        self.global_case.timeline.sort(key=lambda x: x.date if x.date else date.min)

    def _merge_states(self, new_states: List[State]):
        """
        CRITICAL GSW LOGIC:
        If New State contradicts Old State, do not overwrite.
        Close the Old State (add end_date).
        Open the New State.
        """
        for new_state in new_states:
            # Find states for the same entity and attribute (e.g. same Person, same "MaritalStatus")
            existing_states = [
                s for s in self.global_case.states 
                if s.entity_id == new_state.entity_id and s.name == new_state.name
            ]
            
            # Check for conflict/update
            # If we have an open state (no end_date) and the new state has a later start_date
            open_state = next((s for s in existing_states if s.is_ongoing or s.end_date is None), None)
            
            if open_state:
                if new_state.start_date and open_state.start_date and new_state.start_date > open_state.start_date:
                    # We found a state change!
                    # e.g. Old: Married (Start: 2000), New: Divorced (Start: 2020)
                    # Close the old state
                    open_state.end_date = new_state.start_date
                    open_state.is_ongoing = False
                    print(f"Reconciler: Updated State '{new_state.name}' for {new_state.entity_id}: Closed previous state, opened new.")
            
            self.global_case.states.append(new_state)

