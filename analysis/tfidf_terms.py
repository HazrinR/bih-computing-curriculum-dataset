import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data/structured/unified/all_courses.json"
STOPWORDS_FILE = PROJECT_ROOT / "analysis/stopwords_bs.txt"
OUTPUT_FILE = PROJECT_ROOT / "results/top_tfidf_terms.csv"

INSTITUTIONS = ["etf", "fit", "ibu"]
TOP_N = 10

# Light stemming: remove common Bosnian case endings so that
# 'razvoj', 'razvoja', 'razvoju' are counted as one term.
SUFFIXES = sorted(
    ["ijama", "ama", "ima", "ova", "eva", "ovi", "evi", "oga", "omu",
     "om", "em", "im", "og", "ih", "u", "a", "e", "i", "o"],
    key=len, reverse=True,
)
TOKEN = re.compile(r"\b[^\W\d_]{3,}\b")


def load_stopwords(path):
    words = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            words.update(line.split())
    return words


def light_stem(word):
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def course_text(course):
    """Learning outcomes + topics: the two fields every course has."""
    return (course["learning_outcomes"] + " " + " ".join(course["topics"])).lower()


stopwords = load_stopwords(STOPWORDS_FILE)
surface_forms = {}   # stem -> {word: count}, to show a readable word later


def analyzer(text):
    stems = []
    for word in TOKEN.findall(text):
        if word in stopwords:
            continue
        stem = light_stem(word)
        surface_forms.setdefault(stem, {}).setdefault(word, 0)
        surface_forms[stem][word] += 1
        stems.append(stem)
    return stems


def readable(stem):
    forms = surface_forms.get(stem, {stem: 1})
    return max(forms, key=forms.get)


with INPUT_FILE.open("r", encoding="utf-8") as f:
    courses = json.load(f)

documents = [course_text(c) for c in courses]
institution = np.array([c["institution_key"] for c in courses])

vectorizer = TfidfVectorizer(
    analyzer=analyzer,
    min_df=2,          # term must appear in at least 2 courses
    max_df=0.25,       # ignore terms used in more than 25% of all courses
    sublinear_tf=True,
)
matrix = vectorizer.fit_transform(documents)
terms = vectorizer.get_feature_names_out()

print(f"TF-IDF matrix: {matrix.shape[0]} courses x {matrix.shape[1]} terms\n")

rows = []
for inst in INSTITUTIONS:
    mask = institution == inst
    mean_scores = np.asarray(matrix[mask].mean(axis=0)).ravel()
    top = mean_scores.argsort()[::-1][:TOP_N]
    print(f"{inst.upper()}: " + ", ".join(readable(terms[i]) for i in top))
    for rank, i in enumerate(top, start=1):
        rows.append({
            "institution": inst.upper(),
            "rank": rank,
            "term": readable(terms[i]),
            "mean_tfidf": round(float(mean_scores[i]), 4),
            "courses_with_term": int((matrix[mask][:, i] > 0).sum()),
            "courses_total": int(mask.sum()),
        })

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
print(f"\nSaved to: {OUTPUT_FILE}")