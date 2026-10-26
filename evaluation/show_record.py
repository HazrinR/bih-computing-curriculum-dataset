import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data/structured/unified/all_courses.json"

FIELDS = [
    "course_name",
    "course_code",
    "ects",
    "year_of_study",
    "semester_options",
    "status_original",
    "learning_outcomes",
    "topics",
]

if len(sys.argv) < 2:
    print("Usage: python evaluation/show_record.py <dataset_id>")
    raise SystemExit(1)

dataset_id = sys.argv[1]

with INPUT_FILE.open("r", encoding="utf-8") as f:
    courses = {c["dataset_id"]: c for c in json.load(f)}

if dataset_id not in courses:
    print(f"Unknown dataset_id: {dataset_id}")
    raise SystemExit(1)

course = courses[dataset_id]

print("=" * 80)
print(f"{dataset_id}  |  {course['source_file']}  |  PDF page {course['source_page']}")
print("=" * 80)

for field in FIELDS:
    value = course.get(field)
    print(f"\n--- {field} ---")
    if isinstance(value, list) and field == "topics":
        for i, item in enumerate(value, start=1):
            print(f"  {i}. {item}")
    else:
        print(value)

if course.get("has_source_inconsistency"):
    print("\n--- documented source inconsistency ---")
    print(course.get("source_inconsistencies"))