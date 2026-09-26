"""Company career sites without a standard ATS API (parsed from their HTML/JSON)."""
import re
from urllib.parse import quote

from ..http import get_json, get_text, strip_html
from ..models import Job


class DeloitteUSI:
    """usijobs.deloitte.com (Deloitte US - India Offices)."""

    SEARCH = "https://usijobs.deloitte.com/en_US/careersUSI/SearchJobs/{term}?jobRecordsPerPage=50"
    ARTICLE = re.compile(r'<article class="article--result.*?</article>', re.S)
    LINK = re.compile(r'<a href="(https://usijobs\.deloitte\.com/en_US/careersUSI/JobDetail/[^"]+/(\d+))"[^>]*>(.*?)</a>', re.S)

    def fetch(self, cfg, terms):
        jobs = {}
        for term in terms:
            page = get_text(self.SEARCH.format(term=quote(term)))
            for block in self.ARTICLE.findall(page):
                m = self.LINK.search(block)
                if not m:
                    continue
                url, job_id, title = m.groups()
                subtitle = strip_html(block[m.end():])
                location = subtitle.split("|")[-1].strip() if "|" in subtitle else "India"
                jobs[job_id] = Job(
                    company=cfg["name"], title=strip_html(title), location=f"{location}, India",
                    url=url, source="deloitte_usi", job_id=job_id,
                )
        return list(jobs.values())

    def describe(self, job, cfg):
        job.description = strip_html(get_text(job.url))


class Capgemini:
    API = "https://cg-job-search-microservices.azurewebsites.net/api/job-search"

    def fetch(self, cfg, terms):
        jobs = {}
        for term in terms:
            data = get_json(self.API, params={"page": 1, "size": 100, "country_code": "in-en", "search": term})
            for j in data.get("data", []):
                jobs[j["_id"]] = Job(
                    company=cfg["name"], title=j.get("title", ""), location=f"{j.get('location', '')}, India",
                    url=j.get("apply_job_url", "").split("?")[0], source="capgemini", job_id=j["_id"],
                    posted=(j.get("updated_at") or "")[:10], description=j.get("description_stripped", ""),
                )
        return list(jobs.values())


class Cognizant:
    SEARCH = "https://careers.cognizant.com/india-en/jobs/?keyword={term}"
    CARD = re.compile(r'<div class="card card-job" data-id="(\d+)">(.*?)(?=<div class="card card-job"|$)', re.S)
    LINK = re.compile(r'href="(/india-en/jobs/\d+/[^"]+)">(.*?)</a>', re.S)
    # First meta item is the location; the site also lists jobs outside India.
    LOCATION = re.compile(r'<li class="list-inline-item">(.*?)</li>', re.S)

    def fetch(self, cfg, terms):
        jobs = {}
        for term in terms:
            page = get_text(self.SEARCH.format(term=quote(term)))
            for job_id, card in self.CARD.findall(page):
                link, location = self.LINK.search(card), self.LOCATION.search(card)
                if not link:
                    continue
                jobs[job_id] = Job(
                    company=cfg["name"], title=strip_html(link.group(2)),
                    location=strip_html(location.group(1)) if location else "",
                    url=f"https://careers.cognizant.com{link.group(1)}", source="cognizant", job_id=job_id,
                )
        return list(jobs.values())

    def describe(self, job, cfg):
        job.description = strip_html(get_text(job.url))
