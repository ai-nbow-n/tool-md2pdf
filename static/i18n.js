/* Translate interface chrome only; document and conversation content stay intact. */
(() => {
  const strings = {
    'Legal notice (Impressum)': ['Impressum', 'Aviso legal (Impressum)'],
    'Privacy policy': ['Datenschutzerklärung', 'Política de privacidad'],
    'Data transparency': ['Datentransparenz', 'Transparencia de datos'],
    'This editor sets one strictly necessary cookie,': ['Dieser Editor setzt ein unbedingt erforderliches Cookie,', 'Este editor instala una cookie estrictamente necesaria,'],
    ', which keeps your private workspace for 24 hours after your last activity, and this browser keeps two settings of yours: the language and that you have read this notice. No analytics, no cookies from other companies, nothing sent elsewhere.': [
      ', das Ihren privaten Arbeitsbereich 24 Stunden nach Ihrer letzten Aktivität behält; außerdem merkt sich dieser Browser zwei Einstellungen von Ihnen: die Sprache und dass Sie diesen Hinweis gelesen haben. Keine Analyse, keine Cookies anderer Unternehmen, nichts wird anderswohin gesendet.',
      ', que conserva su espacio de trabajo privado durante 24 horas desde su última actividad; además, este navegador guarda dos ajustes suyos: el idioma y que ha leído este aviso. Sin analítica, sin cookies de otras empresas, nada se envía a otro lugar.'],
    'Understood': ['Verstanden', 'Entendido'],
    'Licence: Apache 2.0 · notices': ['Lizenz: Apache 2.0 · Hinweise', 'Licencia: Apache 2.0 · avisos'],
    'New': ['Neu', 'Nuevo'],
    'Open Markdown': ['Markdown öffnen', 'Abrir Markdown'],
    'Download Markdown': ['Markdown herunterladen', 'Descargar Markdown'],
    'Download PDF': ['PDF herunterladen', 'Descargar PDF'],
    'Files are processed on this server in your temporary workspace and expire after 24 hours of inactivity. Download your work to keep it.': ['Dateien werden auf diesem Server in Ihrem temporären Arbeitsbereich verarbeitet und verfallen nach 24 Stunden Inaktivität. Laden Sie Ihre Arbeit herunter, um sie zu behalten.', 'Los archivos se procesan en este servidor en su espacio temporal y caducan tras 24 horas de inactividad. Descargue su trabajo para conservarlo.'],
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
    "Assistant": ["Assistent", "Asistente"],
    "Checking the assistant…": ["Assistent wird geprüft…", "Comprobando el asistente…"],
    "The assistant runs on this site's own server. No API key is needed, and your text is not sent to any other company.": ["Der Assistent läuft auf dem eigenen Server dieser Website. Ein API-Schlüssel ist nicht nötig, und Ihr Text wird an kein anderes Unternehmen gesendet.", "El asistente se ejecuta en el propio servidor de este sitio. No necesita clave API y su texto no se envía a ninguna otra empresa."],
    "The assistant runs on the Ollama server this app is configured to use. No API key is needed.": ["Der Assistent läuft auf dem Ollama-Server, den diese App verwendet. Ein API-Schlüssel ist nicht nötig.", "El asistente se ejecuta en el servidor Ollama que usa esta aplicación. No necesita clave API."],
    "Chat includes the open Markdown, including unsaved changes. Replies can take one to three minutes. Requested edits are saved to that file.": ["Der Chat enthält das geöffnete Markdown einschließlich ungespeicherter Änderungen. Antworten können ein bis drei Minuten dauern. Angeforderte Änderungen werden in dieser Datei gespeichert.", "El chat incluye el Markdown abierto, con los cambios sin guardar. Las respuestas pueden tardar de uno a tres minutos. Las modificaciones solicitadas se guardan en ese archivo."],
    "Ask about the open Markdown, or ask the assistant to edit it.": ["Fragen Sie zum geöffneten Markdown oder lassen Sie es vom Assistenten bearbeiten.", "Pregunte sobre el Markdown abierto o pida al asistente que lo edite."],
    "The assistant is not available right now.": ["Der Assistent ist gerade nicht verfügbar.", "El asistente no está disponible en este momento."],
    "The assistant is not available right now. Please try again later.": ["Der Assistent ist gerade nicht verfügbar. Bitte versuchen Sie es später erneut.", "El asistente no está disponible en este momento. Vuelva a intentarlo más tarde."],
    "This document is too long for the assistant. Shorten it, or ask about a shorter document.": ["Dieses Dokument ist für den Assistenten zu lang. Kürzen Sie es oder fragen Sie zu einem kürzeren Dokument.", "Este documento es demasiado largo para el asistente. Acórtelo o pregunte sobre un documento más corto."],
    "This conversation is too long for the assistant. Start a new chat.": ["Diese Unterhaltung ist für den Assistenten zu lang. Starten Sie einen neuen Chat.", "Esta conversación es demasiado larga para el asistente. Inicie un nuevo chat."],
    "The assistant is answering another request. Try again in a minute.": ["Der Assistent beantwortet gerade eine andere Anfrage. Versuchen Sie es in einer Minute erneut.", "El asistente está respondiendo otra solicitud. Vuelva a intentarlo en un minuto."],
    "The assistant returned edits that do not match the document. Nothing was changed; please rephrase and try again.": ["Der Assistent hat Änderungen geliefert, die nicht zum Dokument passen. Es wurde nichts geändert; bitte formulieren Sie die Anfrage neu.", "El asistente devolvió modificaciones que no coinciden con el documento. No se cambió nada; reformule la solicitud e inténtelo de nuevo."],
    "The assistant returned no answer. Please rephrase your message.": ["Der Assistent hat keine Antwort geliefert. Bitte formulieren Sie Ihre Nachricht neu.", "El asistente no devolvió ninguna respuesta. Reformule su mensaje."],
    "The assistant's model is not installed on this server.": ["Das Modell des Assistenten ist auf diesem Server nicht installiert.", "El modelo del asistente no está instalado en este servidor."],
    "The assistant could not answer. Please try again.": ["Der Assistent konnte nicht antworten. Bitte versuchen Sie es erneut.", "El asistente no pudo responder. Vuelva a intentarlo."],
    "The assistant did not finish within 180 seconds. Nothing was changed. Try a shorter request.": ["Der Assistent ist nicht innerhalb von 180 Sekunden fertig geworden. Es wurde nichts geändert. Versuchen Sie eine kürzere Anfrage.", "El asistente no terminó en 180 segundos. No se cambió nada. Pruebe con una solicitud más corta."],
    "Your message is too long for the assistant. Shorten it.": ["Ihre Nachricht ist für den Assistenten zu lang. Bitte kürzen Sie sie.", "Su mensaje es demasiado largo para el asistente. Acórtelo."],
    "This change is too large for the assistant. Ask for a smaller part of it, or edit the document directly.": ["Diese Änderung ist für den Assistenten zu umfangreich. Bitten Sie um einen kleineren Teil oder bearbeiten Sie das Dokument direkt.", "Este cambio es demasiado grande para el asistente. Pida una parte más pequeña o edite el documento directamente."],
    "Your connection has used this hour's assistant time. Try again later.": ["Ihre Verbindung hat die Assistentenzeit dieser Stunde aufgebraucht. Versuchen Sie es später erneut.", "Su conexión ha agotado el tiempo de asistente de esta hora. Vuelva a intentarlo más tarde."],
    "Request timed out or was cancelled. Please try again.": ["Die Anfrage ist abgelaufen oder wurde abgebrochen. Bitte versuchen Sie es erneut.", "La solicitud caducó o se canceló. Vuelva a intentarlo."],
    "Cannot reach the app. Check your connection and try again.": ["Die App ist nicht erreichbar. Prüfen Sie Ihre Verbindung und versuchen Sie es erneut.", "No se puede acceder a la aplicación. Compruebe su conexión y vuelva a intentarlo."],
    "Request failed. Check that the app is running.": ["Die Anfrage ist fehlgeschlagen. Prüfen Sie, ob die App läuft.", "La solicitud falló. Compruebe que la aplicación esté en marcha."],
    "Invalid edit response. Nothing was changed.": ["Ungültige Antwort mit Änderungen. Es wurde nichts geändert.", "Respuesta de modificación no válida. No se cambió nada."],
    "The Markdown changed while the assistant was replying. Edits were not applied; send your request again.": ["Das Markdown hat sich geändert, während der Assistent geantwortet hat. Die Änderungen wurden nicht übernommen; senden Sie Ihre Anfrage erneut.", "El Markdown cambió mientras el asistente respondía. No se aplicaron las modificaciones; envíe su solicitud de nuevo."],
    "The file changed on disk. Reload it before continuing the chat.": ["Die Datei wurde auf dem Datenträger geändert. Laden Sie sie neu, bevor Sie den Chat fortsetzen.", "El archivo cambió en el disco. Vuelva a cargarlo antes de continuar el chat."],
    "Send 1–100 messages, or start a new chat.": ["Senden Sie 1–100 Nachrichten oder starten Sie einen neuen Chat.", "Envíe entre 1 y 100 mensajes o inicie un nuevo chat."],
    "Conversation is too large. Start a new chat.": ["Die Unterhaltung ist zu groß. Starten Sie einen neuen Chat.", "La conversación es demasiado grande. Inicie un nuevo chat."],
    'Open a Markdown file to start chatting.': ['Öffne eine Markdown-Datei, um zu chatten.', 'Abre un archivo Markdown para empezar a chatear.'],
    'Start a new chat to continue.': ['Starte einen neuen Chat, um fortzufahren.', 'Inicia un nuevo chat para continuar.'],
    'Saving line edits…': ['Änderungen werden gespeichert…', 'Guardando modificaciones…'],
    'Saved': ['Gespeichert', 'Guardado'],
    'Save failed': ['Speichern fehlgeschlagen', 'Error al guardar'],
    'Compiling...': ['Kompilierung läuft...', 'Compilando...'],
    'Compiled OK': ['Erfolgreich kompiliert', 'Compilado correctamente'],
    'Chat edits saved — compile to update PDF': ['Chat-Änderungen gespeichert — zum Aktualisieren des PDFs kompilieren', 'Cambios del chat guardados — compila para actualizar el PDF'],
    'Close': ['Schließen', 'Cerrar'],
  };
  const prefixes = {
    "Assistant document limit (characters): ": ["Dokumentlimit des Assistenten (Zeichen): ", "Límite de documento del asistente (caracteres): "],
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
  const routeLanguage = location.pathname.split('/')[1];
  if (document.body.dataset.hosted === 'true' && ['en', 'de', 'es'].includes(routeLanguage)) language = routeLanguage;
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
  const roots = ['panel', 'fab', 'pdf-ph', 'chat-bubble', 'chat-head', 'chat-status', 'chat-form', 'chat-empty', 'storage-notice'];
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
        if (node.parentElement.closest('input, textarea, #language-select, #file-select option[value]:not([value=""])')) continue;
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
