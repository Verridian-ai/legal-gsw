from typing import List, Dict, Any, Optional
from datetime import date
from .schema import LegalCase, Event, Object, TemporalEntity

def evaluate_property_split(timeline: List[Event]) -> Dict[str, Any]:
    """
    Evaluates Section 79 (Property) factors by replaying the narrative.
    
    Args:
        timeline: Chronological list of Events.
        
    Returns:
        Analysis dict containing asset pool construction and contribution mapping.
    """
    
    # 1. Determine Critical Dates
    # We look for specific Event Types to anchor the timeline.
    cohabitation_start = None
    separation_date = None
    
    sorted_events = sorted(timeline, key=lambda x: x.date if x.date else date.min)
    
    for event in sorted_events:
        if event.type in ["CohabitationStart", "Marriage"]:
            if not cohabitation_start: # Take the earliest
                cohabitation_start = event.date
        elif event.type in ["Separation", "Divorce"]:
            separation_date = event.date # Take the latest usually, but Separation is key

    relationship_interval = TemporalEntity(start_date=cohabitation_start, end_date=separation_date)

    # 2. Reconstruct Asset Pool (Simplified Replay)
    # We track assets mentioned in Purchase/Sale events.
    # Note: In a full system, we would query the 'State' nodes. Here we infer from Events.
    
    # Map object_id -> {status: 'owned', value: ...}
    assets_ledger = {} 
    
    for event in sorted_events:
        # Acquisitions
        if event.type in ["Purchase", "Acquisition", "InheritanceReceived"]:
            for obj_id in event.object_ids:
                assets_ledger[obj_id] = {"status": "Acquired", "date": event.date, "context": event.description}
        
        # Disposals
        elif event.type in ["Sale", "Disposal", "Loss"]:
            for obj_id in event.object_ids:
                if obj_id in assets_ledger:
                    assets_ledger[obj_id]["status"] = "Disposed"
                    assets_ledger[obj_id]["disposal_date"] = event.date

    # Filter for current assets (not disposed)
    current_pool = {k: v for k, v in assets_ledger.items() if v["status"] != "Disposed"}

    # 3. Contribution Assessment
    # Classify contributions based on when they happened relative to the relationship.
    contributions = {
        "initial": [],      # Pre-cohabitation
        "financial_during": [],
        "non_financial": [], # Parenting/Homemaker events
        "post_separation": []
    }

    for event in sorted_events:
        if not event.date:
            continue
            
        is_pre = relationship_interval.start_date and event.date < relationship_interval.start_date
        is_during = relationship_interval.contains(event.date)
        is_post = relationship_interval.end_date and event.date > relationship_interval.end_date
        
        desc = f"{event.date}: {event.description}"

        if event.type in ["FinancialContribution", "InheritanceReceived", "GiftReceived", "Windfall"]:
            if is_pre:
                contributions["initial"].append(desc)
            elif is_during:
                contributions["financial_during"].append(desc)
            elif is_post:
                contributions["post_separation"].append(desc)
                
        elif event.type in ["Parenting", "Homemaker", "Renovation"]:
            contributions["non_financial"].append(desc)
            
        elif event.type in ["Waste", "Gambling"]:
            # Negative contributions are critical
            contributions.setdefault("negative", []).append(desc)

    return {
        "timeline_markers": {
            "cohabitation": cohabitation_start,
            "separation": separation_date,
            "duration_years": (separation_date.year - cohabitation_start.year) if (separation_date and cohabitation_start) else "Unknown"
        },
        "inferred_asset_pool": list(current_pool.values()),
        "contributions_analysis": contributions
    }
