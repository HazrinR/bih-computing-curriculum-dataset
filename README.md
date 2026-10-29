# Unified Computing Curriculum Dataset – Bosnia and Herzegovina

Dataset and code accompanying the paper *"Construction and Validation of a
Unified Computing Curriculum Dataset from Three Higher Education Institutions
in Bosnia and Herzegovina"*.

A structured, course-level dataset of undergraduate computing curricula from
three higher education institutions in Bosnia and Herzegovina, together with
the code used to extract, parse, validate and analyse it.

| Institution | Programme | Courses | Curriculum version |
|---|---|---:|---|
| FIT – Faculty of Information Technologies, Džemal Bijedić University of Mostar | Bachelor of IT – Software Development track | 35 | not stated in the document |
| IBU – International Burch University, Faculty of Engineering, Natural and Medical Sciences | Information Technologies (1st cycle) | 44 | 2024/2025 |
| ETF – Faculty of Electrical Engineering, University of Sarajevo | Computer Science and Informatics (1st cycle) | 41 | 2014 (still in use) |
| **Total** | | **120** | |

This dataset covers three institutions and is not a complete census of
computing curricula in Bosnia and Herzegovina.

## Source documents

The original curriculum PDFs are publicly available from the institutions and
are **not included** in this repository (copyright remains with the
institutions). Download links and retrieval dates are also listed in
`data/sources.json`.

| Institution | Download link | Save as | Retrieved |
|---|---|---|---|
| FIT | https://www.fit.ba/content/a77e95ef-1a7c-4cae-b37a-f3a4619ecc1b | `data/raw/fit/FIT curriculum BOS.pdf` | 2026-08-19 |
| IBU | https://drive.google.com/drive/folders/14Y8jSEPG3CDvBQNEQQuif7irIZzOsHQI | `data/raw/ibu/IBU curriculum BOS.pdf` | 2026-09-12 |
| ETF | https://etf.unsa.ba/uploads/d0937793ed9bdd70032558e470669f9b.pdf | `data/raw/etf/ETF curriculum BOS.pdf` | 2026-08-23 |

All three documents are written in Bosnian. IBU publishes identical curriculum
specifications in Bosnian and English; the Bosnian version was used so that all
sources are in the same language. Instruction at IBU is delivered in English.

### Course selection

All courses with a detailed course specification in the selected document were
included, mandatory and elective:

- **FIT**: all 35 course specifications of the Software Development track.
- **IBU**: all 44 department-level courses (codes `IT xxxx`). Faculty-wide
  (`FENMS`) and university-wide (`IBU`) courses are published in separate
  documents and are mostly general, non-technical courses; they are not
  included, so IBU year 1 contains only 3 courses.
- **ETF**: common first-year courses and courses of the Computer Science and
  Informatics (RI) department.

## Repository structure

```
data/
  sources.json              source URL, version, dates and language per institution
  structured/<inst>/        per-institution JSON (output of the parsers)
  structured/unified/       all_courses.json  <- the final dataset (120 courses)
scripts/                    extraction, parsing, validation, dataset building
evaluation/                 manual correctness evaluation and its scripts
analysis/                   descriptive statistics, field completeness, learning-outcome counts and TF-IDF analysis
results/                    output tables of the evaluation and analysis
```

## How to run

Requires Python 3.14.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

1. Download the three PDFs (links above) and save them under the given names.
2. Run the pipeline in this order:

```bash
# 1. PDF -> text (one page marker per PDF page)
python scripts/extract_pdf.py        # FIT
python scripts/extract_ibu.py
python scripts/extract_etf.py

# 2. text -> structured JSON per institution
python scripts/parse_fit.py
python scripts/parse_ibu.py
python scripts/parse_etf.py

# 3. validation per institution
python scripts/validate_fit.py
python scripts/validate_ibu.py
python scripts/validate_etf.py

# 4. unified dataset + validation
python scripts/build_unified_dataset.py
python scripts/validate_unified.py

# 5. analysis
python analysis/lo_counts.py
python analysis/make_fig2_schema.py   # Fig. 2 of the paper
python analysis/descriptive_stats.py  # Table III of the paper
python analysis/field_completeness.py # Table IV of the paper
python analysis/tfidf_terms.py

# 6. (optional) load into a local MongoDB
python scripts/load_mongodb.py
```

The structured dataset in `data/structured/` is included, so steps 5–6 can be
run without downloading the PDFs.

## Data dictionary

`data/structured/unified/all_courses.json` contains one JSON object per course.
Missing information is stored as `null` or `[]` and is never inferred.

| Group | Field | Description |
|---|---|---|
| Identity | `dataset_id` | Unique identifier, e.g. `fit_001` |
| | `institution_key` | `fit`, `ibu` or `etf` |
| | `institution`, `faculty`, `program` | As written in the source document |
| | `degree_level` | As written in the source document |
| | `degree_level_normalized` | Normalized value (`bachelor`) |
| | `course_name` | Course name as in the source |
| | `course_code` | Course code; `null` for FIT (not given in the source) |
| Study structure | `year_of_study` | Year of study (1–3) |
| | `semester`, `semester_options` | Semester; `semester_options` lists all semesters in which an elective can be taken |
| | `ects` | ECTS credits |
| | `status_original` | Course status as in the source (e.g. `Obavezni`, `Izborni`) |
| | `status_normalized` | `mandatory`, `elective` or `mixed` |
| Content | `learning_outcomes` | Learning outcomes, original text |
| | `learning_outcomes_list` | Learning outcomes split into individual statements (`scripts/lo_splitter.py`) |
| | `topics` | List of course topics |
| | `description`, `objectives` | Course description / objectives, if given |
| | `teaching_methods`, `assessment`, `student_obligations`, `prerequisites` | As given in the source |
| | `literature`, `mandatory_literature`, `recommended_literature`, `additional_literature` | Literature lists |
| | `lecture_hours`, `laboratory_hours`, `tutorial_hours`, `self_study_hours` | Weekly hours (ETF only) |
| Language | `document_language` | Language of the curriculum document (`bs` for all records) |
| | `instruction_language` | Language of instruction (`en` for IBU, `bs` for FIT and ETF) |
| | `instruction_language_source` | Where the instruction language comes from (course specification or institution level) |
| | `language` | Raw value of the language field in the source, if given (IBU only) |
| Provenance | `source_file`, `source_page` | Source PDF file and page where the course specification starts |
| | `source_url`, `retrieval_date` | Download link and date of the source document |
| | `curriculum_version` | Curriculum version or academic year, as stated in the document |
| | `extraction_date` | Date on which the text was extracted from the PDF |
| Consistency | `has_source_inconsistency` | `true` if the source document contains conflicting values for this course |
| | `source_inconsistencies` | List of the detected discrepancies |
| | `source_*`, `curriculum_table_*` | The two conflicting values (name, code, year, semester, ECTS) as found in the detailed specification and in the curriculum table |

## Evaluation

* `evaluation/sample_for_validation.py` draws the stratified random sample
  (10 records per institution, seed 42).
* `evaluation/validation_sample.csv` contains the manual judgements
  (1 = correct, 0.5 = partly correct, 0 = wrong) for eight fields.
* `evaluation/compute_accuracy.py` computes strict and lenient accuracy
  (`results/accuracy_results.csv`, Table V of the paper).
* `evaluation/lo_split_evaluation.csv` contains the evaluation of the
  learning-outcome splitter on FIT (development and test sample).
* `evaluation/compare_versions.py` compares the dataset before and after the
  parser corrections; the earlier version is not included in the repository.

## License

Code: MIT. Structured data in `data/structured/`: CC BY 4.0. See `LICENSE`.
The original curriculum documents remain the property of the institutions and
are not redistributed.