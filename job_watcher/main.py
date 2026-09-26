"""Daily run: fetch postings, filter to new relevant roles, score, report and email."""
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .filters import Filters, min_years
from .report import send_email, to_markdown, write_reports
from .scoring import score_jobs
from .sources import SOURCES
from .store import SeenStore

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("job_watcher")


def load_yaml(name):
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf-8"))


def fetch_company(company, terms):
    source = SOURCES[company["ats"]]
    return company, source.fetch(company, terms)


def run(dry_run=False, send=True, only=None, test_email=False, resend_all=False):
    profile = load_yaml("profile.yaml")
    companies = [c for c in load_yaml("companies.yaml")["companies"] if not only or c["name"] in only]
    filters = Filters(profile)
    store = SeenStore(ROOT / "data" / "seen.json")
    errors, candidates = [], []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_company, c, profile["search_terms"]) for c in companies]
        for future, company in zip(futures, companies):
            try:
                _, jobs = future.result()
            except Exception as exc:
                errors.append(f"{company['name']} ({exc.__class__.__name__})")
                continue
            fresh = [j for j in jobs if resend_all or j.key not in store]
            new = [j for j in fresh if filters.title_ok(j.title)]
            # Some firms use vague titles; read those descriptions and keep them only if they mention my skills.
            vague = [j for j in fresh if company.get("broad_titles") and not filters.title_ok(j.title)
                     and filters.generic_title_ok(j.title)]
            log.info("%-22s %4d postings, %3d title matches, %3d vague titles",
                     company["name"], len(jobs), len(new), len(vague))
            candidates += [(company, j, False) for j in new] + [(company, j, True) for j in vague]

    def enrich(item):
        company, job, vague = item
        source = SOURCES[company["ats"]]
        if not job.description and hasattr(source, "describe"):
            try:
                source.describe(job, company)
            except Exception as exc:
                log.warning("No description for %s: %s", job.url, exc)
        job.min_years = min_years(job.description)
        job.vague = vague
        return job

    with ThreadPoolExecutor(max_workers=8) as pool:
        evaluated = list(pool.map(enrich, candidates))

    located = [
        j for j in evaluated
        if filters.location_ok(j.location) and filters.description_ok(j.description)
        and (not j.vague or filters.skill_hits(j.description) >= filters.min_skill_hits)
    ]
    core = [j for j in located if filters.experience_ok(j.min_years)]
    stretch = [j for j in located if filters.is_stretch(j.min_years)]
    score_jobs(core + stretch, profile)
    min_score = profile.get("stretch_min_score", 75)
    for job in stretch:
        job.stretch = True
    matches = core + [j for j in stretch if (j.score or 0) >= min_score]
    floor = profile.get("min_fit_score", 40)
    matches = [j for j in matches if j.score is None or j.score >= floor]  # unscored jobs are kept
    matches.sort(key=lambda j: (-(j.score or 0), j.min_years if j.min_years is not None else 99, j.company))

    markdown = to_markdown(matches, errors)
    print(markdown)
    if dry_run:
        return matches
    write_reports(markdown, ROOT / "reports")
    for job in evaluated:
        store.add(job.key)
    store.save()
    if send and send_email(matches, errors, test=test_email or resend_all):
        log.info("Email sent with %d jobs", len(matches))
    elif test_email:
        raise SystemExit("Test email not sent: check the GMAIL_USER and GMAIL_APP_PASSWORD secrets")
    return matches


def cli():
    parser = argparse.ArgumentParser(description="Watch company career sites for matching jobs.")
    parser.add_argument("--dry-run", action="store_true", help="print matches without saving state or emailing")
    parser.add_argument("--no-email", action="store_true", help="save state and reports but skip the email")
    parser.add_argument("--company", action="append", help="only check this company (repeatable)")
    parser.add_argument("--test-email", action="store_true", help="send the email even when there are no new jobs")
    parser.add_argument("--resend-all", action="store_true", help="include already-reported jobs (full digest)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(dry_run=args.dry_run, send=not args.no_email, only=args.company, test_email=args.test_email, resend_all=args.resend_all)
