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


def run(dry_run=False, send=True, only=None):
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
            new = [j for j in jobs if j.key not in store and filters.title_ok(j.title)]
            log.info("%-22s %4d postings, %3d new title matches", company["name"], len(jobs), len(new))
            candidates += [(company, j) for j in new]

    def enrich(pair):
        company, job = pair
        source = SOURCES[company["ats"]]
        if not job.description and hasattr(source, "describe"):
            try:
                source.describe(job, company)
            except Exception as exc:
                log.warning("No description for %s: %s", job.url, exc)
        job.min_years = min_years(job.description)
        return job

    with ThreadPoolExecutor(max_workers=8) as pool:
        evaluated = list(pool.map(enrich, candidates))

    matches = [j for j in evaluated if filters.location_ok(j.location) and filters.experience_ok(j.min_years)]
    score_jobs(matches, profile)
    matches.sort(key=lambda j: (-(j.score or 0), j.min_years if j.min_years is not None else 99, j.company))

    markdown = to_markdown(matches, errors)
    print(markdown)
    if dry_run:
        return matches
    write_reports(markdown, ROOT / "reports")
    for job in evaluated:
        store.add(job.key)
    store.save()
    if send and send_email(matches, errors):
        log.info("Email sent with %d jobs", len(matches))
    return matches


def cli():
    parser = argparse.ArgumentParser(description="Watch company career sites for matching jobs.")
    parser.add_argument("--dry-run", action="store_true", help="print matches without saving state or emailing")
    parser.add_argument("--no-email", action="store_true", help="save state and reports but skip the email")
    parser.add_argument("--company", action="append", help="only check this company (repeatable)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(dry_run=args.dry_run, send=not args.no_email, only=args.company)
