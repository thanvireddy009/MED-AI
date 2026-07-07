"""
db.py
──────
Uploads fda_extracted_data.json into Neon Postgres, one column per field
(not just a JSONB blob) — run schema.sql once first.
 
Writes to three tables:
  - adverse_event_reports    one row per report, every scalar field broken
                              out into its own column (plus a `report`
                              JSONB column kept as a full backup copy)
  - concomitant_medications  0-or-more rows per report
  - laboratory_tests         0-or-more rows per report
 
Re-running this is safe: each report's row is upserted (ON CONFLICT ...
DO UPDATE), and its child rows are deleted and re-inserted fresh each time
so you never end up with duplicate/stale medication or lab-test rows from
a prior run.
 
Each report is committed independently, so one bad record can't roll back
everything else — you get a clear per-report count at the end instead of
a single opaque failure.
"""
 
import os
import json
import psycopg
 
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_PoqTtpQ7M2ln@ep-proud-fog-atsgo3lt-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
)
 
INPUT_JSON = "fda_extracted_data.json"
 
 
def na_if_blank(v):
    """Normalize missing values consistently; keeps 'N/A' sentinel text as-is
    since that's what your extractor already uses throughout."""
    if v is None:
        return None
    v = str(v).strip()
    return v if v else None
 
 
def upsert_report(cur, report: dict):
    pi = report.get("patient_information", {}) or {}
    ae = report.get("adverse_events", {}) or {}
    sd = report.get("suspect_drug", {}) or {}
    mh = report.get("medical_history", {}) or {}
    ri = report.get("reporter_information", {}) or {}
 
    cur.execute(
        """
        INSERT INTO adverse_event_reports (
            report_id, file_name,
            patient_identifier, full_name, date_of_birth, age, sex, weight, race_ethnicity,
            type_of_report, outcome, date_of_event, date_of_report, event_description, medical_history_preexisting,
            product_name, ndc_unique_id, manufacturer, lot_number, dose_amount, frequency, route,
            indication, therapy_start_date, therapy_stop_date, event_abated_after_stop,
            event_reappeared_after_reintro, product_type, ongoing_therapy,
            preexisting_conditions,
            reporter_last_name, reporter_first_name, reporter_address, reporter_city, reporter_state,
            reporter_zip, reporter_phone, reporter_email, reporter_occupation,
            reporter_health_professional, reporter_also_reported_to, reporter_identity_disclosed,
            report, updated_at
        )
        VALUES (
            %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, now()
        )
        ON CONFLICT (report_id) DO UPDATE SET
            file_name                      = EXCLUDED.file_name,
            patient_identifier             = EXCLUDED.patient_identifier,
            full_name                      = EXCLUDED.full_name,
            date_of_birth                  = EXCLUDED.date_of_birth,
            age                            = EXCLUDED.age,
            sex                            = EXCLUDED.sex,
            weight                         = EXCLUDED.weight,
            race_ethnicity                 = EXCLUDED.race_ethnicity,
            type_of_report                 = EXCLUDED.type_of_report,
            outcome                        = EXCLUDED.outcome,
            date_of_event                  = EXCLUDED.date_of_event,
            date_of_report                 = EXCLUDED.date_of_report,
            event_description              = EXCLUDED.event_description,
            medical_history_preexisting    = EXCLUDED.medical_history_preexisting,
            product_name                   = EXCLUDED.product_name,
            ndc_unique_id                  = EXCLUDED.ndc_unique_id,
            manufacturer                   = EXCLUDED.manufacturer,
            lot_number                     = EXCLUDED.lot_number,
            dose_amount                    = EXCLUDED.dose_amount,
            frequency                      = EXCLUDED.frequency,
            route                          = EXCLUDED.route,
            indication                     = EXCLUDED.indication,
            therapy_start_date             = EXCLUDED.therapy_start_date,
            therapy_stop_date              = EXCLUDED.therapy_stop_date,
            event_abated_after_stop        = EXCLUDED.event_abated_after_stop,
            event_reappeared_after_reintro = EXCLUDED.event_reappeared_after_reintro,
            product_type                   = EXCLUDED.product_type,
            ongoing_therapy                = EXCLUDED.ongoing_therapy,
            preexisting_conditions         = EXCLUDED.preexisting_conditions,
            reporter_last_name             = EXCLUDED.reporter_last_name,
            reporter_first_name            = EXCLUDED.reporter_first_name,
            reporter_address               = EXCLUDED.reporter_address,
            reporter_city                  = EXCLUDED.reporter_city,
            reporter_state                 = EXCLUDED.reporter_state,
            reporter_zip                   = EXCLUDED.reporter_zip,
            reporter_phone                 = EXCLUDED.reporter_phone,
            reporter_email                 = EXCLUDED.reporter_email,
            reporter_occupation            = EXCLUDED.reporter_occupation,
            reporter_health_professional   = EXCLUDED.reporter_health_professional,
            reporter_also_reported_to      = EXCLUDED.reporter_also_reported_to,
            reporter_identity_disclosed    = EXCLUDED.reporter_identity_disclosed,
            report                         = EXCLUDED.report,
            updated_at                     = now()
        RETURNING (xmax = 0) AS inserted
        """,
        (
            report.get("report_id"), report.get("file_name"),
            na_if_blank(pi.get("patient_identifier")), na_if_blank(pi.get("full_name")),
            na_if_blank(pi.get("date_of_birth")), na_if_blank(pi.get("age")),
            na_if_blank(pi.get("sex")), na_if_blank(pi.get("weight")), na_if_blank(pi.get("race_ethnicity")),
            na_if_blank(ae.get("type_of_report")), na_if_blank(ae.get("outcome")),
            na_if_blank(ae.get("date_of_event")), na_if_blank(ae.get("date_of_report")),
            na_if_blank(ae.get("event_description")), na_if_blank(ae.get("medical_history_preexisting")),
            na_if_blank(sd.get("product_name")), na_if_blank(sd.get("ndc_unique_id")),
            na_if_blank(sd.get("manufacturer")), na_if_blank(sd.get("lot_number")),
            na_if_blank(sd.get("dose_amount")), na_if_blank(sd.get("frequency")), na_if_blank(sd.get("route")),
            na_if_blank(sd.get("indication")), na_if_blank(sd.get("therapy_start_date")),
            na_if_blank(sd.get("therapy_stop_date")), na_if_blank(sd.get("event_abated_after_stop")),
            na_if_blank(sd.get("event_reappeared_after_reintro")), na_if_blank(sd.get("product_type")),
            na_if_blank(sd.get("ongoing_therapy")),
            na_if_blank(mh.get("preexisting_conditions")),
            na_if_blank(ri.get("last_name")), na_if_blank(ri.get("first_name")),
            na_if_blank(ri.get("address")), na_if_blank(ri.get("city")), na_if_blank(ri.get("state")),
            na_if_blank(ri.get("zip")), na_if_blank(ri.get("phone")), na_if_blank(ri.get("email")),
            na_if_blank(ri.get("occupation")), na_if_blank(ri.get("health_professional")),
            na_if_blank(ri.get("also_reported_to")), na_if_blank(ri.get("identity_disclosed")),
            json.dumps(report),
        ),
    )
    return cur.fetchone()[0]
 
 
def replace_child_rows(cur, report_id: str, report: dict):
    cur.execute("DELETE FROM concomitant_medications WHERE report_id = %s", (report_id,))
    for med in report.get("concomitant_medications", []) or []:
        cur.execute(
            """
            INSERT INTO concomitant_medications (report_id, entry, product_name, therapy_start, therapy_end, note)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                report_id,
                med.get("entry"), med.get("product_name"),
                med.get("therapy_start"), med.get("therapy_end"), med.get("note"),
            ),
        )
 
    cur.execute("DELETE FROM laboratory_tests WHERE report_id = %s", (report_id,))
    for test in report.get("laboratory_tests", []) or []:
        cur.execute(
            """
            INSERT INTO laboratory_tests (report_id, test_parameter, result, low_ref, high_ref, unit, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                report_id,
                test.get("test_parameter"), test.get("result"),
                test.get("low_ref"), test.get("high_ref"), test.get("unit"), test.get("date"),
            ),
        )
 
 
def main():
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
 
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        reports = json.load(f)
 
    inserted, updated, failed = 0, 0, 0
    meds_total, labs_total = 0, 0
 
    for report in reports:
        report_id = report.get("report_id")
        try:
            was_insert = upsert_report(cur, report)
            replace_child_rows(cur, report_id, report)
            conn.commit()
 
            if was_insert:
                inserted += 1
            else:
                updated += 1
            meds_total += len(report.get("concomitant_medications", []) or [])
            labs_total += len(report.get("laboratory_tests", []) or [])
        except Exception as e:
            failed += 1
            print(f"✗ Failed on {report.get('file_name')} ({report_id}): {e}")
            conn.rollback()
            continue
 
    cur.close()
    conn.close()
 
    print(
        f"✓ Upload complete — reports inserted: {inserted}, updated: {updated}, failed: {failed}, "
        f"total: {len(reports)} | medication rows: {meds_total}, lab test rows: {labs_total}"
    )
 
 
if __name__ == "__main__":
    main()
 