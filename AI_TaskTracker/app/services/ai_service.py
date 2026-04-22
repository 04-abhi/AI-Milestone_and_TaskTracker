"""
AI Service — Groq Cloud API
Handles all LLM calls for:
  - Milestone Planner  (generate day-wise plan from a goal)
  - Breakdown Planner  (recovery plan for a procrastinated task)

Groq API is OpenAI-compatible.
Base URL : https://api.groq.com/openai/v1
Models   : llama-3.3-70b-versatile, llama3-70b-8192, mixtral-8x7b-32768
Docs     : https://console.groq.com/docs
"""
import json
import re
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


# ── Shared helpers ──────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown wrappers."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*",     "", text)
    text = re.sub(r"```\s*$",     "", text)
    return text.strip()


async def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """
    POST to Groq OpenAI-compatible /chat/completions endpoint.
    Returns the raw text content of the first choice.
    Raises ValueError on API-level or network errors.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Get a free key at https://console.groq.com and add it to .env"
        )

    url = f"{settings.GROQ_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.4,   # low temp → more deterministic JSON output
        "max_tokens": 4096,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise ValueError(
            "Groq API request timed out after 60s. "
            "Try a shorter deadline or simpler description."
        )
    except httpx.RequestError as e:
        raise ValueError(f"Network error calling Groq API: {e}")

    if response.status_code != 200:
        body = response.text[:600]
        logger.error(f"Groq API error {response.status_code}: {body}")

        # Give a clear message for the most common errors
        if response.status_code == 401:
            raise ValueError("Groq API key is invalid. Check GROQ_API_KEY in .env")
        if response.status_code == 429:
            raise ValueError(
                "Groq rate limit reached. "
                "Wait a moment and try again, or check your plan at console.groq.com"
            )
        if response.status_code == 400:
            raise ValueError(
                f"Groq rejected the request (400). "
                f"Check GROQ_MODEL in .env — current value: '{settings.GROQ_MODEL}'. "
                f"Valid models: llama-3.3-70b-versatile, llama3-70b-8192, mixtral-8x7b-32768. "
                f"Raw error: {body}"
            )
        raise ValueError(f"Groq API returned {response.status_code}: {body}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected Groq response structure: {e}") from e

    logger.info(
        f"Groq call OK — model={settings.GROQ_MODEL} "
        f"tokens={data.get('usage', {}).get('total_tokens', '?')}"
    )
    return content


def _parse_json_response(raw: str, context: str = "AI") -> Any:
    """Strip fences, parse JSON, raise ValueError with context on failure."""
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"{context} JSON parse error: {e}\nRaw output:\n{cleaned[:600]}")
        raise ValueError(
            f"{context} returned invalid JSON. Please try again."
        ) from e


# ── Milestone Planner ───────────────────────────────────────────────────────

PLANNER_SYSTEM = (
    "You are an AI planner generator. "
    "You ONLY output valid JSON — no explanation, no markdown, no preamble. "
    "Never wrap the JSON in code fences."
)


async def generate_milestone_plan(
    title: str,
    description: str,
    days: int,
) -> dict:
    """
    Returns a dict matching:
    {
      "title": str,
      "description": str,
      "deadline_days": int,
      "plan": [{"day": int, "task": str, "subtasks": [str, ...]}, ...]
    }
    """
    user_prompt = f"""User Input:
Title: {title}
Description: {description or 'Not provided'}
Deadline: {days} days

Your job:
Generate a day-wise actionable plan so the user can achieve the goal within the deadline.

STRICT RULES:
- Output ONLY valid JSON
- NO explanation text
- NO markdown
- NO code fences
- FOLLOW schema EXACTLY
- Generate exactly {days} entries (1 per day)
- Each day must have:
  - "day" number
  - "task" (short main task, max 10 words)
  - "subtasks" (2-4 actionable steps, each max 15 words)

SCHEMA:
{{
  "title": "",
  "description": "",
  "deadline_days": 0,
  "plan": [
    {{
      "day": 1,
      "task": "",
      "subtasks": []
    }}
  ]
}}

IMPORTANT:
- Tasks must be progressive (gradually increasing difficulty)
- Tasks must be realistic and achievable
- Adapt based on the goal type (fitness, learning, skill, project, etc.)
- Ensure consistency and logical progression"""

    raw = await _call_groq(PLANNER_SYSTEM, user_prompt)
    plan = _parse_json_response(raw, context="Milestone Planner")

    if not isinstance(plan.get("plan"), list):
        raise ValueError("AI response missing 'plan' array.")
    if len(plan["plan"]) != days:
        logger.warning(
            f"Planner returned {len(plan['plan'])} days, expected {days}"
        )

    return plan


# ── Procrastination Breakdown Planner ──────────────────────────────────────

BREAKDOWN_SYSTEM = (
    "You are a task recovery planner. "
    "You ONLY output valid JSON — no explanation, no markdown, no preamble. "
    "Never wrap the JSON in code fences."
)


async def generate_breakdown_plan(
    title: str,
    description: str,
    original_due_date: str,
    days_overdue: int,
    recovery_days: int,
    done_subtasks: list[str],
    pending_subtasks: list[str],
) -> dict:
    """
    Returns a dict matching:
    {
      "title": str,
      "remaining_summary": str,
      "recovery_days": int,
      "plan": [{"day": int, "task": str, "subtasks": [str, ...]}, ...]
    }
    """
    if done_subtasks:
        progress_note = (
            f"Already completed (DO NOT repeat): {', '.join(done_subtasks)}.\n"
            f"Still pending: {', '.join(pending_subtasks) if pending_subtasks else 'infer from context'}."
        )
    else:
        progress_note = "No subtasks tracked yet — plan from scratch based on task title and description."

    user_prompt = f"""Original Task: {title}
Description: {description or 'Not provided'}
Original Due Date: {original_due_date}
Days overdue: {days_overdue}
Recovery window: {recovery_days} days from today

Subtask Progress:
{progress_note}

The user procrastinated this task. Generate a realistic {recovery_days}-day recovery plan that:
- SKIPS already completed work entirely
- Covers only the REMAINING work
- Is progressive and achievable day by day
- Fits the scope into the recovery window realistically

STRICT RULES:
- Output ONLY valid JSON
- NO explanation, NO markdown, NO code fences
- Exactly {recovery_days} day entries in the plan array

SCHEMA:
{{
  "title": "",
  "remaining_summary": "one sentence describing what still needs to be done",
  "recovery_days": {recovery_days},
  "plan": [
    {{
      "day": 1,
      "task": "",
      "subtasks": []
    }}
  ]
}}"""

    raw = await _call_groq(BREAKDOWN_SYSTEM, user_prompt)
    plan = _parse_json_response(raw, context="Breakdown Planner")

    if not isinstance(plan.get("plan"), list):
        raise ValueError("AI response missing 'plan' array.")

    return plan
