const form = document.getElementById("job-search");
const list = document.getElementById("jobs-list");
const status = document.getElementById("jobs-status");
const linkedInLink = document.getElementById("linkedin-search");

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : "";
  } catch { return ""; }
}

function renderJobs(data) {
  list.replaceChildren();
  if (!document.getElementById("job-query").value && data.query) document.getElementById("job-query").value = data.query;
  linkedInLink.href = safeExternalUrl(data.linkedinUrl) || "https://www.linkedin.com/jobs/";
  if (!Array.isArray(data.jobs) || !data.jobs.length) {
    status.textContent = data.message || "No matching vacancies were returned. Try a broader search.";
    return;
  }
  status.textContent = `${data.jobs.length} recent vacancies${Number.isFinite(data.total) ? ` · ${data.total.toLocaleString()} total matches` : ""}.`;
  data.jobs.forEach(job => {
    const article = document.createElement("article");
    article.className = "job-card";
    const eyebrow = document.createElement("div");
    eyebrow.className = "eyebrow muted";
    eyebrow.textContent = "ADZUNA LISTING";
    const heading = document.createElement("h2");
    heading.textContent = job.title || "Job opportunity";
    const meta = document.createElement("p");
    meta.className = "job-meta";
    meta.textContent = [job.company, job.location, job.createdAt ? new Date(job.createdAt).toLocaleDateString() : ""].filter(Boolean).join(" · ");
    const description = document.createElement("p");
    description.className = "job-description";
    description.textContent = job.description || "Open the listing to view role details.";
    article.append(eyebrow, heading, meta, description);
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
  status.textContent += " · Listings by Adzuna.";
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
  linkedInLink.href = `https://www.linkedin.com/jobs/search/?${new URLSearchParams({keywords:query.get("what"),location:query.get("where"),sortBy:"DD",f_TPR:"r604800"})}`;
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
document.addEventListener("DOMContentLoaded", async () => {
  const today = document.getElementById("today");
  if (today) today.textContent = new Intl.DateTimeFormat(undefined,{weekday:"short",month:"short",day:"numeric"}).format(new Date());
  searchJobs();
});
