"""Job search integrations for the Updraft job board."""
from html.parser import HTMLParser
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import ADZUNA_APP_ID, ADZUNA_APP_KEY
from .data import CAREER_DEGREES, CAREER_SKILLS, ROLES

COUNTRIES = {"au", "br", "ca", "de", "fr", "gb", "in", "nl", "pl", "sg", "us", "za"}
COUNTRY_NAMES = {
    "au": "Australia", "br": "Brazil", "ca": "Canada", "de": "Germany",
    "fr": "France", "gb": "United Kingdom", "in": "India", "nl": "Netherlands",
    "pl": "Poland", "sg": "Singapore", "us": "United States", "za": "South Africa",
}


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        if value.strip():
            self.parts.append(value.strip())


def _plain_text(value):
    parser = _TextOnly()
    parser.feed(str(value or ""))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _default_query(profile):
    career = profile.get("career") or {}
    spec_id = career.get("specializationId")
    for degree in CAREER_DEGREES:
        for specialization in degree.get("specializations", []):
            if specialization.get("id") == spec_id:
                return specialization.get("label", "")
    return next((role["label"] for role in ROLES if role["id"] == profile.get("roleId")), "Software Developer")


def _linkedin_url(query, location, country=None):
    location = str(location or "").strip()
    country_name = COUNTRY_NAMES.get(str(country or "").strip().lower(), "")
    includes_country = any(name.casefold() in location.casefold() for name in COUNTRY_NAMES.values())
    if country_name and not includes_country:
        location = f"{location}, {country_name}".strip(", ")
    params = {
        "keywords": query,
        "sortBy": "DD",
        "f_TPR": "r604800",
        "refresh": "true",
        "origin": "JOB_SEARCH_PAGE_JOB_FILTER",
    }
    if location:
        params["location"] = location
    return "https://www.linkedin.com/jobs/search/?" + urlencode(params)


def _normalize(ad):
    place = ad.get("location") or {}
    company = ad.get("company") or {}
    created = str(ad.get("created", ""))
    url = str(ad.get("redirect_url", ""))
    if not url.startswith("https://"):
        url = ""
    description = _plain_text(ad.get("description", ""))
    return {
        "id": str(ad.get("id", "")),
        "title": _plain_text(ad.get("title", "Job opportunity"))[:180],
        "company": _plain_text(company.get("display_name", "Employer"))[:120],
        "location": _plain_text(place.get("display_name", "Location not specified"))[:180],
        "description": description[:420] + ("…" if len(description) > 420 else ""),
        "createdAt": created,
        "url": url,
    }


def search_jobs(profile, query="", location="", country="in"):
    query = str(query or _default_query(profile)).strip()[:120]
    location = str(location or "").strip()[:100]
    country = str(country or "in").strip().lower()
    if country not in COUNTRIES:
        country = "in"
    linkedin = _linkedin_url(query, location, country)
    result = {
        "query": query,
        "location": location,
        "country": country,
        "linkedinUrl": linkedin,
        "provider": "Adzuna",
        "providerConfigured": bool(ADZUNA_APP_ID and ADZUNA_APP_KEY),
        "jobs": [],
    }
    if not result["providerConfigured"]:
        result["message"] = "No recent vacancies are available right now. Try another search or open LinkedIn results."
        return result

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": 20,
        "what": query,
        "sort_by": "date",
        "content-type": "application/json",
    }
    if location:
        params["where"] = location
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "UpdraftJobSearch/1.0"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result["jobs"] = [_normalize(ad) for ad in payload.get("results", []) if isinstance(ad, dict)]
        result["total"] = int(payload.get("count", len(result["jobs"])))
        result["message"] = "Latest matching vacancies from Adzuna. LinkedIn search is available separately."
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        result["message"] = "The live job provider could not be reached. Try again or use the LinkedIn search link."
    return result
