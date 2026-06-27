"""
es_audit.py — ship audit events to Elasticsearch so they can be charted in
Kibana. Best-effort: every call is wrapped so a missing/slow ES never breaks
the gateway. The canonical audit record still lives in Postgres (audit_log).
"""

import os
from datetime import datetime, timezone

ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
AUDIT_INDEX = "audit-log"

_es = None
_disabled = False


def _client():
    global _es, _disabled
    if _disabled:
        return None
    if _es is None:
        try:
            from elasticsearch import Elasticsearch
            _es = Elasticsearch(ES_URL, request_timeout=2)
            if not _es.indices.exists(index=AUDIT_INDEX):
                _es.indices.create(index=AUDIT_INDEX, mappings={"properties": {
                    "@timestamp": {"type": "date"},
                    "user_name": {"type": "keyword"},
                    "role": {"type": "keyword"},
                    "action": {"type": "keyword"},
                    "table_name": {"type": "keyword"},
                    "record_id": {"type": "keyword"},
                }})
        except Exception:
            _disabled = True
            return None
    return _es


def ship(user_name, action, table_name, record_id, role=""):
    es = _client()
    if es is None:
        return
    try:
        es.index(index=AUDIT_INDEX, document={
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "user_name": user_name, "role": role, "action": action,
            "table_name": table_name, "record_id": str(record_id),
        })
    except Exception:
        pass
