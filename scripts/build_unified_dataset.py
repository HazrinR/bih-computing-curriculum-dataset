from pathlib import Path
import json
from datetime import date
from lo_splitter import split_learning_outcomes

# ==========================================================
# HELPERS
# ==========================================================

def normalize_status(status):
    """
    Create an analysis-friendly normalized status while preserving
    the original source status separately.
    """
    if not status:
        return None

    value = status.strip().lower()

    if "obavezni" in value and "izborni" in value:
        return "mixed"

    if "obavezni" in value:
        return "mandatory"

    if "izborni" in value:
        return "elective"

    return "other"


def ensure_list(value):
    """Normalize None/string/list values to a list."""
    if value is None or value == "":
        return []

    if isinstance(value, list):
        return value

    return [value]


def normalize_course(course, institution_key, index):
    """
    Convert FIT, IBU, and ETF records to one shared schema.

    Source values are preserved. Missing fields are represented
    by None or [] rather than invented values.
    """

    semester_options = course.get("semester_options") or []

    if not semester_options and course.get("semester") is not None:
        semester_options = [course.get("semester")]

    normalized = {
        # --------------------------------------------------
        # IDENTIFIERS
        # --------------------------------------------------
        "dataset_id": f"{institution_key}_{index:03d}",
        "institution_key": institution_key,

        # --------------------------------------------------
        # INSTITUTION / PROGRAM
        # --------------------------------------------------
        "institution": course.get("institution"),
        "faculty": course.get("faculty"),
        "program": course.get("program"),
        "degree_level": course.get("degree_level"),

        # --------------------------------------------------
        # COURSE IDENTITY
        # --------------------------------------------------
        "course_name": course.get("course_name"),
        "course_code": course.get("course_code"),

        # --------------------------------------------------
        # STUDY STRUCTURE
        # --------------------------------------------------
        "year_of_study": course.get("year_of_study"),
        "semester": course.get("semester"),
        "semester_options": semester_options,
        "ects": course.get("ects"),

        # --------------------------------------------------
        # STATUS
        # --------------------------------------------------
        "status_original": course.get("status"),
        "status_normalized": normalize_status(
            course.get("status")
        ),

        # --------------------------------------------------
        # COURSE CONTENT
        # --------------------------------------------------
        "description": course.get("description"),
        "objectives": course.get("objectives"),
        "learning_outcomes": course.get("learning_outcomes"),
        "learning_outcomes_list": split_learning_outcomes(
            course.get("learning_outcomes")
        ),
        "topics": ensure_list(course.get("topics")),
        "teaching_methods": course.get("teaching_methods"),
        "student_obligations": course.get("student_obligations"),
        "assessment": course.get("assessment"),
        "prerequisites": course.get("prerequisites"),
        "language": course.get("language"),

        # --------------------------------------------------
        # LITERATURE
        # --------------------------------------------------
        "literature": ensure_list(
            course.get("literature")
        ),
        "mandatory_literature": ensure_list(
            course.get("mandatory_literature")
        ),
        "recommended_literature": ensure_list(
            course.get("recommended_literature")
        ),
        "additional_literature": ensure_list(
            course.get("additional_literature")
        ),

        # --------------------------------------------------
        # HOURS / WORKLOAD
        # --------------------------------------------------
        "lecture_hours": course.get("lecture_hours"),
        "laboratory_hours": course.get("laboratory_hours"),
        "tutorial_hours": course.get("tutorial_hours"),
        "self_study_hours": course.get("self_study_hours"),

        # --------------------------------------------------
        # PROVENANCE
        # --------------------------------------------------
        "source_file": course.get("source_file"),
        "source_page": course.get("source_page"),

        # --------------------------------------------------
        # SOURCE CONSISTENCY
        # --------------------------------------------------
        "has_source_inconsistency": bool(
            course.get("has_source_inconsistency")
            or course.get("code_inconsistency")
        ),

        "source_inconsistencies": ensure_list(
            course.get("source_inconsistencies")
        ),

        "source_name": course.get("source_name"),
        "source_code": course.get("source_code"),

        "curriculum_table_name": course.get(
            "curriculum_table_name"
        ),
        "curriculum_table_code": course.get(
            "curriculum_table_code"
        ),

        "source_year_of_study": course.get(
            "source_year_of_study"
        ),
        "curriculum_table_year_of_study": course.get(
            "curriculum_table_year_of_study"
        ),

        "source_semester": course.get(
            "source_semester"
        ),
        "curriculum_table_semester": course.get(
            "curriculum_table_semester"
        ),

        "source_ects": course.get("source_ects"),
        "curriculum_table_ects": course.get(
            "curriculum_table_ects"
        ),

        # IBU-specific source inconsistency fields
        "ibu_source_code": course.get("source_code")
        if institution_key == "ibu"
        else None,

        "ibu_curriculum_table_code": course.get(
            "curriculum_table_code"
        )
        if institution_key == "ibu"
        else None,

        # ETF-specific source metadata
        "program_source_value": course.get(
            "program_source_value"
        ),
    }

    # If an IBU record has only code_inconsistency and no textual
    # source_inconsistencies list, document it explicitly.
    if (
        institution_key == "ibu"
        and course.get("code_inconsistency")
        and not normalized["source_inconsistencies"]
    ):
        normalized["source_inconsistencies"] = [
            "course_code differs between curriculum table and detailed specification"
        ]

    return normalized

# ==========================================================
# SOURCE METADATA (data/sources.json)
# ==========================================================

def load_sources(project_root):
    """Load source URL, version, dates and language per institution."""
    path = project_root / "data" / "sources.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_degree_level(value):
    """All three programmes are first-cycle (bachelor) programmes."""
    if not value:
        return None
    v = value.lower()
    if "prvi ciklus" in v or "i ciklusa" in v or "bachelor" in v:
        return "bachelor"
    return "other"


def get_extraction_date(project_root, institution_key, source_file):
    """Date when the PDF was converted to text (date of the .txt file)."""
    txt_name = Path(source_file).with_suffix(".txt").name
    txt_path = project_root / "data" / "extracted" / institution_key / txt_name
    if not txt_path.exists():
        return None
    return date.fromtimestamp(txt_path.stat().st_mtime).isoformat()


def add_source_metadata(record, source, project_root):
    """Add source-level metadata to one unified course record."""
    record["degree_level_normalized"] = normalize_degree_level(
        record.get("degree_level")
    )
    record["document_language"] = source.get("document_language")
    record["instruction_language"] = source.get("instruction_language")
    record["instruction_language_source"] = source.get(
        "instruction_language_source"
    )
    record["source_url"] = source.get("source_url")
    record["curriculum_version"] = source.get("curriculum_version")
    record["retrieval_date"] = source.get("retrieval_date")
    record["extraction_date"] = get_extraction_date(
        project_root,
        record["institution_key"],
        record["source_file"],
    )
    return record

def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    project_root = Path(__file__).resolve().parent.parent

    input_files = {
        "fit": (
            project_root
            / "data"
            / "structured"
            / "fit"
            / "fit_courses.json"
        ),
        "ibu": (
            project_root
            / "data"
            / "structured"
            / "ibu"
            / "ibu_courses.json"
        ),
        "etf": (
            project_root
            / "data"
            / "structured"
            / "etf"
            / "etf_courses.json"
        ),
    }

    output_path = (
        project_root
        / "data"
        / "structured"
        / "unified"
        / "all_courses.json"
    )

    all_courses = []
    sources = load_sources(project_root)

    print("=" * 90)
    print("BUILDING UNIFIED CURRICULUM DATASET")
    print("=" * 90)

    for institution_key, path in input_files.items():

        if not path.exists():
            print(f"\nERROR: Missing input file:")
            print(path)
            raise SystemExit(1)

        courses = load_json(path)

        print(
            f"{institution_key.upper():4} -> "
            f"{len(courses)} courses"
        )

        for index, course in enumerate(
            courses,
            start=1,
        ):
            normalized = normalize_course(
                course,
                institution_key,
                index,
            )

            
            normalized = add_source_metadata(
                normalized,
                sources[institution_key],
                project_root,
            )

            all_courses.append(normalized)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            all_courses,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    print("-" * 90)
    print(
        f"TOTAL -> {len(all_courses)} courses"
    )

    print(
        f"Unified dataset saved to:\n"
        f"{output_path}"
    )

    print()

    # ------------------------------------------------------
    # QUICK SUMMARY
    # ------------------------------------------------------

    counts = {}

    for course in all_courses:
        key = course["institution_key"]
        counts[key] = counts.get(key, 0) + 1

    print("INSTITUTION COUNTS")
    print("-" * 90)

    for key, count in counts.items():
        print(
            f"{key.upper():4}: {count}"
        )

    inconsistencies = [
        course
        for course in all_courses
        if course["has_source_inconsistency"]
    ]

    print()
    print(
        f"Courses with documented source inconsistencies: "
        f"{len(inconsistencies)}"
    )

    print()
    print("=" * 90)
    print("UNIFIED DATASET FINISHED")
    print("=" * 90)
