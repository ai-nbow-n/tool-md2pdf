/* Translate interface chrome only; document and conversation content stay intact. */
(() => {
  const strings = {
    'Language': ['Sprache', 'Idioma'],
    'Hide panel': ['Panel ausblenden', 'Ocultar panel'],
    'Toggle panel': ['Panel einblenden', 'Mostrar panel'],
    '-- no files --': ['-- keine Dateien --', '-- sin archivos --'],
    'Save': ['Speichern', 'Guardar'],
    'Compile': ['Kompilieren', 'Compilar'],
    '▶ Compile': ['▶ Kompilieren', '▶ Compilar'],
    'Ready': ['Bereit', 'Listo'],
    'Configuration': ['Konfiguration', 'Configuración'],
    'Input directory': ['Eingabeverzeichnis', 'Carpeta de entrada'],
    'Output directory': ['Ausgabeverzeichnis', 'Carpeta de salida'],
    'Page size': ['Seitengröße', 'Tamaño de página'],
    'Font style': ['Schriftart', 'Tipo de letra'],
    'Font size': ['Schriftgröße', 'Tamaño de letra'],
    'Default': ['Standard', 'Predeterminado'],
    'Style': ['Stil', 'Estilo'],
    'Article': ['Artikel', 'Artículo'],
    'Plain': ['Einfach', 'Simple'],
    'Auto-save on change': ['Änderungen automatisch speichern', 'Guardar cambios automáticamente'],
    '(2 s debounce)': ['(nach 2 s Pause)', '(tras 2 s de pausa)'],
    'API connection': ['API-Verbindung', 'Conexión API'],
    'Model': ['Modell', 'Modelo'],
    'API key': ['API-Schlüssel', 'Clave API'],
    'Paste your OpenAI API key': ['OpenAI-API-Schlüssel einfügen', 'Pega tu clave API de OpenAI'],
    'Choose a model, then connect. You can switch anytime for the next message.': ['Modell wählen und verbinden. Für die nächste Nachricht kannst du jederzeit wechseln.', 'Elige un modelo y conecta. Puedes cambiarlo para el siguiente mensaje.'],
    'Your key is cleared on reload. Chat includes the open Markdown, including unsaved changes. Requested edits are saved to that file.': ['Dein Schlüssel wird beim Neuladen gelöscht. Der Chat enthält das geöffnete Markdown inklusive ungespeicherter Änderungen. Angeforderte Änderungen werden in dieser Datei gespeichert.', 'Tu clave se borra al recargar. El chat incluye el Markdown abierto y los cambios sin guardar. Las modificaciones solicitadas se guardan en ese archivo.'],
    'Connect': ['Verbinden', 'Conectar'],
    'Disconnect': ['Trennen', 'Desconectar'],
    'Not connected': ['Nicht verbunden', 'Sin conexión'],
    'Editor': ['Editor', 'Editor'],
    'PDF Preview': ['PDF-Vorschau', 'Vista previa del PDF'],
    'Compile to see preview': ['Für die Vorschau kompilieren', 'Compila para ver la vista previa'],
    'Open chat': ['Chat öffnen', 'Abrir chat'],
    'Close chat': ['Chat schließen', 'Cerrar chat'],
    'New chat': ['Neuer Chat', 'Nuevo chat'],
    'Conversation': ['Unterhaltung', 'Conversación'],
    'Chat message': ['Chatnachricht', 'Mensaje de chat'],
    'Message…': ['Nachricht…', 'Mensaje…'],
    'Send': ['Senden', 'Enviar'],
    'Wait…': ['Warten…', 'Espera…'],
    'Connect your API in settings, choose a model, and say hello.': ['Verbinde deine API in den Einstellungen, wähle ein Modell und sag Hallo.', 'Conecta tu API en los ajustes, elige un modelo y saluda.'],
    'Connect your API in settings to start chatting.': ['Verbinde deine API in den Einstellungen, um zu chatten.', 'Conecta tu API en los ajustes para empezar a chatear.'],
    'Connect your API in settings.': ['Verbinde deine API in den Einstellungen.', 'Conecta tu API en los ajustes.'],
    'Enter your API key and click Connect.': ['API-Schlüssel eingeben und auf Verbinden klicken.', 'Introduce tu clave API y pulsa Conectar.'],
    'Enter your API key first.': ['Gib zuerst deinen API-Schlüssel ein.', 'Introduce primero tu clave API.'],
    'Connecting and loading models…': ['Verbindung wird hergestellt und Modelle werden geladen…', 'Conectando y cargando modelos…'],
    'Open a Markdown file to start chatting.': ['Öffne eine Markdown-Datei, um zu chatten.', 'Abre un archivo Markdown para empezar a chatear.'],
    'Start a new chat to continue.': ['Starte einen neuen Chat, um fortzufahren.', 'Inicia un nuevo chat para continuar.'],
    'Saving line edits…': ['Änderungen werden gespeichert…', 'Guardando modificaciones…'],
    'Saved': ['Gespeichert', 'Guardado'],
    'Save failed': ['Speichern fehlgeschlagen', 'Error al guardar'],
    'Compiling...': ['Kompilierung läuft...', 'Compilando...'],
    'Compiled OK': ['Erfolgreich kompiliert', 'Compilado correctamente'],
    'Chat edits saved — compile to update PDF': ['Chat-Änderungen gespeichert — zum Aktualisieren des PDFs kompilieren', 'Cambios del chat guardados — compila para actualizar el PDF'],
  };
  const prefixes = {
    'Connected · ': ['Verbunden · ', 'Conectado · '],
    'Context loaded · ': ['Kontext geladen · ', 'Contexto cargado · '],
    'Ready · ': ['Bereit · ', 'Listo · '],
    'Thinking · ': ['Denkt nach · ', 'Pensando · '],
    'Still working · ': ['In Bearbeitung · ', 'Procesando · '],
    'Line edits saved · ': ['Änderungen gespeichert · ', 'Modificaciones guardadas · '],
    'Failed to load ': ['Laden fehlgeschlagen: ', 'Error al cargar '],
    'Error -- ': ['Fehler -- ', 'Error -- '],
  };
  const selector = document.getElementById('language-select');
  let language = 'en';
  try { language = localStorage.getItem('md2pdf-language') || 'en'; } catch (_) { /* Storage may be unavailable. */ }
  if (!['en', 'de', 'es'].includes(language)) language = 'en';
  const originals = new WeakMap();
  function translate(text) {
    if (language === 'en') return text;
    const index = language === 'de' ? 0 : 1;
    const key = text.trim();
    if (strings[key]) return text.replace(key, strings[key][index]);
    for (const [prefix, values] of Object.entries(prefixes)) {
      if (text.startsWith(prefix)) return values[index] + text.slice(prefix.length);
    }
    return text;
  }
  function update(node, key, read, write) {
    const records = originals.get(node) || {};
    const value = read();
    if (!records[key] || value !== records[key].rendered) records[key] = {source: value};
    const rendered = translate(records[key].source);
    records[key].rendered = rendered;
    originals.set(node, records);
    if (value !== rendered) write(rendered);
  }
  const roots = ['panel', 'fab', 'pdf-ph', 'chat-bubble', 'chat-head', 'chat-status', 'chat-form', 'chat-empty'];
  function render() {
    observer.disconnect();
    document.documentElement.lang = language;
    selector.value = language;
    const targets = roots.map(id => document.getElementById(id)).filter(Boolean);
    targets.push(...document.querySelectorAll('.pane-bar'));
    for (const root of targets) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if (node.parentElement.closest('input, textarea, #language-select, #api-model, #file-select option[value]:not([value=""])')) continue;
        update(node, 'text', () => node.nodeValue, value => { node.nodeValue = value; });
      }
      for (const element of [root, ...root.querySelectorAll('[title], [aria-label], [placeholder]')]) {
        for (const attribute of ['title', 'aria-label', 'placeholder']) {
          if (element.hasAttribute(attribute)) update(element, attribute, () => element.getAttribute(attribute), value => element.setAttribute(attribute, value));
        }
      }
      observer.observe(root, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['title', 'aria-label', 'placeholder']});
    }
  }
  const observer = new MutationObserver(render);
  selector.addEventListener('change', () => {
    language = selector.value;
    try { localStorage.setItem('md2pdf-language', language); } catch (_) { /* Keep the selection for this session. */ }
    render();
  });
  render();
})();
