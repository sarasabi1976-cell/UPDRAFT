const UPDRAFT_THEME_KEY = 'updraft-theme';
let activeTheme = 'light';
try {
  activeTheme = localStorage.getItem(UPDRAFT_THEME_KEY) === 'dark' ? 'dark' : 'light';
} catch { /* Keep the light theme if browser storage is unavailable. */ }
document.documentElement.dataset.theme = activeTheme;

function updateThemeControl(button) {
  const dark = document.documentElement.dataset.theme === 'dark';
  button.textContent = dark ? '☀ Light theme' : '☾ Dark theme';
  button.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
  button.setAttribute('aria-pressed', String(dark));
  button.title = dark ? 'Switch to light theme' : 'Switch to dark theme';
}

document.addEventListener('DOMContentLoaded', () => {
  const actions = document.querySelector('.top-actions');
  if (!actions) return;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'theme-toggle';
  button.addEventListener('click', () => {
    activeTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = activeTheme;
    try { localStorage.setItem(UPDRAFT_THEME_KEY, activeTheme); } catch { /* Theme works until this tab closes. */ }
    updateThemeControl(button);
  });
  const avatar = actions.querySelector('.avatar');
  actions.insertBefore(button, avatar || null);
  updateThemeControl(button);
});

document.addEventListener('DOMContentLoaded', () => {
  const today = document.getElementById('today');

  if (today) {
    today.textContent = new Intl.DateTimeFormat('en', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    }).format(new Date());
  }

  document.querySelectorAll('.tab').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab === button);
      });

      document.querySelectorAll('[data-tab-content]').forEach(section => {
        section.hidden = section.dataset.tabContent !== button.dataset.tab;
      });
    });
  });

  document.querySelectorAll('[data-local-form]').forEach(form => {
    form.addEventListener('submit', event => {
      event.preventDefault();
      const message = form.querySelector('.form-message');
      if (message) {
        message.textContent = 'Preferences captured in this interface. Server connection can be added later.';
      }
    });
  });
});

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const response = await fetch('/api/auth/me', { credentials: 'same-origin', headers: { Accept: 'application/json' } });
    if (!response.ok) return;
    const data = await response.json();
    const user = data.user || {};
    const name = user.name || 'Guest';
    const initials = name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase() || 'U';
    document.querySelectorAll('.avatar.mini[href]').forEach(avatar => {
      avatar.textContent = initials;
      avatar.title = data.authenticated ? `${name} (@${user.username}) — Account / switch user` : 'Guest — Account / switch user';
      avatar.setAttribute('aria-label', avatar.title);
    });
  } catch (error) { console.warn('Could not refresh account indicator:', error); }
});
