from pathlib import Path
import json
import re


# ==========================================================
# CONSTANTS
# ==========================================================

INSTITUTION = "Internacionalni Burč univerzitet"
FACULTY = "Fakultet za inžinjering, prirodne i medicinske nauke"
PROGRAM = "Informacijske tehnologije"
SOURCE_FILE = "IBU curriculum BOS.pdf"


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def clean_text(value):
    """Normalize whitespace and common PDF extraction artifacts."""
    if not value:
        return ""

    # Join words broken by PDF soft hyphens.
    value = re.sub(r"\u00ad\s*", "", value)

    # Normalize private-use bullet glyph sometimes produced by PDFs.
    value = value.replace("\uf0b7", "•")

    return re.sub(r"\s+", " ", value).strip()


def normalize_line(line):
    """Normalize a line for easier heading comparisons."""
    return clean_text(line).lower()


def is_extraction_artifact(line):
    """Return True for page markers/headers added by extraction or PDF layout."""
    stripped = clean_text(line)

    if not stripped:
        return False

    if re.fullmatch(r"=+", stripped):
        return True

    if re.fullmatch(r"PAGE\s+\d+", stripped, flags=re.IGNORECASE):
        return True

    # Printed page number/footer from the IBU document.
    if re.fullmatch(r"\d+", stripped):
        return True

    normalized = stripped.lower()

    repeated_headers = [
        "kurikulum odsjeka za informacijskih tehnologija",
        "fakultet za inžinjering, prirodne i medicinske nauke",
    ]

    return any(
        normalized.startswith(header)
        for header in repeated_headers
    )


def roman_to_int(value):
    """Convert a Roman numeral used for years/semesters to int."""
    values = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
    }

    if not value:
        return None

    return values.get(value.strip().upper())


def get_next_non_empty_line(lines, start_index):
    """Return the next non-empty line after start_index."""
    for i in range(start_index + 1, len(lines)):
        value = lines[i].strip()

        if value:
            return value

    return ""


def find_source_page(lines, start_index):
    """
    Find the PAGE marker associated with a course by searching
    backwards from the course start.
    """
    for i in range(start_index, -1, -1):
        match = re.fullmatch(
            r"PAGE\s+(\d+)",
            lines[i].strip(),
            flags=re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

    return None


def find_heading(lines, heading):
    """Find an exact section heading."""
    target = normalize_line(heading)

    for i, line in enumerate(lines):
        if normalize_line(line) == target:
            return i

    return None


def get_section_lines(lines, start_index, stop_headings):
    """
    Collect non-empty lines after a heading until another
    known heading is reached.
    """
    if start_index is None:
        return []

    normalized_stops = {
        normalize_line(heading)
        for heading in stop_headings
    }

    collected = []

    for line in lines[start_index + 1:]:
        stripped = line.strip()

        if not stripped:
            continue

        if is_extraction_artifact(stripped):
            continue

        if normalize_line(stripped) in normalized_stops:
            break

        collected.append(stripped)

    return collected


def get_section_text(lines, start_index, stop_headings):
    """Return one cleaned string for a course section."""
    return clean_text(
        " ".join(
            get_section_lines(
                lines,
                start_index,
                stop_headings,
            )
        )
    )


def parse_topics(lines, start_index, stop_headings):
    """
    Parse weekly IBU course content into a list of topics.

    Example:
        Sedmica 1: Uvod
        Sedmica 2: Baze podataka

    becomes:
        ["Uvod", "Baze podataka"]
    """
    section_lines = get_section_lines(
        lines,
        start_index,
        stop_headings,
    )

    topics = []
    current_topic = None

    for line in section_lines:
        match = re.match(
            r"^(?:Sedmica|Sedmiča|Nedelja)\s+\d+\s*:\s*(.*)$",
            line,
            flags=re.IGNORECASE,
        )

        if match:
            if current_topic:
                topics.append(clean_text(current_topic))

            current_topic = match.group(1).strip()
            continue

        # Continuation of a topic that wrapped onto another PDF line.
        if current_topic is not None:
            current_topic += " " + line

    if current_topic:
        topics.append(clean_text(current_topic))

    return topics


def parse_literature_section(
    lines,
    heading,
    stop_headings,
):
    """
    Literature in the IBU document is not consistently numbered.
    Store the section as one complete bibliographic entry/string
    unless the section is empty or contains only '-'.
    """
    index = find_heading(lines, heading)

    if index is None:
        return []

    value = get_section_text(
        lines,
        index,
        stop_headings,
    )

    if not value or value == "-":
        return []

    return [value]


def get_value_after_heading(lines, heading):
    """
    Return the content after an exact heading.

    Supports:
        Heading value

    and:
        Heading
        value
    """
    target = normalize_line(heading)

    for i, line in enumerate(lines):
        stripped = line.strip()
        normalized = normalize_line(stripped)

        if normalized == target:
            return get_next_non_empty_line(lines, i)

        if normalized.startswith(target + " "):
            return clean_text(
                stripped[len(heading):]
            )

    return ""


# ==========================================================
# COURSE PARSER
# ==========================================================

SECTION_HEADINGS = [
    "Opis predmeta",
    "Ciljevi predmeta",
    "Sadržaj predmeta",
    "Metode podučavanja",
    "Metode evaluacije (%)",
    "Ishodi učenja",
    "Preduslovni predmet(i)",
    "Jezik izvođenja nastave",
    "Obavezna literatura",
    "Preporučena literatura",
    "ECTS (OPTEREĆENJE PO STUDENTU)",
]


def parse_single_course(lines, source_page=None):
    """Parse one IBU course specification."""

    course = {
        "institution": INSTITUTION,
        "faculty": FACULTY,
        "program": PROGRAM,
        "course_name": "",
        "course_code": None,
        "source_code": None,
        "curriculum_table_code": None,
        "code_inconsistency": False,
        "degree_level": "Prvi ciklus",
        "year_of_study": None,
        "semester": None,
        "semester_options": [],
        "ects": None,
        "status": "",
        "prerequisites": None,
        "description": "",
        "objectives": "",
        "learning_outcomes": "",
        "topics": [],
        "teaching_methods": "",
        "student_obligations": None,
        "assessment": "",
        "literature": [],
        "mandatory_literature": [],
        "recommended_literature": [],
        "language": None,
        "source_file": SOURCE_FILE,
        "source_page": source_page,
    }

    # ------------------------------------------------------
    # COURSE CODE + NAME
    # ------------------------------------------------------

    course_start_index = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped.startswith("Šifra predmeta:"):
            continue

        course_start_index = i

        code_match = re.search(
            r"Šifra\s+predmeta:\s*([A-Za-z]+)\s*(\d+)",
            stripped,
            flags=re.IGNORECASE,
        )

        if code_match:
            course["course_code"] = clean_text(
                f"{code_match.group(1).upper()} {code_match.group(2)}"
            )

        break

    if course_start_index is not None:
        course_name = get_next_non_empty_line(
            lines,
            course_start_index,
        )

        # In case code and course name are extracted on the same line.
        same_line = lines[course_start_index].strip()

        if course["course_code"]:
            after_code = re.sub(
                r"^Šifra\s+predmeta:\s*"
                + re.escape(course["course_code"])
                + r"\s*",
                "",
                same_line,
                flags=re.IGNORECASE,
            ).strip()

            if after_code:
                course_name = after_code

        course["course_name"] = clean_text(course_name)

    # ------------------------------------------------------
    # COURSE CODE PROVENANCE / CONSISTENCY
    # ------------------------------------------------------

    # Preserve the code exactly as it appears in the detailed
    # course specification.
    course["source_code"] = course["course_code"]

    # By default, the curriculum table and the detailed
    # specification are assumed to use the same code.
    course["curriculum_table_code"] = course["course_code"]

    # Source inconsistency documented in the IBU curriculum:
    # - the programme elective table lists
    #   "Uvod u evolucijsko računanje" as IT 3027
    # - the detailed specification lists it as IT 3030
    #
    # We do NOT silently overwrite course_code because the
    # detailed specification is the source record being parsed.
    # Instead, both values are preserved explicitly.
    if (
        normalize_line(course["course_name"])
        == normalize_line("UVOD U EVOLUCIJSKO RAČUNANJE")
        and course["course_code"] == "IT 3030"
    ):
        course["curriculum_table_code"] = "IT 3027"
        course["code_inconsistency"] = True

    # ------------------------------------------------------
    # YEAR
    # ------------------------------------------------------

    full_text = "\n".join(lines)

    year_match = re.search(
        r"Godina:\s*([IVX]+)",
        full_text,
        flags=re.IGNORECASE,
    )

    if year_match:
        course["year_of_study"] = roman_to_int(
            year_match.group(1)
        )

    # ------------------------------------------------------
    # SEMESTER / SEMESTER OPTIONS
    # ------------------------------------------------------

    semester_match = re.search(
        r"Semestar:\s*([IVX]+(?:\s*,\s*[IVX]+)*)",
        full_text,
        flags=re.IGNORECASE,
    )

    if semester_match:
        raw_semesters = re.findall(
            r"[IVX]+",
            semester_match.group(1),
            flags=re.IGNORECASE,
        )

        semester_options = [
            roman_to_int(value)
            for value in raw_semesters
        ]

        semester_options = [
            value
            for value in semester_options
            if value is not None
        ]

        course["semester_options"] = semester_options

        if len(semester_options) == 1:
            course["semester"] = semester_options[0]

    # ------------------------------------------------------
    # ECTS
    # ------------------------------------------------------

    ects_match = re.search(
        r"ECTS\s+(?:bodovi|bodova|Krediti)\s*:\s*(\d+(?:[.,]\d+)?)",
        full_text,
        flags=re.IGNORECASE,
    )

    if ects_match:
        course["ects"] = float(
            ects_match.group(1).replace(",", ".")
        )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    status_match = re.search(
        r"Status:\s*([^\n]+)",
        full_text,
        flags=re.IGNORECASE,
    )

    if status_match:
        course["status"] = clean_text(
            status_match.group(1)
        )

    # ------------------------------------------------------
    # DESCRIPTION
    # ------------------------------------------------------

    description_index = find_heading(
        lines,
        "Opis predmeta",
    )

    course["description"] = get_section_text(
        lines,
        description_index,
        [
            "Ciljevi predmeta",
        ],
    )

    # ------------------------------------------------------
    # OBJECTIVES
    # ------------------------------------------------------

    objectives_index = find_heading(
        lines,
        "Ciljevi predmeta",
    )

    course["objectives"] = get_section_text(
        lines,
        objectives_index,
        [
            "Sadržaj predmeta",
        ],
    )

    # ------------------------------------------------------
    # TOPICS
    # ------------------------------------------------------

    topics_index = find_heading(
        lines,
        "Sadržaj predmeta",
    )

    course["topics"] = parse_topics(
        lines,
        topics_index,
        [
            "Metode podučavanja",
        ],
    )

    # ------------------------------------------------------
    # TEACHING METHODS
    # ------------------------------------------------------

    teaching_index = find_heading(
        lines,
        "Metode podučavanja",
    )

    course["teaching_methods"] = get_section_text(
        lines,
        teaching_index,
        [
            "Metode evaluacije (%)",
        ],
    )

    # ------------------------------------------------------
    # ASSESSMENT
    # ------------------------------------------------------

    assessment_index = find_heading(
        lines,
        "Metode evaluacije (%)",
    )

    course["assessment"] = get_section_text(
        lines,
        assessment_index,
        [
            "Ishodi učenja",
        ],
    )

    # ------------------------------------------------------
    # LEARNING OUTCOMES
    # ------------------------------------------------------

    outcomes_index = find_heading(
        lines,
        "Ishodi učenja",
    )

    course["learning_outcomes"] = get_section_text(
        lines,
        outcomes_index,
        [
            "Preduslovni predmet(i)",
        ],
    )

    # ------------------------------------------------------
    # PREREQUISITES
    # ------------------------------------------------------

    prerequisites_index = find_heading(
        lines,
        "Preduslovni predmet(i)",
    )

    prerequisite_text = get_section_text(
        lines,
        prerequisites_index,
        [
            "Jezik izvođenja nastave",
        ],
    )

    if prerequisite_text and prerequisite_text != "-":
        course["prerequisites"] = prerequisite_text

    # ------------------------------------------------------
    # LANGUAGE
    # ------------------------------------------------------

    language_index = find_heading(
        lines,
        "Jezik izvođenja nastave",
    )

    language_text = get_section_text(
        lines,
        language_index,
        [
            "Obavezna literatura",
        ],
    )

    if language_text and language_text != "-":
        course["language"] = language_text

    # ------------------------------------------------------
    # LITERATURE
    # ------------------------------------------------------

    mandatory = parse_literature_section(
        lines,
        "Obavezna literatura",
        [
            "Preporučena literatura",
        ],
    )

    recommended = parse_literature_section(
        lines,
        "Preporučena literatura",
        [
            "ECTS (OPTEREĆENJE PO STUDENTU)",
        ],
    )

    course["mandatory_literature"] = mandatory
    course["recommended_literature"] = recommended

    course["literature"] = mandatory + [
        item
        for item in recommended
        if item not in mandatory
    ]

    # ------------------------------------------------------
    # FINAL CLEANUP
    # ------------------------------------------------------

    text_fields = [
        "course_name",
        "degree_level",
        "status",
        "description",
        "objectives",
        "learning_outcomes",
        "teaching_methods",
        "assessment",
    ]

    for field in text_fields:
        course[field] = clean_text(course[field])

    return course


# ==========================================================
# PARSE ALL COURSES
# ==========================================================

def parse_courses(text):
    """
    Split the IBU extracted TXT into detailed course specifications.

    Only detailed specifications beginning with "Šifra predmeta:"
    are treated as course records. Curriculum-table placeholders such
    as "XXX xxx Izborni kurs" are therefore not created as fake courses.
    """

    lines = text.splitlines()

    course_starts = []

    for i, line in enumerate(lines):
        if line.strip().startswith("Šifra predmeta:"):
            course_starts.append(i)

    print(f"Found {len(course_starts)} detailed course starts")

    courses = []

    for index, start in enumerate(course_starts):
        if index + 1 < len(course_starts):
            end = course_starts[index + 1]
        else:
            end = len(lines)

        course_lines = lines[start:end]

        source_page = find_source_page(
            lines,
            start,
        )

        course = parse_single_course(
            course_lines,
            source_page=source_page,
        )

        if course["course_name"]:
            courses.append(course)

    print(f"Found {len(courses)} detailed courses")

    return courses


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("IBU PARSER STARTED")

    project_root = Path(__file__).resolve().parent.parent

    input_path = (
        project_root
        / "data"
        / "extracted"
        / "ibu"
        / "IBU curriculum BOS.txt"
    )

    output_path = (
        project_root
        / "data"
        / "structured"
        / "ibu"
        / "ibu_courses.json"
    )

    print(f"Project root: {project_root}")
    print(f"Input path: {input_path}")

    if not input_path.exists():
        print("\nERROR: INPUT FILE DOES NOT EXIST!")
        print(input_path)
        raise SystemExit(1)

    text = input_path.read_text(
        encoding="utf-8"
    )

    print(
        f"Input file read successfully: "
        f"{len(text)} characters"
    )

    courses = parse_courses(text)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            courses,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    print(f"JSON dataset saved to: {output_path}")

    print("\n" + "=" * 100)
    print("ALL IBU DETAILED COURSES")
    print("=" * 100)
    print(f"Found {len(courses)} courses\n")

    for number, course in enumerate(
        courses,
        start=1,
    ):
        semester_display = (
            course["semester"]
            if course["semester"] is not None
            else course["semester_options"]
        )

        print(
            f"{number:2}. "
            f"{course['course_code']} | "
            f"{course['course_name']} | "
            f"Year: {course['year_of_study']} | "
            f"Semester: {semester_display} | "
            f"ECTS: {course['ects']} | "
            f"Status: {course['status']} | "
            f"Page: {course['source_page']}"
            + (
                f" | TABLE CODE: {course['curriculum_table_code']} "
                f"| CODE INCONSISTENCY"
                if course["code_inconsistency"]
                else ""
            )
        )

    print("\n" + "=" * 100)
    print("IBU PARSER FINISHED")
    print("=" * 100)
