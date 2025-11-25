import os
import json
import asyncio
from typing import Optional, Union, Dict, Any
from openai import AsyncOpenAI
from pydantic import ValidationError
from src.logic.schema import LegalCase

# OpenRouter Model Strings
PRODUCTION_MODEL = "google/gemini-2.5-flash-preview-09-2025"
EXPERIMENTAL_MODEL = "google/gemini-3-pro-preview"

class TheOperator:
    """
    The Extraction Layer.
    Acts as the 'Episodic Legal Observer'.
    Uses OpenRouter to access Google Gemini models.
    """
    def __init__(self, api_key: Optional[str] = None, use_experiment: bool = False):
        # Prerequisite: Verify OPENROUTER_API_KEY is in the environment
        # (or reuse GOOGLE_API_KEY if that's where the user stored the OpenRouter key)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY (or GOOGLE_API_KEY) is not set.")
        
        # NEW Client Initialization
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        
        # Select Model
        self.model_name = EXPERIMENTAL_MODEL if use_experiment else PRODUCTION_MODEL
        self.is_experimental = use_experiment

    async def extract_timeline(self, text: str, ontology_context: str = "") -> Optional[LegalCase]:
        """
        Extracts a LegalCase structure from raw text using Gemini via OpenRouter.
        Implements Smart Fallback (Experiment -> Production).
        """
        prompt = f"""
        You are an Episodic Legal Observer.
        Your task: Read the provided legal text and extract a structured Semantic Map.
        
        Goal: Build a Timeline of People, Assets, States, and Events.
        
        NARRATIVE RULES (The Movie Timeline):
        - For every Event, identify the Actor's Role at that specific moment.
        - Capture Role Evolution: e.g., In 2015 'John' is 'Husband'; in 2020 he is 'Respondent'.
        
        CONTEXT DATA is provided below in TOON format (Table-Oriented). 
        structure_name[Count]{{columns...}}
        Use this vocabulary to standardize your JSON output.
        
        {ontology_context}
        
        Standardization Rule: 
        - If a mapped entity fits one of the Standard Terms above, use that Term. 
        - Do not use vague words like 'Object' or 'Place' if a specific term applies.
        
        Schema Requirements:
        1. Persons: Name, Role (Applicant/Respondent).
        2. Objects: Assets, Children, Businesses.
        3. Timeline (Events): Specific occurrences (Marriage, Purchase, Separation).
        4. States: Statuses with start/end dates (e.g., "Married", "Valuation: $500k").
        
        Output strictly valid JSON matching the following structure:
        {{
            "case_id": "derived_from_context_or_uuid",
            "title": "Smith v Jones",
            "persons": [ 
                {{ "name": "Mr. Smith", "role_in_case": "Applicant", "description": "Husband, 45yo" }} 
            ],
            "objects": [ 
                {{ "name": "Marital Home", "type": "Property", "description": "123 Main St, Sydney" }} 
            ],
            "timeline": [ 
                {{ "date": "2010-01-01", "type": "Marriage", "description": "Parties married in Sydney" }} 
            ],
            "states": [ 
                {{ "name": "RelationshipStatus", "value": "Married", "start_date": "2010-01-01" }} 
            ],
            "outcomes": [ 
                {{ "description": "Final Property Orders made", "type": "Order" }} 
            ]
        }}
        
        Important:
        - Infer dates where possible (YYYY-MM-DD).
        - If a State changes (e.g. value of house), capture the specific date in the State object.
        """
        
        response_text = None
        
        # Thinking Config: For EXPERIMENTAL_MODEL, pass the reasoning parameters via extra_body.
        extra_params = {}
        
        print(f"DEBUG: Operator using model {self.model_name} with params: {extra_params}")

        # ATTEMPT 1: Selected Model (Experiment or Production)
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that outputs strict JSON."},
                    {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text}"}
                ],
                extra_body=extra_params
            )
            response_text = response.choices[0].message.content
            
        except Exception as e:
            # Fallback Logic
            if self.is_experimental:
                print(f"⚠️ Gemini 3 Pro unavailable ({e}). Falling back to Stable 2.5 Flash.")
                try:
                    response = await self.client.chat.completions.create(
                        model=PRODUCTION_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a helpful AI assistant that outputs strict JSON."},
                            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text}"}
                        ]
                    )
                    response_text = response.choices[0].message.content
                except Exception as e2:
                    print(f"❌ Production Model also failed: {e2}")
                    return None
            else:
                print(f"❌ Production Model failed: {e}")
                return None

        if not response_text:
            return None

        # PARSE & CLEAN
        try:
            # Clean markdown code blocks if present
            cleaned_text = response_text
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(cleaned_text)
            
            # Robust List Handling
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            # Validate with Pydantic
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

    async def review_extraction(self, text: str, case: LegalCase) -> LegalCase:
        """
        Reflexion Step: The model critiques its own extraction to improve specificity.
        """
        prompt = f"""
        You are a Senior Legal Analyst auditing a junior clerk's extraction.
        
        Review the extracted Case JSON against the Original Text.
        
        CRITIQUE GOALS:
        1. Specificity: Change generic labels like "Order" to specific ones like "Final Parenting Order" or "Property Settlement".
        2. Missing Data: Did we miss a crucial Asset or Person?
        3. Dates: Are the dates accurate?
        
        CURRENT JSON:
        {case.model_dump_json()}
        
        Output the CORRECTED JSON (full structure).
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that outputs strict JSON."},
                    {"role": "user", "content": f"{prompt}\n\nORIGINAL TEXT (Excerpt):\n{text[:5000]}"}
                ]
            )
            
            response_text = response.choices[0].message.content
             # Clean markdown code blocks if present
            cleaned_text = response_text
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()

            data = json.loads(cleaned_text)
            
            # FIX: Robust List Handling
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            return LegalCase.model_validate(data)
            
        except Exception as e:
            print(f"Reflexion Failed: {e}. Keeping original.")
            return case
