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
let currentPlanItems = [];

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
  currentPlanItems = items.map(item => ({ ...item }));
  document.getElementById('plan-title').textContent = [plan?.title, plan?.durationLabel].filter(Boolean).join(' · ') || 'Your personalized prep plan';
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
  document.getElementById('plan-recommendation').textContent = recommendation ? `✦ ${recommendation}` : '';
}

async function loadPlan() {
  planErrorElement.hidden = true;
  planStatusElement.textContent = 'Loading your plan…';
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

function openPlanEditor() {
  const editor = document.getElementById('plan-editor');
  const container = document.getElementById('plan-edit-items');
  container.replaceChildren();

  currentPlanItems.forEach((item, index) => {
    const row = document.createElement('div');
    row.className = 'plan-edit-row';
    const fields = document.createElement('div');
    fields.className = 'plan-edit-fields';

    const addField = (labelText, field, value) => {
      const label = document.createElement('label');
      label.textContent = labelText;
      const input = document.createElement('input');
      input.type = field === 'week' ? 'number' : 'text';
      input.value = value == null ? '' : String(value);
      input.dataset.field = field;
      input.dataset.id = String(item.id);
      if (field === 'title') { input.maxLength = 120; input.required = true; }
      if (field === 'description') input.maxLength = 240;
      if (field === 'week') { input.min = '1'; input.max = '52'; input.step = '1'; input.required = true; }
      fields.append(label, input);
    };

    addField(`Activity ${index + 1}`, 'title', item.title);
    addField('Description', 'description', item.description);
    addField('Week', 'week', item.week || 1);
    row.append(fields);
    container.append(row);
  });

  document.getElementById('plan-edit-status').textContent = currentPlanItems.length ? '' : 'There are no activities to edit yet.';
  editor.hidden = false;
  editor.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function savePlanSchedule() {
  const status = document.getElementById('plan-edit-status');
  const edited = new Map(currentPlanItems.map(item => [String(item.id), { id: item.id }]));
  document.querySelectorAll('#plan-edit-items [data-field]').forEach(input => {
    const item = edited.get(input.dataset.id);
    if (item) item[input.dataset.field] = input.dataset.field === 'week' ? Number(input.value) : input.value.trim();
  });
  const items = [...edited.values()];
  if (!items.length || items.some(item => !item.title || item.title.length > 120 || (item.description || '').length > 240 || !Number.isInteger(item.week) || item.week < 1 || item.week > 52)) {
    status.textContent = 'Enter an activity name and a whole-number week from 1 to 52 for each item.';
    return;
  }

  const button = document.getElementById('save-plan-edit');
  button.disabled = true;
  status.textContent = 'Saving your schedule…';
  try {
    const response = await fetch(`${PLAN_ENDPOINT}/schedule`, {
      method: 'PATCH', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ items })
    });
    if (!response.ok) throw new Error(`Schedule save failed (${response.status})`);
    document.getElementById('plan-editor').hidden = true;
    await loadPlan();
    planStatusElement.textContent = 'Your custom schedule was saved.';
  } catch (error) {
    console.error('Unable to save custom schedule:', error);
    status.textContent = 'Could not save your schedule. Please try again.';
  } finally {
    button.disabled = false;
  }
}

document.getElementById('retry-plan').addEventListener('click', loadPlan);
document.getElementById('edit-schedule').addEventListener('click', openPlanEditor);
document.getElementById('cancel-plan-edit').addEventListener('click', () => { document.getElementById('plan-editor').hidden = true; });
document.getElementById('save-plan-edit').addEventListener('click', savePlanSchedule);

document.addEventListener('DOMContentLoaded', loadPlan);
