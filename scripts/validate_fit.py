from pathlib import Path
import json


def is_empty(value):
    """
    Returns True if a value is empty or missing.
    """
    return value is None or value == "" or value == []


def validate_courses(courses):
    """
    Validate the structure and important fields of all courses.
    """

    required_fields = [
        "course_name",
        "degree_level",
        "year_of_study",
        "semester",
        "ects",
        "status",
        "objectives",
        "learning_outcomes",
        "topics",
        "teaching_methods",
        "student_obligations",
        "assessment",
        "literature",
    ]

    print("=" * 80)
    print("FIT DATASET VALIDATION")
    print("=" * 80)

    print(f"Total courses: {len(courses)}")
    print()

    # --------------------------------------------------
    # 1. Check required fields
    # --------------------------------------------------

    print("FIELD COMPLETENESS")
    print("-" * 80)

    for field in required_fields:
        filled = 0
        missing = 0

        for course in courses:
            if is_empty(course.get(field)):
                missing += 1
            else:
                filled += 1

        print(
            f"{field:25} "
            f"Filled: {filled:2} | "
            f"Missing: {missing:2}"
        )

    print()

    # --------------------------------------------------
    # 2. Check duplicate course names
    # --------------------------------------------------

    print("DUPLICATE COURSE NAMES")
    print("-" * 80)

    course_names = [
        course.get("course_name")
        for course in courses
        if course.get("course_name")
    ]

    duplicates = []

    for name in sorted(set(course_names)):
        if course_names.count(name) > 1:
            duplicates.append(name)

    if duplicates:
        for name in duplicates:
            print(f"Duplicate: {name}")
    else:
        print("No duplicate course names found.")

    print()

    # --------------------------------------------------
    # 3. Check invalid values
    # --------------------------------------------------

    print("INVALID VALUES")
    print("-" * 80)

    invalid_courses = False

    for index, course in enumerate(courses, start=1):

        name = course.get("course_name", "UNKNOWN")

        year = course.get("year_of_study")
        semester = course.get("semester")
        ects = course.get("ects")

        if year not in [1, 2, 3]:
            print(
                f"{index}. {name}: "
                f"invalid year_of_study = {year}"
            )
            invalid_courses = True

        if semester not in [1, 2, 3, 4, 5, 6]:
            print(
                f"{index}. {name}: "
                f"invalid semester = {semester}"
            )
            invalid_courses = True

        if ects is None or ects <= 0:
            print(
                f"{index}. {name}: "
                f"invalid ECTS = {ects}"
            )
            invalid_courses = True

    if not invalid_courses:
        print("No invalid year, semester, or ECTS values found.")

    print()

    # --------------------------------------------------
    # 4. Check possible year-semester inconsistencies
    # --------------------------------------------------

    print("POSSIBLE YEAR-SEMESTER INCONSISTENCIES")
    print("-" * 80)

    inconsistencies = []

    for index, course in enumerate(courses, start=1):

        name = course.get("course_name")
        year = course.get("year_of_study")
        semester = course.get("semester")

        expected_year = ((semester - 1) // 2) + 1

        if year != expected_year:
            inconsistencies.append(
                {
                    "index": index,
                    "course_name": name,
                    "year": year,
                    "semester": semester,
                    "expected_year": expected_year,
                }
            )

    if inconsistencies:
        for item in inconsistencies:
            print(
                f"{item['index']}. {item['course_name']} | "
                f"Year: {item['year']} | "
                f"Semester: {item['semester']} | "
                f"Expected year: {item['expected_year']}"
            )
    else:
        print("No year-semester inconsistencies found.")

    print()

    # --------------------------------------------------
    # 5. Check missing course codes
    # --------------------------------------------------

    print("COURSE CODES")
    print("-" * 80)

    missing_codes = 0

    for course in courses:
        if is_empty(course.get("course_code")):
            missing_codes += 1

    print(f"Courses without course code: {missing_codes}")
    print()

    # --------------------------------------------------
    # 6. Check ECTS totals
    # --------------------------------------------------

    print("ECTS SUMMARY")
    print("-" * 80)

    total_ects = sum(
        course.get("ects", 0) or 0
        for course in courses
    )

    print(f"Total ECTS across all listed courses: {total_ects}")
    print()

    # --------------------------------------------------
    # 7. Check empty non-core fields
    # --------------------------------------------------

    print("COURSES WITH MISSING NON-CORE FIELDS")
    print("-" * 80)

    non_core_fields = [
    "prerequisites",
    "learning_outcomes",
    "topics",
    "teaching_methods",
    "student_obligations",
    "assessment",
    "literature",
]

    missing_non_core = False

    for index, course in enumerate(courses, start=1):

        missing_fields = []

        for field in non_core_fields:
            if is_empty(course.get(field)):
                missing_fields.append(field)

        if missing_fields:
            missing_non_core = True

            print(
                f"{index}. {course.get('course_name')}"
            )
            print(
                f"   Missing: {', '.join(missing_fields)}"
            )

    if not missing_non_core:
        print("No missing non-core fields found.")

    print()

    print("=" * 80)
    print("VALIDATION FINISHED")
    print("=" * 80)


if __name__ == "__main__":

    project_root = Path(__file__).resolve().parent.parent

    json_path = (
        project_root
        / "data"
        / "structured"
        / "fit"
        / "fit_courses.json"
    )

    print(f"Reading JSON file: {json_path}")

    with json_path.open("r", encoding="utf-8") as file:
        courses = json.load(file)

    validate_courses(courses)