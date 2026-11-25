(() => {
  const RESULTS_URL = '/api/career/recommendations';

  const resultsContainer = document.getElementById('career-results');
  const statusMessage = document.getElementById('career-status');
  const emptyState = document.getElementById('career-empty');
  const errorState = document.getElementById('career-error');
  const retryButton = document.getElementById('retry-careers');
  const downloadButton = document.getElementById('download-careers');
  let currentMatches = [];

  if (!resultsContainer) return;

  function addText(parent, tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value == null ? '' : String(value);
    parent.append(element);
    return element;
  }

  function addList(parent, heading, items) {
    if (!Array.isArray(items) || items.length === 0) return;

    const group = document.createElement('section');
    group.className = 'career-detail-group';
    addText(group, 'h3', '', heading);
    const list = document.createElement('ul');

    items.forEach(item => {
      const li = document.createElement('li');
      li.textContent = String(item);
      list.append(li);
    });

    group.append(list);
    parent.append(group);
  }

  function addLinks(parent, links) {
    if (!Array.isArray(links) || links.length === 0) return;

    const validLinks = links.filter(link => {
      try {
        const url = new URL(link.url);
        return ['http:', 'https:'].includes(url.protocol);
      } catch {
        return false;
      }
    });

    if (!validLinks.length) return;

    addText(parent, 'h3', '', 'Explore opportunities');
    const list = document.createElement('ul');

    validLinks.forEach(link => {
      const li = document.createElement('li');
      const anchor = document.createElement('a');
      anchor.href = new URL(link.url).href;
      anchor.target = '_blank';
      anchor.rel = 'noopener noreferrer';
      anchor.textContent = String(link.label || 'Learn more');
      li.append(anchor);
      list.append(li);
    });

    parent.append(list);
  }

  function renderMatches(data) {
    const matches = Array.isArray(data) ? data : data.matches || [];
    currentMatches = matches;
    if (downloadButton) downloadButton.disabled = matches.length === 0;
    resultsContainer.replaceChildren();
    errorState.hidden = true;
    emptyState.hidden = matches.length > 0;

    if (!matches.length) {
      statusMessage.textContent = '';
      return;
    }

    matches.forEach(match => {
      const card = document.createElement('section');
      card.className = 'panel career-result-card';

      const percent = Number.isFinite(Number(match.matchPercent))
        ? Math.max(0, Math.min(100, Number(match.matchPercent)))
        : null;
      const header = document.createElement('div');
      header.className = 'career-card-header';
      const heading = document.createElement('div');
      addText(heading, 'div', 'eyebrow muted', 'CAREER MATCH');
      addText(heading, 'h2', '', match.title || 'Career option');
      header.append(heading);
      if (percent !== null) {
        const score = document.createElement('div');
        score.className = 'career-score';
        score.setAttribute('aria-label', `${percent}% skill match`);
        addText(score, 'strong', '', `${percent}%`);
        addText(score, 'span', '', 'MATCH');
        header.append(score);
      }
      card.append(header);

      if (percent !== null) {
        const track = document.createElement('div');
        track.className = 'career-match-track';
        track.setAttribute('role', 'progressbar');
        track.setAttribute('aria-label', `Skill match for ${match.title || 'career option'}`);
        track.setAttribute('aria-valuemin', '0');
        track.setAttribute('aria-valuemax', '100');
        track.setAttribute('aria-valuenow', String(percent));
        const fill = document.createElement('span');
        fill.style.width = `${percent}%`;
        track.append(fill);
        card.append(track);
      }
      addText(card, 'p', 'career-description', match.description || '');

      addList(card, 'Skills needed for this role', match.requiredSkills);
      addList(card, 'Your skill gaps', match.skillGaps);
      addList(card, 'Suggested study order', match.studyTasks);
      addLinks(card, match.links);

      resultsContainer.append(card);
    });

    statusMessage.textContent =
      `${matches.length} career match${matches.length === 1 ? '' : 'es'} found. Match scores use your ratings for each role’s required skills.`;
  }

  function makePdfText(value) {
    return String(value ?? '')
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[–—]/g, '-')
      .replace(/[’‘]/g, "'")
      .replace(/[“”]/g, '"')
      .replace(/[^\x20-\x7E]/g, '')
      .replace(/\\/g, '\\\\')
      .replace(/\(/g, '\\(')
      .replace(/\)/g, '\\)');
  }

  function downloadMatchesPdf() {
    if (!currentMatches.length) return;
    const lines = [
      'UPDRAFT - PERSONALIZED CAREER MATCHES',
      `Generated ${new Date().toLocaleDateString()}`,
      "Match scores reflect your ratings for each role's required skills.",
      ''
    ];
    currentMatches.forEach((match, index) => {
      lines.push(`${index + 1}. ${match.title || 'Career option'} - ${match.matchPercent ?? 0}% match`);
      lines.push(match.description || '');
      lines.push(`Skills needed: ${(match.requiredSkills || []).join(', ') || 'Not listed'}`);
      lines.push(`Skill gaps: ${(match.skillGaps || []).join(', ') || 'No priority gaps'}`);
      lines.push('Suggested study order:');
      (match.studyTasks || []).forEach((task, taskIndex) => lines.push(`  ${taskIndex + 1}. ${task}`));
      lines.push('');
    });

    const wrapped = [];
    lines.forEach(line => {
      const text = String(line);
      if (!text) { wrapped.push(''); return; }
      for (let offset = 0; offset < text.length; offset += 86) wrapped.push(text.slice(offset, offset + 86));
    });
    const pages = [];
    for (let offset = 0; offset < wrapped.length; offset += 46) pages.push(wrapped.slice(offset, offset + 46));
    const objects = [null];
    const addObject = value => { objects.push(value); return objects.length - 1; };
    const fontId = addObject('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>');
    const pageIds = [];
    pages.forEach(pageLines => {
      const commands = ['BT', '/F1 10 Tf', '48 794 Td', '14 TL'];
      pageLines.forEach((line, lineIndex) => {
        if (lineIndex) commands.push('T*');
        commands.push(`(${makePdfText(line)}) Tj`);
      });
      commands.push('ET');
      const stream = commands.join('\n');
      const contentId = addObject(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
      pageIds.push(addObject(`<< /Type /Page /Parent PAGES_ID /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${fontId} 0 R >> >> /Contents ${contentId} 0 R >>`));
    });
    const pagesId = addObject(`<< /Type /Pages /Kids [${pageIds.map(id => `${id} 0 R`).join(' ')}] /Count ${pageIds.length} >>`);
    pageIds.forEach(id => { objects[id] = objects[id].replace('PAGES_ID', String(pagesId)); });
    const catalogId = addObject(`<< /Type /Catalog /Pages ${pagesId} 0 R >>`);
    let pdf = '%PDF-1.4\n';
    const offsets = [0];
    for (let id = 1; id < objects.length; id += 1) {
      offsets[id] = pdf.length;
      pdf += `${id} 0 obj\n${objects[id]}\nendobj\n`;
    }
    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${objects.length}\n0000000000 65535 f \n`;
    for (let id = 1; id < objects.length; id += 1) pdf += `${String(offsets[id]).padStart(10, '0')} 00000 n \n`;
    pdf += `trailer\n<< /Size ${objects.length} /Root ${catalogId} 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
    const blob = new Blob([pdf], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'updraft-career-matches.pdf';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function loadMatches() {
    errorState.hidden = true;
    statusMessage.textContent = 'Loading your matches…';

    try {
      const response = await fetch(RESULTS_URL, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`Career results request failed (${response.status})`);
      }

      renderMatches(await response.json());
    } catch (error) {
      console.error('Could not load career matches:', error);
      statusMessage.textContent = '';
      errorState.hidden = false;
    }
  }

  retryButton?.addEventListener('click', loadMatches);
  downloadButton?.addEventListener('click', downloadMatchesPdf);
  loadMatches();
})();
