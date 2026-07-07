import pandas as pd
import json
import re

# ─────────────────────────────────────────────
# Step 1: Load the Excel file
# ─────────────────────────────────────────────
data = pd.read_excel('pdf_classification.xlsx')

# ─────────────────────────────────────────────
# Step 2: Helpers
# ─────────────────────────────────────────────
def extract_field(text, *patterns, default="N/A"):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip()
            if val:
                return val
    return default


def extract_block(text, start_marker, end_markers):
    start = re.search(start_marker, text, re.IGNORECASE)
    if not start:
        return ""
    chunk = text[start.end():]
    for em in end_markers:
        end = re.search(em, chunk, re.IGNORECASE)
        if end:
            chunk = chunk[:end.start()]
    return chunk.strip()


# ─────────────────────────────────────────────
# Step 3: Per-record extractors
# ─────────────────────────────────────────────

def parse_patient_information(text):
    return {
        "patient_identifier": extract_field(text,
            r"Patient\s+Identifier[:\s]+([A-Z0-9\-]+)",
            r"Patient\s*\nIdentifier:?\s*([A-Z0-9\-]+)",
            r"Patient\s+([A-Z0-9\-]+)\s+Full Name"),

        # Handles 3 layouts:
        # 1. Native: "Full Name \n(Conf.): \nJames R. Mitchell"
        # 2. Native alt: "Full Name (Conf.): Jennifer L. Brooks"
        # 3. Scanned: "Full Name Thomas E. Robinson" (same line, no colon)
        "full_name": extract_field(text,
            r"Full Name\s*\n\s*\(Conf\.\)[:\s]*\n\s*([\w][^\n]+?)(?:\s*\n|Date of Birth)",
            r"Full Name\s*\(Conf\.\)[:\s]+([\w\s\.]+?)(?:\n|Date of Birth)",
            r"Full Name\s+([A-Z][a-z]+(?:\s+[A-Z][\w]*\.?){1,3}(?:\s+[A-Z][a-z]+)?)\s*\n",
            r"(?:Identifier:\s*\S+\s+Full Name\s+)([\w][\w\s]+?)(?:\n|Date of Birth)"),

        "date_of_birth": extract_field(text,
            r"Date of Birth[:\s]+([\d\-A-Za-z]+)"),

        "age": extract_field(text,
            r"Age[:\s]+([\d]+\s*year\(s\))"),

        "sex": extract_field(text,
            r"Sex[:\s]+(Male|Female)"),

        # OCR misreads "lb" as "Ib" or "|b" — accept all variants
        "weight": extract_field(text,
            r"Weight[:\s]+([\d]+\s*(?:lb|Ib|LB|\|b))"),

        # Scanned layout: "Race / White\n\nEthnicity:" — value is on Race line
        "race_ethnicity": extract_field(text,
            r"Race\s*/\s*Ethnicity[:\s]+([\w\s\/]+?)(?:\n|  [A-Z])",
            r"Race\s*/\s*\nEthnicity[:\s]+([\w\s\/]+?)(?:\n|  [A-Z])",
            r"Race\s*/\s*([\w\s]+?)\n\s*\nEthnicity",
            r"Race\s*/\s*\n([\w\s]+?)\n",
            r"Race\s*/\s+([\w][\w\s]+?)\n"),
    }


def parse_adverse_events(text):
    block = extract_block(
        text,
        r"B\.\s+ADVERSE EVENT",
        [r"B\.6\s+RELEVANT", r"C\.\s+PRODUCT", r"D\.\s+SUSPECT"]
    )
    return {
        "type_of_report": extract_field(text,
            r"Type of Report[:\s]+([\w\s\-–]+?)(?:\n|Outcome)"),
        "outcome": extract_field(text,
            r"Outcome[:\s]+([\w\s\-]+?)(?:\n|Date of Event)"),
        "date_of_event": extract_field(text,
            r"Date of Event[:\s]+([\d\-A-Za-z]+)"),
        "date_of_report": extract_field(text,
            r"Date of This\s*\nReport[:\s]+([\d\-A-Za-z]+)",
            r"Date of This Report[:\s]+([\d\-A-Za-z]+)",
            r"Date of This\s+([\d\-A-Za-z]+)\s*\nReport"),
        "event_description": extract_field(block,
            r"Describe Event.*?(?:B\.5\))?\s*([\s\S]+?)(?:Other Relevant|$)"),
        "medical_history_preexisting": extract_field(block,
            r"Other Relevant History.*?(?:B\.7\))?\s*([\s\S]+?)$"),
    }


def parse_suspect_drug(text):
    block = extract_block(
        text,
        r"D\.\s+SUSPECT PRODUCT",
        [r"E\.\s+SUSPECT MEDICAL", r"F\.\s+OTHER"]
    )
    return {
        "product_name": extract_field(block,
            r"Product Name[:\s]+([\w\s\d]+?)(?:\n|NDC)"),
        "ndc_unique_id": extract_field(block,
            r"NDC\s*/\s*Unique ID[:\s]+([\w\-]+)"),
        "manufacturer": extract_field(block,
            r"Manufacturer[:\s]+([\w\s\.,]+?)(?:\n|Lot)"),
        "lot_number": extract_field(block,
            r"Lot\s*#[:\s]+([\w]+)"),
        "dose_amount": extract_field(block,
            r"Dose\s*/\s*Amount[:\s]+([\w\s]+?)(?:\n|Frequency)"),
        "frequency": extract_field(block,
            r"Frequency[:\s]+([\w\s\(\)]+?)(?:\n|Route)"),
        "route": extract_field(block,
            r"Route[:\s]+([\w]+?)(?:\n|Diagnosis)"),
        "indication": extract_field(block,
            r"(?:Diagnosis|Indication)[:\s\(]+[\w\s\)]*[:\)]\s*([\w\s]+?)(?:\n|Therapy)"),
        "therapy_start_date": extract_field(block,
            r"Therapy Start\s*\nDate[:\s]+([\d\-A-Za-z]+)",
            r"Therapy Start\s+Date[:\s]+([\d\-A-Za-z]+)",
            r"Therapy Start\s+([\d\-A-Za-z]+)"),
        "therapy_stop_date": extract_field(block,
            r"Therapy Stop\s*\nDate[:\s]+([\d\-A-Za-z]+)",
            r"Therapy Stop\s+Date[:\s]+([\d\-A-Za-z]+)",
            r"Therapy Stop\s+([\d\-A-Za-z]+)"),
        "event_abated_after_stop": extract_field(block,
            r"Event Abated\s*\nAfter Stop\?[:\s]+(Yes|No)",
            r"Event Abated\s+After Stop\?[:\s]+(Yes|No)",
            r"Event Abated\s+(Yes|No)"),
        "event_reappeared_after_reintro": extract_field(block,
            r"Event Reappeared\s*\nAfter Reintro\?[:\s]+(Yes|No)",
            r"Event Reappeared\s+After Reintro\?[:\s]+(Yes|No)",
            r"Event Reappeared\s+(Yes|No)"),
        "product_type": extract_field(block,
            r"Product Type[:\s]+([\w\s\-–]+?)(?:\n|Ongoing)"),
        "ongoing_therapy": extract_field(block,
            r"Ongoing Therapy\?[:\s]+(Yes|No)"),
    }


def parse_concomitant_medications(text):
    block = extract_block(
        text,
        r"F\.\s+OTHER.*?MEDICAL PRODUCTS",
        [r"G\.\s+REPORTER"]
    )
    medications = []
    rows = re.findall(
        r"(\d)\s+([\w][\w\s/\-]+?)\s+([\d\-A-Za-z—–]+)\s+([\d\-A-Za-z—–]+)",
        block
    )
    for row in rows:
        name = row[1].strip()
        if name and name.lower() not in ("—", "-", ""):
            medications.append({
                "entry": row[0],
                "product_name": name,
                "therapy_start": row[2].strip() if row[2].strip() not in ("—", "–") else "N/A",
                "therapy_end":   row[3].strip() if row[3].strip() not in ("—", "–") else "N/A",
            })
    return medications if medications else [{"note": "See History / Medical Record"}]


def parse_medical_history(text):
    return {
        "preexisting_conditions": extract_field(text,
            r"Other Relevant History[^:]*:[^\n]*\n([\s\S]+?)(?:\n\s*B\.6|\n\s*C\.|\n\s*D\.)",
            r"Other Relevant History[^:]*\n([\s\S]+?)(?:\n\s*B\.6|\n\s*C\.|\n\s*D\.)"),
    }


def parse_laboratory_tests(text):
    block = extract_block(
        text,
        r"B\.6\s+RELEVANT TEST",
        [r"C\.\s+PRODUCT", r"D\.\s+SUSPECT"]
    )
    block = re.sub(r"Test\s*/\s*Parameter\s+Result.*?(?:Date|Unit)\s*\n", "", block, flags=re.IGNORECASE)

    tests = []
    rows = re.findall(
        r"([\w\s/]+?)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\w/%]+)\s+([\d\-A-Za-z]+)",
        block
    )
    for row in rows:
        tests.append({
            "test_parameter": row[0].strip(),
            "result":         row[1].strip(),
            "low_ref":        row[2].strip(),
            "high_ref":       row[3].strip(),
            "unit":           row[4].strip(),
            "date":           row[5].strip(),
        })

    if not tests:
        alt = re.findall(r"([\w\s/]+?)\s+(High|Low|Positive|Negative)\s+([\d\-A-Za-z]+)", block)
        for row in alt:
            tests.append({
                "test_parameter": row[0].strip(),
                "result":         row[1].strip(),
                "low_ref":        "N/A",
                "high_ref":       "N/A",
                "unit":           "N/A",
                "date":           row[2].strip(),
            })

    return tests


def parse_reporter_information(text):
    block = extract_block(text, r"G\.\s+REPORTER INFORMATION", [r"Submission of a report"])
    return {
        "last_name":           extract_field(block, r"Last Name[:\s]+([\w]+)"),
        "first_name":          extract_field(block, r"First Name[:\s]+([\w]+)"),
        "address":             extract_field(block, r"Address[:\s]+([\w\d\s]+?)(?:\n|City)"),
        "city":                extract_field(block, r"City[:\s]+([\w\s]+?)(?:\n|State)"),
        "state":               extract_field(block, r"State[:\s]+([A-Z]{2})"),
        "zip":                 extract_field(block, r"ZIP[:\s]+([\d]+)"),
        "phone":               extract_field(block, r"Phone[:\s]+([\d\-]+)"),
        "email":               extract_field(block, r"Email[:\s]+([\w\.\@]+)"),
        "occupation":          extract_field(block, r"Occupation[:\s]+([\w\s]+?)(?:\n|Health)"),
        "health_professional": extract_field(block,
            r"Health\s*\nProfessional\?[:\s]+(Yes|No)",
            r"Health Professional\?[:\s]+(Yes|No)",
            r"Health\s+(Yes|No)"),
        "also_reported_to":    extract_field(block, r"Also Reported To[:\s]+([\w\s]+?)(?:\n|Identity)"),
        "identity_disclosed":  extract_field(block,
            r"Identity\s*\nDisclosed\?[:\s]+(Yes|No)",
            r"Identity Disclosed\?[:\s]+(Yes|No)",
            r"Identity\s+(Yes|No)"),
    }


# ─────────────────────────────────────────────
# Step 4: Process every row
# ─────────────────────────────────────────────
output = []

for _, row in data.iterrows():
    file_name = row.get("File Name", "")
    ocr_text  = row.get("OCR Text", "")

    if pd.isna(ocr_text) or str(ocr_text).strip() == "":
        continue

    text = str(ocr_text)

    record = {
        "file_name":               file_name,
        "report_id":               extract_field(text, r"Report ID[:\s]+([\w\-]+)"),
        "patient_information":     parse_patient_information(text),
        "adverse_events":          parse_adverse_events(text),
        "suspect_drug":            parse_suspect_drug(text),
        "concomitant_medications": parse_concomitant_medications(text),
        "medical_history":         parse_medical_history(text),
        "laboratory_tests":        parse_laboratory_tests(text),
        "reporter_information":    parse_reporter_information(text),
    }

    output.append(record)

# ─────────────────────────────────────────────
# Step 5: Save JSON
# ─────────────────────────────────────────────
output_path = "fda_extracted_data.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print(f"Extracted {len(output)} records -> {output_path}")

# ─────────────────────────────────────────────
# Step 6: N/A accuracy check
# ─────────────────────────────────────────────
print("\n===== Patient Information N/A Check =====")
all_clean = True
for i, doc in enumerate(output):
    pi = doc['patient_information']
    fname = doc['file_name']
    nas = [k for k, v in pi.items() if v == 'N/A']
    if nas and fname != 'image.pdf':
        print(f"  ✗ Record {i} ({fname}): missing {nas}")
        all_clean = False
if all_clean:
    print("  All records clean!")
