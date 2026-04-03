"""
Tech Job Scraper — webscraper.py
Scrapes tech job listings from companies using Greenhouse or Lever ATS.
Both have fully public JSON APIs with no CAPTCHAs or bot detection.

  Greenhouse: boards-api.greenhouse.io/v1/boards/{slug}/jobs
  Lever:      api.lever.co/v0/postings/{slug}

Input:  companies.csv produced by find_companies.py
Output: tech_jobs.csv  (all fields lowercase, spaces → underscores)

Usage:
  python webscraper.py --companies-file companies.csv
  python webscraper.py --companies-file companies.csv --keywords engineer data
  python webscraper.py --companies-file companies.csv --output results.csv

Requirements:
  pip install requests beautifulsoup4
"""

import argparse
import csv
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_KEYWORDS = [
    "engineer", "engineering", "developer", "development",
    "data", "analyst", "analytics", "scientist", "science",
    "architect", "devops", "sre", "platform",
    "machine learning", "ml", "ai", "software", "firmware", "embedded",
    "backend", "frontend", "fullstack", "full-stack", "full stack",
    "cloud", "infrastructure", "network", "security", "cybersecurity",
    "qa", "quality assurance", "test", "product manager", "program manager",
    "technical", "tech lead", "database", "dba", "it ", "systems",
]

CSV_FIELDS = [
    "ats", "company_slug", "company_name", "job_id", "title",
    "location", "department", "job_type", "posted_date",
    "description_text", "url", "scraped_at",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(value: str) -> str:
    """Lowercase and replace whitespace with underscores."""
    return re.sub(r"\s+", "_", str(value).strip().lower())


def normalize_row(row: dict) -> dict:
    skip = {"description_text", "url", "scraped_at"}
    return {k: (normalize(v) if isinstance(v, str) and k not in skip else v)
            for k, v in row.items()}


def is_tech(title: str, keywords: list[str]) -> bool:
    t = title.lower()
    return any(kw in t for kw in keywords)


def strip_html(html: str) -> str:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def get(url: str, params: dict = None) -> dict | list | None:
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# Greenhouse scraper
# ---------------------------------------------------------------------------

def scrape_greenhouse(slug: str, keywords: list[str]) -> list[dict]:
    """
    Fetch all jobs from Greenhouse public API, filter by keyword,
    then fetch each job's detail for the full description.
    """
    data = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
               params={"content": "true"})
    if not data:
        return []

    jobs    = data.get("jobs", [])
    company = jobs[0].get("company_name", slug) if jobs else slug
    results = []

    tech_jobs = [j for j in jobs if is_tech(j.get("title", ""), keywords)]
    print(f"  {len(jobs)} total → {len(tech_jobs)} tech jobs")

    for j in tech_jobs:
        title   = j.get("title", "")
        job_id  = str(j.get("id", ""))
        url     = j.get("absolute_url", f"https://boards.greenhouse.io/{slug}/jobs/{job_id}")

        # Location
        loc_parts = j.get("location", {})
        location  = loc_parts.get("name", "") if isinstance(loc_parts, dict) else str(loc_parts)

        # Department
        depts      = j.get("departments", [])
        department = depts[0].get("name", "") if depts else ""

        # Description (included when ?content=true)
        desc_html = j.get("content", "")
        desc_text = strip_html(desc_html)

        # Posted date
        updated = j.get("updated_at", "")[:10] if j.get("updated_at") else ""

        results.append(normalize_row({
            "ats":              "greenhouse",
            "company_slug":     slug,
            "company_name":     company,
            "job_id":           job_id,
            "title":            title,
            "location":         location,
            "department":       department,
            "job_type":         "",
            "posted_date":      updated,
            "description_text": desc_text,
            "url":              url,
            "scraped_at":       datetime.utcnow().isoformat(),
        }))

    return results

# ---------------------------------------------------------------------------
# Lever scraper
# ---------------------------------------------------------------------------

def scrape_lever(slug: str, keywords: list[str]) -> list[dict]:
    """
    Fetch all postings from Lever public API, filter by keyword.
    Description is included in the listing response.
    """
    data = get(f"https://api.lever.co/v0/postings/{slug}",
               params={"mode": "json"})
    if not isinstance(data, list):
        return []

    company  = data[0].get("company", slug) if data else slug
    results  = []

    tech_jobs = [j for j in data if is_tech(j.get("text", ""), keywords)]
    print(f"  {len(data)} total → {len(tech_jobs)} tech jobs")

    for j in tech_jobs:
        title  = j.get("text", "")
        job_id = j.get("id", "")
        url    = j.get("hostedUrl", f"https://jobs.lever.co/{slug}/{job_id}")

        # Location
        location = j.get("workplaceType", "") or j.get("country", "")
        categories = j.get("categories", {})
        if not location:
            location = categories.get("location", "")

        department = categories.get("team", "") or categories.get("department", "")
        job_type   = categories.get("commitment", "")

        # Description — Lever returns sections as a list of {header, body}
        desc_parts = j.get("descriptionPlain", "") or ""
        if not desc_parts:
            lists = j.get("lists", [])
            desc_parts = " ".join(
                item.get("text", "") + " " + " ".join(item.get("content", []))
                for item in lists
            )
        desc_text = re.sub(r"\s+", " ", desc_parts).strip()

        posted_ts = j.get("createdAt", 0)
        posted_date = (datetime.utcfromtimestamp(posted_ts / 1000).strftime("%Y-%m-%d")
                       if posted_ts else "")

        results.append(normalize_row({
            "ats":              "lever",
            "company_slug":     slug,
            "company_name":     company,
            "job_id":           job_id,
            "title":            title,
            "location":         location,
            "department":       department,
            "job_type":         job_type,
            "posted_date":      posted_date,
            "description_text": desc_text,
            "url":              url,
            "scraped_at":       datetime.utcnow().isoformat(),
        }))

    return results

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], output: str):
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} job(s) to '{output}'")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tech Job Scraper (Greenhouse + Lever)")
    parser.add_argument("--companies-file", required=True, metavar="FILE",
                        help="companies.csv from find_companies.py")
    parser.add_argument("--keywords", nargs="+", metavar="KW",
                        help="Tech-job title keywords (overrides defaults)")
    parser.add_argument("--output", default="tech_jobs.csv")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Delay between companies in seconds (default: 0.5)")
    args = parser.parse_args()

    keywords = [kw.lower() for kw in args.keywords] if args.keywords else DEFAULT_KEYWORDS

    # Load companies CSV
    with open(args.companies_file, newline="", encoding="utf-8") as f:
        reader  = csv.DictReader(f)
        companies = [row for row in reader if row.get("slug", "").strip()]

    print(f"Companies : {len(companies)}")
    print(f"Keywords  : {', '.join(keywords[:8])}{'...' if len(keywords) > 8 else ''}")
    print(f"Output    : {args.output}")
    print("=" * 60)

    all_results = []

    for i, row in enumerate(companies, 1):
        ats  = row.get("ats", "greenhouse").strip().lower()
        slug = row.get("slug", "").strip()
        if not slug:
            continue

        print(f"\n[{i}/{len(companies)}] {slug} ({ats})")

        if ats == "greenhouse":
            results = scrape_greenhouse(slug, keywords)
        elif ats == "lever":
            results = scrape_lever(slug, keywords)
        else:
            print(f"  Unknown ATS '{ats}', skipping")
            continue

        if not results:
            print("  No tech jobs found")
        else:
            print(f"  Scraped {len(results)} tech job(s)")
            all_results.extend(results)

        time.sleep(args.delay)

    print("\n" + "=" * 60)
    if all_results:
        write_csv(all_results, args.output)
        print(f"Total: {len(all_results)} tech jobs across {len(companies)} companies.")
    else:
        print("No data scraped.")


if __name__ == "__main__":
    main()