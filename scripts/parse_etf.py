from pathlib import Path
import json
import re


# ==========================================================
# CONSTANTS
# ==========================================================

INSTITUTION = "Univerzitet u Sarajevu"
FACULTY = "Elektrotehnički fakultet"
PROGRAM = "Računarstvo i informatika"
SOURCE_FILE = "ETF curriculum BOS.pdf"


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def clean_text(value):
    """Normalize whitespace and common PDF extraction artifacts."""
    if not value:
        return ""

    value = value.replace("\uFFFd", "")

    # Join words broken by PDF soft hyphens, including a line break/space.
    value = re.sub(r"\u00ad\s*", "", value)

    # Normalize private-use bullet glyph produced by the PDF font.
    value = value.replace("\uf0b7", "•")

    return re.sub(r"\s+", " ", value).strip()


def normalize_line(line):
    """Normalize text for heading comparisons."""
    return clean_text(line).lower()


def is_extraction_artifact(line):
    """Return True for page markers/footers that are not course content."""
    stripped = clean_text(line)

    if not stripped:
        return False

    if re.fullmatch(r"=+", stripped):
        return True

    if re.fullmatch(r"PAGE\s+\d+", stripped, flags=re.IGNORECASE):
        return True

    # Printed ETF footer such as 24/98.
    if re.fullmatch(r"\d+\s*/\s*\d+", stripped):
        return True

    return False


def find_source_page(lines, start_index):
    """
    Find the PAGE marker associated with a module by searching
    backwards from the module start.
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
    """
    Find a heading that may appear:
      - alone on one line
      - followed by its value on the same line
    """
    target = normalize_line(heading)

    for i, line in enumerate(lines):
        normalized = normalize_line(line)

        if normalized == target:
            return i

        if normalized.startswith(target + " "):
            return i

    return None


def find_split_heading(lines, heading):
    """
    Find headings split over up to three PDF-extracted lines.

    Example:
        Laboratorijske
        vježbe
    """
    target = normalize_line(heading)

    for i in range(len(lines)):
        combined = ""

        for j in range(i, min(i + 3, len(lines))):
            if not lines[j].strip():
                continue

            combined = clean_text(
                combined + " " + lines[j]
            )

            normalized = normalize_line(combined)

            if normalized == target:
                return i, j

            if normalized.startswith(target + " "):
                return i, j

            if len(normalized) > len(target) + 80:
                break

    return None, None


def get_value_after_label(lines, label):
    """
    Extract a metadata value for ETF table-like module headers.

    Handles:
        Godina studija
        1

    and:
        Godina studija 1
    """
    target = normalize_line(label)

    for i, line in enumerate(lines):
        stripped = line.strip()
        normalized = normalize_line(stripped)

        if normalized == target:
            for j in range(i + 1, len(lines)):
                candidate = lines[j].strip()

                if candidate:
                    return clean_text(candidate)

            return ""

        if normalized.startswith(target + " "):
            value = stripped[len(label):].strip()

            if value:
                return clean_text(value)

    return ""


def get_value_after_split_label(lines, label):
    """
    Extract a value when a label itself may be split over lines.
    """
    start, end = find_split_heading(lines, label)

    if start is None:
        return ""

    # If the last heading line already contains the value after
    # the complete label, attempt to extract it.
    combined_heading = clean_text(
        " ".join(lines[start:end + 1])
    )

    target = clean_text(label)

    if normalize_line(combined_heading).startswith(
        normalize_line(target) + " "
    ):
        value = combined_heading[len(target):].strip()

        if value:
            return clean_text(value)

    for i in range(end + 1, len(lines)):
        candidate = lines[i].strip()

        if candidate:
            return clean_text(candidate)

    return ""


def get_section_lines(lines, start_index, stop_headings):
    """
    Collect lines after a section heading until another known
    section heading is reached.
    """
    if start_index is None:
        return []

    normalized_stops = [
        normalize_line(value)
        for value in stop_headings
    ]

    collected = []

    for line in lines[start_index + 1:]:
        stripped = line.strip()

        if not stripped:
            continue

        if is_extraction_artifact(stripped):
            continue

        normalized = normalize_line(stripped)

        should_stop = any(
            normalized == stop
            or normalized.startswith(stop + " ")
            for stop in normalized_stops
        )

        if should_stop:
            break

        collected.append(stripped)

    return collected


def get_section_text(lines, start_index, stop_headings):
    """Return one cleaned string for a section."""
    if start_index is None:
        return ""

    # Some headings have content on the same line.
    heading_line = lines[start_index].strip()
    same_line_content = ""

    for possible_heading in [
        "Ishodi modula",
        "Sadržaj modula",
        "Didaktičke metode",
        "Provjera znanja",
        "Preduvjeti",
    ]:
        normalized_heading = normalize_line(possible_heading)

        if normalize_line(heading_line).startswith(
            normalized_heading + " "
        ):
            same_line_content = heading_line[
                len(possible_heading):
            ].strip()
            break

    section_lines = get_section_lines(
        lines,
        start_index,
        stop_headings,
    )

    parts = []

    if same_line_content:
        parts.append(same_line_content)

    parts.extend(section_lines)

    return clean_text(" ".join(parts))


def parse_numbered_items(raw_lines):
    """
    Parse numbered items where a reference/topic may span
    multiple extracted lines.

    If numbering cannot be recognized, preserve the section
    as one text entry rather than discarding source content.
    """
    items = []
    current = None

    for line in raw_lines:
        stripped = line.strip()

        if not stripped:
            continue

        match = re.match(
            r"^(\d+)\.\s*(.*)$",
            stripped,
        )

        if match:
            if current:
                items.append(clean_text(current))

            current = match.group(2).strip()
            continue

        if current is not None:
            current += " " + stripped
        else:
            current = stripped

    if current:
        items.append(clean_text(current))

    return [
        item
        for item in items
        if item
    ]


def parse_topics(lines, start_index, stop_headings):
    """Parse numbered ETF module content into topic entries."""
    raw_lines = get_section_lines(
        lines,
        start_index,
        stop_headings,
    )

    return parse_numbered_items(raw_lines)


def parse_literature(lines):
    """
    Parse recommended and additional literature.

    ETF literature sections generally look like:
        Literatura
        Preporučena
        1. ...
        2. ...
        Dodatna
        1. ...
    """
    literature_index = find_heading(
        lines,
        "Literatura",
    )

    if literature_index is None:
        return [], []

    recommended = []
    additional = []

    recommended_index = find_heading(
        lines,
        "Preporučena",
    )

    additional_index = find_heading(
        lines,
        "Dodatna",
    )

    if recommended_index is not None:
        recommended_lines = get_section_lines(
            lines,
            recommended_index,
            [
                "Dodatna",
                "Didaktičke metode",
                "Provjera znanja",
                "Preduvjeti",
            ],
        )

        recommended = parse_numbered_items(
            recommended_lines
        )

    if additional_index is not None:
        additional_lines = get_section_lines(
            lines,
            additional_index,
            [
                "Didaktičke metode",
                "Provjera znanja",
                "Preduvjeti",
            ],
        )

        additional = parse_numbered_items(
            additional_lines
        )

    return recommended, additional


def to_int(value):
    """Convert simple numeric text to int when possible."""
    if not value:
        return None

    match = re.search(r"-?\d+", value)

    if not match:
        return None

    return int(match.group(0))


def to_float(value):
    """Convert a numeric value with comma or dot decimal separator."""
    if not value:
        return None

    match = re.search(
        r"\d+(?:[.,]\d+)?",
        value,
    )

    if not match:
        return None

    return float(
        match.group(0).replace(",", ".")
    )


# ==========================================================
# PARSE ONE MODULE
# ==========================================================

def parse_single_module(lines, source_page=None):
    """Parse one detailed ETF module specification."""

    course = {
        "institution": INSTITUTION,
        "faculty": FACULTY,
        "program": PROGRAM,
        "course_name": "",
        "course_code": None,
        "source_name": None,
        "source_code": None,
        "curriculum_table_name": None,
        "curriculum_table_code": None,
        "source_year_of_study": None,
        "curriculum_table_year_of_study": None,
        "source_semester": None,
        "curriculum_table_semester": None,
        "source_ects": None,
        "curriculum_table_ects": None,
        "has_source_inconsistency": False,
        "source_inconsistencies": [],
        "degree_level": "Bachelor / prvi ciklus",
        "year_of_study": None,
        "semester": None,
        "ects": None,
        "status": "",
        "prerequisites": None,
        "description": None,
        "objectives": None,
        "learning_outcomes": "",
        "topics": [],
        "teaching_methods": "",
        "student_obligations": None,
        "assessment": "",
        "literature": [],
        "recommended_literature": [],
        "additional_literature": [],
        "language": None,
        "program_source_value": None,
        "lecture_hours": None,
        "laboratory_hours": None,
        "tutorial_hours": None,
        "self_study_hours": None,
        "source_file": SOURCE_FILE,
        "source_page": source_page,
    }

    # ------------------------------------------------------
    # BASIC HEADER FIELDS
    # ------------------------------------------------------

    course["course_name"] = get_value_after_label(
        lines,
        "Naziv modula",
    )

    course_code = get_value_after_label(
        lines,
        "Šifra modula",
    )

    if course_code:
        # Normalize different dash characters while preserving
        # the source code content.
        course_code = (
            course_code
            .replace("–", "-")
            .replace("—", "-")
        )

        course["course_code"] = clean_text(
            course_code
        )

    program_value = get_value_after_label(
        lines,
        "Program",
    )

    if program_value:
        course["program_source_value"] = program_value

    course["year_of_study"] = to_int(
        get_value_after_label(
            lines,
            "Godina studija",
        )
    )

    course["semester"] = to_int(
        get_value_after_label(
            lines,
            "Semestar",
        )
    )

    course["status"] = clean_text(
        get_value_after_label(
            lines,
            "Tip modula",
        )
    )

    course["ects"] = to_float(
        get_value_after_label(
            lines,
            "ECTS",
        )
    )

    course["lecture_hours"] = to_int(
        get_value_after_label(
            lines,
            "Predavanja",
        )
    )

    course["laboratory_hours"] = to_int(
        get_value_after_split_label(
            lines,
            "Laboratorijske vježbe",
        )
    )

    course["tutorial_hours"] = to_int(
        get_value_after_label(
            lines,
            "Tutorijali",
        )
    )

    course["self_study_hours"] = to_int(
        get_value_after_split_label(
            lines,
            "Opterećenje – samostalni rad",
        )
    )

    # ------------------------------------------------------
    # SOURCE / CURRICULUM TABLE CONSISTENCY
    # ------------------------------------------------------

    # Preserve values from the detailed module specification.
    course["source_name"] = course["course_name"]
    course["source_code"] = course["course_code"]
    course["source_year_of_study"] = course["year_of_study"]
    course["source_semester"] = course["semester"]
    course["source_ects"] = course["ects"]

    # By default, assume the overview curriculum table agrees
    # with the detailed module specification.
    course["curriculum_table_name"] = course["course_name"]
    course["curriculum_table_code"] = course["course_code"]
    course["curriculum_table_year_of_study"] = course["year_of_study"]
    course["curriculum_table_semester"] = course["semester"]
    course["curriculum_table_ects"] = course["ects"]

    # Document known inconsistencies between the curriculum
    # overview tables (PDF pages 2-6) and detailed module
    # specifications. We do NOT silently overwrite the detailed
    # specification values.
    table_overrides = {
        "Inženjerska matematika 2": {
            "course_code": "ETF IM2 I-1280",
        },
        "Sistemsko programiranje": {
            "course_code": "ETF RII SP I-2350",
        },
        "Osnove računarskih mreža": {
            "course_code": "ETF RIO ORM I-2460",
            "year_of_study": 2,
            "semester": 4,
        },
        "Automati i formalni jezici": {
            "year_of_study": 2,
            "semester": 4,
        },
        "CAD-CAM inžinjering": {
            "course_code": "ETF RII CCI I-2450",
        },
        "Digitalno procesiranje signala": {
            "course_code": "ETF RII DPS I-2450",
            "year_of_study": 2,
            "semester": 4,
        },
        "Verifikacija i validacija softvera": {
            "course_code": "ETF RIO VVS I-3550",
        },
        "Računarsko modeliranje i simulacija": {
            "course_name": "Računarsko modeliranje i simulacije",
        },
        "Projektovanje informacionih sistema": {
            "course_code": "ETF RIO PIS I-3660",
            "ects": 5.0,
        },
        "Administracija računarskih mreža": {
            "course_code": "ETF RIO ARM I-3650",
        },
        "Dizajn i arhitektura softverskih sistema": {
            "course_code": "ETF RIO ASS I-3650",
        },
        "Projektovanje i sinteza digitalnih sistema": {
            "course_code": "ETF RIO PDS I-3650",
        },
        "Završni rad": {
            "course_code": "ETF RIO ZR I-36130",
        },
    }

    override = table_overrides.get(course["course_name"])

    if override:
        if "course_name" in override:
            course["curriculum_table_name"] = override["course_name"]

        if "course_code" in override:
            course["curriculum_table_code"] = override["course_code"]

        if "year_of_study" in override:
            course["curriculum_table_year_of_study"] = override["year_of_study"]

        if "semester" in override:
            course["curriculum_table_semester"] = override["semester"]

        if "ects" in override:
            course["curriculum_table_ects"] = override["ects"]

    # Build explicit inconsistency descriptions.
    if course["curriculum_table_name"] != course["source_name"]:
        course["source_inconsistencies"].append(
            "course_name differs between curriculum table and detailed specification"
        )

    if course["curriculum_table_code"] != course["source_code"]:
        course["source_inconsistencies"].append(
            "course_code differs between curriculum table and detailed specification"
        )

    if (
        course["curriculum_table_year_of_study"]
        != course["source_year_of_study"]
    ):
        course["source_inconsistencies"].append(
            "year_of_study differs between curriculum table and detailed specification"
        )

    if (
        course["curriculum_table_semester"]
        != course["source_semester"]
    ):
        course["source_inconsistencies"].append(
            "semester differs between curriculum table and detailed specification"
        )

    if course["curriculum_table_ects"] != course["source_ects"]:
        course["source_inconsistencies"].append(
            "ECTS differs between curriculum table and detailed specification"
        )

    course["has_source_inconsistency"] = bool(
        course["source_inconsistencies"]
    )

    # ------------------------------------------------------
    # LEARNING OUTCOMES
    # ------------------------------------------------------

    outcomes_index = find_heading(
        lines,
        "Ishodi modula",
    )

    course["learning_outcomes"] = (
        get_section_text(
            lines,
            outcomes_index,
            [
                "Sadržaj modula",
                "Literatura",
                "Didaktičke metode",
                "Provjera znanja",
                "Preduvjeti",
            ],
        )
    )

    # ------------------------------------------------------
    # TOPICS / CONTENT
    # ------------------------------------------------------

    topics_index = find_heading(
        lines,
        "Sadržaj modula",
    )

    course["topics"] = parse_topics(
        lines,
        topics_index,
        [
            "Literatura",
            "Didaktičke metode",
            "Provjera znanja",
            "Preduvjeti",
        ],
    )

    # ------------------------------------------------------
    # LITERATURE
    # ------------------------------------------------------

    recommended, additional = (
        parse_literature(lines)
    )

    course["recommended_literature"] = (
        recommended
    )

    course["additional_literature"] = (
        additional
    )

    course["literature"] = (
        recommended
        + [
            item
            for item in additional
            if item not in recommended
        ]
    )

    # ------------------------------------------------------
    # TEACHING METHODS
    # ------------------------------------------------------

    teaching_index = find_heading(
        lines,
        "Didaktičke metode",
    )

    course["teaching_methods"] = (
        get_section_text(
            lines,
            teaching_index,
            [
                "Provjera znanja",
                "Preduvjeti",
            ],
        )
    )

    # ------------------------------------------------------
    # ASSESSMENT
    # ------------------------------------------------------

    assessment_index = find_heading(
        lines,
        "Provjera znanja",
    )

    course["assessment"] = get_section_text(
        lines,
        assessment_index,
        [
            "Preduvjeti",
        ],
    )

    # ------------------------------------------------------
    # PREREQUISITES
    # ------------------------------------------------------

    prerequisites_index = find_heading(
        lines,
        "Preduvjeti",
    )

    prerequisites = get_section_text(
        lines,
        prerequisites_index,
        [],
    )

    # Remove page/footer artifacts that may appear at the end
    # of the module chunk.
    prerequisites = re.sub(
        r"\b\d+/\d+\b.*$",
        "",
        prerequisites,
    ).strip()

    if prerequisites:
        course["prerequisites"] = prerequisites

    # ------------------------------------------------------
    # FINAL CLEANUP
    # ------------------------------------------------------

    for field in [
        "course_name",
        "degree_level",
        "status",
        "learning_outcomes",
        "teaching_methods",
        "assessment",
    ]:
        if isinstance(course[field], str):
            course[field] = clean_text(
                course[field]
            )

    return course


# ==========================================================
# PARSE ALL MODULES
# ==========================================================

def parse_courses(text):
    """
    Split ETF extracted text into detailed module records.

    The first six PDF pages contain curriculum overview tables.
    Only detailed records beginning with "Naziv modula" are
    parsed here, so elective-slot placeholders are not treated
    as courses.
    """

    lines = text.splitlines()

    course_starts = []

    for i, line in enumerate(lines):
        normalized = normalize_line(line)

        if (
            normalized == "naziv modula"
            or normalized.startswith(
                "naziv modula "
            )
        ):
            course_starts.append(i)

    print(
        f"Found {len(course_starts)} detailed module starts"
    )

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

        course = parse_single_module(
            course_lines,
            source_page=source_page,
        )

        if course["course_name"]:
            courses.append(course)

    print(
        f"Found {len(courses)} detailed courses"
    )

    return courses


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("ETF PARSER STARTED")

    project_root = (
        Path(__file__).resolve().parent.parent
    )

    input_path = (
        project_root
        / "data"
        / "extracted"
        / "etf"
        / "ETF curriculum BOS.txt"
    )

    output_path = (
        project_root
        / "data"
        / "structured"
        / "etf"
        / "etf_courses.json"
    )

    print(f"Project root: {project_root}")
    print(f"Input path: {input_path}")

    if not input_path.exists():
        print(
            "\nERROR: INPUT FILE DOES NOT EXIST!"
        )
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

    print(
        f"JSON dataset saved to: {output_path}"
    )

    print("\n" + "=" * 110)
    print("ALL ETF DETAILED COURSES")
    print("=" * 110)
    print(
        f"Found {len(courses)} courses\n"
    )

    for number, course in enumerate(
        courses,
        start=1,
    ):
        print(
            f"{number:2}. "
            f"{course['course_code']} | "
            f"{course['course_name']} | "
            f"Year: {course['year_of_study']} | "
            f"Semester: {course['semester']} | "
            f"ECTS: {course['ects']} | "
            f"Status: {course['status']} | "
            f"Page: {course['source_page']}"
            + (
                f" | SOURCE INCONSISTENCY: "
                f"{'; '.join(course['source_inconsistencies'])}"
                if course["has_source_inconsistency"]
                else ""
            )
        )

    print("\n" + "=" * 110)
    print("ETF PARSER FINISHED")
    print("=" * 110)
