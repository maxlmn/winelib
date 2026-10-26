"""Everything in your database, to take elsewhere: GET /api/export.json (one file, every table) and
GET /api/export.zip (one CSV per table). Settings › Your data. Nobody is locked in.

The JSON: {"format": "winelib", "version": 1, "exported", "schema" (the migration revision), "tables": {name: [rows]}}
with every column of every table (dates as ISO strings), reference tables included, so a new installation can be
rebuilt from it.
"""
import csv
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

import settings
from db import Base, get_session

router = APIRouter()
FORMAT, VERSION = "winelib", 1


def _tables(session):
    """[(name, Table)] in dependency order (a table after those it points to), app_settings last."""
    names = set(inspect(session.get_bind()).get_table_names())
    tables = [t for t in Base.metadata.sorted_tables if t.name in names]
    if settings.AppSettingsRow.__tablename__ in names:
        tables.append(settings.AppSettingsRow.__table__)
    return [(t.name, t) for t in tables]


def _plain(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _rows(session, table):
    return [{k: _plain(v) for k, v in r._mapping.items()} for r in session.execute(select(table).order_by(*table.primary_key))]


def _revision(session):
    try:
        from sqlalchemy import text
        return session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        return None


def _name(ext):
    return f"winelib_export_{datetime.now():%Y-%m-%d}.{ext}"


@router.get("/api/export.json")
def export_json(session: Session = Depends(get_session)):
    import json
    body = {"format": FORMAT, "version": VERSION, "exported": datetime.now().isoformat(timespec="seconds"),
            "schema": _revision(session), "tables": {name: _rows(session, t) for name, t in _tables(session)}}
    return Response(json.dumps(body, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{_name("json")}"'})


@router.get("/api/export.zip")
def export_zip(session: Session = Depends(get_session)):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, table in _tables(session):
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow([c.name for c in table.columns])
            for row in _rows(session, table):
                w.writerow(["" if v is None else v for v in row.values()])
            z.writestr(f"{name}.csv", out.getvalue())
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{_name("zip")}"'})
