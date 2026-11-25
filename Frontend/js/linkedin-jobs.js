const form = document.getElementById("job-search");
const list = document.getElementById("jobs-list");
const status = document.getElementById("jobs-status");
const linkedInLink = document.getElementById("linkedin-search");
const queryInput = document.getElementById("job-query");
const locationInput = document.getElementById("job-location");
const countryInput = document.getElementById("job-country");

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : "";
  } catch { return ""; }
}

function linkedinSearchUrl(query, location, country) {
  const url = new URL("https://www.linkedin.com/jobs/search/");
  const exactQuery = String(query || "").trim();
  const typedLocation = String(location || "").trim().replace(/\s*,\s*/g, ", ");
  url.searchParams.set("keywords", exactQuery);
  url.searchParams.set("sortBy", "DD");
  url.searchParams.set("refresh", "true");
  url.searchParams.set("origin", "JOB_SEARCH_PAGE_JOB_FILTER");
  const countryName = countryInput.selectedOptions[0]?.textContent.trim() || country;
  let exactLocation = typedLocation;
  const includesCountry = [...countryInput.options].some(option =>
    exactLocation.toLocaleLowerCase().includes(option.textContent.trim().toLocaleLowerCase())
  );
  if (countryName && !includesCountry) {
    exactLocation = [exactLocation, countryName].filter(Boolean).join(", ");
  }
  if (exactLocation) url.searchParams.set("location", exactLocation);
  return url.href;
}

function renderJobs(data) {
  list.replaceChildren();
  if (!queryInput.value && data.query) queryInput.value = data.query;
  linkedInLink.href = linkedinSearchUrl(queryInput.value, locationInput.value, countryInput.value);
  if (!Array.isArray(data.jobs) || !data.jobs.length) {
    status.textContent = data.message || "No matching vacancies were returned. Try a broader search.";
    return;
  }
  status.textContent = `${data.jobs.length} recent vacancies${Number.isFinite(data.total) ? ` · ${data.total.toLocaleString()} total matches` : ""}.`;
  data.jobs.forEach(job => {
    const article = document.createElement("article");
    article.className = "job-card";
    const heading = document.createElement("h2");
    heading.textContent = job.title || "Job opportunity";
    const meta = document.createElement("p");
    meta.className = "job-meta";
    meta.textContent = [job.company, job.location, job.createdAt ? new Date(job.createdAt).toLocaleDateString() : ""].filter(Boolean).join(" · ");
    const description = document.createElement("p");
    description.className = "job-description";
    description.textContent = job.description || "Open the listing to view role details.";
    article.append(heading, meta, description);
    const href = safeExternalUrl(job.url);
    if (href) {
      const link = document.createElement("a");
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "View vacancy and apply ↗";
      article.append(link);
    }
    list.append(article);
  });
}

async function searchJobs(event) {
  event?.preventDefault();
  status.textContent = "Searching latest vacancies…";
  list.replaceChildren();
  const query = new URLSearchParams({
    what: document.getElementById("job-query").value.trim(),
    where: document.getElementById("job-location").value.trim(),
    country: document.getElementById("job-country").value
  });
  linkedInLink.href = linkedinSearchUrl(query.get("what"), query.get("where"), query.get("country"));
  try {
    const response = await fetch(`/api/jobs/search?${query}`, { credentials:"same-origin", headers:{Accept:"application/json"} });
    if (!response.ok) throw new Error(`Job search failed (${response.status})`);
    renderJobs(await response.json());
  } catch (error) {
    console.error("Unable to load job listings:", error);
    status.textContent = "Job search is temporarily unavailable. Try LinkedIn search or try again later.";
  }
}

form.addEventListener("submit", searchJobs);
queryInput.addEventListener("input", () => {
  linkedInLink.href = linkedinSearchUrl(queryInput.value, locationInput.value, countryInput.value);
});
locationInput.addEventListener("input", () => {
  linkedInLink.href = linkedinSearchUrl(queryInput.value, locationInput.value, countryInput.value);
});
countryInput.addEventListener("change", () => {
  linkedInLink.href = linkedinSearchUrl(queryInput.value, locationInput.value, countryInput.value);
});
linkedInLink.addEventListener("click", () => {
  // Build from the current controls at click time so an older search response
  // cannot send the user to stale keywords or a stale location.
  linkedInLink.href = linkedinSearchUrl(queryInput.value, locationInput.value, countryInput.value);
});
document.addEventListener("DOMContentLoaded", async () => {
  const today = document.getElementById("today");
  if (today) today.textContent = new Intl.DateTimeFormat(undefined,{weekday:"short",month:"short",day:"numeric"}).format(new Date());
  searchJobs();
});
