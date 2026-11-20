# Career Venture Lab — Team Lucas (`MKT-1` | Algebra 2)

**Business:** Local-Business Marketing Agency (`MKT-1`)  
**Course:** Algebra 2  
**Stage:** Stage 1 (Deterministic Math Engine, Dated Event Ledger, JSON Save/Restore, Acceptance Tests)

## Project Files
- `app.py` — Streamlit dashboard application (Overview, Startup Funding & Inputs, Persistent Algebra 2 Math Skills Panel, Deterministic Ledger & Simulation Runner, Save/Load JSON Snapshot, Stage 1 Acceptance Test Runner)
- `engine.py` — Core `Decimal`-based accounting engine, capacity calculations, dated ledger generator, and snapshot validator
- `sample_data/monthly_fixture.csv` — Exact 3-month MKT-1 acceptance fixture
- `tests/test_mkt1.py` — Pytest suite verifying baseline constants, 3-month fixture outputs, revision shock, zero-sales edge case, loan accounting, duplicate `run_id` protection, and snapshot import rejections
- `requirements.txt` — Python dependencies

## Run Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the automated test suite:
   ```bash
   pytest -v
   ```
3. Launch the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## Render Deployment Command
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

## Build Stages
- **Stage 1 (Implemented):** Overview & System Map, Startup Funding & Editable Parameters, Persistent Algebra 2 Math Panel (Foundation / Applied / Advanced), Deterministic Monthly Engine & Dated Event Ledger, Save/Load JSON Snapshot, Acceptance Test Runner.
- **Stage 2 (Planned):** Departmental AI Assistant Tabs (Finance, Operations, Marketing, Reviewer), Full Report Center (CSV/PDF), Costed Marketing Studio.
- **Stage 3 (Planned):** Cross-Course Connections Panel, Snapshot-Based Practice Assessment Generator.
