"""
run_lab.py  —  Bangalore City Hospital Meditech Lab launcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ONE command to bring up the whole lab, on Windows / macOS / Linux.

    python run_lab.py            # full setup, then offer to open the HL7 sender
    python run_lab.py --no-ui    # full setup, but don't launch the sender UI
    python run_lab.py --down     # stop the stack (keep data)
    python run_lab.py --wipe     # stop the stack and DELETE all data volumes

What it does, in order:
    1. Verifies Docker Desktop is installed and running.
    2. Installs the Python dependencies (flask, requests, boto3).
    3. docker compose up -d   (pulls images on first run — can take a while).
    4. Waits for Postgres, Elasticsearch, Kibana, MinIO and NiFi to be ready.
    5. Loads mock data  (setup_services.py).
    6. Builds the NiFi HL7 pipeline  (setup_nifi.py).
    7. Optionally launches the HL7 sender web UI.

This replaces start_lab.sh for people who are NOT using WSL/Git-Bash.
No GPU is used anywhere in this lab — a plain laptop is enough; an RTX 5090
machine just has plenty of RAM to run all five containers comfortably.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import time
import socket
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── tiny colour helpers (work on Windows 10+ terminals) ──────────────────────
if os.name == "nt":
    os.system("")  # enable ANSI escape processing on Windows consoles
G, C, Y, R, B, X = "\033[32m", "\033[36m", "\033[33m", "\033[31m", "\033[1m", "\033[0m"


def ok(m):   print(f"  {G}OK{X}  {m}")
def info(m): print(f"  {C}>>{X}  {m}")
def warn(m): print(f"  {Y}!!{X}  {m}")
def err(m):  print(f"  {R}XX{X}  {m}")
def hdr(m):  print(f"\n{B}{'='*64}\n  {m}\n{'='*64}{X}")


# ── Docker / Compose detection ───────────────────────────────────────────────

def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def detect_compose():
    """Return the compose command as a list, or None if unavailable."""
    try:
        if _run(["docker", "compose", "version"]).returncode == 0:
            return ["docker", "compose"]
    except FileNotFoundError:
        return None
    if _run(["docker-compose", "version"]).returncode == 0:
        return ["docker-compose"]
    return None


def check_docker():
    hdr("1/6  Checking Docker")
    try:
        v = _run(["docker", "version", "--format", "{{.Server.Version}}"])
    except FileNotFoundError:
        err("`docker` was not found on PATH.")
        info("Install Docker Desktop, then reopen your terminal:")
        info("https://www.docker.com/products/docker-desktop/")
        sys.exit(1)
    if v.returncode != 0:
        err("Docker is installed but the engine is not running.")
        info("Start Docker Desktop and wait for the whale icon to go steady, then re-run.")
        sys.exit(1)
    ok(f"Docker engine running (server {v.stdout.strip()})")
    compose = detect_compose()
    if not compose:
        err("Neither `docker compose` nor `docker-compose` is available.")
        sys.exit(1)
    ok(f"Compose command: {' '.join(compose)}")
    return compose


# ── dependency install ───────────────────────────────────────────────────────

def install_deps():
    hdr("2/6  Python dependencies")
    needed = {"flask": "flask", "requests": "requests", "boto3": "boto3"}
    missing = []
    for mod in needed:
        try:
            __import__(mod)
        except ImportError:
            missing.append(needed[mod])
    if not missing:
        ok("flask, requests, boto3 already installed")
        return
    info(f"Installing: {', '.join(missing)}")
    cmd = [sys.executable, "-m", "pip", "install", "-q", *missing]
    if _run(cmd).returncode != 0:
        # PEP-668 externally-managed environments (some Linux): retry with override
        _run(cmd + ["--break-system-packages"])
    # verify
    for mod in needed:
        try:
            __import__(mod)
        except ImportError:
            err(f"Could not import {mod} after install. Try:  {sys.executable} -m pip install {needed[mod]}")
            sys.exit(1)
    ok("Dependencies ready")


# ── readiness probes ─────────────────────────────────────────────────────────

def wait_http(url, name, timeout=180):
    import requests
    info(f"Waiting for {name} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=3, verify=False).status_code < 500:
                ok(f"{name} is up")
                return True
        except Exception:
            pass
        time.sleep(3)
    warn(f"{name} did not respond within {timeout}s (continuing anyway)")
    return False


def wait_tcp(host, port, name, timeout=180):
    info(f"Waiting for {name} (tcp {host}:{port}) ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=3):
                ok(f"{name} is up")
                return True
        except Exception:
            time.sleep(3)
    warn(f"{name} tcp {host}:{port} not reachable within {timeout}s")
    return False


# ── steps ─────────────────────────────────────────────────────────────────────

def compose_up(compose):
    hdr("3/6  Starting Docker stack")
    info("docker compose up -d   (first run pulls images — be patient)")
    rc = subprocess.run(compose + ["up", "-d"], cwd=HERE).returncode
    if rc != 0:
        err("docker compose up failed. See the output above.")
        sys.exit(1)
    ok("Containers started")


def wait_all():
    hdr("4/6  Waiting for services")
    import urllib3
    urllib3.disable_warnings()
    wait_tcp("localhost", 5432, "PostgreSQL")
    wait_http("http://localhost:9200/_cluster/health", "Elasticsearch")
    wait_http("http://localhost:9000/minio/health/live", "MinIO")
    wait_http("http://localhost:5601/api/status", "Kibana", timeout=240)
    wait_http("https://localhost:8443/nifi-api/system-diagnostics", "NiFi", timeout=240)


def run_script(label, script):
    info(f"Running {script} ...")
    rc = subprocess.run([sys.executable, str(HERE / script)], cwd=HERE).returncode
    if rc != 0:
        warn(f"{script} exited with code {rc} — check the messages above.")
    else:
        ok(f"{label} complete")


def launch_sender():
    info("Launching the HL7 sender UI (http://localhost:5050) — Ctrl+C to stop.")
    subprocess.run([sys.executable, str(HERE / "hl7_sender.py")], cwd=HERE)


def summary():
    hdr("ALL SERVICES READY")
    rows = [
        ("NiFi (pipeline)", "https://localhost:8443/nifi", "admin / MeditechSecret123!"),
        ("Kibana (charts)", "http://localhost:5601", "(no login)"),
        ("MinIO (files)",   "http://localhost:9001", "admin / MeditechSecret123!"),
        ("PostgreSQL (DB)", "localhost:5432", "admin / adminpassword"),
        ("Elasticsearch",   "http://localhost:9200", "(no login)"),
        ("HL7 Sender UI",   "http://localhost:5050", "python run_lab.py (auto)"),
    ]
    for name, url, cred in rows:
        print(f"  {name:18}{url:34}{cred}")
    print()
    info("First time in NiFi: accept the self-signed certificate warning.")
    info("Verify files received:  docker exec -it nifi ls /tmp/nifi-hl7-inbox/")


# ── stop / wipe ───────────────────────────────────────────────────────────────

def do_down(compose, wipe=False):
    hdr("Stopping the stack" + (" and WIPING data" if wipe else ""))
    args = compose + (["down", "-v"] if wipe else ["down"])
    subprocess.run(args, cwd=HERE)
    ok("Done. " + ("All data volumes deleted." if wipe else "Data preserved."))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    argv = set(sys.argv[1:])
    compose = check_docker()

    if "--down" in argv or "--wipe" in argv:
        do_down(compose, wipe="--wipe" in argv)
        return

    install_deps()
    compose_up(compose)
    wait_all()

    hdr("5/6  Loading mock data")
    run_script("Mock data load", "setup_services.py")

    hdr("6/6  Building the NiFi pipeline")
    run_script("NiFi pipeline", "setup_nifi.py")

    summary()

    if "--no-ui" in argv:
        info("Skipping the sender UI (--no-ui). Start it later with:  python hl7_sender.py")
        return
    try:
        ans = input("\n  Start the HL7 Sender UI now? [Y/n] ").strip().lower()
    except EOFError:
        ans = "n"
    if ans in ("", "y", "yes"):
        launch_sender()
    else:
        info("Run it later with:  python hl7_sender.py")


if __name__ == "__main__":
    main()
