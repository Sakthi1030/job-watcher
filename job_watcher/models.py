from dataclasses import dataclass


@dataclass
class Job:
    company: str
    title: str
    location: str
    url: str
    source: str
    job_id: str
    posted: str = ""
    description: str = ""
    min_years: int | None = None
    score: int | None = None
    reason: str = ""

    @property
    def key(self) -> str:
        return f"{self.source}:{self.company}:{self.job_id}"
