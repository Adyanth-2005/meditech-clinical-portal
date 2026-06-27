# Running the Meditech Lab on Windows 11

A complete, copy-paste guide for a fresh Windows 11 machine. The whole lab runs
in Docker; the only thing installed on Windows directly is Docker Desktop and
Python. **No GPU is used** — your RTX 5090 laptop just makes running five
containers effortless.

---

## What you'll end up with

| Service | URL | Login |
|---|---|---|
| NiFi (pipeline canvas) | https://localhost:8443/nifi | `admin` / `MeditechSecret123!` |
| Kibana (dashboards) | http://localhost:5601 | none |
| MinIO (file console) | http://localhost:9001 | `admin` / `MeditechSecret123!` |
| Elasticsearch | http://localhost:9200 | none |
| PostgreSQL | `localhost:5432` | `admin` / `adminpassword` |
| HL7 Sender UI | http://localhost:5050 | none |

---

## Step 1 — Install Docker Desktop

1. Download **Docker Desktop for Windows** from
   <https://www.docker.com/products/docker-desktop/> and install it.
   (The `apache/nifi` image needs Docker Desktop **4.37.1 or newer** — just take
   the latest.)
2. It will enable the **WSL2** backend. If prompted, let it install/update WSL2
   and reboot.
3. Launch Docker Desktop and wait until the whale icon in the system tray is
   steady (not animating). You can verify in a terminal:
   ```powershell
   docker version
   ```
   You should see both a Client and a Server section.

### Give Docker enough memory (recommended)

Elasticsearch + NiFi + Kibana are RAM-hungry. Docker Desktop → **Settings →
Resources** → set **Memory to at least 8 GB** (your laptop has far more). Apply
& Restart.

---

## Step 2 — Install Python

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/>.
2. **Important:** on the first installer screen, tick
   **"Add python.exe to PATH"**.
3. Verify in a new terminal:
   ```powershell
   python --version
   ```

---

## Step 3 — Get the project onto your machine

Unzip the lab folder somewhere simple, e.g. `C:\meditech-lab`. Open a terminal
**in that folder**:

- **File Explorer:** open the `meditech-lab` folder, click the address bar, type
  `powershell`, and press Enter — PowerShell opens already in that folder.
- Or in PowerShell: `cd C:\meditech-lab`

---

## Step 4 — Start everything (one command)

You have three equivalent options. Pick one.

**Option A — double-click**
Double-click **`start_lab.bat`**. A console window opens and drives the whole
setup.

**Option B — PowerShell**
```powershell
.\start_lab.ps1
```
If PowerShell blocks the script, run this once in the same window first:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Option C — plain Python (works in any terminal)**
```powershell
python run_lab.py
```

What happens next, automatically:
1. Docker check → 2. installs `flask requests boto3` → 3. `docker compose up -d`
(first run **pulls images — this can take 5–15 min** on the first launch) →
4. waits for all services → 5. loads the mock EHR data into Elasticsearch,
Kibana and MinIO → 6. builds the NiFi HL7 pipeline → 7. asks if you want to open
the HL7 sender UI.

When it finishes you'll see a summary table of URLs.

---

## Step 5 — Try it

1. The launcher opens **http://localhost:5050** (the HL7 Sender). Pick a patient
   on the left, choose a message type (ADT-A01, ORU-R01, …), and click **Send**.
2. Open **https://localhost:8443/nifi** — your browser will warn about the
   self-signed certificate; click **Advanced → Continue / Proceed**. Log in with
   `admin` / `MeditechSecret123!`. Watch the processor counters tick up as you
   send messages.
3. Open **http://localhost:5601** (Kibana) → **Analytics → Discover** → pick the
   `hl7-messages` data view to see messages arriving.
4. Open **http://localhost:9001** (MinIO) and browse the pre-loaded buckets
   (`discharge-reports`, `hl7-archive`, …).
5. Query PostgreSQL:
   ```powershell
   docker exec -it postgres psql -U admin -d healthcare_db -c "SELECT * FROM latest_obs;"
   ```
6. Confirm NiFi wrote files to disk:
   ```powershell
   docker exec -it nifi ls /tmp/nifi-hl7-inbox/
   ```

---

## Stopping / resetting

```powershell
python run_lab.py --down    # stop the stack, KEEP all data
python run_lab.py --wipe    # stop the stack and DELETE all data volumes
```
(Equivalently `docker compose down` / `docker compose down -v`.)

To re-load the mock data after a wipe, just run `python run_lab.py` again.

---

## Troubleshooting

**"docker: command not found" / "engine not running"**
Docker Desktop isn't started. Launch it, wait for the steady whale icon, re-run.

**A port is already in use (5432, 9200, 5601, 9000, 9001, 8443, 8081, 5050)**
Something else on your machine owns that port. Find and stop it:
```powershell
netstat -ano | findstr :5432
```
…then stop that process, or edit the left-hand port number in
`docker-compose.yml` (e.g. `"15432:5432"`) and reconnect on the new port.

**NiFi shows "invalid host header"**
Use exactly `https://localhost:8443/nifi`. The compose file already allow-lists
`localhost:8443` and `127.0.0.1:8443`.

**NiFi pipeline didn't auto-start**
NiFi is slow to load processors on first boot. Re-run just the builder:
```powershell
python setup_nifi.py
```
Or start the four processors manually on the NiFi canvas (right-click → Start).

**Kibana is slow / "Kibana server is not ready yet"**
Give it a minute after Elasticsearch is healthy. The launcher already waits, but
Kibana's own UI can take an extra ~60s on first boot.

**Elasticsearch keeps restarting (rare, low-memory machines)**
Raise the WSL2 virtual-memory limit (optional perf tweak — not normally needed
in single-node mode). In PowerShell:
```powershell
wsl -d docker-desktop sysctl -w vm.max_map_count=262144
```
Then restart the ES container: `docker compose restart elasticsearch`.

**Re-run the data load only** (without touching containers)
```powershell
python setup_services.py
python setup_nifi.py
```

---

## The standalone teaching exercise (no Docker needed)

`module2_hands_on_exercise.py` runs entirely on its own with an in-memory SQLite
DB — handy for the coding TODOs:
```powershell
python -m pip install pandas tabulate colorama
python module2_hands_on_exercise.py          # all three exercises
python module2_hands_on_exercise.py --ex 2    # just exercise 2
```

## Regenerating the diagrams (optional)
```powershell
python -m pip install matplotlib numpy
python visualize_meditech_lab.py
python draw_pipeline.py
```
