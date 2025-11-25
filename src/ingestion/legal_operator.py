import os
import json
import asyncio
from typing import Optional
from google import genai
from pydantic import ValidationError
from src.logic.schema import LegalCase

# Using stable Flash model, but explicitly 2.0 Flash as requested
MODEL_NAME = "gemini-2.0-flash" 

class TheOperator:
    """
    The Extraction Layer.
    Acts as the 'Episodic Legal Observer'.
    Uses the new Google GenAI SDK (google-genai).
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")
        
        self.client = genai.Client(api_key=self.api_key)

    async def extract_timeline(self, text: str) -> Optional[LegalCase]:
        """
        Extracts a LegalCase structure from raw text using Gemini.
        """
        prompt = """
        You are an Episodic Legal Observer.
        Your task: Read the provided legal text and extract a structured Semantic Map.
        
        Goal: Build a Timeline of People, Assets, States, and Events.
        
        Schema Requirements (Updated):
        1. Persons: List of {name, role, ...}.
        2. Objects: List of {type, name, ...}.
        3. Timeline: List of {type, date, description, ...}.
        4. States: List of {name, value, start_date, ...}.
        
        Output strictly valid JSON matching the following structure:
        {
            "case_id": "optional_uuid",
            "title": "Case Title",
            "persons": [ { "name": "...", "role": "..." } ],
            "objects": [ { "type": "RealEstate", "name": "..." } ],
            "timeline": [ { "date": "2020-01-01", "type": "...", "description": "..." } ],
            "states": [ { "name": "...", "value": "...", "start_date": "..." } ],
            "outcomes": [ { "type": "Property", "description": "..." } ]
        }
        
        Important:
        - Infer dates where possible (YYYY-MM-DD). If uncertain, use strings like "approx 2020" or "before 1995".
        - If a State changes (e.g. value of house), capture the specific date in the State object.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=MODEL_NAME,
                contents=f"{prompt}\n\nTEXT:\n{text}",
                config={
                    "response_mime_type": "application/json"
                }
            )
            
            raw_json = response.text
            data = json.loads(raw_json)
            
            # Validate with Pydantic (Robust Mode)
            case = LegalCase.model_validate(data)
            return case

        except json.JSONDecodeError:
            print("Operator Error: Model returned invalid JSON.")
            return None
        except ValidationError as e:
            print(f"Operator Error: Schema Validation Failed. {e}")
            return None
        except Exception as e:
            print(f"Operator Error: {e}")
            return None
