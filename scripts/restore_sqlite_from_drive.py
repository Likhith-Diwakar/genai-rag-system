name: Daily RAG Pipeline

on:
  schedule:
    - cron: "0 21 * * *"   # 3:00 AM IST
  workflow_dispatch:

jobs:
  run-sync:
    runs-on: ubuntu-latest

    steps:
      # ── Checkout ─────────────────────────────────────────
      - name: Checkout repo
        uses: actions/checkout@v4

      # ── Python setup ─────────────────────────────────────
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      # ── System dependencies ──────────────────────────────
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y poppler-utils

      # ── Python dependencies ──────────────────────────────
      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install --upgrade --force-reinstall google-genai

      # ── Verify Gemini SDK ────────────────────────────────
      - name: Verify Gemini SDK
        run: |
          python - <<'EOF'
          from google import genai
          print("Google GenAI SDK loaded successfully")
          EOF

      # ── Environment variables ────────────────────────────
      - name: Set environment variables
        run: |
          echo "QDRANT_URL=${{ secrets.QDRANT_URL }}" >> $GITHUB_ENV
          echo "QDRANT_API_KEY=${{ secrets.QDRANT_API_KEY }}" >> $GITHUB_ENV
          echo "GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }}" >> $GITHUB_ENV
          echo "HF_API_TOKEN=${{ secrets.HF_API_TOKEN }}" >> $GITHUB_ENV
          echo "HF_TOKEN=${{ secrets.HF_TOKEN }}" >> $GITHUB_ENV
          echo "SQLITE_FOLDER_ID=${{ secrets.SQLITE_FOLDER_ID }}" >> $GITHUB_ENV
          echo "SQLITE_BACKUP_FOLDER_ID=${{ secrets.SQLITE_BACKUP_FOLDER_ID }}" >> $GITHUB_ENV
          echo "QDRANT_FOLDER_ID=${{ secrets.QDRANT_FOLDER_ID }}" >> $GITHUB_ENV
          echo "OPENROUTER_API_KEY=${{ secrets.OPENROUTER_API_KEY }}" >> $GITHUB_ENV
          echo "GROQ_API_KEY=${{ secrets.GROQ_API_KEY }}" >> $GITHUB_ENV
          echo "SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}" >> $GITHUB_ENV
          echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" >> $GITHUB_ENV

      # ── Service account JSON (multiline safe) ────────────
      - name: Set Google Service Account credentials
        run: |
          echo "GOOGLE_SERVICE_ACCOUNT_JSON<<EOF" >> $GITHUB_ENV
          echo '${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}' >> $GITHUB_ENV
          echo "EOF" >> $GITHUB_ENV

      # ── Verify auth ──────────────────────────────────────
      - name: Verify Google Service Account
        run: |
          python - <<'EOF'
          import os, json

          raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
          if not raw.strip():
              raise SystemExit("GOOGLE_SERVICE_ACCOUNT_JSON is empty")

          data = json.loads(raw)

          required = ["type", "project_id", "private_key", "client_email"]
          missing = [k for k in required if k not in data]

          if missing:
              raise SystemExit(f"Missing keys: {missing}")

          print("Service account OK")
          EOF

      # ── CRITICAL FIX: RESTORE SQLITE ───────────────────
      - name: Restore SQLite DB
        run: |
          python -u scripts/restore_sqlite.py

      # ── Run pipeline ─────────────────────────────────────
      - name: Run Daily Pipeline
        run: |
          python -u scripts/run_daily_sync.py
