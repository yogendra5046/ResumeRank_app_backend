#!/usr/bin/env python3
"""CI fallback: generate a representative ESCO skill fixture (3200 skills).

Run when the real ESCO dataset isn't available in CI:
    python scripts/generate_esco_fixture.py

Outputs: src/infrastructure/skills/data/esco_skills.json.gz
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
import requests

_OUTPUT = Path("src/infrastructure/skills/data/esco_skills.json.gz")
_ESCO_API_URL = "https://ec.europa.eu/esco/api/search"

import time

def fetch_all_skills() -> list[dict]:
    """Fetch all skills from the official ESCO API robustly."""
    all_skills = []
    limit = 20  # Small limit to avoid response truncation and timeouts
    page = 0
    max_retries = 3
    
    print("Fetching ESCO skills (robust mode)...", file=sys.stderr)
    
    while True:
        params = {
            'language': 'en',
            'type': 'skill',
            'limit': limit,
            'offset': page,
            'full': 'true'
        }
        
        success = False
        for attempt in range(max_retries):
            try:
                response = requests.get(_ESCO_API_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                success = True
                break
            except Exception as e:
                print(f"  Attempt {attempt+1} failed: {e}", file=sys.stderr)
                time.sleep(2)
        
        if not success:
            print("Failed to fetch after multiple attempts. Stopping.", file=sys.stderr)
            break
            
        total = data.get('total', 0)
        results = data.get('_embedded', {}).get('results', [])
        
        if not results:
            break
            
        for item in results:
            alt_labels_raw = item.get("alternativeLabel", {})
            alt_labels_en = alt_labels_raw.get("en", []) if isinstance(alt_labels_raw, dict) else []
            
            skill = {
                "uri": item.get("uri"),
                "preferredLabel": {"en": item.get("title")},
                "altLabels": {"en": alt_labels_en},
                "broaderUri": []
            }
            all_skills.append(skill)
            
        if page == 0:
            print(f"  Total reported: {total}", file=sys.stderr)
            
        if len(all_skills) % 100 == 0 or len(results) < limit:
            print(f"  Progress: {len(all_skills)} / {total}", file=sys.stderr)
        
        if len(results) < limit:
            break
            
        page += 1
            
    return all_skills

def generate() -> None:
    skills = fetch_all_skills()
    
    if not skills:
        print("Falling back to minimal skill list due to API error.", file=sys.stderr)
        # Minimal fallback if API is down
        skills = [
            {
                "uri": "http://data.europa.eu/esco/skill/fallback-001",
                "preferredLabel": {"en": "Python programming"},
                "altLabels": {"en": ["python"]},
                "broaderUri": []
            }
        ]

    payload = json.dumps({"skills": skills}).encode()
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(_OUTPUT, "wb") as fh:
        fh.write(payload)

    print(f"Generated {len(skills)} ESCO skills → {_OUTPUT}", file=sys.stderr)

if __name__ == "__main__":
    generate()
