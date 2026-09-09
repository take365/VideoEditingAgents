let selectedProject = null;
let pollTimer = null;
let currentCodexThreadId = null;
let messageSending = false;

const activityStyle = document.createElement('style');
activityStyle.textContent = '.agent-activity{display:flex;align-items:center;gap:8px;color:#65756e}.agent-spinner{width:14px;height:14px;border:2px solid #c9d9d2;border-top-color:#146b55;border-radius:50%;animation:agent-spin .8s linear infinite;display:inline-block}@keyframes agent-spin{to{transform:rotate(360deg)}}.preview-actions{display:flex;align-items:center;gap:8px}.orientation-control{display:flex;align-items:center;gap:5px;color:#65756e;font-size:12px}.orientation-control select{border:1px solid #d4dfd9;border-radius:6px;padding:9px 8px;background:#fff;color:#123a35;font:inherit}';
document.head.appendChild(activityStyle);

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error(await response.text() || `HTTP ${response.status}`);
  return response.json();
}

function el(id) { return document.getElementById(id); }
function setText(id, value) {
  const node = el(id);
  if (node) node.textContent = value;
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function loadProjects() {
  const projects = await api('/api/projects');
  el('projects').innerHTML = projects.map((p) => `<button class="project ${selectedProject?.id === p.id ? 'active' : ''}" data-id="${p.id}">${escapeHtml(p.name)}</button>`).join('') || '<div class="muted">案件はまだありません</div>';
  document.querySelectorAll('.project').forEach((button) => { button.onclick = () => selectProject(button.dataset.id); });
  if (!selectedProject && projects[0]) await selectProject(projects[0].id);
}

async function selectProject(id) {
  selectedProject = await api(`/api/projects/${id}`);
  currentCodexThreadId = null;
  clearTimeout(pollTimer);
  pollTimer = null;
  el('projectTitle').textContent = selectedProject.name;
  el('jobStatus').textContent = '待機中';
  el('videoOrientation').value = 'landscape';
  el('player').innerHTML = '<div class="empty">完成したMP4がここに表示されます</div>';
  el('artifacts').innerHTML = '';
  await Promise.all([loadMessages(), loadFiles(), loadJobs(), loadArtifacts(), loadCodex(), loadCodexThreads()]);
  await loadProjects();
}

async function loadMessages() {
  const messages = await api(`/api/projects/${selectedProject.id}/messages`);
  el('messages').innerHTML = messages.map((m) => `<div class="message ${m.role}"><span>${m.role === 'user' ? 'あなた' : 'アシスタント'}</span><p>${escapeHtml(m.content)}</p></div>`).join('');
  el('messages').scrollTop = el('messages').scrollHeight;
}

async function loadFiles() {
  const files = await api(`/api/projects/${selectedProject.id}/files`);
  const controlNames = new Set(['brief.md', 'scene_plan.md', 'image_prompts.md', 'narration_segments.tsv', 'license_and_tools_note.txt']);
  const visibleFiles = files.filter((file) => {
    const path = file.path.replaceAll('\\', '/');
    const name = path.split('/').pop();
    return !path.startsWith('worktree/') && !path.startsWith('versions/') && !controlNames.has(name);
  });
  const audioFiles = visibleFiles.filter((f) => /\.(wav|mp3|m4a|mp4|webm)$/i.test(f.path));
  el('files').innerHTML = (visibleFiles.map((f) => `<span class="attachment">${escapeHtml(f.path)}</span>`).join('') || '<span class="muted">添付素材はありません。画像・音声・動画を「添付」から追加してください。</span>') +
    (audioFiles.length ? `<div class="quick transcribe-actions"><span>音声を文字起こし:</span>${audioFiles.map((f) => `<button class="quick-action" data-transcribe="${escapeHtml(f.path)}">${escapeHtml(f.path.split(/[\\/]/).pop())}</button>`).join('')}</div>` : '');
  document.querySelectorAll('[data-transcribe]').forEach((button) => {
    button.onclick = async () => {
      button.disabled = true;
      button.textContent = '処理中…';
      try {
        const relative = button.dataset.transcribe.split(/[\\/]/).map(encodeURIComponent).join('/');
        const result = await api(`/api/projects/${selectedProject.id}/transcribe/${relative}?timestamps=true`, { method: 'POST' });
        const preview = result.text.length > 240 ? `${result.text.slice(0, 240)}…` : result.text;
        button.textContent = '完了';
        button.title = `${result.model}: ${preview}`;
      } catch (error) {
        button.disabled = false;
        button.textContent = '再試行';
        button.title = error.message;
      }
    };
  });
}

async function loadJobs() {
  const list = await api(`/api/projects/${selectedProject.id}/jobs`);
  const latest = list[0];
  if (!latest) {
    el('jobStatus').textContent = '待機中';
  } else if (latest.status === 'failed') {
    el('jobStatus').textContent = `${latest.message}（${latest.progress}%地点）`;
  } else if (latest.status === 'cancelled') {
    el('jobStatus').textContent = latest.message;
  } else {
    el('jobStatus').textContent = `${latest.message} (${latest.progress}%)`;
  }
  if (latest && ['succeeded', 'failed', 'cancelled'].includes(latest.status)) {
    el('render').disabled = false;
    el('render').textContent = '▶ 動画を生成';
    await loadMessages();
  }
  if (latest && ['queued', 'running'].includes(latest.status)) {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(loadJobs, 1500);
  }
}

async function loadArtifacts() {
  const list = await api(`/api/projects/${selectedProject.id}/artifacts`);
  el('artifacts').innerHTML = list.map((a) => `<div class="artifact"><span>${escapeHtml(a.name)}</span><a href="/api/projects/${selectedProject.id}/download/${a.path.split('/').map(encodeURIComponent).join('/')}">ダウンロード</a></div>`).join('');
  const video = list.find((a) => a.kind === 'mp4');
  if (video) el('player').innerHTML = `<video controls src="/api/projects/${selectedProject.id}/download/${video.path.split('/').map(encodeURIComponent).join('/')}"></video>`;
}

async function sendMessage(content) {
  if (!selectedProject || !content.trim() || messageSending) return;
  messageSending = true;
  const messages = el('messages');
  const pendingId = `agent-activity-${Date.now()}`;
  messages.insertAdjacentHTML('beforeend', `<div class="message user pending"><span>あなた</span><p>${escapeHtml(content)}</p></div>`);
  messages.insertAdjacentHTML('beforeend', `<div class="message assistant" id="${pendingId}"><span>アシスタント</span><p class="agent-activity"><span class="agent-spinner" aria-hidden="true"></span>処理中…</p></div>`);
  messages.scrollTop = messages.scrollHeight;
  try {
    setText('jobStatus', 'Codexに送信中…');
    await api(`/api/projects/${selectedProject.id}/messages`, { method: 'POST', body: JSON.stringify({ content }) });
    await loadMessages();
  } catch (error) {
    const messages = el('messages');
    messages.insertAdjacentHTML('beforeend', `<div class="message assistant"><span>アシスタント</span><p>処理に失敗しました: ${escapeHtml(error.message)}</p></div>`);
    messages.scrollTop = messages.scrollHeight;
    throw error;
  } finally {
    el(pendingId)?.remove();
    messageSending = false;
  }
}

async function inspectSettings() {
  const info = await api(`/api/projects/${selectedProject.id}/settings`);
  el('videoOrientation').value = info.orientation || 'landscape';
  const orientation = info.orientation === 'portrait' ? '縦型ショート' : '横型標準';
  const text = `現在の設定: ${orientation} / 字幕${info.subtitle_font_size}px / 台本${info.narration_segments}区間 / 画像${info.images}点 / 音声${info.audio}点 / VOICEVOX ${info.voicevox_url} / 話者${info.voicevox_speaker} / 速度${info.voicevox_speed}`;
  el('messages').insertAdjacentHTML('beforeend', `<div class="message assistant"><span>アシスタント</span><p>${escapeHtml(text)}</p></div>`);
  el('messages').scrollTop = el('messages').scrollHeight;
}

async function loadCodex() {
  try {
    const info = await api('/api/codex/account');
    el('codexStatus').textContent = info.account ? `Codex: ${info.account.type || '接続済み'}` : 'Codex未接続';
    el('codexLogin').textContent = info.account ? 'Codexログイン済み' : 'Codexにログイン';
    el('codexLogin').disabled = Boolean(info.account);
    el('codexStatus').title = info.account ? `認証: ${info.account.type || 'unknown'}${info.account.planType ? ` / ${info.account.planType}` : ''}` : (info.error || '未接続');
  } catch (error) {
    el('codexStatus').textContent = 'Codex接続エラー';
    el('codexStatus').title = error.message;
  }
}

async function loadCodexThreads() {
  if (!selectedProject) return;
  const threads = await api(`/api/projects/${selectedProject.id}/codex/threads`);
  if (threads.length && !currentCodexThreadId) currentCodexThreadId = threads[0].thread_id;
}

el('newProject').onclick = async () => {
  const name = prompt('案件名');
  if (!name) return;
  const project = await api('/api/projects', { method: 'POST', body: JSON.stringify({ name }) });
  await selectProject(project.id);
};

el('chatForm').onsubmit = async (event) => {
  event.preventDefault();
  const input = el('message');
  const content = input.value;
  input.value = '';
  const submit = event.submitter || el('chatForm').querySelector('button');
  if (submit) submit.disabled = true;
  try { await sendMessage(content); } catch (error) { if (submit) submit.title = error.message; } finally { if (submit) submit.disabled = false; }
};

document.querySelectorAll('.quick button').forEach((button) => {
  button.onclick = async () => {
    if (messageSending) return;
    button.disabled = true;
    try {
      if (button.dataset.message === '現在の台本と設定を確認して') {
        await inspectSettings();
      } else {
        await sendMessage(button.dataset.message);
        await loadFiles();
      }
    } catch (error) {
      button.title = error.message;
    } finally {
      button.disabled = false;
    }
  };
});

el('upload').onchange = async (event) => {
  if (!selectedProject) return;
  for (const file of event.target.files) {
    const form = new FormData();
    form.append('file', file);
    await fetch(`/api/projects/${selectedProject.id}/uploads`, { method: 'POST', body: form });
  }
  event.target.value = '';
  await loadFiles();
};

el('render').onclick = async () => {
  if (!selectedProject) return;
  await sendMessage('この台本で動画を生成して');
  el('render').disabled = true;
  el('render').textContent = '受付済み…';
  el('jobStatus').textContent = '動画生成を受け付けました。処理中…';
  await loadJobs();
};

el('videoOrientation').onchange = async () => {
  if (!selectedProject) return;
  const select = el('videoOrientation');
  select.disabled = true;
  try {
    await api(`/api/projects/${selectedProject.id}/orientation`, { method: 'POST', body: JSON.stringify({ orientation: select.value }) });
    await loadMessages();
  } catch (error) {
    select.title = error.message;
  } finally {
    select.disabled = false;
  }
};

el('codexLogin').onclick = async () => {
  const result = await api('/api/codex/login', { method: 'POST' });
  if (result.authUrl) window.open(result.authUrl, '_blank');
  await loadCodex();
};

loadProjects().catch((error) => { setText('projectTitle', `起動エラー: ${error.message}`); });
