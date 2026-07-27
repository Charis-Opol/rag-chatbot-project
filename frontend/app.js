// Ministry Knowledge Intelligence Assistant — frontend application logic.
// Talks to the FastAPI backend mounted at the same origin.

const state = {
  token: localStorage.getItem('moict_token') || null,
  user: null,
  view: 'chat',
  sessions: [],
  currentSessionId: null,
  adminTab: 'stats',
};

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str === null || str === undefined ? '' : String(str);
  return div.innerHTML;
}

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

function toast(msg, isError = false) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.background = isError ? '#7a1f1f' : '#14171c';
  el.classList.remove('hidden');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add('hidden'), 4000);
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
  enterApp();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('moict_token');
  document.getElementById('app-shell').classList.add('hidden');
  document.getElementById('login-view').classList.remove('hidden');
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

function enterApp() {
  document.getElementById('login-view').classList.add('hidden');
  document.getElementById('app-shell').classList.remove('hidden');
  document.getElementById('user-name').textContent = state.user.full_name;
  document.getElementById('user-role').textContent = state.user.role_name === 'admin' ? 'IT Officer / Admin' : 'Ministry Staff';
  document.getElementById('user-avatar').textContent = (state.user.full_name || '?').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase();
  const isAdmin = state.user.role_name === 'admin';
  document.querySelectorAll('[data-admin-only]').forEach((el) => el.classList.toggle('hidden', !isAdmin));
  showView('chat');
}

// ---------------------------------------------------------------- ROUTING
const VIEW_TITLES = { chat: 'Chat', knowledge: 'Knowledge Base', assistant: 'AI Document Assistant', upload: 'Upload Documents', admin: 'Admin Panel' };

function showView(name) {
  state.view = name;
  document.querySelectorAll('.view').forEach((el) => el.classList.add('hidden'));
  document.getElementById(`view-${name}`).classList.remove('hidden');
  document.querySelectorAll('.nav-item').forEach((el) => el.classList.toggle('active', el.dataset.view === name));
  document.getElementById('view-title').textContent = VIEW_TITLES[name] || name;
  if (name === 'chat') { loadSessions(); if (!document.getElementById('chat-messages').children.length) newChat(); }
  if (name === 'knowledge') loadKnowledgeBase();
  if (name === 'admin') showAdminTab(state.adminTab);
}

document.querySelectorAll('.nav-item').forEach((btn) => btn.addEventListener('click', () => showView(btn.dataset.view)));

// ---------------------------------------------------------------- CHAT
async function loadSessions() {
  try {
    state.sessions = await api('/chat/sessions');
  } catch (e) {
    toast(e.message, true);
    state.sessions = [];
  }
  renderSessionList();
}

function renderSessionList() {
  const el = document.getElementById('session-list');
  if (!state.sessions.length) {
    el.innerHTML = '<p class="text-xs text-muted px-2 py-3">No conversations yet.</p>';
    return;
  }
  el.innerHTML = state.sessions.map((s) => `
    <button data-session-id="${s.session_id}" class="session-item w-full text-left px-3 py-2 rounded-lg truncate ${s.session_id === state.currentSessionId ? 'active' : ''}">
      ${escapeHtml(s.title)}
    </button>`).join('');
  el.querySelectorAll('[data-session-id]').forEach((btn) => {
    btn.addEventListener('click', () => openSession(parseInt(btn.dataset.sessionId, 10)));
  });
}

async function openSession(sessionId) {
  state.currentSessionId = sessionId;
  renderSessionList();
  try {
    const messages = await api(`/chat/sessions/${sessionId}/messages`);
    renderMessages(messages.map((m) => ({
      sender: m.sender,
      text: m.message_text,
      sources: m.source_document ? JSON.parse(m.source_document) : [],
      grounded: true,
      mock_mode: false,
      message_id: m.message_id,
    })));
  } catch (e) { toast(e.message, true); }
}

function newChat() {
  state.currentSessionId = null;
  renderSessionList();
  document.getElementById('chat-messages').innerHTML = `
    <div class="max-w-2xl mx-auto text-center py-16">
      <div class="w-14 h-14 rounded-2xl bg-gold/15 text-gold mx-auto mb-4 flex items-center justify-center">
        <span class="material-symbols-outlined text-[28px]">smart_toy</span>
      </div>
      <h3 class="font-display font-semibold text-lg mb-2">Ask about ICT regulations &amp; compliance</h3>
      <p class="text-sm text-muted">Answers are grounded in indexed ministry documents, with citations.</p>
    </div>`;
}

function messageBubble(msg) {
  if (msg.sender === 'user') {
    return `<div class="flex justify-end"><div class="msg-bubble-user max-w-xl rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">${escapeHtml(msg.text)}</div></div>`;
  }
  const badge = msg.mock_mode
    ? '<span class="badge-mock text-[11px] font-medium px-2 py-0.5 rounded-full border">Extractive fallback (no LLM)</span>'
    : msg.grounded
      ? '<span class="badge-grounded text-[11px] font-medium px-2 py-0.5 rounded-full border">Grounded answer</span>'
      : '<span class="badge-ungrounded text-[11px] font-medium px-2 py-0.5 rounded-full border">No match found</span>';
  const sources = (msg.sources || []).map((s) => `
    <div class="citation-card bg-white border border-black/10 rounded-xl p-3 text-xs transition-shadow">
      <p class="font-semibold text-ink truncate mb-1">${escapeHtml(s.document)}</p>
      <p class="text-muted mb-1">${s.section && s.section !== '-' ? escapeHtml(s.section) : (s.page && s.page !== '-' ? 'Page ' + escapeHtml(String(s.page)) : '')}</p>
      <p class="text-muted line-clamp-2">${escapeHtml((s.excerpt || '').slice(0, 160))}${(s.excerpt || '').length > 160 ? '…' : ''}</p>
    </div>`).join('');
  const rateBtns = msg.message_id ? `
    <div class="flex items-center gap-1 mt-2">
      <button class="rate-btn p-1 text-muted hover:text-green transition-colors" data-message-id="${msg.message_id}" data-rating="1"><span class="material-symbols-outlined text-[16px]">thumb_up</span></button>
      <button class="rate-btn p-1 text-muted hover:text-red-500 transition-colors" data-message-id="${msg.message_id}" data-rating="-1"><span class="material-symbols-outlined text-[16px]">thumb_down</span></button>
    </div>` : '';
  return `
    <div class="flex gap-4 items-start max-w-3xl">
      <div class="w-9 h-9 rounded-full bg-white border border-black/10 flex items-center justify-center text-charcoal shrink-0">
        <span class="material-symbols-outlined text-[20px]">smart_toy</span>
      </div>
      <div class="flex-1 min-w-0">
        <div class="mb-2">${badge}</div>
        <div class="bg-white border border-black/10 rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">${escapeHtml(msg.text)}</div>
        ${rateBtns}
        ${sources ? `<div class="grid sm:grid-cols-2 gap-2 mt-3">${sources}</div>` : ''}
      </div>
    </div>`;
}

function renderMessages(messages) {
  const el = document.getElementById('chat-messages');
  if (!messages.length) { newChat(); return; }
  el.innerHTML = messages.map(messageBubble).join('');
  attachRatingHandlers();
  el.scrollTop = el.scrollHeight;
}

function attachRatingHandlers() {
  document.querySelectorAll('.rate-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        await api(`/chat/messages/${btn.dataset.messageId}/rate`, { method: 'POST', json: { rating: parseInt(btn.dataset.rating, 10) } });
        toast('Thanks for the feedback.');
      } catch (e) { toast(e.message, true); }
    }, { once: true });
  });
}

document.getElementById('new-chat-btn').addEventListener('click', newChat);

document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  input.style.height = 'auto';

  const el = document.getElementById('chat-messages');
  if (el.querySelector('.font-display')) el.innerHTML = '';
  el.insertAdjacentHTML('beforeend', messageBubble({ sender: 'user', text: message }));
  const thinkingId = 'thinking-' + Date.now();
  el.insertAdjacentHTML('beforeend', `<div id="${thinkingId}" class="flex gap-4 items-center text-sm text-muted"><span class="material-symbols-outlined text-[18px] spin">progress_activity</span> Thinking…</div>`);
  el.scrollTop = el.scrollHeight;

  try {
    const res = await api('/chat/ask', { method: 'POST', json: { message, session_id: state.currentSessionId } });
    document.getElementById(thinkingId)?.remove();
    state.currentSessionId = res.session_id;
    el.insertAdjacentHTML('beforeend', messageBubble({
      sender: 'bot', text: res.answer, sources: res.sources, grounded: res.grounded, mock_mode: res.mock_mode, message_id: res.message_id,
    }));
    attachRatingHandlers();
    el.scrollTop = el.scrollHeight;
    loadSessions();
  } catch (e) {
    document.getElementById(thinkingId)?.remove();
    toast(e.message, true);
  }
});

document.getElementById('chat-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); document.getElementById('chat-form').requestSubmit(); }
});
document.getElementById('chat-input').addEventListener('input', function onInput() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 160) + 'px';
});

// ---------------------------------------------------------------- KNOWLEDGE BASE
async function loadKnowledgeBase() {
  const el = document.getElementById('kb-groups');
  el.innerHTML = '<p class="text-sm text-muted">Loading…</p>';
  try {
    const data = await api('/documents/explorer');
    if (!data.by_category.length) {
      el.innerHTML = '<p class="text-sm text-muted">No documents indexed yet.</p>';
      return;
    }
    el.innerHTML = data.by_category.map((group) => `
      <div>
        <h3 class="font-display font-semibold text-sm mb-3">${escapeHtml(group.key)} <span class="text-muted font-normal">(${group.count})</span></h3>
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          ${group.documents.map((d) => `
            <div class="bg-white border border-black/10 rounded-xl p-4">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded border bg-black/5 text-muted">${escapeHtml(d.file_type)}</span>
                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded border ${d.status === 'active' ? 'bg-green/10 text-green border-green/20' : 'bg-black/5 text-muted'}">${escapeHtml(d.status)}</span>
                <span class="text-[10px] text-muted">v${d.version}</span>
              </div>
              <p class="text-sm font-semibold truncate mb-1">${escapeHtml(d.title)}</p>
              <p class="text-xs text-muted truncate">${escapeHtml(d.department || 'No department')}</p>
              <p class="text-[11px] text-muted mt-1">${new Date(d.upload_date).toLocaleDateString()}</p>
            </div>`).join('')}
        </div>
      </div>`).join('');
  } catch (e) {
    el.innerHTML = `<p class="text-sm text-red-500">${escapeHtml(e.message)}</p>`;
  }
}
document.getElementById('kb-refresh').addEventListener('click', loadKnowledgeBase);

// ---------------------------------------------------------------- AI DOCUMENT ASSISTANT
document.getElementById('assistant-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('assistant-file');
  const mode = document.querySelector('input[name="mode"]:checked').value;
  if (!fileInput.files.length) return;
  const btn = document.getElementById('assistant-submit');
  const resultEl = document.getElementById('assistant-result');
  btn.disabled = true; btn.textContent = 'Analyzing…';
  resultEl.classList.add('hidden');
  const form = new FormData();
  form.append('file', fileInput.files[0]);
  form.append('mode', mode);
  try {
    const res = await api('/assistant/summarize', { method: 'POST', form });
    resultEl.classList.remove('hidden');
    resultEl.innerHTML = `
      ${res.mock_mode ? '<span class="badge-mock text-[11px] font-medium px-2 py-0.5 rounded-full border">Extractive fallback (no LLM)</span><div class="h-3"></div>' : ''}
      <p class="text-sm leading-relaxed whitespace-pre-wrap">${escapeHtml(res.result)}</p>`;
  } catch (e) { toast(e.message, true); } finally {
    btn.disabled = false; btn.textContent = 'Analyze document';
  }
});

// ---------------------------------------------------------------- UPLOAD
document.getElementById('upload-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('upload-file');
  if (!fileInput.files.length) return;
  const btn = document.getElementById('upload-submit');
  const resultEl = document.getElementById('upload-result');
  btn.disabled = true; btn.textContent = 'Uploading…';
  const form = new FormData();
  form.append('file', fileInput.files[0]);
  form.append('department', document.getElementById('upload-department').value);
  form.append('author', document.getElementById('upload-author').value);
  form.append('category', document.getElementById('upload-category').value);
  form.append('date_published', document.getElementById('upload-date').value);
  try {
    const res = await api('/documents/upload', { method: 'POST', form });
    resultEl.classList.remove('hidden');
    resultEl.className = 'mt-4 text-sm rounded-lg px-3 py-2 badge-grounded border';
    resultEl.textContent = `Indexed "${res.document.title}" — ${res.chunks_indexed} chunks embedded.`;
    e.target.reset();
  } catch (err) {
    resultEl.classList.remove('hidden');
    resultEl.className = 'mt-4 text-sm rounded-lg px-3 py-2 badge-ungrounded border';
    resultEl.textContent = err.message;
  } finally {
    btn.disabled = false; btn.textContent = 'Upload & index';
  }
});

// ---------------------------------------------------------------- ADMIN
document.querySelectorAll('.admin-tab').forEach((btn) => btn.addEventListener('click', () => showAdminTab(btn.dataset.tab)));

function showAdminTab(tab) {
  state.adminTab = tab;
  document.querySelectorAll('.admin-tab').forEach((el) => el.classList.toggle('active', el.dataset.tab === tab));
  document.querySelectorAll('.admin-panel').forEach((el) => el.classList.toggle('hidden', el.id !== `admin-panel-${tab}`));
  if (tab === 'stats') loadStats();
  if (tab === 'users') loadUsers();
  if (tab === 'logs') loadLogs();
  if (tab === 'insights') loadInsights();
  if (tab === 'settings') loadSettings();
}

async function loadStats() {
  const el = document.getElementById('stats-cards');
  try {
    const s = await api('/admin/stats');
    const cards = [
      ['Documents indexed', s.documents_indexed],
      ['Pages indexed', s.indexed_pages],
      ['Chunks embedded', s.chunks_embedded],
      ['Total users', s.total_users],
      ['Total queries', s.total_queries],
    ];
    el.innerHTML = cards.map(([label, value]) => `
      <div class="bg-white border border-black/10 rounded-xl p-4">
        <p class="text-2xl font-display font-semibold">${value}</p>
        <p class="text-xs text-muted mt-1">${label}</p>
      </div>`).join('');
  } catch (e) { toast(e.message, true); }
}

document.getElementById('rebuild-index-btn').addEventListener('click', async () => {
  const status = document.getElementById('rebuild-status');
  status.textContent = 'Rebuilding…';
  try {
    const res = await api('/admin/rebuild-index', { method: 'POST' });
    status.textContent = `Done — ${res.chunks_indexed} chunks from ${res.documents_processed} documents.`;
    loadStats();
  } catch (e) { status.textContent = e.message; }
});

async function loadUsers() {
  const el = document.getElementById('users-table-body');
  try {
    const users = await api('/admin/users');
    el.innerHTML = users.map((u) => `
      <tr>
        <td class="px-4 py-3">${escapeHtml(u.full_name)}</td>
        <td class="px-4 py-3 text-muted">${escapeHtml(u.email)}</td>
        <td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded-full border ${u.role_name === 'admin' ? 'badge-grounded' : 'bg-black/5 text-muted'}">${escapeHtml(u.role_name)}</span></td>
        <td class="px-4 py-3">${u.is_active ? '<span class="text-green text-xs font-medium">Active</span>' : '<span class="text-red-500 text-xs font-medium">Disabled</span>'}</td>
        <td class="px-4 py-3 space-x-2">
          <button data-toggle-user="${u.user_id}" class="text-xs text-muted hover:text-ink underline">${u.is_active ? 'Disable' : 'Enable'}</button>
          <button data-reset-user="${u.user_id}" class="text-xs text-muted hover:text-ink underline">Reset password</button>
        </td>
      </tr>`).join('');
    el.querySelectorAll('[data-toggle-user]').forEach((btn) => btn.addEventListener('click', async () => {
      try { await api(`/admin/users/${btn.dataset.toggleUser}/toggle-active`, { method: 'PATCH' }); loadUsers(); } catch (e) { toast(e.message, true); }
    }));
    el.querySelectorAll('[data-reset-user]').forEach((btn) => btn.addEventListener('click', async () => {
      const pw = prompt('New password for this user (min 6 characters):');
      if (!pw) return;
      try { await api(`/admin/users/${btn.dataset.resetUser}/reset-password`, { method: 'POST', json: { new_password: pw } }); toast('Password reset.'); } catch (e) { toast(e.message, true); }
    }));
  } catch (e) { toast(e.message, true); }
}

async function loadLogs() {
  const el = document.getElementById('logs-table-body');
  try {
    const logs = await api('/admin/logs');
    el.innerHTML = logs.map((l) => `
      <tr>
        <td class="px-4 py-3 text-muted whitespace-nowrap">${new Date(l.timestamp).toLocaleString()}</td>
        <td class="px-4 py-3">${escapeHtml(l.action)}</td>
        <td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded-full border ${l.tag === 'ok' ? 'badge-grounded' : l.tag === 'warn' ? 'badge-mock' : 'badge-ungrounded'}">${escapeHtml(l.tag)}</span></td>
      </tr>`).join('');
  } catch (e) { toast(e.message, true); }
}

async function loadInsights() {
  try {
    const data = await api('/admin/insights');
    document.getElementById('insights-top-questions').innerHTML = data.top_questions.length
      ? data.top_questions.map((q) => `<div class="flex justify-between gap-2"><span class="truncate">${escapeHtml(q.question)}</span><span class="text-muted shrink-0">${q.count}×</span></div>`).join('')
      : '<p class="text-muted">No questions asked yet.</p>';
    document.getElementById('insights-gaps').innerHTML = data.knowledge_gaps.length
      ? data.knowledge_gaps.map((g) => `<div><p>${escapeHtml(g.question)}</p><p class="text-[11px] text-muted">${new Date(g.timestamp).toLocaleString()}</p></div>`).join('')
      : '<p class="text-muted">No knowledge gaps recorded.</p>';
    document.getElementById('insights-activity').innerHTML = data.recent_activity.length
      ? data.recent_activity.map((a) => `<div class="flex justify-between gap-2"><span class="truncate">${escapeHtml(a.action)}</span><span class="text-muted shrink-0 text-[11px]">${new Date(a.timestamp).toLocaleString()}</span></div>`).join('')
      : '<p class="text-muted">No activity yet.</p>';
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

// ---------------------------------------------------------------- LOGOUT
document.getElementById('logout-btn').addEventListener('click', logout);

// ---------------------------------------------------------------- LOGIN FORM
document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');
  const btn = document.getElementById('login-submit');
  btn.disabled = true; btn.textContent = 'Signing in…';
  try {
    await login(document.getElementById('login-email').value.trim(), document.getElementById('login-password').value);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false; btn.textContent = 'Sign in';
  }
});

// ---------------------------------------------------------------- HEALTH CHECK + BOOT
async function checkHealth() {
  const el = document.getElementById('backend-status');
  try {
    const res = await fetch('/api/health');
    if (res.ok) { el.textContent = 'Backend online — offline RAG mode.'; return; }
    throw new Error('unhealthy');
  } catch {
    el.textContent = 'Backend unreachable — start the FastAPI server.';
  }
}

(async function boot() {
  checkHealth();
  const resumed = await tryResumeSession();
  if (resumed) enterApp();
})();
