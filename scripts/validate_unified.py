from pathlib import Path
import json
from collections import Counter


EXPECTED_COUNTS = {
    "fit": 35,
    "ibu": 44,
    "etf": 41,
}

EXPECTED_TOTAL = 120
EXPECTED_INCONSISTENCIES = 14

CORE_FIELDS = [
    "dataset_id",
    "institution_key",
    "institution",
    "faculty",
    "program",
    "course_name",
    "year_of_study",
    "ects",
    "status_original",
    "status_normalized",
    "learning_outcomes",
    "topics",
    "source_file",
    "source_page",
]


def is_empty(value):
    return value is None or value == "" or value == []


def validate(courses):

    print("=" * 100)
    print("UNIFIED DATASET VALIDATION")
    print("=" * 100)
    print(f"Total records: {len(courses)}")
    print()

    # --------------------------------------------------
    # 1. TOTAL COUNT
    # --------------------------------------------------

    print("TOTAL COUNT CHECK")
    print("-" * 100)

    if len(courses) == EXPECTED_TOTAL:
        print(f"OK: Expected {EXPECTED_TOTAL}, found {len(courses)}.")
    else:
        print(
            f"ERROR: Expected {EXPECTED_TOTAL}, found {len(courses)}."
        )

    print()

    # --------------------------------------------------
    # 2. INSTITUTION COUNTS
    # --------------------------------------------------

    print("INSTITUTION COUNTS")
    print("-" * 100)

    institution_counts = Counter(
        course.get("institution_key")
        for course in courses
    )

    for key, expected in EXPECTED_COUNTS.items():
        actual = institution_counts.get(key, 0)

        status = "OK" if actual == expected else "ERROR"

        print(
            f"{status}: {key.upper():4} "
            f"Expected: {expected:2} | Found: {actual:2}"
        )

    print()

    # --------------------------------------------------
    # 3. DATASET ID UNIQUENESS
    # --------------------------------------------------

    print("DATASET ID UNIQUENESS")
    print("-" * 100)

    ids = [
        course.get("dataset_id")
        for course in courses
    ]

    duplicate_ids = [
        dataset_id
        for dataset_id, count in Counter(ids).items()
        if count > 1
    ]

    if duplicate_ids:
        print("ERROR: Duplicate dataset_id values found:")

        for dataset_id in duplicate_ids:
            print(f"   {dataset_id}")
    else:
        print("OK: All dataset_id values are unique.")

    print()

    # --------------------------------------------------
    # 4. CORE FIELD COMPLETENESS
    # --------------------------------------------------

    print("CORE FIELD COMPLETENESS")
    print("-" * 100)

    for field in CORE_FIELDS:

        filled = sum(
            1
            for course in courses
            if not is_empty(course.get(field))
        )

        missing = len(courses) - filled

        print(
            f"{field:25} "
            f"Filled: {filled:3} | "
            f"Missing: {missing:3}"
        )

    print()

    # --------------------------------------------------
    # 5. STATUS NORMALIZATION
    # --------------------------------------------------

    print("STATUS NORMALIZATION")
    print("-" * 100)

    allowed_statuses = {
        "mandatory",
        "elective",
        "mixed",
        "other",
    }

    status_counts = Counter(
        course.get("status_normalized")
        for course in courses
    )

    for status, count in sorted(
        status_counts.items(),
        key=lambda item: str(item[0]),
    ):
        print(f"{status}: {count}")

    invalid_statuses = [
        course
        for course in courses
        if course.get("status_normalized")
        not in allowed_statuses
    ]

    if invalid_statuses:
        print()
        print("ERROR: Invalid normalized statuses found:")

        for course in invalid_statuses:
            print(
                f"   {course['dataset_id']} | "
                f"{course['course_name']} | "
                f"{course.get('status_normalized')}"
            )
    else:
        print("OK: All normalized statuses are valid.")

    print()

    # --------------------------------------------------
    # 6. COURSE CODE SUMMARY
    # --------------------------------------------------

    print("COURSE CODE SUMMARY")
    print("-" * 100)

    for key in EXPECTED_COUNTS:

        institution_courses = [
            course
            for course in courses
            if course.get("institution_key") == key
        ]

        missing_codes = sum(
            1
            for course in institution_courses
            if is_empty(course.get("course_code"))
        )

        print(
            f"{key.upper():4} | "
            f"Courses: {len(institution_courses):2} | "
            f"Missing course_code: {missing_codes:2}"
        )

    print()

    # --------------------------------------------------
    # 7. SEMESTER REPRESENTATION
    # --------------------------------------------------

    print("SEMESTER REPRESENTATION")
    print("-" * 100)

    no_semester_info = []

    for course in courses:

        semester = course.get("semester")
        semester_options = (
            course.get("semester_options")
            or []
        )

        if semester is None and not semester_options:
            no_semester_info.append(course)

    if no_semester_info:
        print("WARNING: Records without semester information:")

        for course in no_semester_info:
            print(
                f"   {course['dataset_id']} | "
                f"{course['course_name']}"
            )
    else:
        print(
            "OK: Every record has semester or semester_options."
        )

    print()

    # --------------------------------------------------
    # 8. YEAR / SEMESTER CONSISTENCY
    # --------------------------------------------------

    print("YEAR-SEMESTER CONSISTENCY")
    print("-" * 100)

    inconsistencies = []

    for course in courses:

        year = course.get("year_of_study")
        semester = course.get("semester")
        semester_options = (
            course.get("semester_options")
            or []
        )

        semesters = (
            [semester]
            if semester is not None
            else semester_options
        )

        for sem in semesters:

            if sem not in [1, 2, 3, 4, 5, 6]:
                continue

            expected_year = ((sem - 1) // 2) + 1

            if year != expected_year:
                inconsistencies.append(
                    (
                        course["dataset_id"],
                        course["course_name"],
                        year,
                        sem,
                        expected_year,
                    )
                )

    if inconsistencies:
        for item in inconsistencies:
            print(
                f"{item[0]} | {item[1]} | "
                f"Year: {item[2]} | "
                f"Semester: {item[3]} | "
                f"Expected year: {item[4]}"
            )
    else:
        print("OK: No year-semester inconsistencies found.")

    print()

    # --------------------------------------------------
    # 9. SOURCE INCONSISTENCIES
    # --------------------------------------------------

    print("SOURCE INCONSISTENCIES")
    print("-" * 100)

    source_inconsistent = [
        course
        for course in courses
        if course.get("has_source_inconsistency")
    ]

    print(
        f"Expected: {EXPECTED_INCONSISTENCIES} | "
        f"Found: {len(source_inconsistent)}"
    )

    if len(source_inconsistent) == EXPECTED_INCONSISTENCIES:
        print("OK: Source inconsistency count matches expectation.")
    else:
        print("WARNING: Source inconsistency count differs from expectation.")

    by_institution = Counter(
        course.get("institution_key")
        for course in source_inconsistent
    )

    for key, count in sorted(by_institution.items()):
        print(f"{key.upper():4}: {count}")

    print()

    for course in source_inconsistent:
        print(
            f"{course['dataset_id']} | "
            f"{course['course_name']}"
        )

        for issue in course.get(
            "source_inconsistencies",
            [],
        ):
            print(f"   - {issue}")

    print()

    # --------------------------------------------------
    # 10. DUPLICATE COURSE NAME WITHIN INSTITUTION
    # --------------------------------------------------

    print("DUPLICATE COURSE NAMES WITHIN INSTITUTION")
    print("-" * 100)

    duplicate_name_found = False

    for key in EXPECTED_COUNTS:

        names = [
            course.get("course_name")
            for course in courses
            if course.get("institution_key") == key
        ]

        duplicates = [
            name
            for name, count in Counter(names).items()
            if count > 1
        ]

        if duplicates:
            duplicate_name_found = True

            for name in duplicates:
                print(
                    f"{key.upper()} | Duplicate name: {name}"
                )

    if not duplicate_name_found:
        print(
            "OK: No duplicate course names within institutions."
        )

    print()

    # --------------------------------------------------
    # 11. DUPLICATE COURSE CODES WITHIN INSTITUTION
    # --------------------------------------------------

    print("DUPLICATE COURSE CODES WITHIN INSTITUTION")
    print("-" * 100)

    for key in EXPECTED_COUNTS:

        codes = [
            course.get("course_code")
            for course in courses
            if (
                course.get("institution_key") == key
                and not is_empty(course.get("course_code"))
            )
        ]

        duplicates = [
            code
            for code, count in Counter(codes).items()
            if count > 1
        ]

        if duplicates:
            for code in duplicates:
                print(
                    f"{key.upper()} | Duplicate code: {code}"
                )
        else:
            print(
                f"{key.upper()} | "
                f"No duplicate non-empty course codes."
            )

    print()

    # --------------------------------------------------
    # 12. PROVENANCE
    # --------------------------------------------------

    print("PROVENANCE CHECK")
    print("-" * 100)

    missing_provenance = [
        course
        for course in courses
        if (
            is_empty(course.get("institution"))
            or is_empty(course.get("faculty"))
            or is_empty(course.get("program"))
            or is_empty(course.get("source_file"))
            or course.get("source_page") is None
        )
    ]

    if missing_provenance:
        print(
            f"ERROR: {len(missing_provenance)} records "
            f"have incomplete provenance."
        )

        for course in missing_provenance:
            print(
                f"   {course['dataset_id']} | "
                f"{course['course_name']}"
            )
    else:
        print(
            "OK: All 120 records contain complete provenance."
        )

    print()

    # --------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------

    print("=" * 100)
    print("UNIFIED DATASET VALIDATION FINISHED")
    print("=" * 100)


if __name__ == "__main__":

    project_root = (
        Path(__file__).resolve().parent.parent
    )

    json_path = (
        project_root
        / "data"
        / "structured"
        / "unified"
        / "all_courses.json"
    )

    print(f"Reading JSON file: {json_path}")

    if not json_path.exists():
        print("\nERROR: JSON FILE DOES NOT EXIST!")
        print(json_path)
        raise SystemExit(1)

    with json_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        courses = json.load(file)

    validate(courses)
