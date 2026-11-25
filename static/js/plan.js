// GET /api/plan
// { title, durationLabel, items:[{id,title,description,week,completed}], recommendation }
// PATCH /api/plan/items/{id} with { completed:boolean }
// POST /api/plan/schedule to begin schedule editing (optional { editUrl } response)

const PLAN_ENDPOINT = '/api/plan';
const planItemsElement = document.getElementById('plan-items');
const planCountElement = document.getElementById('plan-count');
const planProgressElement = document.getElementById('plan-progress');
const planStatusElement = document.getElementById('plan-status');
const planErrorElement = document.getElementById('plan-error');

function text(value, fallback = '') {
  return value == null || value === '' ? fallback : String(value);
}

function updateProgress(items) {
  const complete = items.filter(item => item.completed).length;
  const total = items.length;
  planCountElement.textContent = `${complete} of ${total} items complete`;
  planProgressElement.style.width = total ? `${complete / total * 100}%` : '0%';
}

function renderPlan(plan) {
  const items = Array.isArray(plan?.items) ? plan.items : [];
  document.getElementById('plan-title').textContent = [plan?.title, plan?.durationLabel].filter(Boolean).join(' ┬╖ ') || 'Your personalized prep plan';
  planItemsElement.replaceChildren();
  planErrorElement.hidden = true;

  if (!items.length) {
    planStatusElement.textContent = 'Your plan does not have any items yet.';
    planStatusElement.className = 'plan-empty';
  } else {
    planStatusElement.textContent = '';
    planStatusElement.className = 'plan-status';
    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'plan-row';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'plan-item-check';
      checkbox.checked = item.completed === true;
      checkbox.disabled = item.id == null || item.id === '';
      checkbox.setAttribute('aria-label', `${checkbox.checked ? 'Mark incomplete' : 'Mark complete'}: ${text(item.title, 'Plan item')}`);

      const content = document.createElement('div');
      content.className = 'plan-item-copy';
      const title = document.createElement('b');
      title.textContent = text(item.title, 'Plan item');
      const description = document.createElement('small');
      description.textContent = text(item.description, '');
      content.append(title, description);

      const week = document.createElement('span');
      week.className = 'week-pill';
      week.textContent = item.week == null || item.week === '' ? '' : `WEEK ${text(item.week)}`;
      row.append(checkbox, content, week);
      planItemsElement.append(row);

      checkbox.addEventListener('change', async () => {
        const previousValue = !checkbox.checked;
        checkbox.disabled = true;
        try {
          const response = await fetch(`${PLAN_ENDPOINT}/items/${encodeURIComponent(item.id)}`, {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ completed: checkbox.checked })
          });
          if (!response.ok) throw new Error(`Plan update failed (${response.status})`);
          item.completed = checkbox.checked;
          updateProgress(items);
          planStatusElement.textContent = 'Plan progress saved.';
        } catch (error) {
          console.error('Unable to update plan item:', error);
          checkbox.checked = previousValue;
          planStatusElement.textContent = 'Could not save that change. Please try again.';
        } finally {
          checkbox.disabled = false;
          checkbox.setAttribute('aria-label', `${checkbox.checked ? 'Mark incomplete' : 'Mark complete'}: ${text(item.title, 'Plan item')}`);
        }
      });
    });
  }

  updateProgress(items);
  const recommendation = text(plan?.recommendation);
  document.getElementById('plan-recommendation').textContent = recommendation ? `Γ£ª ${recommendation}` : '';
}

async function loadPlan() {
  planErrorElement.hidden = true;
  planStatusElement.textContent = 'Loading your planΓÇª';
  planStatusElement.className = 'plan-status';
  try {
    const response = await fetch(PLAN_ENDPOINT, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    });
    if (!response.ok) throw new Error(`Plan request failed (${response.status})`);
    const plan = await response.json();
    renderPlan(plan);
  } catch (error) {
    console.error('Unable to load prep plan:', error);
    document.getElementById('plan-title').textContent = 'Your personalized prep plan';
    planItemsElement.replaceChildren();
    planCountElement.textContent = '0 of 0 items complete';
    planProgressElement.style.width = '0%';
    planStatusElement.textContent = 'Plan data could not be loaded.';
    planErrorElement.hidden = false;
  }
}

document.getElementById('retry-plan').addEventListener('click', loadPlan);
document.getElementById('edit-schedule').addEventListener('click', async () => {
  planStatusElement.textContent = 'Opening schedule settingsΓÇª';
  try {
    const response = await fetch(`${PLAN_ENDPOINT}/schedule`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    });
    if (!response.ok) throw new Error(`Schedule request failed (${response.status})`);
    const result = await response.json().catch(() => ({}));
    if (typeof result.editUrl === 'string') {
      const destination = new URL(result.editUrl, window.location.href);
      if (destination.origin === window.location.origin) window.location.href = destination.href;
    } else {
      planStatusElement.textContent = 'Schedule editing is ready to connect to your backend.';
    }
  } catch (error) {
    console.error('Unable to open schedule settings:', error);
    planStatusElement.textContent = 'Your backend needs to provide the schedule editing endpoint.';
  }
});

document.addEventListener('DOMContentLoaded', loadPlan);
