import logging
import json
from core.database import get_connection

logger = logging.getLogger(__name__)

def log_action(user_id: str, action: str, resource: str = None, resource_id: str = None, details: dict = None, ip_address: str = None):
    """Write an audit log entry to both DB and file."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_logs (user_id, action, resource, resource_id, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, action, resource, resource_id, json.dumps(details or {}), ip_address))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Audit log DB write failed: {e}")

    logger.info(f"AUDIT | user={user_id} action={action} resource={resource} id={resource_id} details={details}")
