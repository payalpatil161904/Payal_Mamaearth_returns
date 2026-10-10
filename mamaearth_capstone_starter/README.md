# Mamaearth Returns & Growth Intelligence Pipeline

## Business question
Where are returns really coming from, and what is the true revenue picture once the data is cleaned?

## Pipeline
**SQL → Python → GenAI**

1. SQL creates the relational store and produces the nine raw-data business reports.
2. Python reads the original CSVs, cleans/reconciles the data, performs EDA and writes verified `narrator/findings.json`.
3. The narrator consumes `findings.json` and produces an SCR (Situation–Complication–Resolution) narrative using Gemini or a fully offline fallback.

## Structure
```text
README.md
requirements.txt
sql/
  schema.sql
  seed_data.sql
  reports.sql
data/
  customers.csv
  products.csv
  orders.csv
analysis/
  clean_and_eda.py
  visualize.py
visualizations/
  return_rate_by_payment.png
  monthly_revenue_trend.png
narrator/
  findings.json
  generate_narrative.py
  sample_output.txt
```

## Run order

### 1. MySQL Workbench
Open and run `sql/schema.sql`.
Then run `sql/seed_data.sql`.
Verify counts: **45 customers, 16 products, 180 orders**.
Then run each query in `sql/reports.sql` and compare with its expected-output comment.

### 2. Google Colab / Python
Install:
```python
!pip install pandas matplotlib google-genai
```
Run:
```python
!python analysis/clean_and_eda.py
!python analysis/visualize.py
```
`clean_and_eda.py` writes `narrator/findings.json`. The visualization script creates the two required PNGs.

### 3. GenAI narrator
Without an API key:
```python
!python narrator/generate_narrative.py
```
The offline fallback works without network access.

With Google AI Studio:
```python
import os
os.environ["GEMINI_API_KEY"]="YOUR_KEY_HERE"
!python narrator/generate_narrative.py
```
Never commit the API key.

## Key verification figures
Raw revenue **₹99,860.20**; cleaned revenue **₹97,358.30**; duplicate delta **₹2,501.90**; COD return rate **44.4%**; highest-risk segment **COD + Tier-2 at 54.5%**; true peak **2026-03 at ₹20,318.90**.

## Submission
Submit **one public GitHub repository link**. The brief explicitly requires the repository as the submission and does not require a PDF, slides, screenshots or video.
