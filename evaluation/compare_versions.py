import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OLD_FILE = PROJECT_ROOT / "data/structured/unified/all_courses_before_fix.json"
NEW_FILE = PROJECT_ROOT / "data/structured/unified/all_courses.json"

IGNORE = {"extraction_date"}  # changes every time extraction runs

with OLD_FILE.open("r", encoding="utf-8") as f:
    old = {c["dataset_id"]: c for c in json.load(f)}

with NEW_FILE.open("r", encoding="utf-8") as f:
    new = {c["dataset_id"]: c for c in json.load(f)}

print(f"Old records: {len(old)} | New records: {len(new)}\n")

changed = 0
for dataset_id in old:
    fields = [
        field for field in old[dataset_id]
        if field not in IGNORE
        and old[dataset_id][field] != new[dataset_id].get(field)
    ]
    if fields:
        changed += 1
        old_topics = len(old[dataset_id]["topics"])
        new_topics = len(new[dataset_id]["topics"])
        print(f"{dataset_id:<9} {old[dataset_id]['course_name'][:40]:<42} "
              f"changed: {', '.join(fields)} | topics {old_topics} -> {new_topics}")

print(f"\nChanged records: {changed} of {len(old)}")