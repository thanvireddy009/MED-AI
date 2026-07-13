"""
validation_engine.py
─────────────────────
Validates extracted FDA 3500 fields and generates:
  - validation_report.json  (per-record errors)
  - quality_report.json     (overall data quality summary)
"""

import json
import re
from datetime import datetime

INPUT_FILE       = "llm_extracted_data.json"
VALIDATION_FILE  = "validation_report.json"
QUALITY_FILE     = "quality_report.json"

# ─────────────────────────────────────────────
# MANDATORY FIELDS
# ─────────────────────────────────────────────
MANDATORY_FIELDS = [
    ("patient_information", "patient_identifier"),
    ("patient_information", "full_name"),
    ("patient_information", "date_of_birth"),
    ("patient_information", "sex"),
    ("adverse_events", "date_of_event"),
    ("adverse_events", "outcome"),
    ("adverse_events", "event_description"),
    ("suspect_drug", "product_name"),
    ("suspect_drug", "dose_amount"),
    ("reporter_information", "last_name"),
    ("reporter_information", "first_name"),
    ("reporter_information", "occupation"),
]

# Valid values for controlled fields
VALID_SEX     = {"male", "female"}
VALID_OUTCOMES = {
    "death", "life-threatening", "hospitalization",
    "disability or permanent damage",
    "congenital anomaly or birth defect",
    "required intervention to prevent permanent impairment/damage",
    "other serious or important medical events",
}
VALID_ROUTES = {
    "oral", "intravenous", "subcutaneous", "intramuscular",
    "topical", "inhalation", "transdermal", "rectal",
    "ophthalmic", "nasal", "n/a"
}
VALID_UNITS = {"lb", "kg", "mg", "ml", "mcg", "g", "units", "iu", "meq"}

DATE_FORMATS = ["%d-%b-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def is_missing(val):
    return val is None or str(val).strip().lower() in ("", "n/a", "null", "none")


def parse_date(val):
    if is_missing(val):
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(val).strip(), fmt)
        except ValueError:
            continue
    return None


def has_unit(val):
    if is_missing(val):
        return False
    val = str(val).lower()
    return any(unit in val for unit in VALID_UNITS)


def auto_fix(record, field_path, issue_type):
    """Apply simple auto-fixes for common issues."""
    section, field = field_path
    val = record.get(section, {}).get(field, "")

    # Fix: normalize age to include year(s)
    if field == "age" and not is_missing(val):
        numeric = re.sub(r"[^\d]", "", str(val))
        if numeric:
            record[section][field] = f"{numeric} year(s)"
            return f"Auto-fixed: normalized age to '{record[section][field]}'"

    # Fix: normalize weight unit typos (Ib → lb, |b → lb)
    if field == "weight" and not is_missing(val):
        fixed = str(val).replace("Ib", "lb").replace("|b", "lb")
        if fixed != str(val):
            record[section][field] = fixed
            return f"Auto-fixed: normalized weight unit to '{fixed}'"

    # Fix: strip extra whitespace from all fields
    if not is_missing(val):
        stripped = str(val).strip()
        if stripped != str(val):
            record[section][field] = stripped
            return f"Auto-fixed: stripped whitespace"

    return None


# ─────────────────────────────────────────────
# VALIDATION RULES
# ─────────────────────────────────────────────
def validate_record(record):
    errors   = []
    warnings = []
    fixes    = []

    file_name = record.get("file_name", "unknown")

    # Skip non-FDA documents
    if is_missing(record.get("report_id")) and file_name == "image.pdf":
        return errors, warnings, fixes, record

    # ── Rule 1: Mandatory fields cannot be empty ──
    for section, field in MANDATORY_FIELDS:
        val = record.get(section, {}).get(field)
        if is_missing(val):
            errors.append({
                "rule": "MANDATORY_FIELD",
                "field": f"{section}.{field}",
                "message": f"Mandatory field '{field}' is missing or empty",
                "severity": "ERROR"
            })

    # ── Rule 2: Date format validation ──
    date_fields = [
        ("patient_information", "date_of_birth"),
        ("adverse_events", "date_of_event"),
        ("suspect_drug", "therapy_start_date"),
        ("suspect_drug", "therapy_stop_date"),
    ]
    for section, field in date_fields:
        val = record.get(section, {}).get(field)
        if not is_missing(val) and parse_date(val) is None:
            errors.append({
                "rule": "INVALID_DATE_FORMAT",
                "field": f"{section}.{field}",
                "message": f"'{val}' is not a valid date format",
                "severity": "ERROR"
            })

    # ── Rule 3: Therapy end must be after start ──
    start = parse_date(record.get("suspect_drug", {}).get("therapy_start_date"))
    stop  = parse_date(record.get("suspect_drug", {}).get("therapy_stop_date"))
    if start and stop and stop < start:
        errors.append({
            "rule": "DATE_ORDER",
            "field": "suspect_drug.therapy_stop_date",
            "message": f"Therapy stop date ({stop.date()}) is before start date ({start.date()})",
            "severity": "ERROR"
        })

    # ── Rule 4: Age cannot be negative or unrealistic ──
    age_val = record.get("patient_information", {}).get("age", "")
    if not is_missing(age_val):
        numeric = re.sub(r"[^\d]", "", str(age_val))
        if numeric:
            age_num = int(numeric)
            if age_num < 0:
                errors.append({
                    "rule": "INVALID_AGE",
                    "field": "patient_information.age",
                    "message": f"Age cannot be negative: {age_val}",
                    "severity": "ERROR"
                })
            elif age_num > 130:
                errors.append({
                    "rule": "INVALID_AGE",
                    "field": "patient_information.age",
                    "message": f"Age {age_num} is unrealistically high",
                    "severity": "WARNING"
                })
            # Auto-fix age format
            fix = auto_fix(record, ("patient_information", "age"), "age_format")
            if fix:
                fixes.append(fix)

    # ── Rule 5: Weight must include units ──
    weight = record.get("patient_information", {}).get("weight", "")
    if not is_missing(weight):
        if not has_unit(weight):
            warnings.append({
                "rule": "MISSING_UNIT",
                "field": "patient_information.weight",
                "message": f"Weight '{weight}' is missing unit (lb/kg)",
                "severity": "WARNING"
            })
        # Auto-fix weight unit typos
        fix = auto_fix(record, ("patient_information", "weight"), "unit_typo")
        if fix:
            fixes.append(fix)

    # ── Rule 6: Sex must be valid value ──
    sex = record.get("patient_information", {}).get("sex", "")
    if not is_missing(sex) and str(sex).lower() not in VALID_SEX:
        errors.append({
            "rule": "INVALID_VALUE",
            "field": "patient_information.sex",
            "message": f"Sex '{sex}' is not valid. Expected: male/female",
            "severity": "ERROR"
        })

    # ── Rule 7: Outcome must be a recognized value ──
    outcome = record.get("adverse_events", {}).get("outcome", "")
    if not is_missing(outcome):
        outcome_lower = str(outcome).lower()
        if not any(v in outcome_lower for v in VALID_OUTCOMES):
            warnings.append({
                "rule": "UNRECOGNIZED_OUTCOME",
                "field": "adverse_events.outcome",
                "message": f"Outcome '{outcome}' is not a standard FDA MedWatch value",
                "severity": "WARNING"
            })

    # ── Rule 8: Dose amount should include units ──
    dose = record.get("suspect_drug", {}).get("dose_amount", "")
    if not is_missing(dose) and not has_unit(dose):
        warnings.append({
            "rule": "MISSING_UNIT",
            "field": "suspect_drug.dose_amount",
            "message": f"Dose amount '{dose}' is missing unit (mg/ml/mcg etc.)",
            "severity": "WARNING"
        })

    # ── Rule 9: NDC format validation (should match ##########-###-##) ──
    ndc = record.get("suspect_drug", {}).get("ndc_unique_id", "")
    if not is_missing(ndc) and ndc.lower() != "n/a":
        if not re.match(r"^\d{5}-\d{3,4}-\d{2}$", str(ndc).strip()):
            warnings.append({
                "rule": "INVALID_NDC_FORMAT",
                "field": "suspect_drug.ndc_unique_id",
                "message": f"NDC '{ndc}' does not match expected format (XXXXX-XXX-XX)",
                "severity": "WARNING"
            })

    # ── Rule 10: Route must be a recognized value ──
    route = record.get("suspect_drug", {}).get("route", "")
    if not is_missing(route) and str(route).lower() not in VALID_ROUTES:
        warnings.append({
            "rule": "UNRECOGNIZED_ROUTE",
            "field": "suspect_drug.route",
            "message": f"Route '{route}' is not a standard value",
            "severity": "WARNING"
        })

    # ── Rule 11: Report ID format ──
    report_id = record.get("report_id", "")
    if not is_missing(report_id):
        if not re.match(r"FDA-3500-PT-\d{4}-\d{3,4}", str(report_id)):
            warnings.append({
                "rule": "INVALID_REPORT_ID",
                "field": "report_id",
                "message": f"Report ID '{report_id}' does not match expected format",
                "severity": "WARNING"
            })

    return errors, warnings, fixes, record


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def run():
    records = json.load(open(INPUT_FILE, encoding="utf-8"))

    validation_results = []
    quality_summary = {
        "total_records": len(records),
        "valid_records": 0,
        "records_with_errors": 0,
        "records_with_warnings": 0,
        "auto_fixes_applied": 0,
        "error_breakdown": {},
        "warning_breakdown": {},
        "field_completeness": {},
    }

    all_fields = [f"{s}.{f}" for s, f in MANDATORY_FIELDS]
    field_present = {f: 0 for f in all_fields}

    for record in records:
        if record.get("error"):
            continue

        errors, warnings, fixes, fixed_record = validate_record(record)

        status = "VALID" if not errors else "INVALID"
        if not errors and warnings:
            status = "VALID_WITH_WARNINGS"

        result = {
            "file_name": record.get("file_name"),
            "status": status,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "auto_fixes": fixes,
            "errors": errors,
            "warnings": warnings,
        }
        validation_results.append(result)

        # Update quality summary
        if not errors:
            quality_summary["valid_records"] += 1
        else:
            quality_summary["records_with_errors"] += 1
        if warnings:
            quality_summary["records_with_warnings"] += 1
        quality_summary["auto_fixes_applied"] += len(fixes)

        # Error breakdown
        for e in errors:
            rule = e["rule"]
            quality_summary["error_breakdown"][rule] = quality_summary["error_breakdown"].get(rule, 0) + 1
        for w in warnings:
            rule = w["rule"]
            quality_summary["warning_breakdown"][rule] = quality_summary["warning_breakdown"].get(rule, 0) + 1

        # Field completeness
        for section, field in MANDATORY_FIELDS:
            key = f"{section}.{field}"
            val = fixed_record.get(section, {}).get(field)
            if not is_missing(val):
                field_present[key] += 1

    # Calculate field completeness %
    total = quality_summary["total_records"]
    for field, count in field_present.items():
        quality_summary["field_completeness"][field] = f"{count/total*100:.1f}%"

    # Save validation report
    with open(VALIDATION_FILE, "w", encoding="utf-8") as f:
        json.dump(validation_results, f, indent=4)

    # Save quality report
    with open(QUALITY_FILE, "w", encoding="utf-8") as f:
        json.dump(quality_summary, f, indent=4)

    # Print summary
    print(f"\n{'='*55}")
    print(f"VALIDATION REPORT")
    print(f"{'='*55}")
    print(f"Total records:          {quality_summary['total_records']}")
    print(f"Valid records:          {quality_summary['valid_records']}")
    print(f"Records with errors:    {quality_summary['records_with_errors']}")
    print(f"Records with warnings:  {quality_summary['records_with_warnings']}")
    print(f"Auto-fixes applied:     {quality_summary['auto_fixes_applied']}")

    print(f"\nError breakdown:")
    for rule, count in quality_summary["error_breakdown"].items():
        print(f"  {rule}: {count}")

    print(f"\nWarning breakdown:")
    for rule, count in quality_summary["warning_breakdown"].items():
        print(f"  {rule}: {count}")

    print(f"\nField completeness:")
    for field, pct in quality_summary["field_completeness"].items():
        icon = "✓" if float(pct.replace("%","")) >= 90 else "✗"
        print(f"  {icon} {field:<45} {pct}")

    print(f"\nReports saved:")
    print(f"  {VALIDATION_FILE}")
    print(f"  {QUALITY_FILE}")


if __name__ == "__main__":
    run()
