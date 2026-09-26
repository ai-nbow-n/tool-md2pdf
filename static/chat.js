/* Chat with the editing assistant on nbow.io's own server. There is no API key
   and no model choice: the server runs one model. History lives only in this
   tab's memory. */
(() => {
  const el = id => document.getElementById(id);
  let available = false, busy = false, model = '', maxChars = 0, history = [], controller = null, revision = 0;
  const snapshot = () => window.markdownChat?.snapshot();

  function status(id, message, state = '') {
    el(id).textContent = message;
    el(id).dataset.state = state;
  }
  function tooLong() {
    const current = snapshot();
    // Code points, as the server counts them (not UTF-16 units).
    return Boolean(current && maxChars && [...current.content].length > maxChars);
  }
  function controls() {
    el('chat-new').disabled = busy;
    el('chat-input').disabled = busy || !available || !snapshot();
    el('chat-send').disabled = busy || !available || !snapshot();
    el('chat-send').textContent = busy ? 'Wait…' : 'Send';
  }
  function readyText() {
    if (!available) return 'The assistant is not available right now.';
    if (!snapshot()) return 'Open a Markdown file to start chatting.';
    if (tooLong()) return 'This document is too long for the assistant. Shorten it, or ask about a shorter document.';
    return 'Ready · ' + model;
  }
  function clearChat() {
    history = [];
    el('chat-messages').replaceChildren();
    el('chat-input').value = '';
  }
  // `shared` requests (chat, apply) are cancelled when the file changes; the
  // status check has its own controller so a file load cannot abort it.
  async function api(path, body, onProgress = null, shared = true) {
    const requestController = new AbortController();
    if (shared) controller = requestController;
    const timeout = Number(el('chat-window').dataset[path === 'chat' ? 'chatTimeout' : 'connectionTimeout']);
    const started = Date.now();
    const timer = setTimeout(() => requestController.abort(), timeout);
    const progressTimer = onProgress ? setInterval(() => onProgress(Math.floor((Date.now() - started) / 1000)), 1000) : null;
    try {
      const response = await fetch(window.md2pdfUrl('/api/llm/' + path), {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body), signal: requestController.signal,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Request failed. Check that the app is running.');
      return data;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('Request timed out or was cancelled. Please try again.');
      if (error instanceof TypeError) throw new Error('Cannot reach the app. Check your connection and try again.');
      throw error;
    } finally {
      clearTimeout(timer);
      if (progressTimer) clearInterval(progressTimer);
      if (controller === requestController) controller = null;
    }
  }
  async function checkAssistant() {
    status('api-status', 'Checking the assistant…');
    try {
      const data = await api('status', {}, null, false);
      model = typeof data.model === 'string' ? data.model : '';
      maxChars = Number(data.max_document_chars) || 0;
      available = data.available === true && Boolean(model);
    } catch (_) {
      available = false;
    }
    el('chat-title').textContent = model ? 'Chat · ' + model : 'Chat';
    if (maxChars) el('assistant-limit').textContent = 'Assistant document limit (characters): ' + maxChars;
    status('api-status', available ? 'Ready · ' + model : 'The assistant is not available right now.', available ? 'ok' : 'error');
    if (!busy) status('chat-status', readyText(), available && !tooLong() ? '' : 'error');
    controls();
  }
  function addMessage(role, text) {
    el('chat-empty')?.remove();
    const message = document.createElement('div');
    message.className = 'chat-message ' + role;
    const label = document.createElement('strong');
    label.textContent = role === 'user' ? 'You' : 'Assistant · ' + model;
    const content = document.createElement('span');
    content.textContent = text; // Never execute HTML returned by a model.
    message.append(label, content);
    el('chat-messages').append(message);
    el('chat-messages').scrollTop = el('chat-messages').scrollHeight;
    return message;
  }
  function showChat(open) {
    el('chat-window').hidden = !open;
    el('chat-bubble').setAttribute('aria-expanded', String(open));
    el('chat-bubble').setAttribute('aria-label', open ? 'Close chat' : 'Open chat');
    if (open && !available && !busy) checkAssistant();
    if (open) (available ? el('chat-input') : el('chat-close')).focus();
    else el('chat-bubble').focus();
  }

  el('chat-bubble').addEventListener('click', () => showChat(el('chat-window').hidden));
  el('chat-close').addEventListener('click', () => showChat(false));
  el('chat-window').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); showChat(false); }
    event.stopPropagation();
  });
  window.addEventListener('markdown-file-changed', () => {
    revision++;
    if (controller) controller.abort();
    busy = false;
    clearChat();
    status('chat-status', available && snapshot() && !tooLong() ? 'Context loaded · ' + snapshot().filename : readyText(),
      !available || tooLong() ? 'error' : '');
    controls();
  });
  el('chat-new').addEventListener('click', () => {
    clearChat();
    status('chat-status', readyText(), available && !tooLong() ? '' : 'error');
  });

  el('chat-form').addEventListener('submit', async event => {
    event.preventDefault();
    const text = el('chat-input').value.trim();
    if (!text || busy || !available || !snapshot()) return;
    if (history.length >= 100) {
      status('chat-status', 'Start a new chat to continue.', 'error');
      return;
    }
    if (tooLong()) {
      status('chat-status', readyText(), 'error');
      return;
    }
    const currentRevision = revision;
    const messages = [...history, {role: 'user', content: text}];
    const pending = addMessage('user', text);
    el('chat-input').value = '';
    busy = true;
    controls();
    status('chat-status', 'Thinking · ' + model);
    try {
      await window.markdownChat.settle();
      if (revision !== currentRevision) return;
      const documentSnapshot = snapshot();
      const data = await api('chat', {messages, document: documentSnapshot}, seconds => {
        if (revision !== currentRevision) return;
        status('chat-status', (seconds >= 30 ? 'Still working' : 'Thinking') + ' · ' + model + ' · ' + seconds + 's');
      });
      if (revision !== currentRevision) return;
      if (typeof data.reply !== 'string' || !data.reply.trim()) throw new Error('The assistant returned no answer. Please rephrase your message.');
      if (!Array.isArray(data.edits)) throw new Error('Invalid edit response. Nothing was changed.');
      if (data.edits.length) {
        await window.markdownChat.settle();
        if (revision !== currentRevision) return;
        if (JSON.stringify(snapshot()) !== JSON.stringify(documentSnapshot)) {
          throw new Error('The Markdown changed while the assistant was replying. Edits were not applied; send your request again.');
        }
        window.markdownChat.lock(true);
        status('chat-status', 'Saving line edits…');
        try {
          const saved = await api('apply', {document: documentSnapshot, disk_revision: data.disk_revision, edits: data.edits});
          window.markdownChat.updated(saved);
        } finally {
          window.markdownChat.lock(false);
        }
      }
      history = [...messages, {role: 'assistant', content: data.reply}];
      addMessage('assistant', data.reply);
      status('chat-status', data.edits.length ? 'Line edits saved · ' + model + ' · ' + documentSnapshot.filename : readyText());
    } catch (error) {
      if (revision !== currentRevision) return;
      pending.remove();
      el('chat-input').value = text;
      status('chat-status', error.message, 'error');
    } finally {
      if (revision === currentRevision) {
        busy = false;
        controls();
        if (!el('chat-window').hidden) el('chat-input').focus();
      }
    }
  });
  el('chat-input').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      el('chat-form').requestSubmit();
    }
  });
  controls();
  checkAssistant();
})();
