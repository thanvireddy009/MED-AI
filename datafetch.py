import pandas as pd

# Read the Excel report
data = pd.read_excel('pdf_classification.xlsx')

output_file = 'ocr_text_output.txt'

with open(output_file, 'w', encoding='utf-8') as f:
    for i, row in data.iterrows():
        file_name = row['File Name']
        text = row['OCR Text']

        # Skip rows with no extracted text (e.g. image2.pdf with 0 characters)
        if pd.isna(text) or str(text).strip() == "":
            continue

        # Header so you know which file this text came from
        f.write(f"{'=' * 80}\n")
        f.write(f"FILE: {file_name}\n")
        f.write(f"{'=' * 80}\n\n")

        f.write(str(text))
        f.write("\n")

        # Page break after each record except the last
        if i < len(data) - 1:
            f.write('\f')

print(f"Data saved to {output_file}")
