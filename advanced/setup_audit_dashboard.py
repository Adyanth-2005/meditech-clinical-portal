"""
setup_audit_dashboard.py — register a Kibana data view over the `audit-log`
Elasticsearch index so you can build an access-audit dashboard.

  python setup_audit_dashboard.py

Prereqs: the lab stack running (Elasticsearch + Kibana), and at least one audit
event shipped (log into the portal once so the index exists).
"""
import sys
import requests

ES = "http://localhost:9200"
KIBANA = "http://localhost:5601"
INDEX = "audit-log"


def main():
    # ensure index exists (so the data view has something to point at)
    try:
        if requests.get(f"{ES}/{INDEX}", timeout=5).status_code == 404:
            requests.put(f"{ES}/{INDEX}", json={"mappings": {"properties": {
                "@timestamp": {"type": "date"}, "user_name": {"type": "keyword"},
                "role": {"type": "keyword"}, "action": {"type": "keyword"},
                "table_name": {"type": "keyword"}, "record_id": {"type": "keyword"}}}},
                timeout=10)
            print(f"  created ES index '{INDEX}'")
    except Exception as e:
        print(f"  ! could not reach Elasticsearch at {ES}: {e}"); sys.exit(1)

    body = {"data_view": {"title": INDEX, "name": "Audit Log", "timeFieldName": "@timestamp"}}
    r = requests.post(f"{KIBANA}/api/data_views/data_view",
                      json=body, headers={"kbn-xsrf": "true"}, timeout=15)
    if r.status_code in (200, 201):
        print("  ✓ Kibana data view 'Audit Log' created")
    elif "Duplicate" in r.text or r.status_code == 409:
        print("  ✓ Kibana data view 'Audit Log' already exists")
    else:
        print(f"  ! Kibana responded {r.status_code}: {r.text[:200]}")

    print("\nOpen Kibana → Analytics → Discover → 'Audit Log' (set time range to "
          "Last 1 hour). Build a Lens bar chart: X = action (Top values), "
          "Y = Count, Break down by user_name — that's your access-audit dashboard.")


if __name__ == "__main__":
    main()
