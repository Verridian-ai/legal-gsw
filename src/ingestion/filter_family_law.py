import json
import re
import os
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE_DIR / "data" / "raw" / "corpus.jsonl"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "family_law_subset.jsonl"

# POSITIVE INDICATORS (Must have at least one)
FAMILY_LAW_KEYWORDS = [
    r"Family Law Act",
    r"Family Court",
    r"Federal Circuit and Family Court",
    r"parenting order",
    r"property settlement",
    r"child support",
    r"spousal maintenance",
    r"decree nisi",
    r"decree absolute",
    r"independent children's lawyer",
    r"family violence order"
]

# NEGATIVE INDICATORS (Must NOT have any, unless strongly overridden?)
# We use these to filter out Migration/Commercial cases that happen to be in Federal Circuit Court
EXCLUDED_KEYWORDS = [
    r"Migration Act",
    r"Migration Regulations",
    r"Refugee Review Tribunal",
    r"Protection Visa",
    r"Industrial Relations Act",
    r"Bankruptcy Act", # Careful, family law overlaps with bankruptcy, but pure bankruptcy cases should be excluded.
    r"Corporations Act", # Similar overlap risk, but usually distinct.
    r"Administrative Appeals Tribunal" # AAT usually handles Migration/Social Security, not Family.
]

# Compile regex patterns
POS_PATTERN = re.compile("|".join(FAMILY_LAW_KEYWORDS), re.IGNORECASE)
NEG_PATTERN = re.compile("|".join(EXCLUDED_KEYWORDS), re.IGNORECASE)

def is_family_law_case(doc):
    """
    Determines if a document is relevant Australian Family Law material.
    """
    # 1. Filter by Type
    # We primarily want Case Law (decisions). 
    # If it's legislation, ONLY include the Family Law Act itself.
    doc_type = doc.get('type', 'decision')
    title = doc.get('citation', '') or doc.get('name', '') # Legislation uses 'citation' or 'name'
    
    if doc_type == 'primary_legislation':
        # Only keep the main Act
        if "Family Law Act 1975" in title:
            return True
        return False

    # 2. Filter Decisions
    text_content = doc.get('text', '') or doc.get('body', '')
    jurisdiction = doc.get('jurisdiction', '') or doc.get('court', '')
    catchwords = doc.get('catchwords', '') # Some datasets have this field
    
    full_text = f"{title} {text_content} {jurisdiction} {catchwords}"
    
    # Check Exclusions first (Fail Fast)
    # But be careful: A Family Law case might cite the Migration Act.
    # Heuristic: If it mentions 'Migration Act' AND 'Protection Visa', it's likely Migration.
    # Simpler: If it matches NEG_PATTERN, we tend to exclude, UNLESS it has very strong Family signals.
    # For now, let's trust the NEG_PATTERN to filter out the bulk of noise.
    if NEG_PATTERN.search(full_text):
        # Double check: Does it strictly explicitly mention Family Court in the jurisdiction?
        # Migration cases are often in "Federal Circuit Court" (General), not "Family Court".
        if "Family Court" in jurisdiction:
            # If it's in the Family Court, keep it even if it mentions Bankruptcy/Migration (rare edge case)
            return True
        return False

    # 3. Check Positive Indicators
    if POS_PATTERN.search(full_text):
        return True
        
    return False

def filter_corpus():
    """
    Streams the raw corpus and filters for Australian Family Law cases.
    """
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found at {INPUT_FILE}")
        return

    print(f"Starting filtration process...")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    
    count_total = 0
    count_matched = 0
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
             open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                count_total += 1
                try:
                    doc = json.loads(line)
                    
                    if is_family_law_case(doc):
                        outfile.write(line)
                        count_matched += 1
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error processing line {count_total}: {e}")
                    continue

                # Progress update
                if count_total % 1000 == 0:
                    print(f"Processed {count_total} docs | Found {count_matched} Family Law cases...", end='\r')
        
        print(f"\n\nFiltration Complete.")
        print(f"Total Documents Scanned: {count_total}")
        print(f"Family Law Subset: {count_matched}")
        print(f"Saved to: {OUTPUT_FILE}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    filter_corpus()
