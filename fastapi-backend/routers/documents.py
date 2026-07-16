import os
import json
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from core.database import get_connection
from core.auth import get_current_user
from core.audit import log_action

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

LLM_JSON_PATH = Path(__file__).resolve().parents[3] / "llm_extracted_data.json"


def load_llm_data(file_name: str):
    if not LLM_JSON_PATH.exists():
        return None
    with open(LLM_JSON_PATH, "r") as f:
        data = json.load(f)
    return next((d for d in data if d["file_name"] == file_name), None)


# ─────────────────────────────────────────────
# POST /upload
# ─────────────────────────────────────────────
@router.post("/upload", summary="Upload a PDF document")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    doc_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{doc_id}-{file.filename}"

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Auto-load extracted data if available
    extracted = load_llm_data(file.filename)
    status = "reviewed" if extracted else "pending"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO documents (id, file_name, file_path, status, extracted_data)
        VALUES (%s, %s, %s, %s, %s) RETURNING *
    """, (doc_id, file.filename, str(file_path), status, json.dumps(extracted) if extracted else None))
    doc = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    log_action(user["username"], "UPLOAD", "document", doc_id, {"file": file.filename}, request.client.host)
    logger.info(f"Uploaded: {file.filename} by {user['username']}")

    return doc


# ─────────────────────────────────────────────
# POST /extract/{document_id}
# ─────────────────────────────────────────────
@router.post("/extract/{document_id}", summary="Trigger extraction for a document")
def extract_document(
    document_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    extracted = load_llm_data(doc["file_name"])
    if not extracted:
        raise HTTPException(status_code=404, detail=f"No extracted data found for {doc['file_name']}")

    cur.execute("""
        UPDATE documents SET extracted_data = %s, status = 'reviewed' WHERE id = %s RETURNING *
    """, (json.dumps(extracted), document_id))
    updated = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    log_action(user["username"], "EXTRACT", "document", document_id, {"file": doc["file_name"]}, request.client.host)
    return updated


# ─────────────────────────────────────────────
# GET /documents
# ─────────────────────────────────────────────
@router.get("/documents", summary="List all documents")
def list_documents(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, file_name, upload_date, status, review_notes FROM documents ORDER BY upload_date DESC")
    docs = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return docs


# ─────────────────────────────────────────────
# GET /results/{document_id}
# ─────────────────────────────────────────────
@router.get("/results/{document_id}", summary="Get extracted results for a document")
def get_results(document_id: str, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    cur.close()
    conn.close()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(doc)


# ─────────────────────────────────────────────
# PUT /results/{document_id}
# ─────────────────────────────────────────────
class UpdateData(BaseModel):
    extracted_data: Optional[dict] = None
    validated_data: Optional[dict] = None
    review_notes: Optional[str] = None

@router.put("/results/{document_id}", summary="Update reviewed data for a document")
def update_results(
    document_id: str,
    body: UpdateData,
    request: Request,
    user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE documents
        SET extracted_data = COALESCE(%s::jsonb, extracted_data),
            validated_data = COALESCE(%s::jsonb, validated_data),
            review_notes   = COALESCE(%s, review_notes)
        WHERE id = %s RETURNING *
    """, (
        json.dumps(body.extracted_data) if body.extracted_data else None,
        json.dumps(body.validated_data) if body.validated_data else None,
        body.review_notes,
        document_id
    ))
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="Document not found")

    log_action(user["username"], "UPDATE", "document", document_id, {}, request.client.host)
    return dict(updated)


# ─────────────────────────────────────────────
# POST /approve/{document_id}
# ─────────────────────────────────────────────
class ApproveBody(BaseModel):
    notes: Optional[str] = None
    updated_data: Optional[dict] = None

@router.post("/approve/{document_id}", summary="Approve a document")
def approve_document(
    document_id: str,
    body: ApproveBody,
    request: Request,
    user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    final_data = body.updated_data or doc["extracted_data"]

    # Save to review history
    cur.execute("""
        INSERT INTO review_history (document_id, action, previous_data, updated_data, reviewer, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (document_id, "approved", json.dumps(dict(doc["extracted_data"]) if doc["extracted_data"] else {}),
          json.dumps(final_data), user["username"], body.notes))

    # Update document
    cur.execute("""
        UPDATE documents SET status = 'approved', review_notes = %s, validated_data = %s
        WHERE id = %s RETURNING *
    """, (body.notes, json.dumps(final_data), document_id))
    updated = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    log_action(user["username"], "APPROVE", "document", document_id, {"notes": body.notes}, request.client.host)
    return updated


# ─────────────────────────────────────────────
# POST /reject/{document_id}
# ─────────────────────────────────────────────
class RejectBody(BaseModel):
    notes: str

@router.post("/reject/{document_id}", summary="Reject a document")
def reject_document(
    document_id: str,
    body: RejectBody,
    request: Request,
    user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    doc = cur.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    cur.execute("""
        INSERT INTO review_history (document_id, action, previous_data, reviewer, notes)
        VALUES (%s, %s, %s, %s, %s)
    """, (document_id, "rejected", json.dumps(dict(doc["extracted_data"]) if doc["extracted_data"] else {}),
          user["username"], body.notes))

    cur.execute("""
        UPDATE documents SET status = 'rejected', review_notes = %s WHERE id = %s RETURNING *
    """, (body.notes, document_id))
    updated = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    log_action(user["username"], "REJECT", "document", document_id, {"notes": body.notes}, request.client.host)
    return updated


# ─────────────────────────────────────────────
# GET /audit-logs
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# GET /search
# ─────────────────────────────────────────────
@router.get("/search", summary="Search approved documents by patient name or ID")
def search_documents(query: str, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
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
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
    results = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return results
