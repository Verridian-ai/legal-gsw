import json
from pathlib import Path
from collections import Counter
from datetime import date, datetime

def generate_report(json_path: str, output_path: str):
    """
    Analyzes the GSW Graph Snapshot and generates a Markdown Intelligence Report.
    """
    print(f"[Analyst] Reading snapshot from {json_path}...")
    
    if not Path(json_path).exists():
        print("Snapshot not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # --- Extraction Stats ---
    persons = data.get("persons", [])
    objects = data.get("objects", [])
    timeline = data.get("timeline", [])
    outcomes = data.get("outcomes", [])
    states = data.get("states", [])
    
    # In the Pilot, we have 1 Global Case containing all merged knowledge
    total_cases = 1 
    total_persons = len(persons)
    total_assets = len(objects)
    total_events = len(timeline)
    
    # --- Vocabulary Analysis ---
    asset_types = [obj.get("type", "Unknown") for obj in objects]
    asset_counts = Counter(asset_types).most_common(20)
    
    outcome_types = [out.get("type", "Unknown") for out in outcomes]
    outcome_counts = Counter(outcome_types).most_common(20)

    # New: Person Roles
    roles = [p.get("role_in_case", "Unknown") for p in persons if p.get("role_in_case")]
    role_counts = Counter(roles).most_common(10)

    # New: Event Types
    event_types = [e.get("type", "Unknown") for e in timeline]
    event_counts = Counter(event_types).most_common(20)

    # New: State Types
    state_types = [s.get("name", "Unknown") for s in states]
    state_counts = Counter(state_types).most_common(10)

    # --- Temporal Analysis ---
    dates = []
    for event in timeline:
        d_str = event.get("date")
        if d_str and len(d_str) >= 4: # Simple filter
            dates.append(d_str)
    
    dates.sort()
    earliest = dates[0] if dates else "N/A"
    latest = dates[-1] if dates else "N/A"

    # --- Complexity Score ---
    # Avg events per person
    complexity = total_events / total_persons if total_persons > 0 else 0

    # --- Connectivity Audit (The Detective) ---
    multi_case_persons = [p for p in persons if len(p.get("involved_cases", [])) > 1]
    recidivism_count = len(multi_case_persons)
    
    # Potential Duplicates (Simple Fuzzy Check - Start with same 5 chars)
    # In a real prod system, we'd use a dedicated Dedupe library or LLM call
    names = sorted([p.get("name", "") for p in persons])
    potential_duplicates = []
    for i in range(len(names) - 1):
        n1, n2 = names[i], names[i+1]
        if n1 and n2 and n1[:5].lower() == n2[:5].lower() and n1 != n2:
            potential_duplicates.append(f"{n1} <--> {n2}")
    
    # Deepest History
    deepest_gap = 0
    deepest_person = "N/A"
    
    # Map person ID to dates
    person_dates = {p.get("id"): [] for p in persons}
    for evt in timeline:
        d = evt.get("date")
        if not d or len(d) < 4: continue
        
        # Add to all participants
        for pid in evt.get("participant_ids", []):
            if pid in person_dates:
                person_dates[pid].append(d)
                
    for pid, dlist in person_dates.items():
        if len(dlist) < 2: continue
        dlist.sort()
        try:
            # Rough year calc
            y1 = int(dlist[0][:4])
            y2 = int(dlist[-1][:4])
            gap = y2 - y1
            if gap > deepest_gap:
                deepest_gap = gap
                # Find name
                p_obj = next((p for p in persons if p.get("id") == pid), None)
                deepest_person = p_obj.get("name") if p_obj else "Unknown"
        except:
            continue

    # --- Report Generation ---
    report = f"""# LEGAL LANDSCAPE REPORT: Australian Family Law (Pilot)

## 1. Executive Summary
**System Status**: Online & Learning
**Knowledge Graph Stats**:
- **{total_cases}** Active Legal Context (Global Pilot)
- **{total_persons}** Unique Individuals Tracked
- **{total_assets}** Assets/Objects Identified
- **{total_events}** Historical Events Logged
- **{len(outcomes)}** Legal Outcomes Recorded

## 2. Connectivity Audit (The Detective)
**Cross-Case Tracking**:
- **{recidivism_count}** Persons appear in multiple cases.
- **Connectivity Score**: {recidivism_count / total_persons * 100:.1f}% of the population is linked.

**Potential Duplicates (Risk Scan)**:
"""
    if potential_duplicates:
        for duo in potential_duplicates[:5]:
            report += f"- ⚠️ {duo}\n"
    else:
        report += "- ✅ No obvious name-collisions found.\n"

    report += f"""
**Deepest History**:
- **{deepest_person}** has a timeline spanning **{deepest_gap} years**.

## 3. Temporal Horizon
The "Memory" of the system spans from **{earliest}** to **{latest}**.

## 4. The Dictionary (Dynamic Ontology)

### A. Most Common Assets (Top 20)
"""
    for atype, count in asset_counts:
        report += f"- **{atype}**: {count}\n"

    report += "\n### B. Legal Outcomes (Top 20)\n"
    for otype, count in outcome_counts:
        report += f"- **{otype}**: {count}\n"

    report += "\n### C. Event Types (Top 20)\n"
    for etype, count in event_counts:
        report += f"- **{etype}**: {count}\n"

    report += "\n### D. Participant Roles (Top 10)\n"
    for role, count in role_counts:
        report += f"- **{role}**: {count}\n"

    report += "\n### E. Tracked States (Top 10)\n"
    for stype, count in state_counts:
        report += f"- **{stype}**: {count}\n"

    report += f"""
## 4. Complexity Metrics
- ** Narrative Depth**: {complexity:.2f} Events per Person (avg)
- ** State Tracking**: {len(states)} Total State Nodes (Snapshots of reality)

---
*Generated by GSW Analyst Agent*
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"[Analyst] Report generated at {output_path}")

if __name__ == "__main__":
    generate_report("data/processed/graph_snapshot.json", "LEGAL_LANDSCAPE_REPORT.md")
