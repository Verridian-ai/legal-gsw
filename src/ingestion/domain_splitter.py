import json
import re
import os
from pathlib import Path
from collections import Counter
import sys

# Add current directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from classification_config import CLASSIFICATION_MAP, DOMAIN_MAPPING, LEGISLATION_STATUS_MAP

# --- CONFIGURATION ---

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE_DIR / "data" / "raw" / "corpus.jsonl"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "domains"

# Ensure output dir exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- COMPILATION ---
# Pre-compile regex patterns for performance
PATTERNS = {}
for category, keywords in CLASSIFICATION_MAP.items():
    # Escape keywords to be safe, though most are simple strings
    # Using word boundaries \b to avoid partial matches (e.g. "tax" in "taxi")
    # But some keywords might be multi-word.
    # Join with |
    pattern_str = "|".join([re.escape(k) for k in keywords])
    PATTERNS[category] = re.compile(pattern_str, re.IGNORECASE)

# Broad Domains to File Handles
# Invert the mapping for easy lookup? No, we need granular -> broad.
# We will iterate DOMAIN_MAPPING to find the Broad Domain for a given Category.
CATEGORY_TO_DOMAIN = {}
for broad, granular_list in DOMAIN_MAPPING.items():
    for granular in granular_list:
        CATEGORY_TO_DOMAIN[granular] = broad

# --- CLASSIFICATION LOGIC ---

def classify_document(doc):
    """
    Returns (BroadDomain, SpecificCategory).
    """
    
    # 1. Legislation Check (Strict Whitelist logic)
    # We can use the Hierarchy/Status map if needed, but for now keep it simple.
    # If it is legislation, we check if it matches a specific category (e.g. Family Law Act -> Family_General).
    # If not, it goes to 'Legislation_Other'.
    
    doc_type = doc.get('type', '')
    if doc_type in ['primary_legislation', 'secondary_legislation', 'bill']:
        title = doc.get('citation', '') or doc.get('name', '') or ""
        
        # Check all patterns against the title
        best_cat = None
        for category, pattern in PATTERNS.items():
            if pattern.search(title):
                best_cat = category
                break # First match wins for title? Or specific priority?
        
        if best_cat:
            domain = CATEGORY_TO_DOMAIN.get(best_cat, "Unclassified")
            return domain, best_cat
        else:
            return "Legislation_Other", "Legislation_Other"

    # 2. Case Law / Decisions
    text_content = doc.get('text', '') or doc.get('body', '')
    jurisdiction = doc.get('jurisdiction', '') or doc.get('court', '')
    catchwords = doc.get('catchwords', '')
    citation = doc.get('citation', '')
    
    full_text = f"{citation} {catchwords} {text_content[:10000]}" # Limit text scan for speed? Or full?
    # Full text is better for accuracy but slower. Let's use full text if performance allows.
    # The catchwords are high value.
    
    scores = Counter()
    
    for category, pattern in PATTERNS.items():
        # Count matches
        # len(findall) is slow. boolean search is fast.
        # Let's do boolean first.
        if pattern.search(full_text):
            scores[category] += 1
            # Boost if in catchwords or title
            if pattern.search(catchwords) or pattern.search(citation):
                scores[category] += 5
            
            # Specific Jurisdiction Boosts
            if "Family" in category and "Family Court" in jurisdiction:
                scores[category] += 10
            if "Migration" in category and ("Refugee" in catchwords or "Migration" in catchwords):
                scores[category] += 10
    
    if not scores:
        return "Unclassified", "Unclassified"

    # Determine Winner
    best_category, score = scores.most_common(1)[0]
    
    # PRIORITY OVERRIDES
    # If Migration score is present, it often dominates.
    if scores['Admin_Migration'] > 0:
        # But wait, if Family score is HIGHER, it might be Family.
        # e.g. "Family Court appeal regarding visa status of child".
        # Actually, "visa status" -> Admin_Migration usually.
        # But we want Family Law.
        # Let's trust the score.
        pass

    broad_domain = CATEGORY_TO_DOMAIN.get(best_category, "Unclassified")
    
    return broad_domain, best_category

def split_corpus():
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found at {INPUT_FILE}")
        return

    print("--- STARTING MASTER ONTOLOGY SPLITTER ---")
    print(f"Input: {INPUT_FILE}")
    print(f"Output Dir: {OUTPUT_DIR}")

    # Open file handles for all Broad Domains
    # Plus Legislation_Other and Unclassified
    files = {}
    unique_domains = set(DOMAIN_MAPPING.keys())
    unique_domains.add("Legislation_Other")
    unique_domains.add("Unclassified")

    try:
        for domain in unique_domains:
            files[domain] = open(OUTPUT_DIR / f"{domain.lower()}.jsonl", 'w', encoding='utf-8')

        stats = Counter()
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as infile:
            for line_num, line in enumerate(infile):
                try:
                    doc = json.loads(line)
                    domain, category = classify_document(doc)
                    
                    # Inject classification into doc
                    doc['classification'] = category
                    doc['domain'] = domain
                    
                    # Write to Broad Domain file
                    files[domain].write(json.dumps(doc) + "\n")
                    stats[domain] += 1
                    stats[category] += 1 # Track detailed stats too
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error Line {line_num}: {e}")
                    continue

                if line_num % 1000 == 0:
                    print(f"Processed {line_num} docs... Broad Stats: {dict(stats.most_common(5))}", end='\r')

        print(f"\n--- SPLIT COMPLETE ---")
        print("Top Categories:")
        print(json.dumps(dict(stats.most_common(20)), indent=2))

    finally:
        # Close all handles
        for f in files.values():
            f.close()

if __name__ == "__main__":
    split_corpus()
