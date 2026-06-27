#!/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║  Bangalore City Hospital — Meditech Lab Startup         ║
# ║  UE26MT324 · PES University                             ║
# ╠══════════════════════════════════════════════════════════╣
# ║  Run this ONCE at the start of each lab session.        ║
# ║  Usage:  bash start_lab.sh                              ║
# ╚══════════════════════════════════════════════════════════╝

set -e
BOLD="\033[1m"; GREEN="\033[32m"; CYAN="\033[36m"; RESET="\033[0m"

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Bangalore City Hospital — Meditech Lab                 ║"
echo "║  UE26MT324 · Medical Informatics · PES University       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Step 1: Install Python dependencies ──────────────────────
echo -e "${CYAN}[1/5] Installing Python dependencies…${RESET}"
pip3 install flask requests boto3 --break-system-packages -q 2>/dev/null || \
pip3 install flask requests boto3 -q 2>/dev/null || true
echo -e "${GREEN}  ✓ Dependencies ready${RESET}"

# ── Step 2: Start Docker stack ───────────────────────────────
echo -e "${CYAN}[2/5] Starting Docker services…${RESET}"
docker compose up -d
echo -e "${GREEN}  ✓ Docker stack started${RESET}"

# ── Step 3: Wait for services ────────────────────────────────
echo -e "${CYAN}[3/5] Waiting for services to initialise (90s)…${RESET}"
echo "  NiFi takes the longest — please wait."
sleep 30
echo "  Still waiting (PostgreSQL + ES + Kibana + MinIO)…"
sleep 30
echo "  Almost there…"
sleep 30
echo -e "${GREEN}  ✓ Wait complete${RESET}"

# ── Step 4: Load mock data ────────────────────────────────────
echo -e "${CYAN}[4/5] Loading mock data into ES + Kibana + MinIO…${RESET}"
python3 setup_services.py
echo ""

# ── Step 5: Create NiFi pipeline ─────────────────────────────
echo -e "${CYAN}[5/5] Creating NiFi HL7 pipeline…${RESET}"
python3 setup_nifi.py
echo ""

# ── Summary ──────────────────────────────────────────────────
echo -e "${BOLD}══════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}  ALL SERVICES READY${RESET}"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  SERVICE          URL                         CREDENTIALS"
echo "  ─────────────    ──────────────────────────  ───────────────────────"
echo "  NiFi (pipeline)  https://localhost:8443/nifi  admin / MeditechSecret123!"
echo "  Kibana (charts)  http://localhost:5601         (no login)"
echo "  MinIO (files)    http://localhost:9001         admin / MeditechSecret123!"
echo "  PostgreSQL (DB)  localhost:5432                admin / adminpassword"
echo "  Elasticsearch    http://localhost:9200         (no login)"
echo ""
echo "  HL7 SENDER UI  →  run: python3 hl7_sender.py"
echo "                     then open: http://localhost:5050"
echo ""
echo "══════════════════════════════════════════════════════════"
echo ""
read -p "  Start HL7 Sender UI now? [Y/n] " yn
case $yn in
  [Nn]*) echo "  Run manually: python3 hl7_sender.py" ;;
  *)     python3 hl7_sender.py ;;
esac
