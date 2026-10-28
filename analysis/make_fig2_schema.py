"""Draw Fig. 2: structure of a unified course record (all_courses.json)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "figures/fig2_unified_course_record.png"

GROUPS = [
    ("Core Metadata", "#dbe8f7", "#5b8cc8", [
        "course_name", "course_code",
        "degree_level", "degree_level_normalized",
        "year_of_study", "ects",
        "semester", "semester_options",
        "status_original", "status_normalized",
    ]),
    ("Course Content", "#dcefdc", "#5a9e5a", [
        "description", "objectives",
        "learning_outcomes", "learning_outcomes_list",
        "topics", "teaching_methods",
        "assessment", "prerequisites",
        "literature", "",
    ]),
    ("Provenance and Quality", "#f6dede", "#c46a6a", [
        "institution", "source_file",
        "source_page", "source_url",
        "curriculum_version", "retrieval_date",
        "extraction_date", "document_language",
        "instruction_language", "has_source_inconsistency",
        "source_inconsistencies", "",
    ]),
]

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
MONO = {"family": "monospace", "size": 5.8}

fig_w, row_h = 3.5, 0.17
heights = [0.32 + row_h * ((len(f) + 1) // 2) for _, _, _, f in GROUPS]
fig_h = 0.62 + sum(heights) + 0.08 * len(GROUPS)
fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)
ax.set_xlim(0, fig_w)
ax.set_ylim(0, fig_h)
ax.axis("off")

# dataset_id box
top = fig_h - 0.05
ax.add_patch(FancyBboxPatch((0.85, top - 0.44), 1.8, 0.42,
             boxstyle="round,pad=0.02", fc="#ece6f5", ec="#8a78b5", lw=0.8))
ax.text(1.75, top - 0.14, "dataset_id", ha="center", va="center",
        fontdict={"family": "monospace", "size": 7.5, "weight": "bold"})
ax.text(1.75, top - 0.32, "unique identifier of a course record",
        ha="center", va="center", fontsize=6, style="italic")

y = top - 0.56
ax.plot([1.75, 1.75], [top - 0.46, y], color="#444", lw=0.6)
for (title, fc, ec, fields), h in zip(GROUPS, heights):
    ax.add_patch(FancyBboxPatch((0.05, y - h), fig_w - 0.1, h,
                 boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=0.8))
    ax.text(fig_w / 2, y - 0.13, title, ha="center", va="center",
            fontsize=7.5, weight="bold")
    for i, name in enumerate(fields):
        col, row = i % 2, i // 2
        ax.text(0.18 + col * 1.62, y - 0.33 - row * row_h, name,
                ha="left", va="center", fontdict=MONO)
    y -= h + 0.08

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight", pad_inches=0.02)
print(f"Saved to: {OUTPUT_FILE}")