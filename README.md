# Xovate Data Validation Engine

I built this as a tiny full-stack playground: FastAPI does the heavy lifting with Pandas, and a Vite + React client gives humans a friendlier face than curl. Feed it a CSV with `id`, `email`, and `age`, and it tells you exactly what needs fixing.

## How the pieces come together
- **FastAPI backend (`backend/`)** ingests CSV files through `POST /validate`. It parses with Pandas, runs the volume/email/age checks, and responds with a simple `status` plus a list of row-level errors. The server enables permissive CORS during development so the frontend can talk to it; lock this down before deploying publicly.
- **Built-in docs/testing** – I left FastAPI’s Swagger UI exposed at `/docs`, so you can validate payloads without leaving the browser and share auto-generated curl snippets. It’s the same contract the React app uses, just friendlier for quick API pokes.
- **React frontend (`frontend/`)** is a single-page uploader. Drop a CSV, it calls the backend, and displays a status chip plus a table of issues. No design awards, but it focuses on clarity.
- **Sample CSVs**: `test_data_clean.csv` should pass, `test_data_dirty.csv` showcases every failure case.

## Spinning it up locally
### Backend (FastAPI)
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Prefer containers? `docker build -t xovate-validator . && docker run --rm -p 8000:8000 xovate-validator`.

### Frontend (React)
```bash
cd frontend
npm install
npm run dev
```
Visit the printed Vite URL (defaults to `http://localhost:5173`). If your backend lives elsewhere, set `VITE_API_BASE_URL` in `frontend/.env`.

## Validation behavior (TL;DR for stakeholders)
1. **Column sanity** – If `id`, `email`, or `age` is missing, the API returns immediate global errors so nobody assumes a partial success.
2. **Volume guard** – Less than 11 data rows? You get one `_file` error and the rest of the checks stop.
3. **Email completeness** – Blank or whitespace emails are flagged individually with their CSV row index (header is row 0).
4. **Age rules** – Values must be integers between 18 and 100. The response distinguishes invalid formats (`"30yrs"`, empty, etc.) from out-of-range numbers (`12`, `101`).
5. **Multiple hits allowed** – A single row can appear multiple times in the error list (e.g., missing email and invalid age).

## Quick manual test plan
1. Start both services.
2. Upload `test_data_clean.csv` via the frontend → status should flip to `PASS` with zero errors.
3. Upload `test_data_dirty.csv` → expect the 18-error set (7 email gaps + 11 age issues) just like Swagger shows.
4. Kill the backend and submit again → frontend should show a friendly “Failed to fetch” style banner, proving network errors are handled.
5. Rebuild the frontend (`npm run build && npm run preview`) and hit the preview URL to smoke-test production mode.

Once those five steps succeed, the validation engine is ready for anyone who has a CSV and questions about their data quality.
