import json
from pathlib import Path
from collections import Counter

def generate_narrative_report(json_path: str, output_path: str):
    """
    Phase 3.5 Audit: Verifies the GSW 'World Model' coherence.
    Metrics: Role Volatility, Causal Density, Anchoring.
    """
    print(f"[Narrator] Auditing Narrative Integrity from {json_path}...")
    
    if not Path(json_path).exists():
        print("Snapshot not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    persons = data.get("persons", [])
    timeline = data.get("timeline", [])
    states = data.get("states", [])

    # 1. Role Volatility (How many actors change roles?)
    # In the current Pilot Schema, Person.role_in_case is a single string.
    # To track evolution, we need to look at 'Role' states if they exist, or infer from timeline descriptions.
    # For this Pilot version, we'll check if multiple people have the SAME name but different roles (merging failures)
    # OR if we have States named "Role" or similar.
    
    # Ideally, we want: John (2015: Husband) -> John (2018: Respondent)
    # We'll count how many Persons have a defined Role.
    defined_roles = [p for p in persons if p.get("role_in_case")]
    role_volatility_score = len(defined_roles) / len(persons) if persons else 0

    # 2. Causal Density (States linked to Events)
    # A State is 'Causal' if it starts at the same date as an Event.
    causal_states = 0
    for state in states:
        s_date = state.get("start_date")
        if not s_date: continue
        
        # Look for event on same date
        trigger = next((e for e in timeline if e.get("date") == s_date), None)
        if trigger:
            causal_states += 1
            
    causal_density = causal_states / len(states) if states else 0

    # 3. Spatiotemporal Anchoring
    # % of Events with Date AND (implied) Location
    # Pilot data doesn't extract location explicitly yet, so we check Date + Description length
    anchored_events = [e for e in timeline if e.get("date") and len(e.get("date")) >= 4]
    anchor_score = len(anchored_events) / len(timeline) if timeline else 0

    report = f"""# NARRATIVE INTEGRITY REPORT (The World Model)

## 1. Narrative Coherence Metrics
- **Role Definition Rate**: {role_volatility_score*100:.1f}% of actors have a clear legal role.
- **Causal Density**: {causal_density*100:.1f}% of States are triggered by a specific Event. (Higher is better).
- **Temporal Anchoring**: {anchor_score*100:.1f}% of Events are firmly grounded in the timeline.

## 2. Memory Gaps (Forward Falling Questions)
"""
    if causal_density < 0.5:
        report += "- ⚠️ **Low Causal Density**: The AI is observing 'Status Changes' (e.g. Marriage ending) without seeing the 'Cause' (Divorce Event). We need to hunt for missing judgments.\n"
    else:
        report += "- ✅ **Strong Causality**: Most state changes are explained by the timeline.\n"

    report += """
## 3. Recommendations
- If **Causal Density** is low, adjust the Operator Prompt to "Look for the Event that caused this State".
- If **Anchoring** is low, enable "Date Inference" logic in the Reconciler.
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"[Narrator] Narrative Report generated at {output_path}")

if __name__ == "__main__":
    generate_narrative_report("data/processed/graph_snapshot.json", "NARRATIVE_INTEGRITY_REPORT.md")
