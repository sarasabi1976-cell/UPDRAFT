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
