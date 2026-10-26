from pathlib import Path
import json
import re


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def clean_text(value):
    """
    Clean unnecessary whitespace from extracted PDF text.
    """
    if not value:
        return ""

    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_line(line):
    """
    Normalize a single line for easier comparison.
    """
    return clean_text(line).lower()


def get_next_non_empty_line(lines, start_index):
    """
    Return the next non-empty line after start_index.
    """
    for i in range(start_index + 1, len(lines)):
        if lines[i].strip():
            return lines[i].strip()

    return ""


def get_section_lines(lines, start_index, stop_keywords):
    """
    Extract non-empty lines from a section until a stop keyword.
    """
    collected = []

    normalized_stops = [
        normalize_line(keyword)
        for keyword in stop_keywords
    ]

    for line in lines[start_index + 1:]:
        stripped = line.strip()

        if not stripped:
            continue

        normalized = normalize_line(stripped)

        should_stop = False

        for keyword in normalized_stops:
            if normalized.startswith(keyword):
                should_stop = True
                break

        if should_stop:
            break

        collected.append(stripped)

    return collected


def get_section_text(lines, start_index, stop_keywords):
    """
    Extract text from a section until a stop keyword.
    """
    section_lines = get_section_lines(
        lines,
        start_index,
        stop_keywords
    )

    return clean_text(" ".join(section_lines))


def roman_to_int(value):
    """
    Convert Roman numeral to integer.
    """
    values = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6
    }

    if not value:
        return None

    return values.get(value.upper())


def is_numbered_item(line):
    """
    Check whether a line starts with a numbered item.

    Examples:
        1. Introduction
        2. Databases
        10. Software Engineering
    """
    return re.match(
        r"^\d+\.\s*.+",
        line.strip()
    )


def is_number_only(line):
    """
    Check whether a line contains only a number.

    Example:
        1.
        2.
        3.
    """
    return re.match(
        r"^\d+\.\s*$",
        line.strip()
    )


# ==========================================================
# FIND SECTION START
# ==========================================================

def find_section_start(lines, possible_titles):
    """
    Find a section heading.

    Supports:
    - one-line headings
    - two-line headings
    - three-line headings
    - headings split by PDF extraction

    Returns the index of the last heading line.
    """

    normalized_lines = [
        normalize_line(line)
        for line in lines
    ]

    normalized_titles = [
        normalize_line(title)
        for title in possible_titles
    ]

    # ------------------------------------------------------
    # 1. Exact single-line heading
    # ------------------------------------------------------

    for i, normalized in enumerate(normalized_lines):

        if not normalized:
            continue

        for title in normalized_titles:

            if normalized == title:
                return i

    # ------------------------------------------------------
    # 2. Heading split over 2-4 lines
    # ------------------------------------------------------

    for i in range(len(normalized_lines)):

        if not normalized_lines[i]:
            continue

        combined = ""

        for j in range(
            i,
            min(i + 4, len(normalized_lines))
        ):

            if normalized_lines[j]:

                combined = clean_text(
                    combined
                    + " "
                    + normalized_lines[j]
                )

            for title in normalized_titles:

                if combined == title:
                    return j

    return None


# ==========================================================
# FIND SECTION BY PHRASE
# ==========================================================

def find_section_by_phrase(lines, phrase):
    """
    Find a section heading even when the heading is split
    across multiple lines.

    Searches up to four extracted lines.
    """

    normalized_phrase = normalize_line(phrase)

    normalized_lines = [
        normalize_line(line)
        for line in lines
    ]

    for i in range(len(normalized_lines)):

        if not normalized_lines[i]:
            continue

        combined = ""

        for j in range(
            i,
            min(i + 4, len(normalized_lines))
        ):

            if normalized_lines[j]:

                combined = clean_text(
                    combined
                    + " "
                    + normalized_lines[j]
                )

            if normalized_phrase in combined:
                return j

            if len(combined) > len(normalized_phrase) + 100:
                break

    return None


# ==========================================================
# FIND SECTION BY KEYWORDS
# ==========================================================

def find_line_containing(lines, phrases):
    """
    Find the first line containing any of the supplied phrases.
    """

    normalized_phrases = [
        normalize_line(phrase)
        for phrase in phrases
    ]

    for i, line in enumerate(lines):

        normalized = normalize_line(line)

        for phrase in normalized_phrases:

            if phrase in normalized:
                return i

    return None


# ==========================================================
# SOURCE PAGE
# ==========================================================

def find_source_page(lines, start_index):
    """
    Find the PDF page number associated with a course.

    Searches backwards from the course start until it finds
    a line in the format: PAGE 12
    """

    for i in range(start_index, -1, -1):

        match = re.fullmatch(
            r"PAGE\s+(\d+)",
            lines[i].strip(),
            flags=re.IGNORECASE
        )

        if match:
            return int(match.group(1))

    return None


# ==========================================================
# TOPICS
# ==========================================================

def parse_topics(lines, start_index, stop_keywords):
    """
    Extract numbered course topics.

    Handles:
    - 1. Topic
    - 1.
      Topic
    - topics spanning multiple lines
    """

    section_lines = get_section_lines(
        lines,
        start_index,
        stop_keywords
    )

    topics = []
    current_topic = None

    for line in section_lines:

        stripped = line.strip()

        # --------------------------------------------------
        # Number + topic on same line
        # --------------------------------------------------

        match = re.match(
            r"^(\d+)\.\s*(.+)$",
            stripped
        )

        if match:

            if current_topic:
                topics.append(
                    clean_text(current_topic)
                )

            current_topic = match.group(2).strip()

            continue

        # --------------------------------------------------
        # Number on its own line
        # --------------------------------------------------

        number_only = re.match(
            r"^(\d+)\.\s*$",
            stripped
        )

        if number_only:

            if current_topic:
                topics.append(
                    clean_text(current_topic)
                )

            current_topic = ""

            continue

        # --------------------------------------------------
        # Continuation line
        # --------------------------------------------------

        if current_topic is not None:

            current_topic += " " + stripped

    # ------------------------------------------------------
    # Add final topic
    # ------------------------------------------------------

    if current_topic is not None:

        cleaned = clean_text(current_topic)

        if cleaned:
            topics.append(cleaned)

    return topics


# ==========================================================
# LITERATURE
# ==========================================================

def parse_literature(lines, start_index, stop_keywords):
    """
    Extract numbered literature references.

    Handles:

        1. Book title
        2. Another book

    and:

        1.
        Book title

        2.
        Another book

    References can span multiple lines.
    """

    section_lines = get_section_lines(
        lines,
        start_index,
        stop_keywords
    )

    literature = []
    current_reference = None

    for line in section_lines:

        stripped = line.strip()

        # --------------------------------------------------
        # Number + reference on same line
        # --------------------------------------------------

        match = re.match(
            r"^(\d+)\.\s*(.+)$",
            stripped
        )

        if match:

            if current_reference is not None:

                cleaned = clean_text(
                    current_reference
                )

                if cleaned:
                    literature.append(cleaned)

            current_reference = match.group(2).strip()

            continue

        # --------------------------------------------------
        # Number on its own line
        # --------------------------------------------------

        number_only = re.match(
            r"^(\d+)\.\s*$",
            stripped
        )

        if number_only:

            if current_reference is not None:

                cleaned = clean_text(
                    current_reference
                )

                if cleaned:
                    literature.append(cleaned)

            current_reference = ""

            continue

        # --------------------------------------------------
        # Continuation of current reference
        # --------------------------------------------------

        if current_reference is not None:

            current_reference += " " + stripped

    # ------------------------------------------------------
    # Add final reference
    # ------------------------------------------------------

    if current_reference is not None:

        cleaned = clean_text(
            current_reference
        )

        if cleaned:
            literature.append(cleaned)

    return literature


# ==========================================================
# PARSE ALL COURSES
# ==========================================================

def parse_courses(text):
    """
    Split FIT text into individual course records.
    """

    lines = text.splitlines()

    course_starts = []

    for i, line in enumerate(lines):

        if line.strip() != "Naziv predmeta:":
            continue

        next_line = get_next_non_empty_line(
            lines,
            i
        )

        if (
            next_line
            and not next_line.startswith("=")
        ):
            course_starts.append(i)

    print(
        f"Found {len(course_starts)} course starts"
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
            start
        )

        course = parse_single_course(
            course_lines,
            source_page=source_page
        )

        if course["course_name"]:
            courses.append(course)

    print(
        f"Found {len(courses)} courses"
    )

    return courses


# ==========================================================
# PARSE ONE COURSE
# ==========================================================

def parse_single_course(lines, source_page=None):

    course = {
        "institution": "Univerzitet Džemal Bijedić u Mostaru",
        "faculty": "Fakultet informacijskih tehnologija",
        "program": "Bachelor informacijskih tehnologija – usmjerenje Razvoj softvera",
        "course_name": "",
        "course_code": None,
        "degree_level": "",
        "year_of_study": None,
        "semester": None,
        "ects": None,
        "status": "",
        "prerequisites": None,
        "objectives": "",
        "learning_outcomes": "",
        "topics": [],
        "teaching_methods": "",
        "student_obligations": "",
        "assessment": "",
        "literature": [],
        "source_file": "FIT curriculum BOS.pdf",
        "source_page": source_page
    }

    # ======================================================
    # COURSE NAME
    # ======================================================

    for i, line in enumerate(lines):

        if line.strip() != "Naziv predmeta:":
            continue

        name_parts = []

        j = i + 1

        while j < len(lines):

            candidate = lines[j].strip()

            if not candidate:
                j += 1
                continue

            normalized = normalize_line(candidate)

            if (
                normalized.startswith(
                    "šifra predmeta:"
                )
                or normalized.startswith(
                    "ifra predmeta:"
                )
                or normalized.startswith(
                    "nivo ciklusa"
                )
                or normalized.startswith(
                    "ciklusa, godina studija"
                )
                or normalized.startswith(
                    "voditelj predmeta"
                )
            ):
                break

            name_parts.append(candidate)

            j += 1

        course["course_name"] = clean_text(
            " ".join(name_parts)
        )

        break

    # ======================================================
    # COURSE CODE
    # ======================================================

    for i, line in enumerate(lines):

        normalized = normalize_line(line)

        if not (
            normalized.startswith(
                "šifra predmeta:"
            )
            or normalized.startswith(
                "ifra predmeta:"
            )
        ):
            continue

        # --------------------------------------------------
        # Check same line
        # --------------------------------------------------

        same_line = re.search(
            r":\s*(.+)$",
            line
        )

        if same_line:

            value = same_line.group(1).strip()

            if value:
                course["course_code"] = value

        # --------------------------------------------------
        # Check next non-empty line
        # --------------------------------------------------

        if not course["course_code"]:

            value = get_next_non_empty_line(
                lines,
                i
            )

            normalized_value = normalize_line(
                value
            )

            # IMPORTANT:
            # Do not treat section headings as course codes.

            invalid_code_start = (
                "nivo ciklusa",
                "ciklusa",
                "voditelj predmeta",
                "status predmeta",
                "godina",
                "preduslovi",
                "preduvjeti",
                "cilj predmeta",
                "ograničenja",
                "obrazloženje"
            )

            if (
                value
                and not normalized_value.startswith(
                    invalid_code_start
                )
            ):
                course["course_code"] = value

        break

    # ------------------------------------------------------
    # Normalize course code
    # ------------------------------------------------------

    if course["course_code"]:

        code = clean_text(
            course["course_code"]
        )

        if (
            not code
            or code == "0000"
        ):
            course["course_code"] = None
        else:
            course["course_code"] = code

    # ======================================================
    # DEGREE LEVEL
    # ======================================================

    for i, line in enumerate(lines):

        normalized = normalize_line(line)

        is_degree_heading = (
            normalized.startswith(
                "nivo ciklusa"
            )
            or (
                "ciklusa" in normalized
                and "godina studija" in normalized
                and "semestar" in normalized
            )
        )

        if not is_degree_heading:
            continue

        for j in range(
            i + 1,
            min(i + 10, len(lines))
        ):

            value = lines[j].strip()

            if not value:
                continue

            normalized_value = normalize_line(
                value
            )

            if (
                "studij" in normalized_value
                and "ciklusa" in normalized_value
            ):

                course["degree_level"] = clean_text(
                    value
                )

                break

        if course["degree_level"]:
            break

    # ======================================================
    # YEAR AND SEMESTER
    # ======================================================

    for line in lines:

        normalized = normalize_line(line)

        # --------------------------------------------------
        # Format:
        # godina: III / semestar: IV
        # --------------------------------------------------

        match = re.search(
            r"godina\s*:\s*([ivx]+)"
            r".*?"
            r"semestar\s*:\s*([ivx]+)",
            normalized,
            re.IGNORECASE
        )

        if match:

            course["year_of_study"] = (
                roman_to_int(
                    match.group(1)
                )
            )

            course["semester"] = (
                roman_to_int(
                    match.group(2)
                )
            )

            break

        # --------------------------------------------------
        # Format:
        # III godina studija / IV semestar
        # --------------------------------------------------

        match = re.search(
            r"([ivx]+)\s+godina\s+studija"
            r".*?"
            r"([ivx]+)\s+semestar",
            normalized,
            re.IGNORECASE
        )

        if match:

            course["year_of_study"] = (
                roman_to_int(
                    match.group(1)
                )
            )

            course["semester"] = (
                roman_to_int(
                    match.group(2)
                )
            )

            break

        # --------------------------------------------------
        # Format:
        # godina studija III / IV semestar
        # --------------------------------------------------

        match = re.search(
            r"godina\s+studija\s*"
            r"([ivx]+)"
            r".*?"
            r"([ivx]+)\s+semestar",
            normalized,
            re.IGNORECASE
        )

        if match:

            course["year_of_study"] = (
                roman_to_int(
                    match.group(1)
                )
            )

            course["semester"] = (
                roman_to_int(
                    match.group(2)
                )
            )

            break

    # ------------------------------------------------------
    # Calculate year from semester if necessary
    # ------------------------------------------------------

    if (
        course["year_of_study"] is None
        and course["semester"] is not None
    ):

        course["year_of_study"] = (
            (course["semester"] + 1) // 2
        )

    # ======================================================
    # ECTS
    # ======================================================

    for i, line in enumerate(lines):

        normalized = normalize_line(line)

        if "bodovna vrijednost" not in normalized:
            continue

        for j in range(
            i,
            min(i + 8, len(lines))
        ):

            value_line = lines[j].strip()

            if not value_line:
                continue

            match = re.search(
                r"(\d+(?:[.,]\d+)?)\s*ects"
                r"|ects\s*(\d+(?:[.,]\d+)?)",
                value_line,
                re.IGNORECASE
            )

            if match:

                value = (
                    match.group(1)
                    or match.group(2)
                )

                course["ects"] = float(
                    value.replace(",", ".")
                )

                break

        if course["ects"] is not None:
            break

    # ======================================================
    # STATUS
    # ======================================================

    for i, line in enumerate(lines):

        if normalize_line(line) != "status predmeta:":
            continue

        value = get_next_non_empty_line(
            lines,
            i
        )

        if value:

            course["status"] = clean_text(
                value
            )

        break

    # ======================================================
    # PREREQUISITES
    # ======================================================

    prerequisite_index = find_line_containing(
        lines,
        [
            "preduslovi za polaganje predmeta",
            "preduvjeti za polaganje predmeta"
        ]
    )

    if prerequisite_index is not None:

        value = get_next_non_empty_line(
            lines,
            prerequisite_index
        )

        if value:

            normalized_value = normalize_line(
                value
            )

            invalid_starts = (
                "ograničenja",
                "obrazloženje",
                "cilj predmeta",
                "opis općih",
                "okvirni sadržaj",
                "oblici provođenja",
                "ostale obaveze",
                "način provjere",
                "popis osnovne"
            )

            if not normalized_value.startswith(
                invalid_starts
            ):

                course["prerequisites"] = clean_text(
                    value
                )

    # ======================================================
    # OBJECTIVES
    # ======================================================

    objectives_index = find_section_start(
        lines,
        [
            "Cilj predmeta:"
        ]
    )

    if objectives_index is not None:

        course["objectives"] = get_section_text(
            lines,
            objectives_index,
            [
                "Opis općih",
                "Okvirni sadržaj"
            ]
        )

    # ======================================================
    # LEARNING OUTCOMES
    # ======================================================

    learning_index = None

    for i, line in enumerate(lines):

        normalized = normalize_line(line)

        if (
            "opis općih i specifičnih" in normalized
            or "opis općih" in normalized
        ):

            learning_index = i

            # Search for /ishod učenja:
            for j in range(
                i + 1,
                min(i + 8, len(lines))
            ):

                normalized_next = normalize_line(
                    lines[j]
                )

                if "učenja" in normalized_next:

                    learning_index = j
                    break

            break

    if learning_index is not None:

        course["learning_outcomes"] = (
            get_section_text(
                lines,
                learning_index,
                [
                    "Okvirni sadržaj"
                ]
            )
        )

    # ======================================================
    # TOPICS
    # ======================================================

    topics_index = find_section_by_phrase(
        lines,
        "Okvirni sadržaj predmeta"
    )

    if topics_index is not None:

        course["topics"] = parse_topics(
            lines,
            topics_index,
            [
                "Oblici provođenja",
                "Ostale obaveze studenta"
            ]
        )

    # ======================================================
    # TEACHING METHODS
    # ======================================================

    teaching_index = find_section_by_phrase(
        lines,
        "Oblici provođenja nastave/metode učenja"
    )

    if teaching_index is not None:

        course["teaching_methods"] = (
            get_section_text(
                lines,
                teaching_index,
                [
                    "Ostale obaveze studenta",
                    "Način provjere znanja"
                ]
            )
        )

        # ======================================================
    # STUDENT OBLIGATIONS
    # ======================================================

    obligations_index = find_section_by_phrase(
        lines,
        "Ostale obaveze studenta"
    )

    if obligations_index is not None:
        course["student_obligations"] = get_section_text(
            lines,
            obligations_index,
            [
                "Način provjere znanja",
                "Popis osnovne literature",
                "Obavezna literatura",
                "Dodatna literatura",
                "Način praćenja kvalitete"
            ]
        )

        # Remove leftover text from the multi-line section heading.
    course["student_obligations"] = re.sub(
        r"^predviđaju\):\s*",
        "",
        course["student_obligations"],
        flags=re.IGNORECASE
    ).strip()

# Store None instead of an empty string.
    if not course["student_obligations"]:
        course["student_obligations"] = None

    # ======================================================
    # ASSESSMENT
    # ======================================================

    assessment_index = find_section_by_phrase(
        lines,
        "Način provjere znanja"
    )

    if assessment_index is not None:
        course["assessment"] = get_section_text(
            lines,
            assessment_index,
            [
                "Popis osnovne literature",
                "Popis osnovne",
                "Obavezna literatura",
                "Dodatna literatura",
                "Način praćenja kvalitete"
            ]
        )

    # Remove leftover text from the multi-line assessment heading.
    course["assessment"] = re.sub(
        r"^polaganja ispita i % težinskog faktora provjere znanja:\s*",
        "",
        course["assessment"],
        flags=re.IGNORECASE
    ).strip()

    if not course["assessment"]:
        course["assessment"] = None

    # ======================================================
    # LITERATURE
    # ======================================================

    literature_index = find_section_by_phrase(
        lines,
        "Popis osnovne literature i Internet web referenci"
    )

    # Some FIT courses use "Obavezna literatura"
    # instead of placing references directly under
    # "Popis osnovne literature..."
    if literature_index is None:
        literature_index = find_line_containing(
            lines,
            [
                "obavezna literatura"
            ]
        )

    if literature_index is None:
        literature_index = find_line_containing(
            lines,
            [
                "popis osnovne literature"
            ]
        )

    if literature_index is not None:

        course["literature"] = parse_literature(
            lines,
            literature_index,
            [
                "Dodatna literatura",
                "Način praćenja",
                "Način praćenja kvalitete",
                "Kvalitet praćenja",
                "Kvalitet praćenja rada"
            ]
        )

    # If the first literature section exists but produced
    # no references, try "Obavezna literatura" explicitly.
    if not course["literature"]:

        mandatory_literature_index = find_line_containing(
            lines,
            [
                "obavezna literatura"
            ]
        )

        if mandatory_literature_index is not None:

            course["literature"] = parse_literature(
                lines,
                mandatory_literature_index,
                [
                    "Dodatna literatura",
                    "Način praćenja",
                    "Način praćenja kvalitete",
                    "Kvalitet praćenja",
                    "Kvalitet praćenja rada"
                ]
            )



        # ======================================================
    # ADDITIONAL LITERATURE
    # ======================================================

    additional_literature_index = find_line_containing(
        lines,
        [
            "dodatna literatura"
        ]
    )

    if additional_literature_index is not None:

        additional_literature = parse_literature(
            lines,
            additional_literature_index,
            [
                "Popis osnovne literature",
                "Popis osnovne",
                "Način praćenja",
                "Način praćenja kvalitete",
                "Kvalitet praćenja",
                "Kvalitet praćenja rada"
            ]
        )

        # Add additional references to the already parsed
        # mandatory/basic literature.
        for reference in additional_literature:

            if reference not in course["literature"]:
                course["literature"].append(reference)

                
    # ======================================================
    # FINAL CLEANUP
    # ======================================================

    course["course_name"] = clean_text(
        course["course_name"]
    )

    course["degree_level"] = clean_text(
        course["degree_level"]
    )

    course["status"] = clean_text(
        course["status"]
    )

    course["objectives"] = clean_text(
        course["objectives"]
    )

    course["learning_outcomes"] = clean_text(
        course["learning_outcomes"]
    )

    course["teaching_methods"] = clean_text(
        course["teaching_methods"]
    )

    course["student_obligations"] = clean_text(
        course["student_obligations"]
    )

    if not course["student_obligations"]:
        course["student_obligations"] = None

    course["assessment"] = clean_text(
        course["assessment"]
    )

    if not course["assessment"]:
        course["assessment"] = None

    if course["prerequisites"]:
        course["prerequisites"] = clean_text(
            course["prerequisites"]
        )

    if not course["prerequisites"]:
        course["prerequisites"] = None

    if not course["course_code"]:
        course["course_code"] = None

    return course


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("SCRIPT SE POKRENUO")

    # ------------------------------------------------------
    # PROJECT ROOT
    # ------------------------------------------------------

    project_root = (
        Path(__file__).resolve().parent.parent
    )

    print(
        f"Project root: {project_root}"
    )

    # ------------------------------------------------------
    # INPUT FILE
    # ------------------------------------------------------

    input_path = (
        project_root
        / "data"
        / "extracted"
        / "fit"
        / "FIT curriculum BOS.txt"
    )

    print(
        f"Input path: {input_path}"
    )

    if not input_path.exists():

        print(
            "\nERROR: INPUT FILE DOES NOT EXIST!"
        )

        print(input_path)

        raise SystemExit(1)

    # ------------------------------------------------------
    # READ FILE
    # ------------------------------------------------------

    text = input_path.read_text(
        encoding="utf-8"
    )

    print(
        f"Input file read successfully: "
        f"{len(text)} characters"
    )

    # ------------------------------------------------------
    # PARSE COURSES
    # ------------------------------------------------------

    courses = parse_courses(text)

    # ------------------------------------------------------
    # SAVE STRUCTURED JSON DATASET
    # ------------------------------------------------------

    output_path = (
        project_root
        / "data"
        / "structured"
        / "fit"
        / "fit_courses.json"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(courses, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

    print(f"JSON dataset saved to: {output_path}")

    # ------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------

    print("\n" + "=" * 80)
    print("ALL COURSES")
    print("=" * 80)

    print(
        f"Found {len(courses)} courses\n"
    )

    for number, course in enumerate(
        courses,
        start=1
    ):

        print(
            f"{number:2}. "
            f"{course['course_name']} | "
            f"Year: {course['year_of_study']} | "
            f"Semester: {course['semester']} | "
            f"ECTS: {course['ects']} | "
            f"Status: {course['status']}"
        )

    # ------------------------------------------------------
    # FINISHED
    # ------------------------------------------------------

    print("\n" + "=" * 80)
    print("SCRIPT FINISHED")
    print("=" * 80)