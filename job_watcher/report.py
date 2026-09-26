"""Markdown report (committed to the repo) and HTML email via Gmail SMTP."""
import html
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from pathlib import Path


def _exp(job):
    if job.min_years is None:
        return "not stated"
    return f"{job.min_years}+ yrs" + (" (stretch)" if job.stretch else "")


def to_markdown(jobs, errors) -> str:
    lines = [f"# New matching jobs, {date.today():%d %b %Y}", "", f"{len(jobs)} new matches.", ""]
    if jobs:
        lines += ["| Company | Role | Location | Experience | Fit | Link |", "|---|---|---|---|---|---|"]
        cell = lambda s: str(s).replace("|", "/")
        for j in jobs:
            fit = f"{j.score} ({j.reason})" if j.score is not None else ""
            lines.append(
                f"| {cell(j.company)} | {cell(j.title)} | {cell(j.location)} | {_exp(j)} | {cell(fit)} | [Open]({j.url}) |"
            )
    if errors:
        lines += ["", "## Sources that failed this run", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines) + "\n"


def write_reports(markdown: str, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "latest.md").write_text(markdown, encoding="utf-8")
    (reports_dir / f"{date.today().isoformat()}.md").write_text(markdown, encoding="utf-8")


def send_email(jobs, errors, test=False) -> bool:
    user = (os.environ.get("GMAIL_USER") or "").strip()
    # Google shows app passwords as "abcd efgh ijkl mnop"; accept them pasted with spaces.
    password = "".join((os.environ.get("GMAIL_APP_PASSWORD") or "").split())
    if not (user and password and (jobs or test)):
        return False
    rows = "".join(
        f"<tr><td>{html.escape(j.company)}</td><td><a href='{html.escape(j.url)}'>{html.escape(j.title)}</a></td>"
        f"<td>{html.escape(j.location)}</td><td>{_exp(j)}</td>"
        f"<td>{'' if j.score is None else j.score}</td><td>{html.escape(j.reason)}</td></tr>"
        for j in jobs
    )
    intro = "Test email: the job watcher can send mail. " if test else ""
    body = (
        f"<p>{intro}{len(jobs)} new matching jobs today.</p>"
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;font-family:Arial;font-size:13px'>"
        "<tr><th>Company</th><th>Role</th><th>Location</th><th>Experience</th><th>Fit</th><th>Why</th></tr>"
        f"{rows}</table>"
        + (f"<p style='color:#888'>Failed sources: {html.escape(', '.join(errors))}</p>" if errors else "")
    )
    msg = MIMEText(body, "html")
    msg["Subject"] = f"Job watcher{' test' if test else ''}: {len(jobs)} new matches ({date.today():%d %b})"
    msg["From"] = user
    msg["To"] = (os.environ.get("MAIL_TO") or "").strip() or user  # unset secrets arrive as ""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    return True
