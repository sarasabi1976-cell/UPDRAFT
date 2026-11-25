
(() => {
  const RESULTS_URL = '/api/career/recommendations';

  const resultsContainer = document.getElementById('career-results');
  const statusMessage = document.getElementById('career-status');
  const emptyState = document.getElementById('career-empty');
  const errorState = document.getElementById('career-error');
  const retryButton = document.getElementById('retry-careers');

  if (!resultsContainer) return;

  function addText(parent, tag, className, value) {
    const element = document.createElement(tag);

    if (className) {
      element.className = className;
    }

    element.textContent = value == null ? '' : String(value);
    parent.append(element);

    return element;
  }

  function addList(parent, heading, items) {
    if (!Array.isArray(items) || items.length === 0) return;

    addText(parent, 'h3', '', heading);

    const list = document.createElement('ul');

    items.forEach(item => {
      const li = document.createElement('li');
      li.textContent = String(item);
      list.append(li);
    });

    parent.append(list);
  }

  function renderMatches(data) {
    const matches = data.recommendations || [];

    resultsContainer.replaceChildren();
    errorState.hidden = true;
    emptyState.hidden = matches.length > 0;

    if (!matches.length) {
      statusMessage.textContent = 'No matching careers found.';
      return;
    }

    matches.forEach(match => {
      const card = document.createElement('section');
      card.className = 'panel career-result-card';

      addText(card, 'div', 'eyebrow muted', 'YOUR CAREER MATCH');

      addText(
        card,
        'h2',
        '',
        match.role || 'Career option'
      );

      addText(
        card,
        'p',
        'panel-copy',
        match.description || 'A career based on your education and skills.'
      );

      const gaps = (match.skill_gaps || []).map(item =>
        `${item.skill.replaceAll('_', ' ')}: Current ${item.current_level}/5, Required ${item.required_level}/5 (${item.label} gap)`
      );

      addList(card, 'Your skill gaps', gaps);

      const tasks = (match.study_schedule || []).map(task =>
        `${task.skill.replaceAll('_', ' ')} — ${task.burst_time} study hours`
      );

      addList(card, 'Suggested study schedule', tasks);

      if (match.opportunity_link) {
        const link = document.createElement('a');
        link.href = match.opportunity_link;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Explore this career opportunity';

        card.append(link);
      }

      resultsContainer.append(card);
    });

    statusMessage.textContent =
      `${matches.length} career match${matches.length === 1 ? '' : 'es'} found.`;
  }

  async function loadMatches() {
    errorState.hidden = true;
    statusMessage.textContent = 'Loading your matches...';

    try {
      const response = await fetch(RESULTS_URL, {
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Career results request failed (${response.status})`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Could not load career recommendations.');
      }

      renderMatches(data);

    } catch (error) {
      console.error('Could not load career matches:', error);

      statusMessage.textContent = '';
      errorState.hidden = false;
    }
  }

  retryButton?.addEventListener('click', loadMatches);

  loadMatches();
})();
