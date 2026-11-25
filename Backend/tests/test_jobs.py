import json
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

from Backend import jobs


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_normalize_removes_html_and_keeps_https_url():
    job = jobs._normalize({
        "id": 123,
        "title": "<b>Python Developer</b>",
        "company": {"display_name": "Example Co"},
        "location": {"display_name": "London"},
        "description": "<p>Build <strong>Python</strong> services.</p>",
        "created": "2026-11-25",
        "redirect_url": "https://example.com/jobs/123",
    })

    assert job["id"] == "123"
    assert job["title"] == "Python Developer"
    assert job["company"] == "Example Co"
    assert job["description"] == "Build Python services."
    assert job["url"] == "https://example.com/jobs/123"


def test_normalize_discards_non_https_job_url():
    job = jobs._normalize({"redirect_url": "http://example.com/job"})

    assert job["url"] == ""


def test_linkedin_url_includes_keywords_and_location():
    url = jobs._linkedin_url("Data Analyst", "London")
    params = parse_qs(urlsplit(url).query)

    assert url.startswith("https://www.linkedin.com/jobs/search/")
    assert params["keywords"] == ["Data Analyst"]
    assert params["location"] == ["London"]
    assert params["sortBy"] == ["DD"]


def test_search_jobs_without_credentials_returns_empty_jobs(monkeypatch):
    monkeypatch.setattr(jobs, "ADZUNA_APP_ID", "")
    monkeypatch.setattr(jobs, "ADZUNA_APP_KEY", "")

    result = jobs.search_jobs({}, country="invalid")

    assert result["query"] == "Software Developer"
    assert result["country"] == "in"
    assert result["providerConfigured"] is False
    assert result["jobs"] == []
    assert "linkedinUrl" in result


def test_search_jobs_normalizes_adzuna_results(monkeypatch):
    monkeypatch.setattr(jobs, "ADZUNA_APP_ID", "test-id")
    monkeypatch.setattr(jobs, "ADZUNA_APP_KEY", "test-key")

    payload = {
        "count": 1,
        "results": [{
            "id": 456,
            "title": "<b>Backend Engineer</b>",
            "company": {"display_name": "Example Ltd"},
            "location": {"display_name": "Remote"},
            "description": "<p>Build APIs.</p>",
            "created": "2026-11-25",
            "redirect_url": "https://example.com/jobs/456",
        }],
    }

    def fake_urlopen(request, timeout):
        assert timeout == 10
        query = parse_qs(urlsplit(request.full_url).query)
        assert query["app_id"] == ["test-id"]
        assert query["app_key"] == ["test-key"]
        return FakeResponse(payload)

    monkeypatch.setattr(jobs, "urlopen", fake_urlopen)

    result = jobs.search_jobs(
        {},
        query="Backend Engineer",
        location="Remote",
        country="gb",
    )

    assert result["providerConfigured"] is True
    assert result["total"] == 1
    assert result["jobs"][0]["title"] == "Backend Engineer"
    assert result["jobs"][0]["company"] == "Example Ltd"
    assert result["jobs"][0]["url"] == "https://example.com/jobs/456"


def test_search_jobs_handles_provider_connection_error(monkeypatch):
    monkeypatch.setattr(jobs, "ADZUNA_APP_ID", "test-id")
    monkeypatch.setattr(jobs, "ADZUNA_APP_KEY", "test-key")

    def failed_urlopen(request, timeout):
        raise URLError("connection failed")

    monkeypatch.setattr(jobs, "urlopen", failed_urlopen)

    result = jobs.search_jobs({}, query="Python Developer")

    assert result["providerConfigured"] is True
    assert result["jobs"] == []
    assert "could not be reached" in result["message"]