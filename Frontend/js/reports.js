// GET /api/reports returns an aggregate for the authenticated user:
// { metrics:{readinessScore,readinessChange,readinessPeriod,practiceSessions,sessionsChange,sessionsPeriod,
//   focusedHours,focusedDays,streakBest,streakCaption}, selectedSkills:[{id,name,score}],
//   recentWins:[{icon,title,description}], insight }

const REPORTS_ENDPOINT = '/api/reports';
const reportStatus = document.getElementById('report-status');
const reportError = document.getElementById('report-error');

function numberOrZero(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function setText(id, value) {
  document.getElementById(id).textContent = value == null ? '' : String(value);
}

function displayChange(value) {
  const amount = numberOrZero(value);
  return `${amount > 0 ? '↑ ' : amount < 0 ? '↓ ' : ''}${amount}`;
}

function renderReport(report) {
  const metrics = report?.metrics || {};
  setText('readiness-score', numberOrZero(metrics.readinessScore));
  setText('readiness-change', displayChange(metrics.readinessChange));
  setText('readiness-period', metrics.readinessPeriod || 'points in 30 days');
  setText('practice-sessions', numberOrZero(metrics.practiceSessions));
  setText('sessions-change', displayChange(metrics.sessionsChange));
  setText('sessions-period', metrics.sessionsPeriod || 'this month');
  setText('focused-hours', numberOrZero(metrics.focusedHours).toFixed(1));
  setText('focused-period', `${numberOrZero(metrics.focusedDays)} days this week`);
  setText('streak-best', numberOrZero(metrics.streakBest));
  setText('streak-caption', metrics.streakCaption || 'Personal best');

  const skillMap = document.getElementById('skill-map');
  skillMap.replaceChildren();
  const skills = Array.isArray(report?.selectedSkills) ? report.selectedSkills : [];
  if (!skills.length) {
    const empty = document.createElement('p');
    empty.className = 'report-empty';
    empty.textContent = 'Your selected skills will appear here when assessment data is available.';
    skillMap.append(empty);
  } else {
    skills.forEach(skill => {
      const row = document.createElement('div');
      row.className = 'plan-row';
      const name = document.createElement('div');
      name.className = 'skill-name';
      const label = document.createElement('b');
      label.textContent = String(skill.name || 'Selected skill');
      name.append(label);
      const track = document.createElement('div');
      track.className = 'progress-line skill-progress';
      const fill = document.createElement('i');
      const hasScore = skill.score !== null && skill.score !== undefined && skill.score !== '';
      const score = Math.min(100, Math.max(0, numberOrZero(skill.score)));
      fill.style.width = `${hasScore ? score : 0}%`;
      track.append(fill);
      const scoreLabel = document.createElement('span');
      scoreLabel.className = 'week-pill skill-score';
      scoreLabel.textContent = hasScore ? `${score}%` : 'Not assessed';
      row.append(name, track, scoreLabel);
      skillMap.append(row);
    });
  }

  const insight = document.getElementById('report-insight');
  insight.textContent = report?.insight ? String(report.insight) : '';
  insight.hidden = !report?.insight;

  const winsContainer = document.getElementById('recent-wins');
  winsContainer.replaceChildren();
  const wins = Array.isArray(report?.recentWins) ? report.recentWins : [];
  if (!wins.length) {
    const empty = document.createElement('p');
    empty.className = 'report-empty';
    empty.textContent = 'Your progress signals will appear here as you practice.';
    winsContainer.append(empty);
  } else {
    wins.forEach(win => {
      const row = document.createElement('div');
      row.className = 'plan-row';
      const icon = document.createElement('span');
      icon.className = 'topic-icon';
      icon.textContent = String(win.icon || '✦');
      const content = document.createElement('div');
      const title = document.createElement('b');
      title.textContent = String(win.title || 'Progress update');
      const description = document.createElement('small');
      description.textContent = String(win.description || '');
      content.append(title, description);
      row.append(icon, content);
      winsContainer.append(row);
    });
  }
}

async function loadReport() {
  reportError.hidden = true;
  reportStatus.textContent = 'Loading your consolidated report…';
  try {
    const response = await fetch(REPORTS_ENDPOINT, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    });
    if (!response.ok) throw new Error(`Report request failed (${response.status})`);
    renderReport(await response.json());
    reportStatus.textContent = '';
  } catch (error) {
    console.error('Unable to load consolidated report:', error);
    renderReport({ metrics: {}, selectedSkills: [], recentWins: [] });
    reportStatus.textContent = 'Showing zero defaults because the report service is unavailable.';
    reportError.hidden = false;
  }
}

document.getElementById('retry-report').addEventListener('click', loadReport);
document.addEventListener('DOMContentLoaded', () => {
  const today = document.getElementById('today');
  if (today) today.textContent = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date());
  loadReport();
});

document.getElementById('export-pdf')?.addEventListener('click', () => {
  document.title = 'Updraft Progress Report';
  window.print();
});
