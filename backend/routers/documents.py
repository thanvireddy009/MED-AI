import os
import json
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from core.database import get_connection
from core.auth import get_current_user, require_role
from core.audit import log_action

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# llm_extracted_data.json path kept for local dev fallback only
LLM_JSON_PATH = Path(__file__).resolve().parents[3] / "llm_extracted_data.json"


def load_llm_data(file_name: str):
    """Load extracted data from DB first, fall back to local JSON file."""
    # Try DB first (works in production)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT extracted_data FROM llm_extracted_data WHERE file_name = %s", (file_name,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row["extracted_data"]
    except Exception as e:
        logger.warning(f"DB lookup for llm data failed: {e}")

    # Fall back to local JSON (local dev without seeding)
    if LLM_JSON_PATH.exists():
        with open(LLM_JSON_PATH, "r") as f:
            data = json.load(f)
        return next((d for d in data if d["file_name"] == file_name), None)

    return None


def sync_to_json(file_name: str, updated_data: dict) -> bool:
    """Write edited data back into DB (and local JSON if present)."""
    synced = False

    # Update DB
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO llm_extracted_data (file_name, extracted_data)
            VALUES (%s, %s)
            ON CONFLICT (file_name) DO UPDATE
                SET extracted_data = EXCLUDED.extracted_data,
                    updated_at = NOW()
        """, (file_name, json.dumps({**updated_data, "file_name": file_name})))
        conn.commit()
        cur.close()
        conn.close()
        synced = True
    except Exception as e:
        logger.error(f"sync_to_json DB update failed: {e}")

    # Also update local JSON if it exists (local dev)
    try:
        if LLM_JSON_PATH.exists():
            with open(LLM_JSON_PATH, "r") as f:
                all_data = json.load(f)
            idx = next((i for i, d in enumerate(all_data) if d["file_name"] == file_name), -1)
            if idx != -1:
                all_data[idx] = {**updated_data, "file_name": file_name}
                with open(LLM_JSON_PATH, "w") as f:
                    json.dump(all_data, f, indent=4)
    except Exception as e:
        logger.warning(f"sync_to_json local file update failed: {e}")

    return synced


# ── POST /api/documents/upload ───────────────────────────────────────────────
@router.post("/documents/upload", summary="Upload a PDF document")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(require_role("reviewer")),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    doc_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{doc_id}-{file.filename}"

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    extracted = load_llm_data(file.filename)
    status = "pending"  # Always pending — reviewer decides to approve or reject

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documents (id, file_name, file_path, status, extracted_data)
        VALUES (%s, %s, %s, %s, %s) RETURNING *
        """,
        (doc_id, file.filename, str(file_path), status, json.dumps(extracted) if extracted else None),
    )
    doc = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    log_action(user["username"], "UPLOAD", "document", doc_id, {"file": file.filename}, request.client.host)
    logger.info(f"Uploaded: {file.filename} by {user['username']}")
    return doc


# ── GET /api/documents ────────────────────────────────────────────────────────
@router.get("/documents", summary="List all documents")
def list_documents(user: dict = Depends(require_role("reviewer"))):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, file_name, upload_date, status, review_notes FROM documents ORDER BY upload_date DESC")
    docs = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return docs


# ── GET /api/documents/approved ───────────────────────────────────────────────
@router.get("/documents/approved", summary="List approved documents")
def list_approved(user: dict = Depends(require_role("doctor"))):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, file_name, upload_date, validated_data FROM documents WHERE status = 'approved' ORDER BY upload_date DESC"
    )
    docs = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return docs


# ── GET /api/documents/search ─────────────────────────────────────────────────
@router.get("/documents/search", summary="Search approved documents")
def search_documents(query: str, user: dict = Depends(require_role("doctor"))):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, file_name, upload_date, status, validated_data, extracted_data
        FROM documents
        WHERE status = 'approved'
        AND (
            validated_data->'patient_information'->>'full_name' ILIKE %s
            OR validated_data->'patient_information'->>'patient_identifier' ILIKE %s
            OR extracted_data->'patient_information'->>'full_name' ILIKE %s
            OR extracted_data->'patient_information'->>'patient_identifier' ILIKE %s
        )
        ORDER BY upload_date DESC
        """,
        (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"),
    )
    results = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return results


# ── GET /api/documents/:id ────────────────────────────────────────────────────
@router.get("/documents/{document_id}", summary="Get a single document")
def get_document(document_id: str, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    cur.close()
    conn.close()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    document = dict(doc)
    # Doctors can only retrieve approved reports; reviewers and admins can review any report.
    if user["role"] == "doctor" and document["status"] != "approved":
        raise HTTPException(status_code=403, detail="Doctors can only access approved documents")
    return document


# ── POST /api/documents/:id/load-extracted ────────────────────────────────────
@router.post("/documents/{document_id}/load-extracted", summary="Load extracted data from JSON")
def load_extracted(document_id: str, request: Request, user: dict = Depends(require_role("reviewer"))):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    extracted = load_llm_data(doc["file_name"])
    if not extracted:
        raise HTTPException(status_code=404, detail=f"No extracted data found for {doc['file_name']}")

    cur.execute(
        "UPDATE documents SET extracted_data = %s, status = 'reviewed' WHERE id = %s RETURNING *",
        (json.dumps(extracted), document_id),
    )
    updated = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    log_action(user["username"], "LOAD_EXTRACTED", "document", document_id, {}, request.client.host)
    return updated


# ── PUT /api/documents/:id/data ───────────────────────────────────────────────
class UpdateData(BaseModel):
    extracted_data: Optional[dict] = None
    validated_data: Optional[dict] = None
    review_notes: Optional[str] = None


@router.put("/documents/{document_id}/data", summary="Save edited document data")
def update_document_data(
    document_id: str,
    body: UpdateData,
    request: Request,
    user: dict = Depends(require_role("reviewer")),
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE documents
        SET extracted_data = COALESCE(%s::jsonb, extracted_data),
            validated_data = COALESCE(%s::jsonb, validated_data),
            review_notes   = COALESCE(%s, review_notes)
        WHERE id = %s RETURNING *
        """,
        (
            json.dumps(body.extracted_data) if body.extracted_data else None,
            json.dumps(body.validated_data) if body.validated_data else None,
            body.review_notes,
            document_id,
        ),
    )
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="Document not found")

    updated = dict(updated)
    # Sync back to llm_extracted_data.json
    sync_data = body.validated_data or body.extracted_data
    if sync_data:
        synced = sync_to_json(updated["file_name"], sync_data)
        updated["json_synced"] = synced

    log_action(user["username"], "UPDATE", "document", document_id, {}, request.client.host)
    return updated


# ── PUT /api/documents/:id/approve ────────────────────────────────────────────
class ApproveBody(BaseModel):
    notes: Optional[str] = None
    updated_data: Optional[dict] = None


@router.put("/documents/{document_id}/approve", summary="Approve a document")
def approve_document(
    document_id: str,
    body: ApproveBody,
    request: Request,
    user: dict = Depends(require_role("reviewer")),
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    final_data = body.updated_data or doc["extracted_data"]

    cur.execute(
        """
        INSERT INTO review_history (document_id, action, previous_data, updated_data, reviewer, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            document_id, "approved",
            json.dumps(dict(doc["extracted_data"]) if doc["extracted_data"] else {}),
            json.dumps(final_data),
            user["username"], body.notes,
        ),
    )
    cur.execute(
        "UPDATE documents SET status = 'approved', review_notes = %s, validated_data = %s WHERE id = %s RETURNING *",
        (body.notes, json.dumps(final_data), document_id),
    )
    updated = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    sync_to_json(updated["file_name"], final_data if isinstance(final_data, dict) else dict(final_data))
    log_action(user["username"], "APPROVE", "document", document_id, {"notes": body.notes}, request.client.host)
    return updated


# ── PUT /api/documents/:id/reject ─────────────────────────────────────────────
class RejectBody(BaseModel):
    notes: str


@router.put("/documents/{document_id}/reject", summary="Reject a document")
def reject_document(
    document_id: str,
    body: RejectBody,
    request: Request,
    user: dict = Depends(require_role("reviewer")),
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    cur.execute(
        """
        INSERT INTO review_history (document_id, action, previous_data, reviewer, notes)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            document_id, "rejected",
            json.dumps(dict(doc["extracted_data"]) if doc["extracted_data"] else {}),
            user["username"], body.notes,
        ),
    )
    cur.execute(
        "UPDATE documents SET status = 'rejected', review_notes = %s WHERE id = %s RETURNING *",
        (body.notes, document_id),
    )
    updated = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    log_action(user["username"], "REJECT", "document", document_id, {"notes": body.notes}, request.client.host)
    return updated


# ── DELETE /api/documents/:id ─────────────────────────────────────────────────
@router.delete("/documents/{document_id}", summary="Delete a document")
def delete_document(document_id: str, request: Request, user: dict = Depends(require_role("reviewer"))):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM review_history WHERE document_id = %s", (document_id,))
    cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
    conn.commit()
    cur.close()
    conn.close()
    log_action(user["username"], "DELETE", "document", document_id, {}, request.client.host)
    return {"message": "Document deleted"}


# ── GET /api/reviews ──────────────────────────────────────────────────────────
@router.get("/reviews", summary="Get all review history")
def get_all_reviews(user: dict = Depends(require_role("reviewer"))):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rh.*, d.file_name
        FROM review_history rh
        JOIN documents d ON rh.document_id = d.id
        ORDER BY rh.reviewed_at DESC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


# ── GET /api/reviews/:document_id ────────────────────────────────────────────
@router.get("/reviews/{document_id}", summary="Get review history for a document")
def get_document_reviews(document_id: str, user: dict = Depends(require_role("reviewer"))):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM review_history WHERE document_id = %s ORDER BY reviewed_at DESC",
        (document_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


# ── GET /api/audit-logs ───────────────────────────────────────────────────────
@router.get("/audit-logs", summary="Get audit logs (admin only)")
def get_audit_logs(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 500")
    logs = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return logs
