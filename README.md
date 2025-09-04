
# Country Profile — Streamlit One‑Pager

A ready-to-run Streamlit template to turn your Country Profile into a single interactive dashboard page.

## Quickstart

```bash
cd country_profile_streamlit
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown in your terminal.

## Data Inputs (CSV)

Upload your own CSVs with these minimal schemas (column names are case-sensitive):

- **IP activity between two countries** (`flows.csv`)
  - `year` (int), `origin_country` (str), `dest_country` (str), `ip_type` (str: patent|trademark|design), `applications` (int)

- **Top filers** (`top_filers.csv`)
  - `filer` (str), `origin_country` (str), `dest_country` (str), `ip_type` (str), `filings` (int)

- **Gender inventors split** (`gender_split.csv`)
  - `year` (int), `origin_country` (str), `dest_country` (str), `female_inventors` (int), `male_inventors` (int)

- **PPH requests** (`pph.csv`)
  - `year` (int), `direction` (str like "CIPO→JPO"), `requests` (int)

- **Patent importance** (`importance.csv`)
  - `year` (int), `jurisdiction` (str), `importance_score` (float)

You can start with the sample files in `sample_data/` and replace them with your own.

## Design Notes

- **One page** with tabs (Overview, Flows & PPH, Top Filers, Gender, Annex) and a **sticky KPI header**.
- Charts use **Plotly** so they are interactive (hover, zoom, legend toggle).
- Use the left sidebar to **filter year range and IP types**; every chart updates.
- Theme in `.streamlit/config.toml` — tweak to match brand colors.
- Export filtered CSVs via the **Download** button in the header.

## Deploy

- **Local**: `streamlit run app.py`
- **Streamlit Community Cloud**: push to GitHub, then add the app. No servers to manage.
- **Docker** (optional):
  ```Dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  EXPOSE 8501
  CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
  ```

---

Generated: 2025-09-04
