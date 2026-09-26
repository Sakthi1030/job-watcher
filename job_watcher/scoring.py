"""Optional LLM fit score using the Gemini API free tier (skipped without GEMINI_API_KEY)."""
import json
import logging
import os

from .http import get_json, post_json

log = logging.getLogger(__name__)
API = "https://generativelanguage.googleapis.com/v1beta"


def resolve_model(preferred: str, key: str) -> str | None:
    """Use the configured model if it exists, else the newest available Flash model."""
    try:
        models = get_json(f"{API}/models", params={"key": key, "pageSize": 200}).get("models", [])
    except Exception as exc:
        log.warning("Could not list Gemini models: %s", exc)
        return preferred
    usable = [m["name"].removeprefix("models/") for m in models
              if "generateContent" in m.get("supportedGenerationMethods", [])]
    if preferred in usable:
        return preferred
    flash = sorted((n for n in usable if "flash" in n and "lite" not in n and "preview" not in n
                    and "exp" not in n and "image" not in n and "tts" not in n), reverse=True)
    return flash[0] if flash else None

PROMPT = """You are screening job postings for one candidate.

Candidate profile:
{profile}

Job posting:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Rate how well the candidate fits this job from 0 to 100, weighing required skills,
experience level and seniority. Reply as JSON: {{"score": <int>, "reason": "<one short sentence>"}}"""


def score_jobs(jobs, profile: dict) -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not jobs:
        return
    model = resolve_model(profile.get("gemini_model", "gemini-flash-latest"), key)
    if not model:
        log.warning("No Gemini Flash model available; skipping fit scores")
        return
    log.info("Scoring with %s", model)
    url = f"{API}/models/{model}:generateContent?key={key}"
    for job in jobs[: profile.get("max_scored_per_run", 25)]:
        prompt = PROMPT.format(
            profile=profile["candidate_summary"], title=job.title, company=job.company,
            location=job.location, description=job.description[:4000],
        )
        try:
            data = post_json(url, {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
            }, retries=4)  # Gemini free tier returns 503 when busy
            result = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
            job.score, job.reason = int(result["score"]), result.get("reason", "")
        except Exception as exc:  # scoring is best effort; never fail the run over it
            log.warning("Gemini scoring failed for %s: %s", job.title, exc)
