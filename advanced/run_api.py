"""
run_api.py — start the Meditech RBAC gateway.

    python run_api.py            # against the lab's PostgreSQL (must be running)
    python run_api.py --demo     # in-memory demo, zero external services

Then open http://localhost:8000
"""
import os, sys, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = HERE / "api"

def main():
    if "--demo" in sys.argv:
        os.environ["MEDITECH_DEMO"] = "1"
        print(">> DEMO mode (in-memory, no Postgres needed)")
    else:
        print(">> Postgres mode (needs the lab stack running: docker compose up -d)")
    print(">> Open http://localhost:8000   (Ctrl+C to stop)")
    print(">> Logins: admin/admin123 · dr.sharma/doctor123 · rajan/patient123\n")
    subprocess.run([sys.executable, "-m", "uvicorn", "app:app",
                    "--host", "0.0.0.0", "--port", "8000"], cwd=str(API))

if __name__ == "__main__":
    main()
