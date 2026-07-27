// Ministry Knowledge Intelligence Assistant — frontend application logic.
// Single-page app, hash-routed, talking to the real FastAPI backend at
// the same origin. Design ported from ministry_frontend's static mockup;
// this version is wired to live data everywhere.

const state = {
  token: localStorage.getItem('moict_token') || null,
  user: null,
  sessions: [],
  currentSessionId: null,
  kbCategory: 'All',
  adminTab: 'overview',
  assistantFile: null,
};

// ---------------------------------------------------------------- UTILITIES
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str === null || str === undefined ? '' : String(str);
  return div.innerHTML;
}

function firstName(fullName) {
  return (fullName || '').split(' ')[0] || 'there';
}

function roleLabel(roleName) {
  return roleName === 'admin' ? 'IT Officer' : 'Ministry Staff';
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
}

// Deterministic initials avatars — no photos needed, no consent to manage.
const AVATAR_PALETTE = ['#001f40', '#0a3a6b', '#b3730a', '#1e7f4f', '#7a3b8f', '#c81e3a'];

function initialsFromName(name) {
  return (name || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('');
}

function colorForName(name) {
  let hash = 0;
  const s = name || '?';
  for (let i = 0; i < s.length; i++) hash = s.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_PALETTE[Math.abs(hash) % AVATAR_PALETTE.length];
}

function renderAvatars() {
  document.querySelectorAll('[data-avatar-name]').forEach((el) => {
    const name = el.getAttribute('data-avatar-name') || '?';
    el.textContent = initialsFromName(name);
    el.style.background = colorForName(name);
  });
}

function toast(message, isError = false) {
  let el = document.getElementById('app-toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'app-toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.toggle('toast-error', isError);
  el.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.remove('show'), 3200);
}

// Minimal, dependency-free markdown -> HTML so LLM/RAG answers render as
// real paragraphs/lists/emphasis instead of a raw text blob. Escapes first,
// then only ever inserts tags around already-escaped text, so this stays
// safe against untrusted content (user questions, model output).
function renderMarkdown(raw) {
  const lines = escapeHtml(raw).split(/\r?\n/);
  let html = '';
  let listType = null;
  let para = [];

  const inline = (s) => s
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, '$1<em>$2</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');

  const flushPara = () => { if (para.length) { html += `<p>${para.join('<br>')}</p>`; para = []; } };
  const closeList = () => { if (listType) { html += `</${listType}>`; listType = null; } };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) { closeList(); flushPara(); continue; }

    const heading = line.match(/^(#{1,4})\s+(.*)/);
    const bullet = line.match(/^[-*]\s+(.*)/);
    const numbered = line.match(/^\d+[.)]\s+(.*)/);

    if (heading) {
      closeList(); flushPara();
      const level = Math.min(heading[1].length + 3, 6);
      html += `<h${level}>${inline(heading[2])}</h${level}>`;
    } else if (bullet) {
      flushPara();
      if (listType !== 'ul') { closeList(); html += '<ul>'; listType = 'ul'; }
      html += `<li>${inline(bullet[1])}</li>`;
    } else if (numbered) {
      flushPara();
      if (listType !== 'ol') { closeList(); html += '<ol>'; listType = 'ol'; }
      html += `<li>${inline(numbered[1])}</li>`;
    } else {
      closeList();
      para.push(inline(line));
    }
  }
  closeList(); flushPara();
  return html;
}

// ---------------------------------------------------------------- API
async function api(path, { method = 'GET', json = null, form = null } = {}) {
  const headers = {};
  let body;
  if (json !== null) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
  if (form !== null) { body = form; }
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

  const res = await fetch(path, { method, headers, body });
  if (res.status === 401) {
    logout();
    throw new Error('Session expired. Please sign in again.');
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const detail = data && data.detail
      ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return data;
}

// ---------------------------------------------------------------- AUTH
async function login(email, password) {
  const form = new URLSearchParams();
  form.set('username', email);
  form.set('password', password);
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Invalid email or password.');
  state.token = data.access_token;
  state.user = data.user;
  localStorage.setItem('moict_token', state.token);
  renderHeader();
  navigate('dashboard');
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('moict_token');
  renderHeader();
  navigate('landing');
}

async function tryResumeSession() {
  if (!state.token) return false;
  try {
    state.user = await api('/auth/me');
    return true;
  } catch {
    state.token = null;
    localStorage.removeItem('moict_token');
    return false;
  }
}

// ---------------------------------------------------------------- ROUTER
const ROUTES = ['landing', 'login', 'dashboard', 'chat', 'knowledge', 'upload', 'assistant', 'admin'];
const PROTECTED_ROUTES = ['dashboard', 'chat', 'knowledge', 'upload', 'assistant', 'admin'];
const ADMIN_ONLY_ROUTES = ['upload', 'admin'];
const NAV_ITEMS = [
  { route: 'dashboard', label: 'Dashboard' },
  { route: 'chat', label: 'Chat' },
  { route: 'knowledge', label: 'Knowledge Base' },
  { route: 'assistant', label: 'Document Assistant' },
  { route: 'upload', label: 'Upload', adminOnly: true },
  { route: 'admin', label: 'Admin', adminOnly: true },
];

function navigate(route) { location.hash = `#/${route}`; }

function currentRouteFromHash() {
  const h = location.hash.replace(/^#\/?/, '');
  return ROUTES.includes(h) ? h : null;
}

function renderRoute() {
  const authed = !!state.user;
  let route = currentRouteFromHash() || (authed ? 'dashboard' : 'landing');

  if (!authed && PROTECTED_ROUTES.includes(route)) { navigate('login'); return; }
  if (authed && (route === 'landing' || route === 'login')) { navigate('dashboard'); return; }
  if (authed && ADMIN_ONLY_ROUTES.includes(route) && state.user.role_name !== 'admin') { navigate('dashboard'); return; }

  showView(route);
}

function showView(route) {
  document.querySelectorAll('.view').forEach((el) => el.classList.add('hidden'));
  document.getElementById(`view-${route}`).classList.remove('hidden');
  document.querySelectorAll('#main-nav a').forEach((el) => el.classList.toggle('active', el.dataset.nav === route));

  if (route === 'dashboard') loadDashboard();
  if (route === 'chat') { loadSessions(); if (!document.getElementById('chat-thread').children.length) newChat(); }
  if (route === 'knowledge') loadKnowledgeBase();
  if (route === 'admin') showAdminTab(state.adminTab);
  if (route === 'assistant') resetAssistantForm();
  window.scrollTo(0, 0);
}

function renderHeader() {
  const nav = document.getElementById('main-nav');
  const actions = document.getElementById('header-auth-actions');
  const authed = !!state.user;

  if (!authed) {
    nav.innerHTML = '';
    actions.innerHTML = `<a class="btn btn-primary btn-sm" data-nav="login">Staff Access</a>`;
    return;
  }

  nav.innerHTML = NAV_ITEMS
    .filter((item) => !item.adminOnly || state.user.role_name === 'admin')
    .map((item) => `<a data-nav="${item.route}">${item.label}</a>`)
    .join('');

  actions.innerHTML = `
    <span class="avatar" data-avatar-name="${escapeHtml(state.user.full_name)}" style="width:36px;height:36px;font-size:13px;"></span>
    <a class="btn btn-outline btn-sm" id="logout-btn">Logout</a>`;
  renderAvatars();
  document.getElementById('logout-btn').addEventListener('click', logout);
}

document.addEventListener('click', (e) => {
  const navEl = e.target.closest('[data-nav]');
  if (navEl) { e.preventDefault(); navigate(navEl.dataset.nav); }
});
document.querySelectorAll('[data-scroll-features]').forEach((el) => {
  el.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('features-anchor').scrollIntoView({ behavior: 'smooth' });
  });
});

window.addEventListener('hashchange', renderRoute);

// ---------------------------------------------------------------- DASHBOARD
async function loadDashboard() {
  document.getElementById('dashboard-greeting').textContent = `Welcome back, ${firstName(state.user.full_name)}`;
  document.getElementById('dashboard-role').textContent = `${roleLabel(state.user.role_name)} · here's what's happening today.`;

  const uploadCard = document.getElementById('dashboard-upload-action');
  if (state.user.role_name === 'admin') {
    uploadCard.dataset.nav = 'upload';
    uploadCard.style.opacity = '';
    uploadCard.innerHTML = '<span class="material-symbols-outlined">upload_file</span><h4>Upload Document</h4><p>Add a new document to the knowledge base.</p>';
  } else {
    uploadCard.removeAttribute('data-nav');
    uploadCard.style.opacity = '0.55';
    uploadCard.innerHTML = '<span class="material-symbols-outlined">lock</span><h4>Upload Document</h4><p>Restricted to IT Officers.</p>';
  }

  try {
    const [sessions, docs] = await Promise.all([api('/chat/sessions'), api('/documents/')]);
    const recentEl = document.getElementById('dashboard-recent-chats');
    recentEl.innerHTML = sessions.length
      ? sessions.slice(0, 5).map((s) => `<div class="list-row"><span>${escapeHtml(s.title)}</span><span style="color:var(--color-text-muted);">${formatDate(s.created_at)}</span></div>`).join('')
      : '<p class="empty-hint">No conversations yet — start in Chat.</p>';

    document.getElementById('dashboard-doc-count').textContent = docs.length;
    const pinnedEl = document.getElementById('dashboard-pinned-docs');
    pinnedEl.innerHTML = docs.length
      ? docs.slice(0, 3).map((d) => `<div class="pinned-doc"><span class="material-symbols-outlined" style="font-size:18px;color:var(--color-primary);">description</span>${escapeHtml(d.title)}</div>`).join('')
      : '<p class="empty-hint">No documents indexed yet.</p>';
  } catch (e) { toast(e.message, true); }
}

// ---------------------------------------------------------------- CHAT
async function loadSessions() {
  try { state.sessions = await api('/chat/sessions'); } catch (e) { toast(e.message, true); state.sessions = []; }
  renderSessionList();
}

function renderSessionList() {
  const el = document.getElementById('session-list');
  el.innerHTML = '';
  if (!state.sessions.length) { el.innerHTML = '<p class="empty-hint">No conversations yet.</p>'; return; }
  state.sessions.forEach((s) => {
    const row = document.createElement('div');
    row.className = 'list-row session-row' + (s.session_id === state.currentSessionId ? ' active' : '');
    row.textContent = s.title;
    row.addEventListener('click', () => openSession(s.session_id));
    el.appendChild(row);
  });
}

function sourceChipsHtml(sources) {
  return sources.map((s, i) => {
    const suffix = s.section && s.section !== '-' ? ` · ${s.section}` : (s.page && s.page !== '-' ? ` · p.${s.page}` : '');
    return `<button type="button" class="source-chip" data-source-idx="${i}">${escapeHtml(s.document)}${escapeHtml(suffix)}</button>`;
  }).join(' ');
}

function appendMessage({ sender, text, sources = [], grounded = true, mockMode = false, messageId = null, rating = null, showBadge = false }) {
  const thread = document.getElementById('chat-thread');
  const wrap = document.createElement('div');
  wrap.className = 'chat-msg ' + (sender === 'user' ? 'chat-msg-user' : 'chat-msg-bot');

  if (sender === 'bot' && showBadge) {
    const badge = document.createElement('div');
    badge.className = 'chat-status-badge';
    if (mockMode) badge.innerHTML = '<span class="badge badge-warning">Extractive fallback (no LLM)</span>';
    else if (grounded) badge.innerHTML = '<span class="badge badge-success">Grounded answer</span>';
    else badge.innerHTML = '<span class="badge badge-danger">No match found</span>';
    wrap.appendChild(badge);
  }

  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  if (sender === 'user') bubble.textContent = text;
  else bubble.innerHTML = `<div class="md">${renderMarkdown(text)}</div>`;
  wrap.appendChild(bubble);

  if (sender === 'bot' && sources.length) {
    const src = document.createElement('div');
    src.className = 'chat-sources';
    src.innerHTML = `<span class="chat-sources-label">Sources:</span> ${sourceChipsHtml(sources)}`;
    wrap.appendChild(src);
    src.querySelectorAll('.source-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const idx = chip.dataset.sourceIdx;
        const existing = src.querySelector('.source-detail');
        const wasShowingThis = existing && existing.dataset.idx === idx;
        if (existing) existing.remove();
        if (wasShowingThis) return;
        const detail = document.createElement('div');
        detail.className = 'source-detail';
        detail.dataset.idx = idx;
        detail.textContent = sources[idx].excerpt;
        src.appendChild(detail);
      });
    });
  }

  if (sender === 'bot' && messageId) {
    const feedback = document.createElement('div');
    feedback.className = 'chat-feedback';
    feedback.innerHTML = `
      <button type="button" data-rating="1" title="Helpful"><span class="material-symbols-outlined" style="font-size:16px;">thumb_up</span></button>
      <button type="button" data-rating="-1" title="Not helpful"><span class="material-symbols-outlined" style="font-size:16px;">thumb_down</span></button>`;
    if (rating === 1) feedback.querySelector('[data-rating="1"]').classList.add('active-up');
    if (rating === -1) feedback.querySelector('[data-rating="-1"]').classList.add('active-down');
    feedback.querySelectorAll('button').forEach((btn) => {
      btn.addEventListener('click', async () => {
        try {
          const ratingValue = parseInt(btn.dataset.rating, 10);
          await api(`/chat/messages/${messageId}/rate`, { method: 'POST', json: { rating: ratingValue } });
          feedback.querySelectorAll('button').forEach((b) => b.classList.remove('active-up', 'active-down'));
          btn.classList.add(ratingValue === 1 ? 'active-up' : 'active-down');
          toast('Thanks for the feedback.');
        } catch (e) { toast(e.message, true); }
      });
    });
    wrap.appendChild(feedback);
  }

  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
  return wrap;
}

function newChat() {
  state.currentSessionId = null;
  renderSessionList();
  const thread = document.getElementById('chat-thread');
  thread.innerHTML = '';
  appendMessage({
    sender: 'bot',
    text: `Hi ${firstName(state.user.full_name)}, ask me anything about Ministry policy, regulation, or ICT standards — I'll answer only from official documents and always show my sources.`,
  });
  document.getElementById('chat-input')?.focus();
}

async function openSession(sessionId) {
  state.currentSessionId = sessionId;
  renderSessionList();
  try {
    const messages = await api(`/chat/sessions/${sessionId}/messages`);
    const thread = document.getElementById('chat-thread');
    thread.innerHTML = '';
    messages.forEach((m) => appendMessage({
      sender: m.sender,
      text: m.message_text,
      sources: m.source_document ? JSON.parse(m.source_document) : [],
      messageId: m.sender === 'bot' ? m.message_id : null,
      rating: m.rating,
    }));
  } catch (e) { toast(e.message, true); }
}

function setSending(isSending) {
  document.getElementById('chat-send-btn').disabled = isSending;
  document.getElementById('chat-input').disabled = isSending;
}

document.getElementById('new-chat-btn').addEventListener('click', () => { newChat(); toast('New chat started'); });

document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  appendMessage({ sender: 'user', text });
  input.value = '';
  setSending(true);

  const thread = document.getElementById('chat-thread');
  const thinking = document.createElement('div');
  thinking.className = 'chat-msg chat-msg-bot';
  thinking.id = 'chat-thinking';
  thinking.innerHTML = '<div class="chat-bubble chat-thinking">Retrieving relevant documents…</div>';
  thread.appendChild(thinking);
  thread.scrollTop = thread.scrollHeight;

  try {
    const res = await api('/chat/ask', { method: 'POST', json: { message: text, session_id: state.currentSessionId } });
    state.currentSessionId = res.session_id;
    document.getElementById('chat-thinking')?.remove();
    appendMessage({
      sender: 'bot', text: res.answer, sources: res.sources, grounded: res.grounded,
      mockMode: res.mock_mode, messageId: res.message_id, showBadge: true,
    });
    loadSessions();
  } catch (err) {
    document.getElementById('chat-thinking')?.remove();
    appendMessage({ sender: 'bot', text: err.message || 'Something went wrong reaching the knowledge base. Please try again.' });
  } finally {
    setSending(false);
  }
});

// ---------------------------------------------------------------- KNOWLEDGE BASE
async function loadKnowledgeBase() {
  state.kbCategory = 'All';
  try {
    const [explorer, docs] = await Promise.all([api('/documents/explorer'), api('/documents/')]);
    document.getElementById('kb-summary').textContent = `${docs.length} document${docs.length === 1 ? '' : 's'} indexed across ${explorer.by_category.length} categor${explorer.by_category.length === 1 ? 'y' : 'ies'}.`;

    const catEl = document.getElementById('kb-categories');
    const cats = [{ key: 'All', count: docs.length }, ...explorer.by_category.map((g) => ({ key: g.key, count: g.count }))];
    catEl.innerHTML = cats.map((c) => `<div class="kb-category ${c.key === state.kbCategory ? 'active' : ''}" data-cat="${escapeHtml(c.key)}"><span>${escapeHtml(c.key)}</span><span style="color:var(--color-text-muted);">${c.count}</span></div>`).join('');
    catEl.querySelectorAll('[data-cat]').forEach((el) => el.addEventListener('click', () => {
      state.kbCategory = el.dataset.cat;
      catEl.querySelectorAll('.kb-category').forEach((c) => c.classList.toggle('active', c.dataset.cat === state.kbCategory));
      renderKbDocuments(explorer, docs);
    }));
    renderKbDocuments(explorer, docs);
  } catch (e) { toast(e.message, true); }
}

function renderKbDocuments(explorer, docs) {
  const group = explorer.by_category.find((g) => g.key === state.kbCategory);
  const list = state.kbCategory === 'All' ? docs : (group ? group.documents : []);
  const el = document.getElementById('kb-documents');
  el.innerHTML = list.length ? list.map((d) => `
    <div class="doc-row">
      <span class="material-symbols-outlined">description</span>
      <div style="flex:1;">
        <div class="doc-title">${escapeHtml(d.title)}</div>
        <div class="doc-meta">${escapeHtml(d.category || 'Uncategorized')} · v${d.version} · uploaded ${formatDate(d.upload_date)}</div>
      </div>
      <span class="badge ${d.status === 'active' ? 'badge-success' : ''}">${escapeHtml(d.status)}</span>
    </div>`).join('') : `
    <div class="doc-row">
      <span class="material-symbols-outlined">info</span>
      <div style="flex:1;">
        <div class="doc-title">No documents in this category yet</div>
        <div class="doc-meta">Upload a document to make it searchable.</div>
      </div>
    </div>`;
}

// ---------------------------------------------------------------- UPLOAD
function humanFileSize(bytes) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
  return `${bytes.toFixed(1)} ${units[i]}`;
}

function queueRow(file) {
  const row = document.createElement('div');
  row.className = 'upload-row';
  row.innerHTML = `
    <div class="upload-row-main">
      <span class="material-symbols-outlined upload-row-icon">description</span>
      <div>
        <div class="upload-row-name">${escapeHtml(file.name)}</div>
        <div class="upload-row-meta">${humanFileSize(file.size)} · queued</div>
      </div>
    </div>
    <div class="upload-row-progress"><div class="upload-row-progress-bar" style="width:0%"></div></div>`;
  return row;
}

async function handleUploadFiles(fileList) {
  const queue = document.getElementById('upload-queue');
  const emptyHint = queue.querySelector('.empty-hint');
  if (emptyHint) emptyHint.remove();

  for (const file of fileList) {
    const row = queueRow(file);
    queue.prepend(row);
    const bar = row.querySelector('.upload-row-progress-bar');
    const meta = row.querySelector('.upload-row-meta');

    const form = new FormData();
    form.append('file', file);
    form.append('department', document.getElementById('upload-department').value);
    form.append('author', document.getElementById('upload-author').value);
    form.append('category', document.getElementById('upload-category').value);
    form.append('date_published', document.getElementById('upload-date').value);

    let pct = 0;
    const tick = setInterval(() => { pct = Math.min(pct + 12, 90); bar.style.width = pct + '%'; }, 180);

    try {
      const res = await api('/documents/upload', { method: 'POST', form });
      clearInterval(tick);
      bar.style.width = '100%';
      meta.textContent = `${humanFileSize(file.size)} · indexed · ${res.chunks_indexed} chunks embedded`;
      toast(`${file.name} uploaded and indexed`);
    } catch (e) {
      clearInterval(tick);
      meta.textContent = `${humanFileSize(file.size)} · failed — ${e.message}`;
      row.classList.add('upload-row-error');
      toast(`${file.name} failed to upload`, true);
    }
  }
}

(function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => { handleUploadFiles(e.target.files); fileInput.value = ''; });
  ['dragenter', 'dragover'].forEach((evt) => dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add('dropzone-active'); }));
  ['dragleave', 'drop'].forEach((evt) => dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove('dropzone-active'); }));
  dropzone.addEventListener('drop', (e) => handleUploadFiles(e.dataTransfer.files));
})();

// ---------------------------------------------------------------- AI DOCUMENT ASSISTANT
function resetAssistantForm() {
  state.assistantFile = null;
  document.getElementById('assistant-file-label').textContent = 'Drag & drop a document here';
  document.getElementById('assistant-submit').disabled = true;
  document.getElementById('assistant-result').classList.add('hidden');
}

(function initAssistantDropzone() {
  const dropzone = document.getElementById('assistant-dropzone');
  const fileInput = document.getElementById('assistant-file-input');
  const label = document.getElementById('assistant-file-label');
  const submitBtn = document.getElementById('assistant-submit');

  function setFile(file) {
    if (!file) return;
    state.assistantFile = file;
    label.textContent = file.name;
    submitBtn.disabled = false;
  }

  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => setFile(e.target.files[0]));
  ['dragenter', 'dragover'].forEach((evt) => dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add('dropzone-active'); }));
  ['dragleave', 'drop'].forEach((evt) => dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove('dropzone-active'); }));
  dropzone.addEventListener('drop', (e) => setFile(e.dataTransfer.files[0]));
})();

document.getElementById('assistant-submit').addEventListener('click', async () => {
  if (!state.assistantFile) return;
  const mode = document.querySelector('input[name="assistant-mode"]:checked').value;
  const btn = document.getElementById('assistant-submit');
  const resultEl = document.getElementById('assistant-result');
  btn.disabled = true;
  const originalLabel = btn.textContent;
  btn.textContent = 'Analyzing…';
  resultEl.classList.add('hidden');

  const form = new FormData();
  form.append('file', state.assistantFile);
  form.append('mode', mode);
  try {
    const res = await api('/assistant/summarize', { method: 'POST', form });
    resultEl.classList.remove('hidden');
    resultEl.innerHTML = `
      ${res.mock_mode ? '<div style="margin-bottom:12px;"><span class="badge badge-warning">Extractive fallback (no LLM)</span></div>' : ''}
      <div class="md">${renderMarkdown(res.result)}</div>`;
  } catch (e) { toast(e.message, true); } finally {
    btn.disabled = false;
    btn.textContent = originalLabel;
  }
});

// ---------------------------------------------------------------- ADMIN
document.querySelectorAll('.subtab').forEach((btn) => btn.addEventListener('click', () => showAdminTab(btn.dataset.subtab)));

function showAdminTab(tab) {
  state.adminTab = tab;
  document.querySelectorAll('.subtab').forEach((el) => el.classList.toggle('active', el.dataset.subtab === tab));
  document.querySelectorAll('.admin-panel').forEach((el) => el.classList.toggle('hidden', el.id !== `admin-panel-${tab}`));
  if (tab === 'overview') loadOverview();
  if (tab === 'users') loadUsers();
  if (tab === 'logs') loadLogs();
  if (tab === 'insights') loadInsights();
  if (tab === 'settings') loadSettings();
}

async function loadOverview() {
  const el = document.getElementById('stat-grid');
  try {
    const s = await api('/admin/stats');
    const tiles = [
      ['Documents indexed', s.documents_indexed],
      ['Pages indexed', s.indexed_pages],
      ['Chunks embedded', s.chunks_embedded],
      ['Total users', s.total_users],
      ['Total queries', s.total_queries],
    ];
    el.innerHTML = tiles.map(([label, value]) => `<div class="card stat-tile"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`).join('');
  } catch (e) { toast(e.message, true); }
}

document.getElementById('rebuild-index-btn').addEventListener('click', async () => {
  const status = document.getElementById('rebuild-status');
  status.textContent = 'Rebuilding…';
  try {
    const res = await api('/admin/rebuild-index', { method: 'POST' });
    status.textContent = `Done — ${res.chunks_indexed} chunks from ${res.documents_processed} documents.`;
    loadOverview();
  } catch (e) { status.textContent = e.message; }
});

async function loadUsers() {
  const el = document.getElementById('users-table-body');
  try {
    const users = await api('/admin/users');
    el.innerHTML = users.map((u) => `
      <tr>
        <td>${escapeHtml(u.full_name)}</td>
        <td style="color:var(--color-text-secondary);">${escapeHtml(u.email)}</td>
        <td><span class="role-chip">${escapeHtml(u.role_name)}</span></td>
        <td>${u.is_active ? '<span style="color:var(--color-success);font-weight:600;">Active</span>' : '<span style="color:var(--color-danger);font-weight:600;">Disabled</span>'}</td>
        <td>
          <button type="button" class="btn-link" data-toggle-user="${u.user_id}">${u.is_active ? 'Disable' : 'Enable'}</button>
          &nbsp;·&nbsp;
          <button type="button" class="btn-link" data-reset-user="${u.user_id}">Reset password</button>
        </td>
      </tr>`).join('');
    el.querySelectorAll('[data-toggle-user]').forEach((btn) => btn.addEventListener('click', async () => {
      try { await api(`/admin/users/${btn.dataset.toggleUser}/toggle-active`, { method: 'PATCH' }); loadUsers(); toast('User updated.'); } catch (e) { toast(e.message, true); }
    }));
    el.querySelectorAll('[data-reset-user]').forEach((btn) => btn.addEventListener('click', async () => {
      const pw = prompt('New password for this user (min 6 characters):');
      if (!pw) return;
      try { await api(`/admin/users/${btn.dataset.resetUser}/reset-password`, { method: 'POST', json: { new_password: pw } }); toast('Password reset.'); } catch (e) { toast(e.message, true); }
    }));
  } catch (e) { toast(e.message, true); }
}

document.getElementById('add-user-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    full_name: document.getElementById('new-user-name').value.trim(),
    email: document.getElementById('new-user-email').value.trim(),
    password: document.getElementById('new-user-password').value,
    role: document.getElementById('new-user-role').value,
  };
  try {
    await api('/auth/register', { method: 'POST', json: payload });
    toast(`Account created for ${payload.full_name}.`);
    e.target.reset();
    loadUsers();
  } catch (err) { toast(err.message, true); }
});

const LOG_ICON_BY_TAG = { ok: 'check_circle', warn: 'warning', deny: 'block' };

async function loadLogs() {
  const el = document.getElementById('logs-list');
  try {
    const logs = await api('/admin/logs');
    el.innerHTML = logs.length ? logs.map((l) => `
      <div class="action-log-row">
        <span class="material-symbols-outlined icon-${l.tag}">${LOG_ICON_BY_TAG[l.tag] || 'info'}</span>
        <div style="flex:1;">${escapeHtml(l.action)}</div>
        <span style="color:var(--color-text-muted);">${new Date(l.timestamp).toLocaleString()}</span>
      </div>`).join('') : '<div class="action-log-row"><span class="material-symbols-outlined">info</span><div style="flex:1;">No audit entries yet.</div></div>';
  } catch (e) { toast(e.message, true); }
}

async function loadInsights() {
  try {
    const data = await api('/admin/insights');
    document.getElementById('insights-top-questions').innerHTML = data.top_questions.length
      ? data.top_questions.map((q) => `<div class="list-row"><span>${escapeHtml(q.question)}</span><span style="color:var(--color-text-muted);">${q.count}×</span></div>`).join('')
      : '<p class="empty-hint">No questions asked yet.</p>';
    document.getElementById('insights-gaps').innerHTML = data.knowledge_gaps.length
      ? data.knowledge_gaps.map((g) => `<div class="list-row"><span>${escapeHtml(g.question)}</span><span style="color:var(--color-text-muted);">${new Date(g.timestamp).toLocaleDateString()}</span></div>`).join('')
      : '<p class="empty-hint">No knowledge gaps recorded.</p>';
    document.getElementById('insights-activity').innerHTML = data.recent_activity.length
      ? data.recent_activity.map((a) => `<div class="action-log-row"><span class="material-symbols-outlined icon-${a.tag}">${LOG_ICON_BY_TAG[a.tag] || 'info'}</span><div style="flex:1;">${escapeHtml(a.action)}</div><span style="color:var(--color-text-muted);">${new Date(a.timestamp).toLocaleString()}</span></div>`).join('')
      : '<p class="empty-hint">No activity yet.</p>';
  } catch (e) { toast(e.message, true); }
}

async function loadSettings() {
  try {
    const s = await api('/admin/settings');
    document.getElementById('settings-external-toggle').checked = s.external_ai_enabled;
    document.getElementById('settings-provider').value = s.external_ai_provider || '';
  } catch (e) { toast(e.message, true); }
}

document.getElementById('settings-save-btn').addEventListener('click', async () => {
  const status = document.getElementById('settings-status');
  try {
    await api('/admin/settings', {
      method: 'PATCH',
      json: {
        external_ai_enabled: document.getElementById('settings-external-toggle').checked,
        external_ai_provider: document.getElementById('settings-provider').value,
      },
    });
    status.textContent = 'Saved.';
  } catch (e) { status.textContent = e.message; }
});

// ---------------------------------------------------------------- LOGIN FORM
document.getElementById('login-help-toggle').addEventListener('click', () => {
  document.getElementById('login-help-panel').classList.toggle('hidden');
});

document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');
  const btn = document.getElementById('login-submit');
  btn.disabled = true;
  btn.textContent = 'Signing in…';
  try {
    await login(document.getElementById('login-email').value.trim(), document.getElementById('login-password').value);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In to Dashboard →';
  }
});

// ---------------------------------------------------------------- BOOT
(async function boot() {
  renderHeader();
  const resumed = await tryResumeSession();
  if (resumed) renderHeader();
  renderRoute();
})();
