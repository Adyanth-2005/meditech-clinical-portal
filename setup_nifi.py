"""
setup_nifi.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Auto-creates the BCH HL7 pipeline in Apache NiFi via
the REST API. Run AFTER docker compose up -d.

Pipeline built:
  [ListenTCP :8081]
      → [UpdateAttribute  — add timestamp + metadata]
          → [ReplaceText  — stamp a log line]
              → [PutFile  — save to /tmp/nifi-hl7-inbox/]

Students can then see:
  • NiFi canvas counters incrementing as HL7 arrives
  • Data provenance showing each FlowFile's journey
  • Files appearing in /tmp/nifi-hl7-inbox/ (docker exec)

Prerequisites:  pip install requests
Run:            python3 setup_nifi.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import requests, time, sys, json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NIFI_URL = "https://localhost:8443"
USER     = "admin"
PASS     = "MeditechSecret123!"


# ─── helpers ─────────────────────────────────────────────────────────────────

def ok(msg):   print(f"  \033[32m✓\033[0m {msg}")
def err(msg):  print(f"  \033[31m✗\033[0m {msg}")
def info(msg): print(f"  \033[36mℹ\033[0m {msg}")
def hdr(msg):  print(f"\n\033[1m── {msg} {'─'*(52-len(msg))}\033[0m")


# ─── NiFi REST client ─────────────────────────────────────────────────────────

class NiFiClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False

    def wait_ready(self, timeout=120):
        print("  Waiting for NiFi ", end='', flush=True)
        for _ in range(timeout // 5):
            try:
                r = self.session.get(f"{NIFI_URL}/nifi-api/system-diagnostics", timeout=4)
                if r.status_code in (200, 401):
                    print(" ready")
                    return True
            except Exception:
                pass
            print('.', end='', flush=True)
            time.sleep(5)
        print(" TIMEOUT")
        return False

    def login(self):
        r = self.session.post(
            f"{NIFI_URL}/nifi-api/access/token",
            data={"username": USER, "password": PASS},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code != 201:
            raise RuntimeError(f"Login failed ({r.status_code}): {r.text[:200]}")
        self.session.headers["Authorization"] = f"Bearer {r.text}"
        ok("Authenticated with NiFi")

    def root_pg(self):
        r = self.session.get(f"{NIFI_URL}/nifi-api/flow/process-groups/root")
        r.raise_for_status()
        pg_id = r.json()["processGroupFlow"]["id"]
        ok(f"Root process group: {pg_id[:12]}…")
        return pg_id

    def drop_existing_pg(self, root_id, name):
        """Remove any existing process group with the same name."""
        r = self.session.get(f"{NIFI_URL}/nifi-api/flow/process-groups/{root_id}")
        r.raise_for_status()
        pgs = r.json()["processGroupFlow"]["flow"]["processGroups"]
        for pg in pgs:
            if pg["component"]["name"] == name:
                pg_id  = pg["id"]
                pg_ver = pg["revision"]["version"]
                # Stop all processors first
                self.session.put(
                    f"{NIFI_URL}/nifi-api/flow/process-groups/{pg_id}",
                    json={"id": pg_id, "state": "STOPPED",
                          "disconnectedNodeAcknowledged": False}
                )
                time.sleep(2)
                self.session.delete(
                    f"{NIFI_URL}/nifi-api/process-groups/{pg_id}"
                    f"?version={pg_ver}&disconnectedNodeAcknowledged=false"
                )
                info(f"Removed existing group: {name}")

    def create_pg(self, parent_id, name, x=0, y=0):
        r = self.session.post(
            f"{NIFI_URL}/nifi-api/process-groups/{parent_id}/process-groups",
            json={
                "revision": {"version": 0},
                "component": {"name": name, "position": {"x": x, "y": y}},
            },
        )
        r.raise_for_status()
        d = r.json()
        ok(f"Process group: {name}")
        return d["id"]

    def create_proc(self, pg_id, proc_type, name, x, y,
                    properties=None, auto_term=None):
        body = {
            "revision": {"version": 0},
            "component": {
                "type": proc_type,
                "name": name,
                "position": {"x": x, "y": y},
                "config": {
                    "properties":                 properties or {},
                    "schedulingStrategy":         "TIMER_DRIVEN",
                    "schedulingPeriod":           "0 sec",
                    "autoTerminatedRelationships": auto_term or [],
                },
            },
        }
        r = self.session.post(
            f"{NIFI_URL}/nifi-api/process-groups/{pg_id}/processors",
            json=body,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Create processor failed ({r.status_code}): {r.text[:300]}")
        d = r.json()
        proc_id  = d["id"]
        version  = d["revision"]["version"]
        ok(f"  Processor: {name}  ({proc_id[:8]}…)")
        return proc_id, version

    def connect(self, pg_id, src_id, dst_id, relationships=None):
        if relationships is None:
            relationships = ["success"]
        body = {
            "revision": {"version": 0},
            "component": {
                "source":               {"id": src_id, "groupId": pg_id, "type": "PROCESSOR"},
                "destination":          {"id": dst_id, "groupId": pg_id, "type": "PROCESSOR"},
                "selectedRelationships": relationships,
                "backPressureObjectThreshold": "10000",
                "backPressureDataSizeThreshold": "1 GB",
                "flowFileExpiration":   "0 sec",
            },
        }
        r = self.session.post(
            f"{NIFI_URL}/nifi-api/process-groups/{pg_id}/connections",
            json=body,
        )
        r.raise_for_status()
        ok(f"    Connection: {src_id[:8]}… → {dst_id[:8]}…")
        return r.json()["id"]

    def start_proc(self, proc_id, version):
        r = self.session.put(
            f"{NIFI_URL}/nifi-api/processors/{proc_id}/run-status",
            json={
                "revision": {"version": version},
                "state":    "RUNNING",
                "disconnectedNodeAcknowledged": False,
            },
        )
        if r.status_code not in (200, 201, 202):
            info(f"    Start {proc_id[:8]}… status={r.status_code} — may need manual start in UI")
        else:
            ok(f"  ▶ Running: {proc_id[:8]}…")

    def wait_for_nars(self, timeout=120):
        """Wait until standard processors (UpdateAttribute) are loaded."""
        print("  Waiting for NARs to load ", end='', flush=True)
        for _ in range(timeout // 5):
            try:
                r = self.session.get(f"{NIFI_URL}/nifi-api/flow/processor-types", timeout=8)
                if r.status_code == 200:
                    types = r.json().get("processorTypes", [])
                    names = [t["type"] for t in types]
                    if any("UpdateAttribute" in n for n in names):
                        print(" ready")
                        return True
            except Exception:
                pass
            print('.', end='', flush=True)
            time.sleep(5)
        print(" TIMEOUT (proceeding anyway)")
        return False

    def get_proc_version(self, proc_id):
        r = self.session.get(f"{NIFI_URL}/nifi-api/processors/{proc_id}")
        r.raise_for_status()
        return r.json()["revision"]["version"]


# ─── Build the pipeline ───────────────────────────────────────────────────────

def build_pipeline(client, root_id):
    hdr("Creating BCH HL7 Pipeline")

    # Remove old group if it exists from a previous run
    client.drop_existing_pg(root_id, "BCH HL7 Pipeline")
    time.sleep(1)

    pg_id = client.create_pg(root_id, "BCH HL7 Pipeline", x=200, y=200)

    # ── Processor 1: ListenTCP ────────────────────────────────────────────────
    listen_id, listen_ver = client.create_proc(
        pg_id,
        "org.apache.nifi.processors.standard.ListenTCP",
        "Receive HL7 (Port 8081)",
        x=100, y=200,
        properties={
            "Port":                          "8081",
            "Max Number of TCP Connections": "16",
            "Character Set":                 "UTF-8",
        },
        auto_term=[],
    )

    # ── Processor 2: UpdateAttribute — stamp metadata ─────────────────────────
    update_id, update_ver = client.create_proc(
        pg_id,
        "org.apache.nifi.processors.attributes.UpdateAttribute",
        "Stamp Metadata",
        x=440, y=200,
        properties={
            "filename":        "hl7-${now():format('yyyyMMdd-HHmmssSSS')}.hl7",
            "received.at":     "${now():format('yyyy-MM-dd HH:mm:ss')}",
            "source.system":   "hl7-sender-ui",
            "hospital.code":   "BCH",
        },
        auto_term=[],
    )

    # ── Processor 3: ReplaceText — prepend a log header ───────────────────────
    replace_id, replace_ver = client.create_proc(
        pg_id,
        "org.apache.nifi.processors.standard.ReplaceText",
        "Prepend Log Header",
        x=780, y=200,
        properties={
            "Replacement Strategy": "Prepend",
            "Replacement Value":    "# BCH HL7 RECEIVED | ${received.at} | src=${source.system}\n",
        },
        auto_term=[],
    )

    # ── Processor 4: PutFile — save to disk ──────────────────────────────────
    putfile_id, putfile_ver = client.create_proc(
        pg_id,
        "org.apache.nifi.processors.standard.PutFile",
        "Save to Inbox",
        x=1120, y=200,
        properties={
            "Directory":                   "/tmp/nifi-hl7-inbox",
            "Conflict Resolution Strategy": "replace",
            "Create Missing Directories":  "true",
        },
        auto_term=["success", "failure"],
    )

    # ── Connections ───────────────────────────────────────────────────────────
    hdr("Creating connections")
    client.connect(pg_id, listen_id,  update_id,  ["success"])
    client.connect(pg_id, update_id,  replace_id, ["success"])
    client.connect(pg_id, replace_id, putfile_id, ["success", "failure"])

    # ── Start processors ──────────────────────────────────────────────────────
    hdr("Starting processors")
    time.sleep(2)  # let NiFi settle

    for proc_id in [listen_id, update_id, replace_id, putfile_id]:
        ver = client.get_proc_version(proc_id)
        client.start_proc(proc_id, ver)
        time.sleep(0.5)

    return pg_id


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n\033[1m" + "═" * 56)
    print("  BCH NiFi Pipeline Setup")
    print("  Requires: docker compose up -d  (NiFi takes ~90s to start)")
    print("═" * 56 + "\033[0m")

    client = NiFiClient()

    hdr("1. Connecting to NiFi")
    if not client.wait_ready():
        err("NiFi not ready — check: docker logs nifi")
        sys.exit(1)

    hdr("2. Authenticating")
    try:
        client.login()
    except Exception as e:
        err(f"Auth failed: {e}")
        sys.exit(1)

    hdr("3. Waiting for NARs to load")
    client.wait_for_nars()

    hdr("4. Getting root process group")
    root_id = client.root_pg()

    try:
        pg_id = build_pipeline(client, root_id)
    except Exception as e:
        err(f"Pipeline build failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    print("\n" + "═" * 56)
    print("  PIPELINE READY")
    print("─" * 56)
    print("  Process group : BCH HL7 Pipeline")
    print("  Listening on  : TCP localhost:8081")
    print("  Saves files to: /tmp/nifi-hl7-inbox/  (inside NiFi container)")
    print()
    print("  To verify files received:")
    print("    docker exec -it nifi ls /tmp/nifi-hl7-inbox/")
    print()
    print("  Open the NiFi canvas to see counters update:")
    print("    https://localhost:8443/nifi")
    print("    Login: admin / MeditechSecret123!")
    print()
    print("  Then run the HL7 sender:")
    print("    python3 hl7_sender.py")
    print("═" * 56 + "\n")


if __name__ == "__main__":
    main()
