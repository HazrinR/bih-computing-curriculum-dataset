from pathlib import Path
import json
from collections import Counter


CORE_FIELDS = [
    "institution",
    "faculty",
    "program",
    "course_name",
    "course_code",
    "degree_level",
    "year_of_study",
    "semester",
    "ects",
    "status",
    "learning_outcomes",
    "topics",
    "teaching_methods",
    "assessment",
    "source_file",
    "source_page",
    "source_name",
    "source_code",
    "curriculum_table_name",
    "curriculum_table_code",
    "source_year_of_study",
    "curriculum_table_year_of_study",
    "source_semester",
    "curriculum_table_semester",
    "source_ects",
    "curriculum_table_ects",
    "has_source_inconsistency",
]

OPTIONAL_FIELDS = [
    "prerequisites",
    "description",
    "objectives",
    "student_obligations",
    "literature",
    "recommended_literature",
    "additional_literature",
    "language",
    "program_source_value",
    "lecture_hours",
    "laboratory_hours",
    "tutorial_hours",
    "self_study_hours",
]


def is_empty(value):
    return value is None or value == "" or value == []


def validate_courses(courses):

    print("=" * 105)
    print("ETF DATASET VALIDATION")
    print("=" * 105)
    print(f"Total detailed courses: {len(courses)}")
    print()

    # --------------------------------------------------
    # 1. FIELD COMPLETENESS
    # --------------------------------------------------

    print("FIELD COMPLETENESS")
    print("-" * 105)

    for field in CORE_FIELDS + OPTIONAL_FIELDS:

        filled = sum(
            1
            for course in courses
            if not is_empty(course.get(field))
        )

        missing = len(courses) - filled

        print(
            f"{field:25} "
            f"Filled: {filled:2} | "
            f"Missing: {missing:2}"
        )

    print()

    # --------------------------------------------------
    # 2. DUPLICATE NAMES
    # --------------------------------------------------

    print("DUPLICATE COURSE NAMES")
    print("-" * 105)

    names = [
        course.get("course_name")
        for course in courses
        if course.get("course_name")
    ]

    duplicate_names = [
        name
        for name, count in Counter(names).items()
        if count > 1
    ]

    if duplicate_names:
        for name in sorted(duplicate_names):
            print(f"Duplicate course name: {name}")
    else:
        print("No duplicate course names found.")

    print()

    # --------------------------------------------------
    # 3. DUPLICATE CODES
    # --------------------------------------------------

    print("DUPLICATE COURSE CODES")
    print("-" * 105)

    codes = [
        course.get("course_code")
        for course in courses
        if course.get("course_code")
    ]

    duplicate_codes = [
        code
        for code, count in Counter(codes).items()
        if count > 1
    ]

    if duplicate_codes:
        for code in sorted(duplicate_codes):

            print(f"\nDuplicate code: {code}")

            for course in courses:
                if course.get("course_code") == code:
                    print(
                        f"   {course['course_name']} "
                        f"| Page: {course['source_page']}"
                    )
    else:
        print("No duplicate course codes found.")

    print()

    # --------------------------------------------------
    # 4. INVALID VALUES
    # --------------------------------------------------

    print("INVALID OR SUSPICIOUS VALUES")
    print("-" * 105)

    issues = []

    for index, course in enumerate(courses, start=1):

        name = course.get("course_name", "UNKNOWN")
        year = course.get("year_of_study")
        semester = course.get("semester")
        ects = course.get("ects")
        page = course.get("source_page")

        if year not in [1, 2, 3]:
            issues.append(
                f"{index}. {name}: invalid year_of_study = {year}"
            )

        if semester not in [1, 2, 3, 4, 5, 6]:
            issues.append(
                f"{index}. {name}: invalid semester = {semester}"
            )

        if ects is None or ects <= 0:
            issues.append(
                f"{index}. {name}: invalid ECTS = {ects}"
            )

        if page is None:
            issues.append(
                f"{index}. {name}: source_page is missing"
            )

    if issues:
        for issue in issues:
            print(issue)
    else:
        print(
            "No invalid year, semester, ECTS, or source_page values found."
        )

    print()

    # --------------------------------------------------
    # 5. YEAR / SEMESTER CONSISTENCY
    # --------------------------------------------------

    print("YEAR-SEMESTER CONSISTENCY")
    print("-" * 105)

    inconsistencies = []

    for index, course in enumerate(courses, start=1):

        year = course.get("year_of_study")
        semester = course.get("semester")

        if semester in [1, 2, 3, 4, 5, 6]:

            expected_year = ((semester - 1) // 2) + 1

            if year != expected_year:
                inconsistencies.append(
                    (
                        index,
                        course.get("course_name"),
                        year,
                        semester,
                        expected_year,
                    )
                )

    if inconsistencies:
        for item in inconsistencies:
            print(
                f"{item[0]}. {item[1]} | "
                f"Year: {item[2]} | "
                f"Semester: {item[3]} | "
                f"Expected year: {item[4]}"
            )
    else:
        print("No year-semester inconsistencies found.")

    print()

    # --------------------------------------------------
    # 6. STATUS SUMMARY
    # --------------------------------------------------

    print("STATUS SUMMARY")
    print("-" * 105)

    status_counts = Counter(
        course.get("status")
        for course in courses
    )

    for status, count in sorted(
        status_counts.items(),
        key=lambda item: str(item[0]),
    ):
        print(f"{status}: {count}")

    print()

    # --------------------------------------------------
    # 7. ECTS SUMMARY
    # --------------------------------------------------

    print("ECTS SUMMARY")
    print("-" * 105)

    total_ects = sum(
        course.get("ects", 0) or 0
        for course in courses
    )

    print(
        f"Sum of ECTS across all detailed course records: {total_ects}"
    )

    print(
        "NOTE: This is not the programme ECTS total because the "
        "dataset includes elective alternatives."
    )

    print()

    # --------------------------------------------------
    # 8. IMPORTANT MISSING FIELDS
    # --------------------------------------------------

    print("COURSES WITH IMPORTANT MISSING FIELDS")
    print("-" * 105)

    important_fields = [
        "learning_outcomes",
        "topics",
        "teaching_methods",
        "assessment",
        "literature",
    ]

    problem_count = 0

    for index, course in enumerate(courses, start=1):

        missing = [
            field
            for field in important_fields
            if is_empty(course.get(field))
        ]

        if missing:
            problem_count += 1

            print(
                f"{index}. {course['course_code']} | "
                f"{course['course_name']}"
            )

            print(
                f"   Missing: {', '.join(missing)}"
            )

    if problem_count == 0:
        print("No important fields are missing.")

    print()

    # --------------------------------------------------
    # 9. PREREQUISITES SUMMARY
    # --------------------------------------------------

    print("PREREQUISITES SUMMARY")
    print("-" * 105)

    with_prerequisites = [
        course
        for course in courses
        if not is_empty(course.get("prerequisites"))
    ]

    without_prerequisites = (
        len(courses) - len(with_prerequisites)
    )

    print(
        f"Courses with prerequisite text: {len(with_prerequisites)}"
    )

    print(
        f"Courses without prerequisite text: {without_prerequisites}"
    )

    print()

    # --------------------------------------------------
    # 10. SOURCE PROGRAM VALUES
    # --------------------------------------------------

    print("PROGRAM SOURCE VALUES")
    print("-" * 105)

    program_values = Counter(
        course.get("program_source_value")
        for course in courses
    )

    for value, count in sorted(
        program_values.items(),
        key=lambda item: str(item[0]),
    ):
        print(f"{value}: {count}")

    print()

    # --------------------------------------------------
    # 11. SOURCE INCONSISTENCIES
    # --------------------------------------------------

    print("SOURCE INCONSISTENCIES")
    print("-" * 105)

    inconsistent_courses = [
        course
        for course in courses
        if course.get("has_source_inconsistency")
    ]

    print(
        f"Courses with source inconsistencies: "
        f"{len(inconsistent_courses)}"
    )

    if inconsistent_courses:
        print()

        for course in inconsistent_courses:
            print(
                f"{course['course_code']} | "
                f"{course['course_name']} | "
                f"Page: {course['source_page']}"
            )

            for issue in course.get(
                "source_inconsistencies",
                [],
            ):
                print(f"   - {issue}")

            if (
                course.get("source_code")
                != course.get("curriculum_table_code")
            ):
                print(
                    f"     Detail code: "
                    f"{course.get('source_code')}"
                )
                print(
                    f"     Table code:  "
                    f"{course.get('curriculum_table_code')}"
                )

            if (
                course.get("source_year_of_study")
                != course.get(
                    "curriculum_table_year_of_study"
                )
            ):
                print(
                    f"     Detail year: "
                    f"{course.get('source_year_of_study')}"
                )
                print(
                    f"     Table year:  "
                    f"{course.get('curriculum_table_year_of_study')}"
                )

            if (
                course.get("source_semester")
                != course.get(
                    "curriculum_table_semester"
                )
            ):
                print(
                    f"     Detail semester: "
                    f"{course.get('source_semester')}"
                )
                print(
                    f"     Table semester:  "
                    f"{course.get('curriculum_table_semester')}"
                )

            if (
                course.get("source_ects")
                != course.get("curriculum_table_ects")
            ):
                print(
                    f"     Detail ECTS: "
                    f"{course.get('source_ects')}"
                )
                print(
                    f"     Table ECTS:  "
                    f"{course.get('curriculum_table_ects')}"
                )

            if (
                course.get("source_name")
                != course.get("curriculum_table_name")
            ):
                print(
                    f"     Detail name: "
                    f"{course.get('source_name')}"
                )
                print(
                    f"     Table name:  "
                    f"{course.get('curriculum_table_name')}"
                )

            print()

    else:
        print("No source inconsistencies found.")

    print()

    # --------------------------------------------------
    # 12. PROVENANCE
    # --------------------------------------------------

    print("PROVENANCE CHECK")
    print("-" * 105)

    missing_provenance = [
        course
        for course in courses
        if (
            is_empty(course.get("institution"))
            or is_empty(course.get("faculty"))
            or is_empty(course.get("program"))
            or is_empty(course.get("source_file"))
            or course.get("source_page") is None
            or is_empty(course.get("source_name"))
            or is_empty(course.get("source_code"))
            or is_empty(course.get("curriculum_table_name"))
            or is_empty(course.get("curriculum_table_code"))
        )
    ]

    if missing_provenance:

        for course in missing_provenance:
            print(
                f"{course.get('course_code')} | "
                f"{course.get('course_name')}"
            )
    else:
        print(
            "All courses contain institution, faculty, program, "
            "source file, and source page."
        )

    print()

    print("=" * 105)
    print("VALIDATION FINISHED")
    print("=" * 105)


if __name__ == "__main__":

    project_root = Path(__file__).resolve().parent.parent

    json_path = (
        project_root
        / "data"
        / "structured"
        / "etf"
        / "etf_courses.json"
    )

    print(f"Reading JSON file: {json_path}")

    if not json_path.exists():
        print("\nERROR: JSON FILE DOES NOT EXIST!")
        print(json_path)
        raise SystemExit(1)

    with json_path.open("r", encoding="utf-8") as file:
        courses = json.load(file)

    validate_courses(courses)
