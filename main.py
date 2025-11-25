import asyncio
import os
import json
import argparse
import dotenv
from pathlib import Path
from src.embeddings.vector_store import LocalVectorStore
from src.ingestion.gsw_operator import TheOperator
from src.ingestion.reconciler import Reconciler
from src.analysis.generate_report import generate_report
from src.analysis.narrative_report import generate_narrative_report

# Load environment variables
dotenv.load_dotenv()

async def run_ingestion_pilot(limit: int = 50, calibration_mode: bool = False, use_experiment: bool = False):
    """
    Orchestrator for Phase 3 Ingestion.
    """
    print(f"--- STARTING GSW INGESTION PILOT (Calibration: {calibration_mode}, Experiment: {use_experiment}) ---")
    
    # 1. Initialize Components
    print("[1/4] Initializing Vector Store (BGE-M3)...")
    vector_store = LocalVectorStore()
    
    print("[2/4] Initializing Reconciler (The Brain)...")
    reconciler = Reconciler(vector_store)
    
    # 1.5 Load Existing Graph (Persistent Memory)
    snapshot_path = "data/processed/graph_snapshot.json"
    reconciler.load_graph(snapshot_path)
    
    print("[3/4] Initializing Operator (Gemini)...")
    try:
        operator = TheOperator(use_experiment=use_experiment) # Will read GOOGLE_API_KEY from env
    except ValueError as e:
        print(f"FATAL: {e}")
        print("Please set GOOGLE_API_KEY in your environment.")
        return

    # 2. Load State (Batched Execution)
    state_path = Path("data/processed/ingestion_state.json")
    start_line = 0
    if state_path.exists():
        with open(state_path, 'r') as f:
            state = json.load(f)
            start_line = state.get("last_line", 0)
            print(f"RESUMING from line {start_line}...")

    # 3. Load Data
    data_path = Path("data/processed/domains/family.jsonl")
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        # Fallback to legacy path if domain split hasn't finished/run
        legacy_path = Path("data/processed/family_law_subset.jsonl")
        if legacy_path.exists():
            print(f"⚠️  Falling back to legacy dataset: {legacy_path}")
            data_path = legacy_path
        else:
            return

    print(f"[4/4] Streaming Data from {data_path} (Batch Size: {limit})...")
    
    current_line_idx = 0
    processed_in_batch = 0
    
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Skip to start_line
            if current_line_idx < start_line:
                current_line_idx += 1
                continue
            
            # Stop if batch limit reached
            if processed_in_batch >= limit:
                break
            
            current_line_idx += 1
            processed_in_batch += 1
            
            try:
                raw_doc = json.loads(line)
                # Combine relevant text fields
                text_content = raw_doc.get('text', '') or raw_doc.get('body', '') or raw_doc.get('judgment', '')
                text_content = text_content[:30000] 
                
                if not text_content:
                    continue

                print(f"\nProcessing Case #{current_line_idx}...")
                
                # 0. Get Dynamic Ontology (Self-Improvement)
                ontology_context = reconciler.get_current_context()
                
                # A. OPERATOR: Extract with Context
                local_case = await operator.extract_timeline(text_content, ontology_context)
                
                if local_case:
                    # A.5. REFLEXION (Self-Correction)
                    print("   -> Auditing & Refining extraction...")
                    local_case = await operator.review_extraction(text_content, local_case)

                    # B. RECONCILER: Ingest
                    reconciler.ingest_chunk(local_case)
                    
                    # Report Live Stats
                    g = reconciler.global_graph
                    print(f"   -> Global Memory: {len(g.persons)} Persons, {len(g.states)} States, {len(g.timeline)} Events.")

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"   -> Error processing line {current_line_idx}: {e}")

    print("\n--- BATCH COMPLETE ---")
    
    # 4. Persistence & Analysis
    report_path = "LEGAL_LANDSCAPE_REPORT.md"
    
    if calibration_mode:
        # Save to Temp, Do NOT update state
        temp_snapshot = "data/processed/calibration_snapshot.json"
        print(f"[Orchestrator] CALIBRATION MODE: Saving temp graph to {temp_snapshot}...")
        reconciler.save_graph(temp_snapshot)
        
        print("[Orchestrator] Generating Report from Calibration Data...")
        generate_report(temp_snapshot, report_path)
        
        print("[Orchestrator] ⚠️  State NOT saved. Re-run this command to process the same batch again.")
        
    else:
        # Normal Mode: Save Graph & Update State
        print("[Orchestrator] Saving Graph Snapshot...")
        reconciler.save_graph(snapshot_path)
        
        # Save State
        new_state = {"last_line": current_line_idx}
        with open(state_path, 'w') as f:
            json.dump(new_state, f)
        print(f"[Orchestrator] State saved. Next run starts at line {current_line_idx}.")

        print("[Orchestrator] Generating Intelligence Report...")
        generate_report(snapshot_path, report_path)
    
    # 5. Narrative Audit (Phase 3.5)
    print("[Orchestrator] Running Phase 3.5 Narrative Audit...")
    generate_narrative_report(snapshot_path if not calibration_mode else "data/processed/calibration_snapshot.json", "NARRATIVE_INTEGRITY_REPORT.md")
    
    print(f"✅ Intelligence Report generated at {report_path}")
    print("✅ Narrative Audit Complete. See NARRATIVE_INTEGRITY_REPORT.md for gaps in the World Model.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GSW Ingestion Pilot")
    parser.add_argument("--limit", type=int, default=10, help="Number of cases to process per batch")
    parser.add_argument("--calibration", action="store_true", help="Run in Calibration Mode (does not save progress state)")
    parser.add_argument("--experiment", action="store_true", help="Use Experimental Model (Gemini 3 Pro)")
    
    args = parser.parse_args()
    
    asyncio.run(run_ingestion_pilot(limit=args.limit, calibration_mode=args.calibration, use_experiment=args.experiment))
