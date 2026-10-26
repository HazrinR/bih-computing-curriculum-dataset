import csv
import json
import statistics
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data/structured/unified/all_courses.json"
OUTPUT_FILE = PROJECT_ROOT / "results/lo_counts_per_course.csv"

INSTITUTIONS = ["etf", "fit", "ibu"]

with INPUT_FILE.open("r", encoding="utf-8") as f:
    courses = json.load(f)

# The learning outcomes are already split into individual statements
# by scripts/lo_splitter.py (field 'learning_outcomes_list').
rows = []
for course in courses:
    rows.append({
        "dataset_id": course["dataset_id"],
        "institution_key": course["institution_key"],
        "course_name": course["course_name"],
        "lo_count": len(course["learning_outcomes_list"]),
        "topic_count": len(course["topics"]),
    })

print(f"{'Institution':<12}{'Courses':>8}{'LO mean':>9}{'LO median':>11}"
      f"{'LO min':>8}{'LO max':>8}{'Topics mean':>13}")
print("-" * 69)

for inst in INSTITUTIONS + ["all"]:
    subset = rows if inst == "all" else [r for r in rows if r["institution_key"] == inst]
    lo = [r["lo_count"] for r in subset]
    topics = [r["topic_count"] for r in subset]
    print(f"{inst.upper():<12}{len(subset):>8}{statistics.mean(lo):>9.2f}"
          f"{statistics.median(lo):>11.1f}{min(lo):>8}{max(lo):>8}"
          f"{statistics.mean(topics):>13.2f}")

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"\nSaved to: {OUTPUT_FILE}")