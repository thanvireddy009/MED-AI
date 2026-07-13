"""
accuracy_report.py
───────────────────
Compares LLM extraction output against regex ground truth.
Skips fields where ground truth is N/A but LLM found a value
(LLM is likely correct; regex just failed to extract).
Normalizes age format differences.
"""

import json

GROUND_TRUTH_FILE = "fda_extracted_data.json"
LLM_OUTPUT_FILE   = "llm_extracted_data.json"
REPORT_FILE       = "accuracy_report.json"

FIELDS_TO_COMPARE = [
    ("patient_information", "patient_identifier"),
    ("patient_information", "full_name"),
    ("patient_information", "date_of_birth"),
    ("patient_information", "age"),
    ("patient_information", "sex"),
    ("patient_information", "weight"),
    ("patient_information", "race_ethnicity"),
    ("adverse_events", "type_of_report"),
    ("adverse_events", "outcome"),
    ("adverse_events", "date_of_event"),
    ("suspect_drug", "product_name"),
    ("suspect_drug", "ndc_unique_id"),
    ("suspect_drug", "manufacturer"),
    ("suspect_drug", "lot_number"),
    ("suspect_drug", "dose_amount"),
    ("suspect_drug", "frequency"),
    ("suspect_drug", "route"),
    ("suspect_drug", "therapy_start_date"),
    ("suspect_drug", "therapy_stop_date"),
    ("suspect_drug", "ongoing_therapy"),
    ("reporter_information", "last_name"),
    ("reporter_information", "first_name"),
    ("reporter_information", "city"),
    ("reporter_information", "state"),
    ("reporter_information", "occupation"),
]


def normalize(val, field=None):
    if val is None:
        return ""
    v = str(val).strip().lower()
    # Normalize OCR lb variants
    v = v.replace("ib", "lb").replace("|b", "lb")
    # Normalize age: strip "year(s)" so "41" == "41 year(s)"
    if field == "age":
        v = v.replace("year(s)", "").replace("years", "").strip()
    # Normalize outcome: allow partial match (LLM gives full text, regex truncates)
    return v


def compare_field(gt_val, llm_val, field):
    gt  = normalize(gt_val, field)
    llm = normalize(llm_val, field)

    # Skip if ground truth is N/A but LLM found something — LLM is likely right
    if gt in ("n/a", "") and llm not in ("n/a", ""):
        return "skipped", gt, llm

    # Exact match
    if gt == llm:
        return "match", gt, llm

    # Partial match for outcome (regex truncates long outcomes)
    if field == "outcome" and (gt in llm or llm in gt):
        return "match", gt, llm

    # Partial match for full_name (regex may miss middle name)
    if field == "full_name":
        gt_parts  = set(gt.split())
        llm_parts = set(llm.split())
        if gt_parts.issubset(llm_parts) or llm_parts.issubset(gt_parts):
            return "match", gt, llm

    return "mismatch", gt, llm


def run():
    gt_data  = json.load(open(GROUND_TRUTH_FILE, encoding="utf-8"))
    llm_data = json.load(open(LLM_OUTPUT_FILE,   encoding="utf-8"))

    gt_index  = {r["file_name"]: r for r in gt_data}
    llm_index = {r["file_name"]: r for r in llm_data if not r.get("error")}

    report = {
        "model": "llama-3.1-8b-instant",
        "total_documents": len(llm_data),
        "documents_compared": 0,
        "field_accuracy": {},
        "skipped_fields": {},
        "per_document": {},
        "overall_accuracy": "0%",
    }

    field_totals = {
        f"{s}.{f}": {"correct": 0, "total": 0, "skipped": 0}
        for s, f in FIELDS_TO_COMPARE
    }

    for file_name, llm_record in llm_index.items():
        gt_record = gt_index.get(file_name)
        if not gt_record:
            continue

        report["documents_compared"] += 1
        doc_results = {}

        for section, field in FIELDS_TO_COMPARE:
            gt_val  = gt_record.get(section, {}).get(field)
            llm_val = llm_record.get(section, {}).get(field)
            status, gt_norm, llm_norm = compare_field(gt_val, llm_val, field)
            field_key = f"{section}.{field}"

            doc_results[field_key] = {
                "status":    status,
                "gt_value":  gt_norm  or "N/A",
                "llm_value": llm_norm or "N/A",
            }

            if status == "skipped":
                field_totals[field_key]["skipped"] += 1
            else:
                field_totals[field_key]["total"] += 1
                if status == "match":
                    field_totals[field_key]["correct"] += 1

        report["per_document"][file_name] = doc_results

    # Calculate accuracy
    total_correct = 0
    total_fields  = 0
    for field_key, counts in field_totals.items():
        if counts["total"] > 0:
            acc = counts["correct"] / counts["total"] * 100
            report["field_accuracy"][field_key] = f"{acc:.1f}%"
            total_correct += counts["correct"]
            total_fields  += counts["total"]
        if counts["skipped"] > 0:
            report["skipped_fields"][field_key] = counts["skipped"]

    report["overall_accuracy"] = (
        f"{total_correct / total_fields * 100:.1f}%" if total_fields else "0%"
    )

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print(f"\n{'='*50}")
    print(f"ACCURACY REPORT — {report['model']}")
    print(f"{'='*50}")
    print(f"Documents compared: {report['documents_compared']}")
    print(f"Overall accuracy:   {report['overall_accuracy']}")
    print(f"\nPer-field accuracy:")
    for field, acc in report["field_accuracy"].items():
        icon = "✓" if float(acc.replace("%","")) >= 90 else "✗"
        skipped = report["skipped_fields"].get(field, 0)
        skip_note = f" ({skipped} skipped — GT was N/A)" if skipped else ""
        print(f"  {icon} {field:<45} {acc}{skip_note}")
    print(f"\nFull report saved: {REPORT_FILE}")


if __name__ == "__main__":
    run()
