
import json
import csv
import random
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / "data/structured/unified/all_courses.json"
OUTPUT_FILE = PROJECT_ROOT / "evaluation/validation_sample.csv"

SAMPLE_SIZE = 10
RANDOM_SEED = 42

with INPUT_FILE.open("r", encoding="utf-8") as f:
    courses = json.load(f)

print("Total courses:", len(courses))
print("Institution distribution:",
      dict(Counter(c["institution_key"] for c in courses)))

random_generator = random.Random(RANDOM_SEED)
selected = []

for institution in sorted(set(c["institution_key"] for c in courses)):
    institution_courses = [
        c for c in courses
        if c["institution_key"] == institution
    ]

    if len(institution_courses) < SAMPLE_SIZE:
        raise ValueError(
            f"Not enough courses for {institution}"
        )

    sample = random_generator.sample(
        sorted(institution_courses, key=lambda c: c["dataset_id"]),
        SAMPLE_SIZE
    )
    selected.extend(sample)

fields = [
    "dataset_id",
    "institution_key",
    "course_name",
    "source_file",
    "source_page",
    "course_boundary_correct",
    "course_name_correct",
    "ects_correct",
    "year_correct",
    "semester_correct",
    "status_correct",
    "learning_outcomes_correct",
    "topics_correct",
    "notes"
]

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

if OUTPUT_FILE.exists():
    raise FileExistsError(
        f"{OUTPUT_FILE} already exists. "
        "The validation sample must not be overwritten."
    )

with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for course in selected:
        writer.writerow({
            "dataset_id": course["dataset_id"],
            "institution_key": course["institution_key"],
            "course_name": course["course_name"],
            "source_file": course["source_file"],
            "source_page": course["source_page"]
        })

print(f"\nSelected {len(selected)} courses.")
print(f"Random seed: {RANDOM_SEED}")
print(f"Saved to: {OUTPUT_FILE}")
