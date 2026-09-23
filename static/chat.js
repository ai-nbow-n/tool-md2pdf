/* Credentials and history live only in this tab's memory. */
(() => {
  const el = id => document.getElementById(id);
  let connected = false, busy = false, loadingModels = false, activeModel = null, history = [], controller = null, revision = 0;
  const catalog = [...el('api-model').options].map(option => option.value);
  const selectedModel = () => el('api-model').value;
  function modelStatus() {
    status('api-status', connected ? 'Connected · ' + selectedModel() : 'Not connected', connected ? 'ok' : '');
    el('chat-title').textContent = 'Chat · ' + selectedModel();
  }
  function populateModels(models, preferred) {
    el('api-model').replaceChildren(...models.map(name => new Option(name, name)));
    el('api-model').value = models.includes(preferred) ? preferred : models[0];
  }
  const credentials = () => ({api_key: el('api-key').value.trim()});
  const snapshot = () => window.markdownChat?.snapshot();

  function status(id, message, state = '') {
    el(id).textContent = message;
    el(id).dataset.state = state;
  }
  function controls() {
    ['api-key', 'api-connect', 'chat-new'].forEach(id => el(id).disabled = busy);
    el('api-model').disabled = loadingModels;
    el('chat-input').disabled = busy || !connected || !snapshot();
    el('chat-send').disabled = busy || !connected || !el('api-model').value || !snapshot();
    el('chat-send').textContent = busy ? 'Wait…' : 'Send';
  }
  function clearChat() {
    history = [];
    el('chat-messages').replaceChildren();
    el('chat-input').value = '';
  }
  function reset(clearKey = false) {
    revision++;
    if (controller) controller.abort();
    connected = false;
    busy = false;
    loadingModels = false;
    activeModel = null;
    if (clearKey) el('api-key').value = '';
    populateModels(catalog, selectedModel());
    clearChat();
    modelStatus();
    status('chat-status', 'Connect your API in settings to start chatting.');
    controls();
  }
  async function api(path, body, onProgress = null) {
    controller = new AbortController();
    const requestController = controller;
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
  function addMessage(role, text, model = null) {
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
    if (open) (connected ? el('chat-input') : el('chat-close')).focus();
    else el('chat-bubble').focus();
  }

  el('chat-bubble').addEventListener('click', () => showChat(el('chat-window').hidden));
  el('chat-close').addEventListener('click', () => showChat(false));
  el('chat-window').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); showChat(false); }
    event.stopPropagation();
  });
  el('api-key').addEventListener('input', () => reset());
  window.addEventListener('markdown-file-changed', () => {
    revision++;
    if (controller) controller.abort();
    busy = false;
    loadingModels = false;
    activeModel = null;
    clearChat();
    status('chat-status', connected ? 'Context loaded · ' + snapshot()?.filename : 'Connect your API in settings.');
    controls();
  });
  el('api-disconnect').addEventListener('click', () => reset(true));
  el('api-model').addEventListener('change', () => {
    modelStatus();
    if (activeModel) status('chat-status', 'Replying with ' + activeModel + ' · next message: ' + selectedModel());
    else status('chat-status', connected ? 'Ready · ' + selectedModel() : 'Enter your API key and click Connect.');
    controls();
  });
  el('chat-new').addEventListener('click', () => {
    clearChat();
    status('chat-status', connected ? 'Ready · ' + el('api-model').value : 'Connect your API in settings.');
  });
  el('api-connect').addEventListener('click', async () => {
    if (busy) return;
    if (!credentials().api_key) {
      status('api-status', 'Enter your API key first.', 'error');
      el('api-key').focus();
      return;
    }
    reset();
    const currentRevision = revision;
    busy = true;
    loadingModels = true;
    controls();
    status('api-status', 'Connecting and loading models…');
    try {
      const data = await api('models', credentials());
      if (revision !== currentRevision) return;
      if (!Array.isArray(data.models) || !data.models.length) throw new Error('No models returned by the API.');
      const preferred = selectedModel();
      populateModels(data.models, preferred);
      connected = true;
      modelStatus();
      status('chat-status', preferred !== selectedModel() ? preferred + ' is unavailable; selected ' + selectedModel() :
        (snapshot() ? 'Context loaded · ' + snapshot().filename : 'Open a Markdown file to start chatting.'));
    } catch (error) {
      if (revision === currentRevision) status('api-status', error.message, 'error');
    } finally {
      if (revision === currentRevision) { busy = false; loadingModels = false; controls(); }
    }
  });

  el('chat-form').addEventListener('submit', async event => {
    event.preventDefault();
    const text = el('chat-input').value.trim();
    if (!text || busy || !connected || !snapshot()) return;
    if (history.length >= 100) {
      status('chat-status', 'Start a new chat to continue.', 'error');
      return;
    }
    const currentRevision = revision;
    const requestModel = selectedModel();
    activeModel = requestModel;
    const messages = [...history, {role: 'user', content: text}];
    const pending = addMessage('user', text);
    el('chat-input').value = '';
    busy = true;
    controls();
    status('chat-status', 'Thinking · ' + requestModel);
    try {
      await window.markdownChat.settle();
      if (revision !== currentRevision) return;
      const documentSnapshot = snapshot();
      const data = await api('chat', {...credentials(), model: requestModel, messages, document: documentSnapshot}, seconds => {
        if (revision !== currentRevision) return;
        const next = selectedModel() !== requestModel ? ' · next: ' + selectedModel() : '';
        status('chat-status', (seconds >= 30 ? 'Still working' : 'Thinking') + ' · ' + requestModel + ' · ' + seconds + 's' + next);
      });
      if (revision !== currentRevision) return;
      if (typeof data.reply !== 'string' || !data.reply.trim()) throw new Error('The API returned no text. Try another model.');
      if (!Array.isArray(data.edits)) throw new Error('Invalid edit response. Nothing was changed.');
      if (data.edits.length) {
        await window.markdownChat.settle();
        if (revision !== currentRevision) return;
        if (JSON.stringify(snapshot()) !== JSON.stringify(documentSnapshot)) {
          throw new Error('The Markdown changed while the assistant was replying. Edits were not applied; send your request again.');
        }
        window.markdownChat.lock(true);
        el('api-disconnect').disabled = true;
        status('chat-status', 'Saving line edits…');
        try {
          const saved = await api('apply', {document: documentSnapshot, disk_revision: data.disk_revision, edits: data.edits});
          window.markdownChat.updated(saved);
        } finally {
          window.markdownChat.lock(false);
          el('api-disconnect').disabled = false;
        }
      }
      history = [...messages, {role: 'assistant', content: data.reply}];
      addMessage('assistant', data.reply, requestModel);
      status('chat-status', data.edits.length ? 'Line edits saved · ' + requestModel + ' · ' + documentSnapshot.filename : 'Ready · ' + selectedModel());
    } catch (error) {
      if (revision !== currentRevision) return;
      pending.remove();
      el('chat-input').value = text;
      status('chat-status', error.message, 'error');
    } finally {
      if (revision === currentRevision) {
        busy = false;
        activeModel = null;
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
  modelStatus();
  controls();
})();
