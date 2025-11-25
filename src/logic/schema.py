from __future__ import annotations
import uuid
from typing import List, Optional, Dict, Any, Literal, Union
from enum import Enum
from pydantic import BaseModel, Field, model_validator, field_validator

# --- Universal GSW Primitives ---

class TemporalEntity(BaseModel):
    """Base class for anything that has a lifespan or occurrence time."""
    start_date: Optional[str] = None # Relaxed from date
    end_date: Optional[str] = None   # Relaxed from date
    is_ongoing: bool = False

# --- Entities ---

class Entity(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    # Track which Case IDs this entity appears in
    involved_cases: List[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def ensure_id(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        return self

class Person(Entity):
    dob: Optional[str] = None
    role_in_case: Optional[str] = None

class Object(Entity):
    type: str

# --- Narrative Nodes ---

class State(TemporalEntity):
    entity_id: Optional[str] = None
    name: str
    value: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Event(BaseModel):
    id: Optional[str] = None
    date: Optional[str] = None # Relaxed
    type: str
    description: str
    participant_ids: List[str] = Field(default_factory=list)
    object_ids: List[str] = Field(default_factory=list)
    triggered_state_ids: List[str] = Field(default_factory=list, alias="triggered_states") # Alias to handle model output

    @model_validator(mode='after')
    def ensure_id(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        return self

# --- Legal Outcomes ---

# OutcomeType Enum removed for flexibility
# We will normalize strings like "Application" -> "Procedural" in a later phase.

class LegalOutcome(BaseModel):
    id: Optional[str] = None
    type: str = "Other" # Now a string to accept any raw label (e.g. "Application", "Interim Order")
    description: str
    orders: List[str] = Field(default_factory=list)
    granted_to_ids: List[str] = Field(default_factory=list)
    related_object_ids: List[str] = Field(default_factory=list)

    @field_validator('orders', mode='before')
    @classmethod
    def normalize_orders(cls, v):
        """Flatten structured orders (dicts) to strings if the model gets too creative."""
        if isinstance(v, list):
            new_orders = []
            for item in v:
                if isinstance(item, dict):
                    # Extract 'text' or 'description' or just dump it
                    new_orders.append(item.get('text') or item.get('description') or str(item))
                else:
                    new_orders.append(str(item))
            return new_orders
        return v

    @model_validator(mode='after')
    def ensure_id(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        return self

# --- The Case Container ---

class LegalCase(BaseModel):
    case_id: Optional[str] = None
    title: Optional[str] = None
    
    # Changed to Lists for robustness
    persons: List[Person] = Field(default_factory=list)
    objects: List[Object] = Field(default_factory=list)
    
    timeline: List[Event] = Field(default_factory=list)
    states: List[State] = Field(default_factory=list)
    outcomes: List[LegalOutcome] = Field(default_factory=list)

    @model_validator(mode='after')
    def ensure_case_id(self):
        if not self.case_id:
            self.case_id = str(uuid.uuid4())
        return self

    def get_entity_states(self, entity_id: str) -> List[State]:
        return [s for s in self.states if s.entity_id == entity_id]
