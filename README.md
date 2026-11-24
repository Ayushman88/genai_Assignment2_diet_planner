# Diet Plan Generator

## Problem Statement
People want simple, healthy meal ideas that fit their dietary preferences, budget, and allergies. This app generates a **7-day meal plan** (Breakfast, Lunch, Dinner) as a structured table along with a categorized **Weekly Shopping List** using a local LLM via **Ollama**.
People want simple, healthy meal ideas that fit their dietary preferences, budget, and allergies. This app generates a **7-day meal plan** (Breakfast, Lunch, Dinner) as a structured table and pastel bento cards, along with a categorized **Weekly Shopping List**.

## Tech Stack
- **Language:** Python 3
- **UI Framework:** Streamlit
- **Local LLM Runtime:** Ollama (`llama3.2` or any installed Ollama model)
- **Export:** `python-docx` (`.docx` with formatted Word table) and UTF-8 `.txt`
- **Frontend:** Clean HTML / CSS / Vanilla JS (warm cream & pastel bento UI)
- **Backend:** Python + FastAPI
- **LLM Support:**
  - **Local:** Ollama (`llama3.2:latest` or any local model)
  - **Cloud / Vercel (One-Host):** OpenRouter (`openrouter/free`)
- **Export:** `python-docx` (`.docx`) and UTF-8 `.txt`

## Project Structure
```text
.
├── app.py               # Streamlit web UI with 5 sample presets & export buttons
├── diet_generator.py    # Prompt builder & Ollama API client
├── exporter.py          # .docx (with table rendering) and .txt export helpers
├── requirements.txt     # Python dependencies
├── api/
│   └── index.py         # FastAPI server & Vercel serverless entrypoint
├── static/
│   └── index.html       # Custom HTML/CSS/JS bento UI
├── diet_generator.py    # Prompt builder, Ollama/OpenRouter client & parser
├── exporter.py          # .docx and .txt export helpers
├── vercel.json          # Single-host Vercel routing
├── requirements.txt
└── README.md
```

## How to Run
## Run Locally (with Ollama)
1. Start Ollama and ensure a model is pulled:
   ```bash
   ollama serve
   ollama pull llama3.2
   ```
2. Install dependencies and start the server:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn api.index:app --reload --port 8000
   ```
3. Open `http://localhost:8000`.

### 1. Start Ollama and pull a model
```bash
ollama serve
ollama pull llama3.2
```

### 2. Install Python dependencies
```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Launch the Streamlit app
```bash
streamlit run app.py
```

Open the local URL shown in your terminal (typically `http://localhost:8501`), choose your **Diet Type** (Vegetarian / Non-Vegetarian), **Cuisine**, **Weekly Budget**, and **Allergies** (or load one of the 5 built-in presets), and click **Generate 7-Day Diet Plan**.

## Sample Test Inputs (for Testing & Screenshots)
1. **Vegetarian** | Indian | Low (~$25 / ₹1,500 per week) | Peanuts
2. **Non-Vegetarian** | Mediterranean | Moderate (~$60 / ₹4,000 per week) | Dairy
3. **Vegetarian** | Asian | Moderate (~$50 / ₹3,500 per week) | Gluten
4. **Non-Vegetarian** | Continental | Low (~$30 / ₹2,000 per week) | Shellfish
5. **Vegetarian** | Mixed / Any | Flexible | None

## Screenshots
_Add 1–2 screenshots of the running Streamlit app showing the 7-day meal plan table and shopping list here._
## Deploy on Vercel (Single Host)
Vercel hosts both `static/index.html` and the Python FastAPI `/api/*` endpoints from one host. Since Vercel cannot reach `localhost:11434` on your machine, add `OPENROUTER_API_KEY` in **Vercel Project Settings → Environment Variables** (it uses `openrouter/free` by default), then deploy with `vercel` or connect your GitHub repo.
