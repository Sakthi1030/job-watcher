"""Optional LLM fit score using the Gemini API free tier (skipped without GEMINI_API_KEY)."""
import json
import logging
import os

from .http import post_json

log = logging.getLogger(__name__)

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
    model = profile.get("gemini_model", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    for job in jobs[: profile.get("max_scored_per_run", 25)]:
        prompt = PROMPT.format(
            profile=profile["candidate_summary"], title=job.title, company=job.company,
            location=job.location, description=job.description[:4000],
        )
        try:
            data = post_json(url, {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
            }, retries=1)
            result = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
            job.score, job.reason = int(result["score"]), result.get("reason", "")
        except Exception as exc:  # scoring is best effort; never fail the run over it
            log.warning("Gemini scoring failed for %s: %s", job.title, exc)
