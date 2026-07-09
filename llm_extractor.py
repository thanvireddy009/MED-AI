"""
llm_extractor.py
─────────────────
Reads ocr_text_output.txt (produced by datafetch.py),
sends each document to Groq (Llama 3 8B) for structured extraction,
saves results to llm_extracted_data.json
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
CLIENT      = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL       = "llama-3.1-8b-instant"
INPUT_FILE  = "ocr_text_output.txt"
OUTPUT_FILE = "llm_extracted_data.json"

# ─────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────
PROMPT = """Extract fields from this FDA 3500 MedWatch adverse event report. Return ONLY valid JSON, no explanation, no markdown, no backticks.

Use this exact structure. Use null for any missing field:

{
  "report_id": "",
  "patient_information": {
    "patient_identifier": "", "full_name": "", "date_of_birth": "",
    "age": "", "sex": "", "weight": "", "race_ethnicity": ""
  },
  "adverse_events": {
    "type_of_report": "", "outcome": "", "date_of_event": "",
    "event_description": "", "medical_history_preexisting": ""
  },
  "suspect_drug": {
    "product_name": "", "ndc_unique_id": "", "manufacturer": "",
    "lot_number": "", "dose_amount": "", "frequency": "", "route": "",
    "indication": "", "therapy_start_date": "", "therapy_stop_date": "",
    "event_abated_after_stop": "", "event_reappeared_after_reintro": "",
    "product_type": "", "ongoing_therapy": ""
  },
  "concomitant_medications": [{"product_name": "", "therapy_start": "", "therapy_end": ""}],
  "medical_history": {"preexisting_conditions": ""},
  "laboratory_tests": [{"test_parameter": "", "result": "", "low_ref": "", "high_ref": "", "unit": "", "date": ""}],
  "reporter_information": {
    "last_name": "", "first_name": "", "address": "", "city": "",
    "state": "", "zip": "", "phone": "", "email": "",
    "occupation": "", "health_professional": "", "also_reported_to": "", "identity_disclosed": ""
  }
}

Document:
{OCR_TEXT}"""


# ─────────────────────────────────────────────
# Parse documents from txt file
# ─────────────────────────────────────────────
def parse_txt_file(filepath):
    """Split ocr_text_output.txt into individual documents by === FILE: === headers."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    sections = re.split(r"={80}\nFILE: (.+?)\n={80}", content)

    documents = []
    for i in range(1, len(sections), 2):
        file_name = sections[i].strip()
        text      = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if text:
            documents.append({"file_name": file_name, "text": text})

    return documents


# ─────────────────────────────────────────────
# Call Groq
# ─────────────────────────────────────────────
def call_groq(ocr_text):
    try:
        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical document extraction specialist. Always return valid JSON only. The patient_identifier is the patient ID code like PT-2025-001, NOT the word Conf or any label text."
                },
                {
                    "role": "user",
                    "content": PROMPT.replace("{OCR_TEXT}", ocr_text)
                }
            ],
            temperature=0,
            max_tokens=2048,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if model adds them
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        # Find JSON object in response
        json_match = re.search(r'\{[\s\S]+\}', raw)
        if json_match:
            raw = json_match.group(0)

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        print(f"  Raw preview: {raw[:300] if 'raw' in dir() else 'N/A'}")
        return None
    except Exception as e:
        print(f"  ✗ Groq API error: {e}")
        return None


# ─────────────────────────────────────────────
# Normalize output
# ─────────────────────────────────────────────
def normalize(obj):
    if isinstance(obj, dict):
        return {k: normalize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize(i) for i in obj]
    elif obj is None or (isinstance(obj, str) and obj.strip() == ""):
        return "N/A"
    return obj


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def run_extraction():
    print(f"Reading documents from: {INPUT_FILE}")
    documents = parse_txt_file(INPUT_FILE)
    print(f"Found {len(documents)} documents\n")

    results = []
    failed  = []

    for i, doc in enumerate(documents, 1):
        file_name = doc["file_name"]
        ocr_text  = doc["text"]

        print(f"[{i}/{len(documents)}] {file_name}")

        extracted = call_groq(ocr_text)

        if extracted:
            extracted = normalize(extracted)
            extracted["file_name"] = file_name
            results.append(extracted)
            name = extracted.get("patient_information", {}).get("full_name", "N/A")
            print(f"  ✓ Extracted — patient: {name}")
        else:
            failed.append(file_name)
            results.append({
                "file_name": file_name,
                "error": "LLM extraction failed",
                "patient_information": {}
            })
            print(f"  ✗ Failed")

        # Save after every doc so progress isn't lost
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Done: {len(results) - len(failed)}/{len(documents)} succeeded")
    print(f"Output saved to: {OUTPUT_FILE}")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    run_extraction()
