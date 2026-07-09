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

def normalize(val):
    if val is None:
        return ""
    v = str(val).strip().lower().replace("  ", " ").replace("ib", "lb")
    v = v.replace(" year(s)", "").replace(" years", "")
    return v

def compare_records(gt, llm):
    results = {}
    for section, field in FIELDS_TO_COMPARE:
        gt_val  = normalize(gt.get(section, {}).get(field))
        llm_val = normalize(llm.get(section, {}).get(field))
        # Skip if ground truth is n/a — regex didn't capture it, LLM may be correct
        if gt_val in ("n/a", ""):
            continue
        match = gt_val == llm_val
        results[f"{section}.{field}"] = {
            "match":     match,
            "gt_value":  gt_val,
            "llm_value": llm_val or "N/A",
        }
    return results

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
        "per_document": {},
        "overall_accuracy": "0%",
    }

    field_totals = {}

    for file_name, llm_record in llm_index.items():
        gt_record = gt_index.get(file_name)
        if not gt_record:
            continue
        comparison = compare_records(gt_record, llm_record)
        report["per_document"][file_name] = comparison
        report["documents_compared"] += 1
        for field_key, result in comparison.items():
            if field_key not in field_totals:
                field_totals[field_key] = {"correct": 0, "total": 0}
            field_totals[field_key]["total"] += 1
            if result["match"]:
                field_totals[field_key]["correct"] += 1

    total_correct = 0
    total_fields  = 0
    for field_key, counts in field_totals.items():
        if counts["total"] > 0:
            acc = counts["correct"] / counts["total"] * 100
            report["field_accuracy"][field_key] = f"{acc:.1f}%"
            total_correct += counts["correct"]
            total_fields  += counts["total"]

    report["overall_accuracy"] = f"{total_correct / total_fields * 100:.1f}%" if total_fields else "0%"

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print(f"\n{'='*50}")
    print(f"ACCURACY REPORT — {report['model']}")
    print(f"{'='*50}")
    print(f"Documents compared: {report['documents_compared']}")
    print(f"Overall accuracy:   {report['overall_accuracy']}")
    print(f"\nPer-field accuracy:")
    for field, acc in report["field_accuracy"].items():
        pct = float(acc.replace("%",""))
        icon = "✓" if pct >= 90 else "~" if pct >= 70 else "✗"
        print(f"  {icon} {field:<45} {acc}")
    print(f"\nFull report saved: {REPORT_FILE}")

if __name__ == "__main__":
    run()
