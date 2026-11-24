import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from diet_generator import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_OPENROUTER_MODEL,
    PROMPT_TEMPLATE,
    build_prompt,
    generate_diet_plan,
    list_ollama_models,
    parse_meal_plan,
)
from exporter import export_to_docx, export_to_txt

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML_PATH = BASE_DIR / "static" / "index.html"

app = FastAPI(title="Diet Plan Generator")


class GenerateRequest(BaseModel):
    diet_type: str = "Vegetarian"
    cuisine: str = "Indian"
    budget: str = "Low (~$25 / ₹1,500 per week)"
    allergies: str = "None"
    provider: str = "ollama"
    model: Optional[str] = None
    ollama_url: str = DEFAULT_OLLAMA_URL
    openrouter_api_key: Optional[str] = None


class ExportRequest(BaseModel):
    markdown: str
    title: str = "Weekly Diet Plan"


@app.get("/", response_class=HTMLResponse)
def serve_home() -> HTMLResponse:
    if not INDEX_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return HTMLResponse(content=INDEX_HTML_PATH.read_text(encoding="utf-8"))


@app.get("/api/status")
def get_status(ollama_url: str = DEFAULT_OLLAMA_URL):
    connected, models, error = list_ollama_models(ollama_url)
    has_openrouter_env = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    is_vercel = bool(os.getenv("VERCEL"))
    default_model = (
        DEFAULT_OLLAMA_MODEL
        if DEFAULT_OLLAMA_MODEL in models
        else (models[0] if models else DEFAULT_OLLAMA_MODEL)
    )
    return {
        "ollama_connected": connected,
        "ollama_models": models,
        "ollama_error": error,
        "default_ollama_model": default_model,
        "default_openrouter_model": DEFAULT_OPENROUTER_MODEL,
        "has_openrouter_env": has_openrouter_env,
        "recommended_provider": "openrouter" if (is_vercel or (not connected and has_openrouter_env)) else "ollama",
        "prompt_template": PROMPT_TEMPLATE,
    }


@app.post("/api/generate")
def generate_plan(req: GenerateRequest):
    try:
        markdown = generate_diet_plan(
            diet_type=req.diet_type,
            cuisine=req.cuisine,
            budget=req.budget,
            allergies=req.allergies,
            provider=req.provider,
            model=req.model,
            base_url=req.ollama_url,
            openrouter_api_key=req.openrouter_api_key,
        )
        days, shopping_categories, shopping_md = parse_meal_plan(markdown)
        return {
            "markdown": markdown,
            "days": days,
            "shopping_categories": shopping_categories,
            "shopping_md": shopping_md,
            "prompt_used": build_prompt(req.diet_type, req.cuisine, req.budget, req.allergies),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/export/docx")
def download_docx(req: ExportRequest):
    payload = export_to_docx(req.markdown, title=req.title)
    slug = (req.title or "weekly_diet_plan").lower().replace(" ", "_").replace("/", "_")
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{slug}.docx"'},
    )


@app.post("/api/export/txt")
def download_txt(req: ExportRequest):
    payload = export_to_txt(req.markdown, title=req.title)
    slug = (req.title or "weekly_diet_plan").lower().replace(" ", "_").replace("/", "_")
    return Response(
        content=payload,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{slug}.txt"'},
    )
