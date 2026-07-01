import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
import pytesseract
from PIL import Image
import io

# If brew installed tesseract somewhere not on PATH, uncomment and set this:
# pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

# Folder containing PDFs
pdf_folder = r"Synthetic data"

# DPI for rendering pages to images before OCR (higher = more accurate, slower)
OCR_DPI = 300

results = []
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def ocr_page(page, dpi=OCR_DPI):
    """Render a PDF page to an image and run Tesseract OCR on it."""
    zoom = dpi / 72  # PyMuPDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img).strip()


for pdf_file in Path(pdf_folder).glob("*.pdf"):

    try:
        doc = fitz.open(pdf_file)

        page_count = len(doc)
        total_text = ""
        total_images = 0

        # Process all pages
        for page in doc:

            # Extract text
            page_text = page.get_text().strip()
            total_text += page_text

            # Count images
            images = page.get_images(full=True)
            total_images += len(images)

        text_length = len(total_text)

        # ---------------------------
        # Classification Logic
        # ---------------------------

        # Native PDF
        if text_length > 500:

            pdf_type = "Native PDF"

        # Scanned PDF (Image Only)
        elif text_length < 50 and total_images > 0:

            pdf_type = "Scanned PDF"

        # Scanned PDF with OCR Layer
        elif 50 <= text_length <= 500 and total_images > 0:

            pdf_type = "Scanned PDF with OCR"

        else:

            pdf_type = "Unknown"

        # ---------------------------
        # OCR Step (only for scanned/image-only PDFs)
        # ---------------------------
        ocr_text = ""
        ocr_applied = "No"

        if pdf_type == "Scanned PDF":
            ocr_chunks = []
            for page in doc:
                ocr_chunks.append(ocr_page(page))
            ocr_text = "\n".join(ocr_chunks).strip()
            ocr_applied = "Yes"
            print(f"  -> OCR extracted {len(ocr_text)} characters from {pdf_file.name}")

        elif pdf_type == "Native PDF":
            ocr_text = total_text
            ocr_applied = "No (native text)"
            print(f"  -> Extracted {len(ocr_text)} characters directly from {pdf_file.name}")

        results.append({
            "File Name": pdf_file.name,
            "Pages": page_count,
            "PDF Type": pdf_type,
            "Multi Page": "Yes" if page_count > 1 else "No",
            "Text Length": text_length,
            "Image Count": total_images,
            "OCR Applied": ocr_applied,
            "OCR Text": ocr_text
        })

        doc.close()

        print(f"✓ Processed: {pdf_file.name}")

    except Exception as e:

        results.append({
            "File Name": pdf_file.name,
            "Pages": "Error",
            "PDF Type": str(e),
            "Multi Page": "",
            "Text Length": "",
            "Image Count": "",
            "OCR Applied": "",
            "OCR Text": ""
        })

        print(f"✗ Error: {pdf_file.name} -> {e}")

# ------------------------------------
# Create DataFrame
# ------------------------------------

df = pd.DataFrame(results)

print("\n===== PDF Classification Summary =====")
print(df.drop(columns=["OCR Text"]))  # keep console output readable

# ------------------------------------
# Save Excel Report (two sheets: full summary + OCR-only text)
# ------------------------------------

output_file = "pdf_classification.xlsx"

ocr_df = df[df["OCR Text"] != ""][["File Name", "Pages", "PDF Type", "OCR Applied", "OCR Text"]]

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Classification", index=False)

    # ---------------------------
    # Formatting: widen columns + wrap text so OCR text is readable
    # ---------------------------
    from openpyxl.styles import Alignment

    class_sheet = writer.sheets["Classification"]
    for col_letter, width in zip("ABCDEFGH", [28, 8, 22, 12, 12, 12, 22, 100]):
        class_sheet.column_dimensions[col_letter].width = width

    wrap_alignment = Alignment(wrap_text=True, vertical="top")
    for row in class_sheet.iter_rows(min_row=2, max_row=class_sheet.max_row, min_col=8, max_col=8):
        for cell in row:
            cell.alignment = wrap_alignment
        # Give each row enough height to show the wrapped text
        class_sheet.row_dimensions[row[0].row].height = 300

print(f"\nExcel report saved: {output_file}")
print(f"  - Sheet 'Classification': all {len(df)} files, including extracted/OCR text in the last column")

# ------------------------------------
# Summary Statistics
# ------------------------------------

print("\n===== Statistics =====")

print(df["PDF Type"].value_counts())

print(f"\nTotal PDFs: {len(df)}")
print(f"PDFs OCR'd: {(df['OCR Applied'] == 'Yes').sum()}")
