import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "evaluation/validation_sample.csv"
OUTPUT_FILE = PROJECT_ROOT / "results/accuracy_results.csv"

FIELDS = [
    "course_boundary",
    "course_name",
    "ects",
    "year",
    "semester",
    "status",
    "learning_outcomes",
    "topics",
]

INSTITUTIONS = ["etf", "fit", "ibu", "all"]


def summarize(rows, field):
    """Return (n, strict accuracy, lenient accuracy) for one field."""
    scores = [float(r[f"{field}_correct"]) for r in rows]
    n = len(scores)
    strict = sum(1 for s in scores if s == 1) / n
    lenient = sum(scores) / n
    return n, strict, lenient


# ----------------------------------------------------------
# LOAD
# ----------------------------------------------------------
with INPUT_FILE.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded {len(rows)} evaluated records.\n")

# ----------------------------------------------------------
# FIELD-LEVEL ACCURACY
# ----------------------------------------------------------
results = []

print(f"{'Field':<20}" + "".join(f"{i.upper():>16}" for i in INSTITUTIONS))
print("-" * (20 + 16 * len(INSTITUTIONS)))

for field in FIELDS:
    line = f"{field:<20}"
    for inst in INSTITUTIONS:
        subset = rows if inst == "all" else [r for r in rows if r["institution_key"] == inst]
        n, strict, lenient = summarize(subset, field)
        line += f"{strict*100:>8.1f}% ({lenient*100:4.1f})"
        results.append({
            "field": field,
            "institution": inst,
            "n": n,
            "strict_accuracy": round(strict, 4),
            "lenient_accuracy": round(lenient, 4),
        })
    print(line)

print("\nFormat: strict % (lenient %)")

# ----------------------------------------------------------
# OVERALL AND RECORD-LEVEL ACCURACY
# ----------------------------------------------------------
all_scores = [float(r[f"{f}_correct"]) for r in rows for f in FIELDS]
fully_correct_records = sum(
    1 for r in rows if all(float(r[f"{f}_correct"]) == 1 for f in FIELDS)
)

print(f"\nTotal field judgements: {len(all_scores)}")
print(f"Fully correct fields:   {sum(1 for s in all_scores if s == 1)} "
      f"({sum(1 for s in all_scores if s == 1) / len(all_scores) * 100:.1f}%)")
print(f"Records with all fields correct: {fully_correct_records}/{len(rows)} "
      f"({fully_correct_records / len(rows) * 100:.1f}%)")

partly = [(r["dataset_id"], f) for r in rows for f in FIELDS if float(r[f"{f}_correct"]) < 1]
print("\nFields not fully correct:")
for dataset_id, field in partly:
    print(f"  {dataset_id}: {field}")

# ----------------------------------------------------------
# SAVE
# ----------------------------------------------------------
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\nSaved to: {OUTPUT_FILE}")