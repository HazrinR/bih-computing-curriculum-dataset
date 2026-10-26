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
    "ects",
    "status",
    "description",
    "objectives",
    "learning_outcomes",
    "topics",
    "teaching_methods",
    "assessment",
    "source_file",
    "source_page",
]

OPTIONAL_FIELDS = [
    "prerequisites",
    "student_obligations",
    "literature",
    "mandatory_literature",
    "recommended_literature",
    "language",
]


def is_empty(value):
    return value is None or value == "" or value == []


def validate_courses(courses):
    print("=" * 100)
    print("IBU DATASET VALIDATION")
    print("=" * 100)
    print(f"Total detailed courses: {len(courses)}")
    print()

    # --------------------------------------------------
    # 1. Field completeness
    # --------------------------------------------------

    print("FIELD COMPLETENESS")
    print("-" * 100)

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
    # 2. Duplicate course names
    # --------------------------------------------------

    print("DUPLICATE COURSE NAMES")
    print("-" * 100)

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
    # 3. Duplicate course codes
    # --------------------------------------------------

    print("DUPLICATE COURSE CODES")
    print("-" * 100)

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
    # 4. Invalid / suspicious values
    # --------------------------------------------------

    print("INVALID OR SUSPICIOUS VALUES")
    print("-" * 100)

    issues = []

    for index, course in enumerate(courses, start=1):
        name = course.get("course_name", "UNKNOWN")
        year = course.get("year_of_study")
        semester = course.get("semester")
        semester_options = course.get("semester_options") or []
        ects = course.get("ects")
        source_page = course.get("source_page")

        if year not in [1, 2, 3]:
            issues.append(
                f"{index}. {name}: invalid year_of_study = {year}"
            )

        if semester is not None and semester not in [1, 2, 3, 4, 5, 6]:
            issues.append(
                f"{index}. {name}: invalid semester = {semester}"
            )

        for option in semester_options:
            if option not in [1, 2, 3, 4, 5, 6]:
                issues.append(
                    f"{index}. {name}: invalid semester option = {option}"
                )

        if semester is None and not semester_options:
            issues.append(
                f"{index}. {name}: no semester information"
            )

        if ects is None or ects <= 0:
            issues.append(
                f"{index}. {name}: invalid ECTS = {ects}"
            )

        if source_page is None:
            issues.append(
                f"{index}. {name}: source_page is missing"
            )

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("No invalid year, semester, ECTS, or source_page values found.")

    print()

    # --------------------------------------------------
    # 5. Year-semester consistency
    # --------------------------------------------------

    print("YEAR-SEMESTER CONSISTENCY")
    print("-" * 100)

    inconsistencies = []

    for index, course in enumerate(courses, start=1):
        year = course.get("year_of_study")
        semester = course.get("semester")
        semester_options = course.get("semester_options") or []

        semesters_to_check = (
            [semester]
            if semester is not None
            else semester_options
        )

        for sem in semesters_to_check:
            expected_year = ((sem - 1) // 2) + 1

            if year != expected_year:
                inconsistencies.append(
                    (
                        index,
                        course.get("course_name"),
                        year,
                        sem,
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
    # 6. Courses with multiple semester options
    # --------------------------------------------------

    print("COURSES WITH MULTIPLE SEMESTER OPTIONS")
    print("-" * 100)

    multiple_semester_courses = [
        course
        for course in courses
        if len(course.get("semester_options") or []) > 1
    ]

    if multiple_semester_courses:
        for course in multiple_semester_courses:
            print(
                f"{course['course_code']} | "
                f"{course['course_name']} | "
                f"Semesters: {course['semester_options']} | "
                f"Page: {course['source_page']}"
            )
    else:
        print("No courses with multiple semester options.")

    print()

    # --------------------------------------------------
    # 7. Status summary
    # --------------------------------------------------

    print("STATUS SUMMARY")
    print("-" * 100)

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
    # 8. ECTS summary
    # --------------------------------------------------

    print("ECTS SUMMARY")
    print("-" * 100)

    total_ects = sum(
        course.get("ects", 0) or 0
        for course in courses
    )

    print(f"Sum of ECTS across all detailed course records: {total_ects}")
    print(
        "NOTE: This is not the programme ECTS total because the "
        "dataset includes elective alternatives."
    )

    print()

    # --------------------------------------------------
    # 9. Important missing fields
    # --------------------------------------------------

    print("COURSES WITH IMPORTANT MISSING FIELDS")
    print("-" * 100)

    important_fields = [
        "description",
        "objectives",
        "learning_outcomes",
        "topics",
        "teaching_methods",
        "assessment",
        "literature",
        "language",
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
            print(f"   Missing: {', '.join(missing)}")

    if problem_count == 0:
        print("No important fields are missing.")

    print()

    # --------------------------------------------------
    # 10. Provenance
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
        for course in missing_provenance:
            print(
                f"{course.get('course_code')} | "
                f"{course.get('course_name')}"
            )
    else:
        print("All courses contain institution, faculty, program, source file, and source page.")

    print()
    print("=" * 100)
    print("VALIDATION FINISHED")
    print("=" * 100)


if __name__ == "__main__":

    project_root = Path(__file__).resolve().parent.parent

    json_path = (
        project_root
        / "data"
        / "structured"
        / "ibu"
        / "ibu_courses.json"
    )

    print(f"Reading JSON file: {json_path}")

    if not json_path.exists():
        print("\nERROR: JSON FILE DOES NOT EXIST!")
        print(json_path)
        raise SystemExit(1)

    with json_path.open("r", encoding="utf-8") as file:
        courses = json.load(file)

    validate_courses(courses)
