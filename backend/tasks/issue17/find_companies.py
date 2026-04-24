"""
Company Finder — find_companies.py
Discovers tech companies that use Greenhouse or Lever ATS by probing their
public JSON APIs (no auth, no CAPTCHA) and exports a verified companies.csv
ready for use with webscraper.py.

  Greenhouse API: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
  Lever API:      https://api.lever.co/v0/postings/{slug}

Both are fully public and return clean JSON with no bot detection.

Usage:
  python find_companies.py
  python find_companies.py --output my_companies.csv
  python find_companies.py --workers 5

Requirements:
  pip install requests
"""

import argparse
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ---------------------------------------------------------------------------
# Candidate company slugs to probe
# These are the URL slugs used by each ATS, e.g.:
#   boards-api.greenhouse.io/v1/boards/airbnb/jobs
#   api.lever.co/v0/postings/netflix
# ---------------------------------------------------------------------------

GREENHOUSE_CANDIDATES = [
    "airbnb", "stripe", "figma", "notion", "discord", "coinbase",
    "robinhood", "brex", "plaid", "chime", "marqeta", "affirm",
    "snowflake", "databricks", "confluent", "fivetran", "dbt",
    "amplitude", "mixpanel", "braze", "iterable", "segment",
    "launchdarkly", "harness", "circleci", "jfrog", "snyk",
    "samsara", "verkada", "abnormalsecurity", "lacework", "wiz",
    "crowdstrike", "sentinelone",
    "coreweave", "scaleai", "cohere",
    "rippling", "lattice", "personio",
    "monday", "asana", "airtable",
    "intercom", "freshworks",
    "pendo", "fullstory", "contentsquare",
    "algolia",
    "adyen", "checkout",
    "docusign", "ironclad",
    "loom", "miro", "invision",
    "vercel", "netlify",
    "cockroachlabs", "planetscale",
    "grafana", "honeycombio", "newrelic",
    "twilio", "vonage", "bandwidth",
    "faire", "mirakl", "commercetools",
    "toasttab", "lightspeedhq",
    "peloton", "whoop",
    "duolingo", "coursera", "udemy", "chegg",
    "ro", "alto",
    "flexport",
    "thumbtack",
    "nextdoor",
    "calm", "headspace",
    "hubspot", "zendesk", "okta",
    "cloudflare", "datadog", "mongodb", "elastic", "hashicorp",
    "pagerduty", "squarespace", "shopify",
    "nvidia", "qualcomm", "arm",
    "intel", "amd",
    "cisco", "juniper", "paloaltonetworks",
    "linkedin", "microsoft", "google", "apple", "amazon", "meta",
    "ibm", "oracle", "sap", "salesforce", "workday",
    "mckinsey", "bcg", "accenture",
    "visa", "mastercard", "amex",
    "jpmorgan", "goldmansachs",
    "boeing", "lockheedmartin", "northropgrumman",
    "ge", "siemens", "honeywell",
    "pfizer", "johnsonandjohnson", "novartis", "roche",
    "netflix", "spotify",
    "uber", "lyft", "doordash", "instacart",
    "airbnb", "booking", "expedia",
    "marriott", "hilton",
    "fedex", "ups",
    "toyota", "honda", "ford", "gm", "bmw",
    "rivian", "lucidmotors", "jobyaviation",
    "spacex", "blueorigin",
    "gitlab", "github", "atlassian",
    "unity", "epicgames", "riotgames", "niantic",
    "twitch", "discord",
    "canva", "webflow", "framer",
    "linear", "height", "shortcut",
    "retool", "airplane", "appsmith",
    "dbt", "prefect", "dagster",
    "weights-and-biases", "huggingface",
    "anthropic", "openai", "mistral",
    "scale", "labelbox", "appen",
    "benchling", "veeva", "medidata",
    "tempus", "flatiron", "guardanthealth",
    "devoted", "oscar", "clover", "cityblock",
    "robinhood", "wealthsimple", "betterment",
    "nerdwallet", "creditkarma", "experian",
    "squareup", "block", "cashapp",
    "shopify", "bigcommerce", "woocommerce",
    "faire", "orderful",
    "samsara", "motive", "keeptruckin",
    "opendoor", "offerpad", "roofstock",
    "blend", "better",
    "procore", "autodesk", "bentley",
    "trimble", "hexagon",
]

LEVER_CANDIDATES = [
    "netflix", "twitter", "x",
    "dropbox", "box",
    "zoom", "slack",
    "stripe", "square",
    "lyft", "doordash",
    "pinterest", "snap", "reddit",
    "roblox", "unity",
    "zendesk", "freshworks", "intercom",
    "shopify", "shopifyplus",
    "atlassian", "jira",
    "hashicorp", "terraform",
    "splunk", "sumologic", "elastic",
    "cloudflare", "fastly", "akamai",
    "twilio", "sendgrid",
    "mongodb", "redis", "neo4j", "influxdata",
    "databricks", "dremio", "firebolt",
    "airbyte", "meltano", "singer",
    "dbtlabs", "lightdash", "metabase",
    "segment", "rudderstack",
    "braze", "klaviyo", "mailchimp",
    "heap", "amplitude", "mixpanel",
    "sentry", "rollbar", "bugsnag",
    "datadog", "newrelic", "dynatrace",
    "pagerduty", "opsgenie", "victorops",
    "github", "gitlab", "bitbucket",
    "jenkins", "circleci", "travis",
    "docker", "kubernetes",
    "chef", "puppet", "ansible",
    "vault", "consul",
    "okta", "auth0", "onelogin",
    "crowdstrike", "sentinelone", "cylance",
    "qualys", "tenable", "rapid7",
    "zscaler", "netskope", "illumio",
    "servicenow", "bmc", "cherwell",
    "jira", "asana", "basecamp",
    "notion", "confluence", "slab",
    "figma", "sketch", "zeplin",
    "invision", "marvel", "proto",
    "loom", "loom", "vidyard",
    "gong", "chorus", "clari",
    "salesforce", "hubspot", "pipedrive",
    "outreach", "salesloft",
    "gainsight", "totango", "churnzero",
    "zuora", "chargebee", "recurly",
    "coupa", "procurify", "tipalti",
    "expensify", "brex", "ramp",
    "bill", "melio", "routable",
    "gusto", "rippling", "bamboohr",
    "workday", "adp", "ceridian",
    "lattice", "15five", "betterworks",
    "leapsome", "reflektive", "small-improvements",
    "greenhouse", "lever", "workable",
    "icims", "taleo", "successfactors",
    "beamery", "phenom", "eightfold",
    "hiretual", "seekout", "gem",
    "indeed", "glassdoor", "linkedin",
    "ziprecruiter", "monster", "careerbuilder",
]

# Deduplicate while preserving order
def _dedup(lst):
    seen, out = set(), []
    for x in lst:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

GREENHOUSE_CANDIDATES = _dedup(GREENHOUSE_CANDIDATES)
LEVER_CANDIDATES      = _dedup(LEVER_CANDIDATES)

CSV_FIELDS = ["ats", "slug", "company_name", "tech_jobs", "total_jobs"]

TECH_KEYWORDS = [
    "engineer", "developer", "data", "scientist", "architect",
    "devops", "sre", "platform", "machine learning", "ml", "ai",
    "software", "backend", "frontend", "fullstack", "cloud",
    "infrastructure", "security", "qa", "analyst", "technical",
    "database", "systems", "firmware", "embedded",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ---------------------------------------------------------------------------
# Probe functions
# ---------------------------------------------------------------------------

def is_tech(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in TECH_KEYWORDS)


def probe_greenhouse(slug: str) -> dict | None:
    # Correct base URL is api.greenhouse.io (not boards-api.greenhouse.io)
    url = f"https://api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = requests.get(url, headers=HEADERS, params={"content": "true"}, timeout=10)
        if r.status_code != 200:
            return None
        data        = r.json()
        jobs        = data.get("jobs", [])
        total       = len(jobs)
        tech        = sum(1 for j in jobs if is_tech(j.get("title", "")))
        company     = jobs[0].get("company_name", slug) if jobs else slug
        return {"ats": "greenhouse", "slug": slug, "company_name": company,
                "tech_jobs": tech, "total_jobs": total}
    except Exception:
        return None


def probe_lever(slug: str) -> dict | None:
    # Lever public postings endpoint
    url = f"https://api.lever.co/v0/postings/{slug}"
    try:
        r = requests.get(url, headers=HEADERS, params={"mode": "json"}, timeout=10)
        if r.status_code != 200:
            return None
        data    = r.json()
        jobs    = data if isinstance(data, list) else data.get("postings", [])
        total   = len(jobs)
        tech    = sum(1 for j in jobs if is_tech(j.get("text", "")))
        company = jobs[0].get("company", slug) if jobs else slug
        return {"ats": "lever", "slug": slug, "company_name": company,
                "tech_jobs": tech, "total_jobs": total}
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ATS Company Finder")
    parser.add_argument("--output",  default="companies.csv")
    parser.add_argument("--workers", type=int, default=5,
                        help="Parallel requests (default: 5)")
    parser.add_argument("--min-tech-jobs", type=int, default=1,
                        help="Minimum tech jobs to include a company (default: 1)")
    args = parser.parse_args()

    print(f"Probing {len(GREENHOUSE_CANDIDATES)} Greenhouse + {len(LEVER_CANDIDATES)} Lever candidates...")
    print(f"Workers: {args.workers}  |  Output: {args.output}\n")

    valid = []

    # Greenhouse
    print("--- Greenhouse ---")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(probe_greenhouse, s): s for s in GREENHOUSE_CANDIDATES}
        done = 0
        for future in as_completed(futures):
            done += 1
            slug   = futures[future]
            result = future.result()
            if result and result["tech_jobs"] >= args.min_tech_jobs:
                valid.append(result)
                print(f"  [{done}/{len(GREENHOUSE_CANDIDATES)}] ✓ {slug:35s} → \"{result['company_name']}\" ({result['tech_jobs']} tech / {result['total_jobs']} total)")
            else:
                print(f"  [{done}/{len(GREENHOUSE_CANDIDATES)}] ✗ {slug}")
            time.sleep(0.05)

    # Lever
    print("\n--- Lever ---")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(probe_lever, s): s for s in LEVER_CANDIDATES}
        done = 0
        for future in as_completed(futures):
            done += 1
            slug   = futures[future]
            result = future.result()
            if result and result["tech_jobs"] >= args.min_tech_jobs:
                valid.append(result)
                print(f"  [{done}/{len(LEVER_CANDIDATES)}] ✓ {slug:35s} → \"{result['company_name']}\" ({result['tech_jobs']} tech / {result['total_jobs']} total)")
            else:
                print(f"  [{done}/{len(LEVER_CANDIDATES)}] ✗ {slug}")
            time.sleep(0.05)

    valid.sort(key=lambda r: r["tech_jobs"], reverse=True)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(valid)

    print(f"\n--- Summary ---")
    print(f"  Greenhouse probed : {len(GREENHOUSE_CANDIDATES)}")
    print(f"  Lever probed      : {len(LEVER_CANDIDATES)}")
    print(f"  Valid companies   : {len(valid)}")
    print(f"  Output            : {args.output}")
    print(f"\nTo scrape jobs, run:")
    print(f"  python webscraper.py --companies-file {args.output}")


if __name__ == "__main__":
    main()