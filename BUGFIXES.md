# Meditech Lab — Bug Report & Fixes

This document lists every issue found while auditing the lab, why it matters,
and exactly what was changed. Items are ordered roughly by impact. Nothing in
the lab's *teaching logic* was broken — most issues are environment/version
problems that bite specifically on a fresh **Windows 11 + Docker Desktop** setup.

> Note on hardware: this lab is pure data engineering (NiFi, Postgres,
> Elasticsearch, Kibana, MinIO). **No GPU / CUDA is used anywhere.** Your RTX
> 5090 laptop is overkill in the best way — it just has plenty of RAM to run
> all five containers at once.

---

## 1. MinIO `:latest` gives a broken web console  *(the big one)*

**File:** `docker-compose.yml`

**Problem.** The stack pinned `minio/minio:latest`. In the **May 2025** MinIO
release the full embedded admin console was removed (it became a stripped-down
read-only "object-browser"), and in **October 2025** MinIO stopped publishing
free images to Docker Hub (that repo is now archived). So `:latest` hands
students a crippled console at `http://localhost:9001` — you can't create
buckets or browse objects the way the lab assumes. This is a silent failure:
everything "starts," but the MinIO exercise doesn't work.

**Fix.** Pinned to a pre-removal April-2025 release that still ships the full
console, served from quay.io (since Docker Hub's `minio/minio` is archived):

```yaml
image: quay.io/minio/minio:RELEASE.2025-04-22T22-12-26Z
```

---

## 2. Kibana could start before Elasticsearch is ready (race condition)

**File:** `docker-compose.yml`

**Problem.** `depends_on: [elasticsearch]` only waits for the ES *container to
start*, not for ES to be *ready to serve*. On a cold boot Kibana often comes up
first, fails to reach ES, and crash-loops for a while.

**Fix.** Added a real healthcheck to Elasticsearch and made Kibana wait for it:

```yaml
elasticsearch:
  healthcheck:
    test: ["CMD-SHELL", "curl -fs http://localhost:9200/_cluster/health || exit 1"]
    interval: 10s ; timeout: 5s ; retries: 20 ; start_period: 30s
kibana:
  depends_on:
    elasticsearch:
      condition: service_healthy
```

(`curl` is bundled inside the official Elasticsearch image, so this is safe.)
A `pg_isready` healthcheck was also added to PostgreSQL.

---

## 3. NiFi "invalid host header" if you don't use *exactly* `localhost:8443`

**File:** `docker-compose.yml`

**Problem.** When NiFi's HTTPS port is published from a container, NiFi checks
the browser's `Host` header against an allow-list. Opening `https://localhost:8443`
is allowed by default, but `https://127.0.0.1:8443` or the machine name throws:
*"System Error — The request contained an invalid host header."* Students who
type `127.0.0.1` will think the lab is broken.

**Fix.** Added the proxy-host allow-list:

```yaml
- NIFI_WEB_PROXY_HOST=localhost:8443,127.0.0.1:8443
```

**Not changed on purpose:** NiFi stays on **1.24.0**. `setup_nifi.py` uses the
NiFi *1.x* REST API (`/nifi-api/access/token`, processor-type names, etc.).
NiFi 2.x changed authentication and the API, so upgrading would break the
pipeline-builder script. Keep 1.24.0.

---

## 4. `version: '3.8'` is obsolete

**File:** `docker-compose.yml`

**Problem.** Docker Compose v2 ignores the top-level `version:` key and prints a
deprecation warning on every command.

**Fix.** Removed it.

---

## 5. `start_lab.sh` is Bash — it doesn't run natively on Windows

**Files:** new `run_lab.py`, `start_lab.bat`, `start_lab.ps1`

**Problem.** `start_lab.sh` uses Bash, `pip3 ... --break-system-packages`, an
interactive `read -p`, and `python3` — all Linux-isms. On Windows you'd need
WSL or Git-Bash, and the `--break-system-packages` flag is a Debian/Ubuntu thing
that doesn't apply (and errors on older pip).

**Fix.** Added a **single cross-platform launcher**, `run_lab.py`, that:

1. checks Docker Desktop is installed *and running*,
2. installs `flask requests boto3` into the current interpreter,
3. runs `docker compose up -d`,
4. waits for all five services with real readiness probes,
5. runs `setup_services.py` then `setup_nifi.py`,
6. offers to open the HL7 sender UI.

It also supports `--no-ui`, `--down` (stop, keep data) and `--wipe` (stop +
delete volumes). `start_lab.bat` (double-clickable) and `start_lab.ps1` are thin
wrappers around it. The original `start_lab.sh` is kept for WSL/macOS/Linux.

---

## 6. `datetime.utcnow()` is deprecated (Python 3.12+)

**File:** `hl7_sender.py`

**Problem.** `datetime.utcnow().isoformat() + "Z"` raises a `DeprecationWarning`
on Python 3.12/3.13 (which is what you'll install fresh on Windows) and produces
a non-timezone-aware timestamp.

**Fix.** `datetime.now(timezone.utc).isoformat()` (added `timezone` to imports).

---

## 7. `/send` returned HTTP 500 on an empty/non-JSON body

**File:** `hl7_sender.py`

**Problem.** `data = request.json` raises if the request has no JSON body or the
wrong content-type, turning a malformed request into a server error.

**Fix.** `data = request.get_json(silent=True) or {}` — now degrades to a clean
`ok: false` response. Verified with an empty-body POST returning 200, not 500.

---

## 8. `hl7-messages` index didn't declare the `conditions` field

**File:** `setup_services.py`

**Problem.** `hl7_sender.py` writes a `conditions` array into the `hl7-messages`
index, but the index mapping never declared it. Elasticsearch's dynamic mapping
papered over this (auto-typing it as text+keyword), so it "worked," but the
field type was left to chance.

**Fix.** Declared `"conditions": {"type": "keyword"}` explicitly in the mapping.

---

## 9. `SyntaxWarning: invalid escape sequence '\s'`

**File:** `module2_hands_on_exercise.py`

**Problem.** A printed hint string contained regex examples like `SpO2:\s+`,
which Python 3.12 flags as an invalid escape sequence in a normal string.

**Fix.** Made that one `print(...)` a raw string (`print(r"""..."""`)).

---

## Things that were checked and are **fine** (no change needed)

- **`setup_nifi.py` pipeline design** — ListenTCP → UpdateAttribute → ReplaceText
  → PutFile. All relationships are either connected or auto-terminated, so the
  processors are valid and startable. The NiFi 1.x REST calls are correct.
- **`init.sql`** — schema, foreign keys, seed data, and the `latest_obs` /
  `diabetic_hypertensive` views are internally consistent and valid PostgreSQL.
- **`module2_hands_on_exercise.py`** — runs end-to-end; the "NOT IMPLEMENTED"
  lines are intentional student TODOs, not bugs.
- **`draw_pipeline.py` / `visualize_meditech_lab.py`** — both regenerate their
  PNGs without error (need only matplotlib + numpy).
- **Elasticsearch heap / `vm.max_map_count`** — because the stack runs ES with
  `discovery.type=single-node`, ES skips the strict bootstrap checks, so it
  starts on Docker Desktop/WSL2 even without raising `vm.max_map_count`. Raising
  it is an optional performance tweak, documented in `WINDOWS_SETUP.md`.

---

## Files changed

| File | Change |
|------|--------|
| `docker-compose.yml` | MinIO pin, ES+PG healthchecks, Kibana waits for ES health, NiFi proxy host, dropped obsolete `version:` |
| `hl7_sender.py` | tz-aware timestamp, hardened JSON parsing |
| `setup_services.py` | declared `conditions` field in `hl7-messages` mapping |
| `module2_hands_on_exercise.py` | raw-string fix for `\s` warning |
| **new** `run_lab.py` | cross-platform one-command launcher |
| **new** `start_lab.bat`, `start_lab.ps1` | Windows launchers |
| **new** `requirements.txt` | pinned Python deps |
| **new** `WINDOWS_SETUP.md` | step-by-step Windows 11 guide |
