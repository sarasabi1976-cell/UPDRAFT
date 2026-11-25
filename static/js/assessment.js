(() => {
  const OPTIONS_URL = '/api/career/options';
  const SUBMIT_URL = '/api/career/assessment';

  const form = document.getElementById('assessment-form');
  const degreeSelect = document.getElementById('degree');
  const specializationSelect = document.getElementById('specialization');
  const skillRatings = document.getElementById('skill-ratings');
  const statusMessage = document.getElementById('assessment-status');
  const submitButton = document.getElementById('submit-assessment');

  if (!form || !degreeSelect || !specializationSelect || !skillRatings) return;

  let degrees = [];

  function makeOption(label, value = '') {
    return new Option(label, value);
  }

  function fillSelect(select, items, placeholder) {
    select.replaceChildren(makeOption(placeholder));

    items.forEach(item => {
      const id = String(item.id ?? item.value ?? '');
      const label = String(item.label ?? item.name ?? '');

      if (id && label) {
        select.add(makeOption(label, id));
      }
    });
  }

  function renderSkills(skills) {
    skillRatings.replaceChildren();

    if (!skills.length) {
      const message = document.createElement('p');
      message.className = 'panel-copy';
      message.textContent = 'No skill choices are available yet.';
      skillRatings.append(message);
      return;
    }

    skills.forEach(skill => {
      const id = String(skill.id ?? '');
      const label = String(skill.label ?? skill.name ?? '');

      if (!id || !label) return;

      const row = document.createElement('div');
      row.className = 'skill-rating-row';

      const name = document.createElement('label');
      name.htmlFor = `skill-${id}`;
      name.textContent = label;

      const select = document.createElement('select');
      select.id = `skill-${id}`;
      select.name = `skill-${id}`;
      select.dataset.skillId = id;
      select.required = true;
      select.setAttribute('aria-label', `Rate your ${label} skill`);
      select.add(makeOption('Choose rating'));

      for (let score = 1; score <= 5; score += 1) {
        select.add(makeOption(String(score), String(score)));
      }

      row.append(name, select);
      skillRatings.append(row);
    });
  }

  degreeSelect.addEventListener('change', () => {
    const degree = degrees.find(item => String(item.id) === degreeSelect.value);
    const specializations = degree?.specializations || [];

    fillSelect(
      specializationSelect,
      specializations,
      degree ? 'Choose a specialization' : 'Choose a degree first'
    );
    specializationSelect.disabled = !degree;
  });

  async function loadOptions() {
    statusMessage.textContent = 'Loading education and skill choicesΓÇª';
    submitButton.disabled = true;

    try {
      const response = await fetch(OPTIONS_URL, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`Options request failed (${response.status})`);
      }

      const data = await response.json();
      degrees = Array.isArray(data.degrees) ? data.degrees : [];

      fillSelect(degreeSelect, degrees, 'Choose a degree');
      renderSkills(Array.isArray(data.skills) ? data.skills : []);

      statusMessage.textContent = 'Complete each field, then submit your assessment.';
      submitButton.disabled = false;
    } catch (error) {
      console.error('Could not load career assessment options:', error);
      statusMessage.textContent =
        'Could not load choices. Check the backend connection and refresh the page.';
      degreeSelect.replaceChildren(makeOption('Options unavailable'));
      skillRatings.textContent = 'Skill choices are currently unavailable.';
    }
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();

    if (!form.reportValidity()) return;

    const skills = {};
    skillRatings.querySelectorAll('select[data-skill-id]').forEach(select => {
      skills[select.dataset.skillId] = Number(select.value);
    });

    const payload = {
      degreeId: degreeSelect.value,
      specializationId: specializationSelect.value,
      studyYear: document.getElementById('study-year').value,
      skills
    };

    submitButton.disabled = true;
    statusMessage.textContent = 'Saving your answers and finding matchesΓÇª';

    try {
      const response = await fetch(SUBMIT_URL, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Assessment request failed (${response.status})`);
      }

       window.location.href = '/results';    
    } catch (error) {
      console.error('Could not submit career assessment:', error);
      statusMessage.textContent =
        'Your answers could not be saved. Please try again.';
      submitButton.disabled = false;
    }
  });

  loadOptions();
})();
