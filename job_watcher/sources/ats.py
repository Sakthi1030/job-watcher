"""Public job-board APIs: SmartRecruiters, Greenhouse, Lever and Workday.

Every source exposes fetch(company_cfg, search_terms) -> list[Job]; sources whose
list endpoint has no description also expose describe(job, company_cfg).
"""
from ..http import get_json, post_json, strip_html
from ..models import Job


class SmartRecruiters:
    def fetch(self, cfg, terms):
        slug = cfg["id"]
        jobs = {}
        for term in terms:
            data = get_json(
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                params={"q": term, "country": "in", "limit": 100},
            )
            for p in data.get("content", []):
                loc = p.get("location", {})
                jobs[p["id"]] = Job(
                    company=cfg["name"], title=p["name"], source="smartrecruiters",
                    location=", ".join(filter(None, [loc.get("city"), loc.get("region"), "India"])),
                    url=f"https://jobs.smartrecruiters.com/{slug}/{p['id']}",
                    job_id=p["id"], posted=p.get("releasedDate", "")[:10],
                )
        return list(jobs.values())

    def describe(self, job, cfg):
        data = get_json(f"https://api.smartrecruiters.com/v1/companies/{cfg['id']}/postings/{job.job_id}")
        sections = data.get("jobAd", {}).get("sections", {})
        job.description = strip_html(" ".join((s or {}).get("text", "") for s in sections.values()))


class Greenhouse:
    def fetch(self, cfg, terms):
        data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{cfg['id']}/jobs", params={"content": "true"})
        return [
            Job(
                company=cfg["name"], title=j["title"], source="greenhouse",
                location=(j.get("location") or {}).get("name", ""), url=j["absolute_url"],
                job_id=str(j["id"]), posted=(j.get("updated_at") or "")[:10],
                description=strip_html(j.get("content", "")),
            )
            for j in data.get("jobs", [])
        ]


class Lever:
    def fetch(self, cfg, terms):
        data = get_json(f"https://api.lever.co/v0/postings/{cfg['id']}", params={"mode": "json"})
        jobs = []
        for p in data:
            lists = " ".join(f"{l.get('text', '')} {strip_html(l.get('content', ''))}" for l in p.get("lists", []))
            jobs.append(Job(
                company=cfg["name"], title=p["text"], source="lever",
                location=p.get("categories", {}).get("location", "") or "", url=p["hostedUrl"],
                job_id=p["id"], description=f"{p.get('descriptionPlain', '')} {lists}",
            ))
        return jobs


class Workday:
    """Workday's career-site JSON API: /wday/cxs/{tenant}/{site}/jobs."""

    def _base(self, cfg):
        return f"https://{cfg['host']}/wday/cxs/{cfg['tenant']}/{cfg['site']}"

    def fetch(self, cfg, terms):
        jobs = {}
        for term in terms:
            for offset in range(0, cfg.get("max_results", 60), 20):
                data = post_json(f"{self._base(cfg)}/jobs", {
                    "appliedFacets": {}, "limit": 20, "offset": offset, "searchText": f"{term} India",
                })
                postings = data.get("jobPostings", [])
                for p in postings:
                    path = p.get("externalPath", "")
                    jobs[path] = Job(
                        company=cfg["name"], title=p.get("title", ""), source="workday",
                        location=p.get("locationsText", ""),
                        url=f"https://{cfg['host']}/en-US/{cfg['site']}{path}",
                        job_id=path, posted=p.get("postedOn", ""),
                    )
                if len(postings) < 20:
                    break
        return list(jobs.values())

    def describe(self, job, cfg):
        info = get_json(f"{self._base(cfg)}{job.job_id}").get("jobPostingInfo", {})
        places = [info.get("location", "")] + info.get("additionalLocations", [])
        country = (info.get("country") or {}).get("descriptor", "")
        job.location = ", ".join(dict.fromkeys(filter(None, places + [country])))
        job.description = strip_html(info.get("jobDescription", ""))
