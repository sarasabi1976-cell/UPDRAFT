(() => {
  const status = document.getElementById('account-status');
  const current = document.getElementById('current-account-title');
  const logoutButton = document.getElementById('logout-button');
  const activityList = document.getElementById('activity-list');

  async function request(path, method = 'GET', body = undefined) {
    const response = await fetch(path, {
      method,
      credentials: 'same-origin',
      headers: body === undefined ? { Accept: 'application/json' } : { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }

  function renderActivity(items) {
    activityList.replaceChildren();
    if (!items.length) {
      const empty = document.createElement('p');
      empty.className = 'account-note';
      empty.textContent = 'Activity will appear here as you use the app.';
      activityList.append(empty);
      return;
    }
    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'activity-row';
      const action = document.createElement('span');
      action.textContent = String(item.action || 'Activity');
      const time = document.createElement('time');
      const parsed = new Date(item.createdAt);
      time.textContent = Number.isNaN(parsed.getTime()) ? String(item.createdAt || '') : parsed.toLocaleString();
      row.append(action, time);
      activityList.append(row);
    });
  }

  async function loadAccounts() {
    const select = document.getElementById('account-picker');
    if (!select) return;
    const data = await request('/api/auth/accounts');
    const accounts = Array.isArray(data.accounts) ? data.accounts : [];
    const previous = select.value;
    select.replaceChildren(new Option(accounts.length ? 'Choose a saved account' : 'No accounts yet', ''));
    accounts.forEach(account => select.add(new Option(`${account.name} (@${account.username})`, account.username)));
    if (accounts.some(account => account.username === previous)) select.value = previous;
  }

  async function refresh() {
    try {
      const data = await request('/api/auth/me');
      const user = data.user || {};
      current.textContent = data.authenticated ? `${user.name} (@${user.username})` : `${user.name || 'Guest'} — guest progress is saved in this browser`;
      logoutButton.hidden = !data.authenticated;
      await loadAccounts();
      const activity = await request('/api/auth/activity');
      renderActivity(Array.isArray(activity.items) ? activity.items : []);
    } catch (error) {
      current.textContent = 'Account service unavailable';
      status.textContent = error.message;
      activityList.textContent = 'Could not load account activity.';
    }
  }

  document.getElementById('account-picker')?.addEventListener('change', event => {
    const username = event.currentTarget.value;
    if (username) document.querySelector('#login-form [name="username"]').value = username;
  });

  document.getElementById('login-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    status.textContent = 'Signing in…';
    try {
      await request('/api/auth/login', 'POST', values);
      form.reset();
      status.textContent = 'Signed in. Loading this user’s saved workspace…';
      window.location.assign('/');
    } catch (error) { status.textContent = error.message; }
  });

  document.getElementById('register-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    if (values.password !== values.confirmPassword) { status.textContent = 'The passwords do not match.'; return; }
    delete values.confirmPassword;
    status.textContent = 'Creating your account…';
    try {
      await request('/api/auth/register', 'POST', values);
      form.reset();
      status.textContent = 'Account created. Loading your saved workspace…';
      window.location.assign('/');
    } catch (error) { status.textContent = error.message; }
  });

  logoutButton.addEventListener('click', async () => {
    status.textContent = 'Signing out…';
    try {
      await request('/api/auth/logout', 'POST', {});
      status.textContent = 'Signed out. Loading the guest workspace…';
      window.location.assign('/');
    } catch (error) { status.textContent = error.message; }
  });

  refresh();
})();
