from pathlib import Path
import pymupdf
#for FIT

def extract_pdf_text(pdf_path: Path, output_path: Path):
    """
    Extract text from every page of a PDF and save it as a TXT file.
    """

    print(f"Opening PDF: {pdf_path}")

    document = pymupdf.open(pdf_path)

    print(f"Number of pages: {len(document)}")

    extracted_pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text()

        extracted_pages.append(
            f"\n{'=' * 80}\n"
            f"PAGE {page_number}\n"
            f"{'=' * 80}\n\n"
            f"{text}"
        )

        print(f"Extracted page {page_number}/{len(document)}")

    document.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        "\n".join(extracted_pages),
        encoding="utf-8"
    )

    print("\nExtraction completed!")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":

    project_root = Path(__file__).resolve().parent.parent

    pdf_path = (
        project_root
        / "data"
        / "raw"
        / "fit"
        / "FIT curriculum BOS.pdf"
    )

    output_path = (
        project_root
        / "data"
        / "extracted"
        / "fit"
        / "FIT curriculum BOS.txt"
    )

    extract_pdf_text(pdf_path, output_path)