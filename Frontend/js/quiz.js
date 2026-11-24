// Practice data is selected by the backend for the authenticated user.
// GET /api/practice/questions -> { questions:[{id,prompt,options:[{id,text}]}] }
// POST /api/practice/answers -> { correct:boolean, explanation?:string }
// GET /api/practice/warmups -> { prompts:[{id,text}] }
// POST /api/practice/focus-sessions -> { durationSeconds, promptId, completed:true }
// GET /api/practice/reviews -> { items:[{id,title,lastPracticed,dueLabel}] }
// POST /api/practice/reviews/{id}/start -> { nextUrl?:string }

const PRACTICE_API = '/api/practice';
const quizState = {
  questions: [],
  index: 0,
  selectedOptionId: null,
  answered: false,
  loaded: false,
  requestedCount: 5,
  previousQuestionIds: []
};
const warmupState = {
  prompts: [],
  index: 0,
  loaded: false,
  served: 0,
  lastPromptId: null
};

let selectedDuration = 300;
let sessionStartedAt = null;
let remainingSeconds = selectedDuration;
let timerInterval = null;
let timerDeadline = null;
let timerRunning = false;

const get = id => document.getElementById(id);

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

function safeInternalUrl(value) {
  if (typeof value !== 'string') return null;

  try {
    const target = new URL(value, window.location.href);
    return target.origin === window.location.origin ? target.href : null;
  } catch {
    return null;
  }
}

function optionId(option) {
  return String(
    option && typeof option === 'object'
      ? option.id ?? option.value ?? ''
      : option ?? ''
  );
}

function optionText(option) {
  return String(
    option && typeof option === 'object'
      ? option.text ?? option.label ?? option.value ?? ''
      : option ?? ''
  );
}

function renderQuestion() {
  const question = quizState.questions[quizState.index];
  const optionsContainer = get('quiz-options');
  const feedback = get('quiz-feedback');

  get('quiz-retry').hidden = true;
  get('quiz-next').hidden = true;
  get('quiz-submit').hidden = false;
  get('quiz-submit').disabled = true;
  get('quiz-submit').textContent = 'Check answer';
  get('quiz-status').textContent = '';

  feedback.hidden = true;
  feedback.replaceChildren();
  optionsContainer.replaceChildren();

  quizState.selectedOptionId = null;
  quizState.answered = false;

  if (!question) {
    get('quiz-count').textContent = quizState.questions.length ? 'SET COMPLETE' : 'NO MATCHING QUESTIONS';
    get('quiz-progress').style.width = '100%';
    get('quiz-question').textContent = quizState.questions.length
      ? 'You have finished this question set.'
      : 'No questions match your current assessment yet.';
    get('quiz-status').textContent = quizState.questions.length
      ? 'Choose a set size and start another fresh question set.'
      : 'Complete the career or skill assessment to get related questions.';
    get('quiz-submit').hidden = true;
    get('quiz-next').textContent = 'Start another set →';
    get('quiz-next').hidden = quizState.questions.length === 0;
    return;
  }

  const prompt = String(question.prompt ?? question.question ?? '');
  const options = Array.isArray(question.options) ? question.options : [];

  get('quiz-count').textContent =
    `QUESTION ${quizState.index + 1} OF ${quizState.questions.length}`;
  get('quiz-progress').style.width =
    `${quizState.index / Math.max(quizState.questions.length, 1) * 100}%`;
  get('quiz-question').textContent = prompt || 'Question text is unavailable.';

  options.forEach((option, index) => {
    const id = optionId(option) || String(index);
    const label = optionText(option);
    if (!label) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'choice';
    button.textContent = `${String.fromCharCode(65 + index)}　${label}`;
    button.dataset.optionId = id;
    button.setAttribute('aria-pressed', 'false');

    button.addEventListener('click', () => {
      if (quizState.answered) return;

      optionsContainer.querySelectorAll('.choice').forEach(item => {
        item.classList.remove('selected');
        item.setAttribute('aria-pressed', 'false');
      });

      button.classList.add('selected');
      button.setAttribute('aria-pressed', 'true');
      quizState.selectedOptionId = id;
      get('quiz-submit').disabled = false;
    });

    optionsContainer.append(button);
  });

  if (!optionsContainer.children.length) {
    get('quiz-status').textContent =
      'No answer options were provided for this question.';
  }
}

async function loadQuestions({ newSet = false } = {}) {
  if (newSet && quizState.questions.length) {
    quizState.previousQuestionIds = [...new Set([...quizState.previousQuestionIds, ...quizState.questions.map(question => String(question.id))])];
  }
  const sizeInput = get('quiz-set-size');
  const requested = Math.max(1, Math.min(10, Number.parseInt(sizeInput.value, 10) || 5));
  sizeInput.value = String(requested);
  quizState.requestedCount = requested;
  get('quiz-count').textContent = 'LOADING YOUR QUESTIONS…';
  get('quiz-status').textContent = '';
  get('quiz-retry').hidden = true;

  try {
    const params = new URLSearchParams({ limit: String(requested) });
    if (quizState.previousQuestionIds.length) params.set('exclude', quizState.previousQuestionIds.join(','));
    const response = await fetch(`${PRACTICE_API}/questions?${params}`, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Question request failed (${response.status})`);
    }

    const data = await response.json();

    quizState.questions = Array.isArray(data)
      ? data
      : Array.isArray(data.questions)
        ? data.questions
        : [];

    quizState.index = 0;
    quizState.loaded = true;
    renderQuestion();
    if (data.restartedRound) {
      quizState.previousQuestionIds = [];
      get('quiz-status').textContent = 'You have practiced all matching questions. This is a fresh round.';
    } else if (quizState.questions.length < requested) {
      get('quiz-status').textContent = `Only ${quizState.questions.length} new matching questions remain in this round.`;
    }
  } catch (error) {
    console.error('Unable to load practice questions:', error);
    get('quiz-count').textContent = 'QUESTIONS UNAVAILABLE';
    get('quiz-question').textContent = '';
    get('quiz-options').replaceChildren();
    get('quiz-submit').hidden = true;
    get('quiz-retry').hidden = false;
    get('quiz-status').textContent =
      'Connect the practice questions endpoint and retry.';
  }
}

async function submitAnswer() {
  const question = quizState.questions[quizState.index];

  if (!question || !quizState.selectedOptionId || quizState.answered) {
    return;
  }

  const submit = get('quiz-submit');
  submit.disabled = true;
  get('quiz-status').textContent = 'Submitting your answer…';

  try {
    const response = await fetch(`${PRACTICE_API}/answers`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify({
        questionId: question.id,
        optionId: quizState.selectedOptionId
      })
    });

    if (!response.ok) {
      throw new Error(`Answer request failed (${response.status})`);
    }

    const result = await response.json().catch(() => ({}));
    quizState.answered = true;

    const feedback = get('quiz-feedback');
    feedback.replaceChildren();

    const title = document.createElement('b');
    title.textContent = result.correct === true
      ? 'Correct. '
      : result.correct === false
        ? 'Not quite. '
        : 'Answer recorded. ';

    feedback.append(
      title,
      document.createTextNode(String(result.explanation || ''))
    );

    feedback.hidden = false;
    get('quiz-status').textContent = '';
    submit.hidden = true;

    if (quizState.index < quizState.questions.length - 1) {
      get('quiz-next').textContent = 'Next question →';
    } else {
      get('quiz-next').textContent = 'Finish';
    }

    get('quiz-next').hidden = false;
  } catch (error) {
    console.error('Unable to submit practice answer:', error);
    get('quiz-status').textContent =
      'Your answer could not be saved. Please try again.';
    submit.disabled = false;
  }
}

function nextQuestion() {
  if (quizState.index >= quizState.questions.length - 1) {
    loadQuestions({ newSet: true });
    return;
  }
  quizState.index += 1;
  renderQuestion();
}

async function loadWarmups() {
  get('warmup-status').textContent = 'Loading prompts…';
  get('warmup-retry').hidden = true;

  try {
    const response = await fetch(`${PRACTICE_API}/warmups`, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Warm-up request failed (${response.status})`);
    }

    const data = await response.json();

    warmupState.prompts = Array.isArray(data)
      ? data
      : Array.isArray(data.prompts)
        ? data.prompts
        : [];

    warmupState.index = 0;
    warmupState.loaded = true;
    renderWarmupPrompt();
  } catch (error) {
    console.error('Unable to load warm-up prompts:', error);
    get('warmup-prompt').textContent =
      'Warm-up prompts are unavailable right now.';
    get('warmup-status').textContent =
      'Connect the warm-up prompts endpoint to load personalized prompts.';
    get('warmup-retry').hidden = false;
  }
}

function renderWarmupPrompt() {
  const prompt = warmupState.prompts[warmupState.index];
  if (prompt) { warmupState.served += 1; warmupState.lastPromptId = prompt.id; }

  get('warmup-prompt').textContent = prompt
    ? String(prompt.text ?? prompt.prompt ?? '')
    : 'No warm-up prompts are available yet.';

  get('warmup-status').textContent = prompt
    ? `Prompt ${warmupState.served} · keep going for another prompt`
    : 'Prompts will appear here when your backend assigns them.';

  get('next-prompt').disabled = warmupState.prompts.length === 0;
}

function showTimer() {
  const exactRemaining = timerRunning && timerDeadline !== null
    ? Math.max(0, (timerDeadline - Date.now()) / 1000)
    : remainingSeconds;
  const hours = Math.floor(exactRemaining / 3600);
  const minutes = Math.floor((exactRemaining % 3600) / 60);
  const seconds = exactRemaining % 60;
  const minuteAngle = (minutes + seconds / 60) * 6;
  const hourAngle = ((hours % 12) + minutes / 60) * 30;
  const elapsed = timerRunning && sessionStartedAt !== null ? (Date.now() - sessionStartedAt) / 1000 : 0;
  const secondAngle = (elapsed % 60) * 6;
  get('hour-hand').style.transform = `translateX(-50%) rotate(${hourAngle}deg)`;
  get('minute-hand').style.transform = `translateX(-50%) rotate(${minuteAngle}deg)`;
  if (!timerRunning) get('second-hand').style.transform = `translateX(-50%) rotate(${secondAngle}deg)`;
  const display = formatTime(remainingSeconds);
  get('timer-readout').textContent = display;
  get('timer-accessible').textContent = `Timer ${display}`;
  get('timer').setAttribute('aria-label', `Timer ${display} remaining`);
}

function stopTimerInterval() {
  if (timerInterval !== null) {
    window.clearInterval(timerInterval);
  }

  timerInterval = null;
  timerDeadline = null;
}

function setTimerDuration(seconds) {
  if (timerRunning) return;

  selectedDuration = Math.max(60, Math.min(7200, Math.floor(seconds)));
  remainingSeconds = selectedDuration;
  const customMinutes = get('custom-minutes');
  if (customMinutes) customMinutes.value = String(Math.ceil(selectedDuration / 60));

  document.querySelectorAll('.duration-choice').forEach(button => {
    button.setAttribute(
      'aria-pressed',
      Number(button.dataset.seconds) === seconds ? 'true' : 'false'
    );
  });

  get('timer-status').textContent = '';
  showTimer();
}

async function recordFocusSession(durationSeconds, completed = true) {
  get('timer-status').textContent = completed ? 'Time is up. Saving your focus session…' : 'Saving the stopped focus session…';

  const prompt = warmupState.prompts[warmupState.index];

  try {
    const response = await fetch(`${PRACTICE_API}/focus-sessions`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify({
        durationSeconds,
        promptId: prompt?.id ?? null,
        completed
      })
    });

    if (!response.ok) {
      throw new Error(`Focus session request failed (${response.status})`);
    }

    get('timer-status').textContent = completed ? 'Focus session complete and saved.' : 'Stopped session saved to your activity.';
  } catch (error) {
    console.error('Unable to save focus session:', error);
    get('timer-status').textContent =
      'The focus session could not be saved to your account.';
  }
}

function finishTimer() {
  stopTimerInterval();
  timerRunning = false;
  get('timer').classList.remove('running');
  remainingSeconds = 0;
  get('timer-start').disabled = false;
  get('timer-stop').disabled = true;
  get('custom-minutes').disabled = false;
  get('apply-custom-duration').disabled = false;

  document.querySelectorAll('.duration-choice').forEach(button => {
    button.disabled = false;
  });

  showTimer();
  recordFocusSession(selectedDuration, true);
}

function startTimer() {
  if (timerRunning) return;
  if (remainingSeconds <= 0) remainingSeconds = selectedDuration;
  timerRunning = true;
  get('timer').classList.add('running');
  sessionStartedAt = Date.now();
  timerDeadline = Date.now() + remainingSeconds * 1000;
  get('timer-start').disabled = true;
  get('timer-stop').disabled = false;
  get('timer-status').textContent = 'Focus timer is running.';
  document.querySelectorAll('.duration-choice').forEach(button => { button.disabled = true; });
  get('custom-minutes').disabled = true;
  get('apply-custom-duration').disabled = true;
  timerInterval = window.setInterval(() => {
    remainingSeconds = Math.max(0, Math.ceil((timerDeadline - Date.now()) / 1000));
    showTimer();
    if (remainingSeconds === 0) finishTimer();
    else showTimer();
  }, 50);
}

function stopTimer() {
  if (!timerRunning) return;
  remainingSeconds = Math.max(0, Math.ceil((timerDeadline - Date.now()) / 1000));
  const elapsed = Math.max(0, Math.floor((Date.now() - sessionStartedAt) / 1000));
  timerRunning = false;
  get('timer').classList.remove('running');
  stopTimerInterval();
  get('timer-start').disabled = false;
  get('timer-stop').disabled = true;
  document.querySelectorAll('.duration-choice').forEach(button => { button.disabled = false; });
  get('custom-minutes').disabled = false;
  get('apply-custom-duration').disabled = false;
  remainingSeconds = selectedDuration;
  showTimer();
  if (elapsed > 0) recordFocusSession(elapsed, false);
  else get('timer-status').textContent = 'Timer stopped before a session began.';
}

function resetTimer() {
  stopTimerInterval();
  timerRunning = false;
  get('timer').classList.remove('running');
  sessionStartedAt = null;
  remainingSeconds = selectedDuration;
  get('timer-start').disabled = false;
  get('timer-stop').disabled = true;
  get('custom-minutes').disabled = false;
  get('apply-custom-duration').disabled = false;
  get('timer-status').textContent = '';

  document.querySelectorAll('.duration-choice').forEach(button => {
    button.disabled = false;
  });

  showTimer();
}

async function loadReviews() {
  get('review-retry').hidden = true;
  get('review-status').textContent = 'Loading your review queue…';

  const list = get('review-list');
  list.replaceChildren();

  try {
    const response = await fetch(`${PRACTICE_API}/reviews`, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Review request failed (${response.status})`);
    }

    const data = await response.json();
    const items = Array.isArray(data)
      ? data
      : Array.isArray(data.items)
        ? data.items
        : [];

    if (!items.length) {
      get('review-status').textContent =
        'No review items are due right now.';
      return;
    }

    get('review-status').textContent = '';

    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'plan-row';

      const icon = document.createElement('span');
      icon.className = 'topic-icon';
      icon.textContent = '↺';

      const detail = document.createElement('div');
      const title = document.createElement('b');
      title.textContent = String(item.title || 'Review item');

      const subtitle = document.createElement('small');
      subtitle.textContent =
        [item.lastPracticed, item.dueLabel].filter(Boolean).join(' · ');

      detail.append(title, subtitle);

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'choice review-button';
      button.textContent = 'Review';

      button.addEventListener('click', async () => {
        button.disabled = true;
        get('review-status').textContent = 'Opening review…';

        try {
          const reviewResponse = await fetch(
            `${PRACTICE_API}/reviews/${encodeURIComponent(item.id)}/start`,
            {
              method: 'POST',
              credentials: 'same-origin',
              headers: { Accept: 'application/json' }
            }
          );

          if (!reviewResponse.ok) {
            throw new Error(`Review start failed (${reviewResponse.status})`);
          }

          const result = await reviewResponse.json().catch(() => ({}));
          const destination = safeInternalUrl(result.nextUrl);

          if (destination) {
            window.location.href = destination;
          } else {
            button.textContent = 'Started';
            get('review-status').textContent = 'Review session started.';
          }
        } catch (error) {
          console.error('Unable to start review:', error);
          button.disabled = false;
          get('review-status').textContent =
            'Could not start this review. Please try again.';
        }
      });

      row.append(icon, detail, button);
      list.append(row);
    });
  } catch (error) {
    console.error('Unable to load review queue:', error);
    get('review-status').textContent =
      'Your review queue could not be loaded.';
    get('review-retry').hidden = false;
  }
}

get('quiz-submit').addEventListener('click', submitAnswer);
get('quiz-next').addEventListener('click', nextQuestion);
get('quiz-retry').addEventListener('click', loadQuestions);
get('review-retry').addEventListener('click', loadReviews);
get('warmup-retry').addEventListener('click', loadWarmups);
get('timer-start').addEventListener('click', startTimer);
get('timer-stop').addEventListener('click', stopTimer);
get('quiz-start-set').addEventListener('click', () => { quizState.previousQuestionIds = []; loadQuestions(); });
get('timer-reset').addEventListener('click', resetTimer);

get('next-prompt').addEventListener('click', () => {
  if (warmupState.prompts.length > 1) {
    if (warmupState.index + 1 >= warmupState.prompts.length) {
      const lastId = warmupState.lastPromptId;
      for (let i = warmupState.prompts.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [warmupState.prompts[i], warmupState.prompts[j]] = [warmupState.prompts[j], warmupState.prompts[i]];
      }
      if (warmupState.prompts.length > 1 && warmupState.prompts[0].id === lastId) {
        [warmupState.prompts[0], warmupState.prompts[1]] = [warmupState.prompts[1], warmupState.prompts[0]];
      }
      warmupState.index = 0;
    } else {
      warmupState.index += 1;
    }
    renderWarmupPrompt();
  }
});

get('apply-custom-duration').addEventListener('click', () => {
  const minutes = Number.parseInt(get('custom-minutes').value, 10);
  if (!Number.isInteger(minutes) || minutes < 1 || minutes > 120) {
    get('timer-status').textContent = 'Choose a timer from 1 to 120 minutes.';
    return;
  }
  setTimerDuration(minutes * 60);
});

document.querySelectorAll('.duration-choice').forEach(button => {
  button.addEventListener('click', () => {
    setTimerDuration(Number(button.dataset.seconds));
  });
});

document.querySelectorAll('.tab').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(tab => {
      tab.setAttribute(
        'aria-selected',
        tab === button ? 'true' : 'false'
      );
    });

    if (button.dataset.tab === 'warmup' && !warmupState.loaded) {
      loadWarmups();
    }

    if (button.dataset.tab === 'review' && !window.reviewQueueLoaded) {
      window.reviewQueueLoaded = true;
      loadReviews();
    }
  });
});

document.addEventListener('DOMContentLoaded', () => {
  const today = get('today');

  if (today) {
    today.textContent = new Intl.DateTimeFormat(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    }).format(new Date());
  }

  showTimer();
  get('timer-stop').disabled = true;
  loadWarmups();

  const requestedTab = new URLSearchParams(window.location.search).get('tab');
  if (requestedTab) {
    const requestedButton = document.querySelector(`.tab[data-tab="${CSS.escape(requestedTab)}"]`);
    requestedButton?.click();
  }
});