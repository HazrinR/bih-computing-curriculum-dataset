"""
Descriptive statistics per institution (Table III of the paper).
Output: results/descriptive_stats.csv
"""
import json
import statistics
import pandas as pd

DATA = "data/structured/unified/all_courses.json"
OUT = "results/descriptive_stats.csv"
INSTITUTIONS = ["fit", "ibu", "etf"]


def semester_type(course):
    """winter = odd semester, summer = even, both = offered in both."""
    options = course.get("semester_options") or [course.get("semester")]
    kinds = {"winter" if s % 2 == 1 else "summer" for s in options if s}
    if len(kinds) == 2:
        return "both"
    return kinds.pop() if kinds else "unknown"


def n_tokens(text):
    """Number of words (tokens separated by spaces)."""
    return len(text.split()) if text else 0


def stats_for(courses):
    ects = [c["ects"] for c in courses]
    row = {"Courses": len(courses)}

    for year in [1, 2, 3]:
        row[f"Year {year}"] = sum(c["year_of_study"] == year for c in courses)

    for kind in ["winter", "summer", "both"]:
        row[f"Semester: {kind}"] = sum(semester_type(c) == kind for c in courses)

    for status in ["mandatory", "elective", "mixed"]:
        row[f"Status: {status}"] = sum(c["status_normalized"] == status for c in courses)

    row["ECTS mean (SD)"] = f"{statistics.mean(ects):.1f} ({statistics.stdev(ects):.1f})"
    row["ECTS median"] = statistics.median(ects)
    row["ECTS range"] = f"{min(ects):g}-{max(ects):g}"

    lo_counts = [len(c["learning_outcomes_list"]) for c in courses]
    topic_counts = [len(c["topics"]) for c in courses]
    row["LOs per course, mean"] = round(statistics.mean(lo_counts), 1)
    row["Topics per course, mean"] = round(statistics.mean(topic_counts), 1)

    lo_tokens = [n_tokens(c["learning_outcomes"]) for c in courses]
    topic_tokens = [n_tokens(" ".join(c["topics"])) for c in courses]
    row["LO text tokens, mean"] = round(statistics.mean(lo_tokens))
    row["Topic text tokens, mean"] = round(statistics.mean(topic_tokens))
    return row


with open(DATA, encoding="utf-8") as f:
    courses = json.load(f)

table = {}
for inst in INSTITUTIONS:
    table[inst.upper()] = stats_for([c for c in courses if c["institution_key"] == inst])
table["Total"] = stats_for(courses)

df = pd.DataFrame(table)
df.to_csv(OUT, encoding="utf-8-sig")
print(df.to_string())
print("\nSaved:", OUT)