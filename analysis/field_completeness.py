"""
Field completeness per institution (Table IV of the paper).
A record counts as filled for a group only if ALL fields in the group are filled.
Output: results/field_completeness.csv
"""
import json
import pandas as pd

DATA = "data/structured/unified/all_courses.json"
OUT = "results/field_completeness.csv"
INSTITUTIONS = ["fit", "ibu", "etf"]

GROUPS = {
    "Institution, faculty, programme, degree level":
        ["institution", "faculty", "program", "degree_level"],
    "Course name, year of study, ECTS, status":
        ["course_name", "year_of_study", "ects", "status_normalized"],
    "Semester (single or options)": ["semester_options"],
    "Course code": ["course_code"],
    "Learning outcomes, topics": ["learning_outcomes", "topics"],
    "Description": ["description"],
    "Objectives": ["objectives"],
    "Teaching methods, assessment": ["teaching_methods", "assessment"],
    "Prerequisites": ["prerequisites"],
    "Literature": ["literature"],
    "Source file, source page, source URL":
        ["source_file", "source_page", "source_url"],
    "Curriculum version, retrieval and extraction date":
        ["curriculum_version", "retrieval_date", "extraction_date"],
    "Document and instruction language":
        ["document_language", "instruction_language"],
}


def is_filled(value):
    return value not in (None, "", [], {})


with open(DATA, encoding="utf-8") as f:
    courses = json.load(f)

rows = []
for group, fields in GROUPS.items():
    row = {"Field group": group}
    for inst in INSTITUTIONS:
        subset = [c for c in courses if c["institution_key"] == inst]
        row[inst.upper()] = sum(all(is_filled(c.get(f)) for f in fields) for c in subset)
    total = sum(row[i.upper()] for i in INSTITUTIONS)
    row["Total"] = f"{total} ({100 * total / len(courses):.0f}%)"
    rows.append(row)

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(df.to_string(index=False))
print("\nSaved:", OUT)