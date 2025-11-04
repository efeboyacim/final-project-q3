import os

import boto3
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(prefix="/internal", tags=["Internal"])

SHARED = os.getenv("S3_EVENT_SHARED_SECRET")
s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
BUCKET = os.getenv("S3_BUCKET")


def _require_secret(x_internal_token: str = Header(None)):
    if not SHARED or x_internal_token != SHARED:
        raise HTTPException(status_code=401, detail="unauthorized")


def _parse_key(key: str):
    parts = key.split("/", 2)
    if len(parts) >= 3 and parts[0] == "project-docs":
        return int(parts[1]), parts[2]
    return None, None


@router.post("/s3-callback")
def s3_callback(payload: dict, db: Session = Depends(get_db), _: None = Depends(_require_secret)):
    ev = payload.get("type")
    key = payload.get("key")
    bucket = payload.get("bucket")

    if bucket != BUCKET or not key:
        raise HTTPException(400, "bad payload")

    pid, name = _parse_key(key)
    if not pid:
        raise HTTPException(400, "bad key")

    from sqlalchemy import text

    if ev == "created":
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
            size_new = int(head["ContentLength"])
        except Exception as e:
            raise HTTPException(404, f"head failed: {e}")

        with db.begin():
            row = db.execute(
                text(
                    "SELECT byte_limit, bytes_used, file_count "
                    "FROM projects WHERE id=:id FOR UPDATE"
                ),
                {"id": pid},
            ).first()

            if not row:
                try:
                    s3.delete_object(Bucket=bucket, Key=key)
                except Exception:
                    pass
                return {"rolled_back": True}

            byte_limit, used, cnt = [int(row[i] or 0) for i in range(3)]

            prev = db.execute(
                text("SELECT size_bytes FROM object_usages WHERE s3_key=:k FOR UPDATE"),
                {"k": key},
            ).first()

            if prev:
                delta = size_new - int(prev[0])
                projected = used + delta

                if byte_limit and projected > byte_limit:
                    db.rollback()
                    try:
                        s3.delete_object(Bucket=bucket, Key=key)
                    except Exception:
                        pass
                    return {"rolled_back": True}

                db.execute(
                    text(
                        "UPDATE object_usages "
                        "SET size_bytes=:s, updated_at=now() WHERE s3_key=:k"
                    ),
                    {"s": size_new, "k": key},
                )
                db.execute(
                    text("UPDATE projects SET bytes_used = bytes_used + :d WHERE id=:id"),
                    {"d": delta, "id": pid},
                )

            else:
                projected = used + size_new
                if byte_limit and projected > byte_limit:
                    db.rollback()
                    try:
                        s3.delete_object(Bucket=bucket, Key=key)
                    except Exception:
                        pass
                    return {"rolled_back": True}

                db.execute(
                    text(
                        "INSERT INTO object_usages(s3_key, project_id, name, size_bytes) "
                        "VALUES (:k, :pid, :n, :s)"
                    ),
                    {"k": key, "pid": pid, "n": name, "s": size_new},
                )
                db.execute(
                    text(
                        "UPDATE projects SET bytes_used = bytes_used + :s, "
                        "file_count = file_count + 1 WHERE id=:id"
                    ),
                    {"s": size_new, "id": pid},
                )
        return {"ok": True}

    elif ev == "removed":
        with db.begin():
            row = db.execute(
                text(
                    "SELECT size_bytes, project_id "
                    "FROM object_usages WHERE s3_key=:k FOR UPDATE"
                ),
                {"k": key},
            ).first()

            if not row:
                return {"skip": True}

            size_old, proj_id = int(row[0]), int(row[1])
            db.execute(
                text(
                    "UPDATE projects SET bytes_used = GREATEST(0, bytes_used - :s), "
                    "file_count = GREATEST(0, file_count - 1) WHERE id=:id"
                ),
                {"s": size_old, "id": proj_id},
            )
            db.execute(text("DELETE FROM object_usages WHERE s3_key=:k"), {"k": key})
        return {"ok": True}

    raise HTTPException(400, "unknown type")
