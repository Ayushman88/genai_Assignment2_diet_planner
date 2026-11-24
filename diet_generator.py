import os
import re
from typing import Dict, List, Optional, Tuple
import requests

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
DEFAULT_OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

PROMPT_TEMPLATE = """Create a concise, healthy 7-day meal plan and weekly shopping list. No intro or outro text.

Preferences:
- Diet: {diet_type}
- Cuisine: {cuisine}
- Budget: {budget}
- Allergies/Avoid: {allergies}

Rules:
1. Strictly follow Diet and Allergies/Avoid.
2. Keep each meal short (3-6 words) and reuse ingredients across days for budget.

Output ONLY these two sections:

## 7-Day Meal Plan
| Day | Breakfast | Lunch | Dinner |
| --- | --- | --- | --- |
| Monday | Example Breakfast | Example Lunch | Example Dinner |
(Write all 7 rows from Monday to Sunday in this exact pipe-table format)

## Weekly Shopping List
Group into 3-4 short bullet categories (**Produce**, **Grains & Staples**, **Proteins & Dairy**, **Pantry**) with brief quantities.
"""


def build_prompt(
    diet_type: str,
    cuisine: str,
    budget: str,
    allergies: str,
) -> str:
    """Build the structured 7-day meal plan + shopping list prompt."""
    clean_allergies = allergies.strip() if allergies and allergies.strip() else "None"
    clean_cuisine = cuisine.strip() if cuisine and cuisine.strip() else "Any / Mixed"
    clean_budget = budget.strip() if budget and budget.strip() else "Moderate"
    return PROMPT_TEMPLATE.format(
        diet_type=diet_type.strip(),
        cuisine=clean_cuisine,
        budget=clean_budget,
        allergies=clean_allergies,
    )


def list_ollama_models(
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 2,
) -> Tuple[bool, List[str], Optional[str]]:
    """Fetch available local models from Ollama /api/tags."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        models = [m["name"] for m in data.get("models", []) if "name" in m]
        return True, models, None
    except requests.exceptions.ConnectionError:
        return False, [], f"Ollama not reachable at {base_url}"
    except requests.exceptions.RequestException as exc:
        return False, [], f"Ollama error: {exc}"


def generate_diet_plan(
    diet_type: str,
    cuisine: str,
    budget: str,
    allergies: str,
    provider: str = "ollama",
    model: Optional[str] = None,
    base_url: str = DEFAULT_OLLAMA_URL,
    openrouter_api_key: Optional[str] = None,
    timeout: int = 120,
) -> str:
    """Generate a 7-day meal plan + shopping list via Ollama (local) or OpenRouter (cloud)."""
    prompt = build_prompt(
        diet_type=diet_type,
        cuisine=cuisine,
        budget=budget,
        allergies=allergies,
    )

    if provider == "openrouter":
        return _generate_via_openrouter(
            prompt=prompt,
            model=model or DEFAULT_OPENROUTER_MODEL,
            api_key=openrouter_api_key or os.getenv("OPENROUTER_API_KEY", ""),
            timeout=timeout,
        )

    return _generate_via_ollama(
        prompt=prompt,
        model=model or DEFAULT_OLLAMA_MODEL,
        base_url=base_url,
        timeout=timeout,
    )


def _generate_via_ollama(prompt: str, model: str, base_url: str, timeout: int) -> str:
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.3,
            "num_predict": 450,
            "num_ctx": 1024,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code == 404:
            raise RuntimeError(f"Model '{model}' not found in Ollama. Run: ollama pull {model}")
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            f"Could not connect to Ollama at {base_url}. Start Ollama with `ollama serve`, or switch provider to OpenRouter."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(f"Ollama timed out after {timeout}s.") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    raw_output = resp.json().get("response", "").strip()
    if not raw_output:
        raise RuntimeError("Ollama returned an empty response.")
    return raw_output


def _generate_via_openrouter(prompt: str, model: str, api_key: str, timeout: int) -> str:
    if not api_key.strip():
        raise RuntimeError(
            "OpenRouter API key is missing. Set OPENROUTER_API_KEY in Vercel/env or paste your key in Settings."
        )
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    try:
        resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        detail = ""
        if exc.response is not None:
            detail = f" ({exc.response.text[:200]})"
        raise RuntimeError(f"OpenRouter request failed: {exc}{detail}") from exc

    choices = resp.json().get("choices", [])
    if not choices:
        raise RuntimeError("OpenRouter returned no choices.")
    raw_output = choices[0].get("message", {}).get("content", "").strip()
    if not raw_output:
        raise RuntimeError("OpenRouter returned an empty response.")
    return raw_output


def parse_meal_plan(markdown_text: str) -> Tuple[List[Dict[str, str]], List[Dict[str, object]], str]:
    """Extract 7-day table rows and categorized shopping list items from Markdown output."""
    days: List[Dict[str, str]] = []
    shopping_lines: List[str] = []
    in_shopping = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if re.match(r"^(?:#{1,4}\s*|\*\*)?.*shopping\s*list.*$", line, re.IGNORECASE):
            in_shopping = True
            continue

        if in_shopping:
            shopping_lines.append(raw_line)
            continue

        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip().replace("**", "") for c in line.strip("|").split("|")]
            if len(cells) >= 4:
                if all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells):
                    continue
                if cells[0].lower() == "day":
                    continue
                days.append(
                    {
                        "day": cells[0],
                        "breakfast": cells[1],
                        "lunch": cells[2],
                        "dinner": cells[3],
                    }
                )
        else:
            # Fallback if a small model outputs "* Monday: Breakfast, Lunch, Dinner"
            day_match = re.match(
                r"^(?:[-*•]\s*)?\*{0,2}(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\*{0,2}\s*:\s*(.+)$",
                line,
                re.IGNORECASE,
            )
            if day_match:
                parts = [p.strip() for p in day_match.group(2).split(",")]
                days.append(
                    {
                        "day": day_match.group(1).title(),
                        "breakfast": parts[0] if len(parts) > 0 else "—",
                        "lunch": parts[1] if len(parts) > 1 else "—",
                        "dinner": ", ".join(parts[2:]) if len(parts) > 2 else "—",
                    }
                )

    shopping_md = "\n".join(shopping_lines).strip()
    shopping_categories = _parse_shopping_categories(shopping_md)
    return days, shopping_categories, shopping_md


def _parse_shopping_categories(shopping_md: str) -> List[Dict[str, object]]:
    """Group shopping list bullet points into categories."""
    categories: List[Dict[str, object]] = []
    current_cat: Dict[str, object] = {"category": "Groceries", "items": []}

    for raw_line in shopping_md.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Category heading like "### Produce", "**Produce:**", or "* Produce:"
        heading_match = re.match(r"^(?:#{1,4}\s*)?\*\*([^*]+?):?\*\*:?\s*$", line)
        bullet_cat_match = re.match(r"^[-*•]\s*\*{0,2}([A-Za-z &/]+)\*{0,2}:\s*$", line)
        h3_match = re.match(r"^#{1,4}\s+(.+)$", line)
        if heading_match or bullet_cat_match or h3_match:
            if current_cat["items"]:
                categories.append(current_cat)
            match = heading_match or bullet_cat_match or h3_match
            cat_name = match.group(1).strip(" :")
            current_cat = {"category": cat_name, "items": []}
            continue

        if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
            item = line[2:].strip().replace("**", "")
            if item:
                current_cat["items"].append(item)

    if current_cat["items"]:
        categories.append(current_cat)

    return categories
