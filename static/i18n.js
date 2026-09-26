/* Translate interface chrome only; document and conversation content stay intact. */
(() => {
  const strings = {
    'New': ['Neu', 'Nuevo'],
    'Open Markdown': ['Markdown öffnen', 'Abrir Markdown'],
    'Download Markdown': ['Markdown herunterladen', 'Descargar Markdown'],
    'Download PDF': ['PDF herunterladen', 'Descargar PDF'],
    'Files are processed on nbow.io in your temporary workspace and expire after 24 hours of inactivity. Download your work to keep it. Corpus sharing is optional.': ['Dateien werden auf nbow.io in Ihrem temporären Arbeitsbereich verarbeitet und verfallen nach 24 Stunden Inaktivität. Laden Sie Ihre Arbeit herunter, um sie zu behalten. Das Teilen mit dem Korpus ist freiwillig.', 'Los archivos se procesan en nbow.io en su espacio temporal y caducan tras 24 horas de inactividad. Descargue su trabajo para conservarlo. Compartir con el corpus es opcional.'],
    'Nothing is shared with the corpus until you confirm on nbow.io.': ['Es wird nichts mit dem Korpus geteilt, bis Sie auf nbow.io bestätigen.', 'No se comparte nada con el corpus hasta que confirme en nbow.io.'],
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
    "The assistant runs on nbow.io's own server. No API key is needed, and your text is not sent to any other company.": ["Der Assistent läuft auf dem eigenen Server von nbow.io. Ein API-Schlüssel ist nicht nötig, und Ihr Text wird an kein anderes Unternehmen gesendet.", "El asistente se ejecuta en el propio servidor de nbow.io. No necesita clave API y su texto no se envía a ninguna otra empresa."],
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
    'Share with nbow.io': ['Mit nbow.io teilen', 'Compartir con nbow.io'],
    'Share this Markdown with nbow.io?': ['Dieses Markdown mit nbow.io teilen?', '¿Compartir este Markdown con nbow.io?'],
    'Sharing with the research corpus is optional. Review the exact Markdown and confirm on nbow.io before it is submitted. Saving or compiling alone does not share it with the corpus.': ['Das Teilen mit dem Forschungskorpus ist freiwillig. Prüfen Sie den genauen Markdown-Text und bestätigen Sie auf nbow.io, bevor er eingereicht wird. Speichern oder Kompilieren allein teilt ihn nicht mit dem Korpus.', 'Compartir con el corpus de investigación es opcional. Revise el Markdown exacto y confirme en nbow.io antes de enviarlo. Guardar o compilar por sí solo no lo comparte con el corpus.'],
    'Not now': ['Jetzt nicht', 'Ahora no'],
    'Review and share': ['Prüfen und teilen', 'Revisar y compartir'],
    'Optional. Contribute this document to the public Markdown corpus for research into how technical documents are written.': ['Freiwillig. Steuern Sie dieses Dokument zum öffentlichen Markdown-Korpus bei, für die Forschung darüber, wie technische Dokumente geschrieben werden.', 'Opcional. Aporte este documento al corpus público de Markdown, para investigar cómo se escriben los documentos técnicos.'],
    'A window opens on nbow.io. It shows you the exact text, asks you to confirm twice, and only then sends it. The file name is never sent. Three documents per hour.': ['Es öffnet sich ein Fenster auf nbow.io. Es zeigt Ihnen den genauen Text, bittet zweimal um Bestätigung und sendet ihn erst dann. Der Dateiname wird nie gesendet. Drei Dokumente pro Stunde.', 'Se abre una ventana en nbow.io. Le muestra el texto exacto, le pide confirmar dos veces y solo entonces lo envía. El nombre del archivo nunca se envía. Tres documentos por hora.'],
    'Nothing is sent until you confirm on nbow.io.': ['Es wird nichts gesendet, bis Sie auf nbow.io bestätigen.', 'No se envía nada hasta que confirme en nbow.io.'],
    'Open a Markdown file first.': ['Öffnen Sie zuerst eine Markdown-Datei.', 'Abra primero un archivo Markdown.'],
    'Opening the nbow.io sharing window…': ['Das nbow.io-Fenster zum Teilen wird geöffnet…', 'Abriendo la ventana para compartir de nbow.io…'],
    'The sharing window is already open.': ['Das Fenster zum Teilen ist bereits offen.', 'La ventana para compartir ya está abierta.'],
    'Waiting for your confirmation in the nbow.io window…': ['Warten auf Ihre Bestätigung im nbow.io-Fenster…', 'Esperando su confirmación en la ventana de nbow.io…'],
    'Shared. Keep the receipt to have it deleted later.': ['Geteilt. Bewahren Sie den Beleg auf, um es später löschen zu lassen.', 'Compartido. Guarde el recibo para poder eliminarlo más adelante.'],
    'Not shared. See the nbow.io window for the reason.': ['Nicht geteilt. Den Grund nennt das nbow.io-Fenster.', 'No se compartió. El motivo está en la ventana de nbow.io.'],
    'Your browser blocked the window. Allow popups for this page.': ['Ihr Browser hat das Fenster blockiert. Erlauben Sie Popups für diese Seite.', 'Su navegador bloqueó la ventana. Permita las ventanas emergentes en esta página.'],
    'The sharing window did not respond. Nothing was sent.': ['Das Fenster zum Teilen hat nicht geantwortet. Es wurde nichts gesendet.', 'La ventana para compartir no respondió. No se envió nada.'],
    'Sending to nbow.io…': ['Wird an nbow.io gesendet…', 'Enviando a nbow.io…'],
    'Shared with nbow.io': ['Mit nbow.io geteilt', 'Compartido con nbow.io'],
    'Not shared with nbow.io': ['Nicht mit nbow.io geteilt', 'No se compartió con nbow.io'],
    'Sharing could not be confirmed': ['Das Teilen konnte nicht bestätigt werden', 'No se pudo confirmar si se compartió'],
    'The document was stored in the nbow.io corpus. Keep this receipt to request deletion later.': ['Das Dokument wurde im nbow.io-Korpus gespeichert. Bewahren Sie diesen Beleg auf, um später die Löschung anzufordern.', 'El documento se guardó en el corpus de nbow.io. Guarde este recibo para solicitar su eliminación más adelante.'],
    'The server did not confirm whether this document was stored. Check the nbow.io window before trying again.': ['Der Server hat nicht bestätigt, ob dieses Dokument gespeichert wurde. Prüfen Sie das nbow.io-Fenster, bevor Sie es erneut versuchen.', 'El servidor no confirmó si se guardó este documento. Revise la ventana de nbow.io antes de volver a intentarlo.'],
    'Nothing was sent to the corpus. Check the nbow.io window for details.': ['Es wurde nichts an den Korpus gesendet. Einzelheiten finden Sie im nbow.io-Fenster.', 'No se envió nada al corpus. Consulte los detalles en la ventana de nbow.io.'],
    'The sharing window closed. Nothing was sent.': ['Das Fenster zum Teilen wurde geschlossen. Es wurde nichts gesendet.', 'Se cerró la ventana para compartir. No se envió nada.'],
    'Sharing is temporarily unavailable. Nothing was sent.': ['Das Teilen ist vorübergehend nicht verfügbar. Es wurde nichts gesendet.', 'Compartir no está disponible temporalmente. No se envió nada.'],
    'Sharing permission expired. Confirm your consent in the nbow.io window and try again.': ['Die Freigabe ist abgelaufen. Bestätigen Sie Ihre Einwilligung im nbow.io-Fenster und versuchen Sie es erneut.', 'El permiso para compartir caducó. Confirme su consentimiento en la ventana de nbow.io y vuelva a intentarlo.'],
    'Confirm your consent in the nbow.io window before sharing.': ['Bestätigen Sie Ihre Einwilligung im nbow.io-Fenster, bevor Sie teilen.', 'Confirme su consentimiento en la ventana de nbow.io antes de compartir.'],
    'The hourly sharing limit has been reached. Nothing was sent.': ['Das stündliche Limit zum Teilen wurde erreicht. Es wurde nichts gesendet.', 'Se alcanzó el límite de documentos por hora. No se envió nada.'],
    'The sharing limit for this network has been reached. Nothing was sent.': ['Das Limit zum Teilen für dieses Netzwerk wurde erreicht. Es wurde nichts gesendet.', 'Se alcanzó el límite para compartir de esta red. No se envió nada.'],
    'This document is too large to share. Nothing was sent.': ['Dieses Dokument ist zum Teilen zu groß. Es wurde nichts gesendet.', 'Este documento es demasiado grande para compartir. No se envió nada.'],
    'This document is empty. Nothing was sent.': ['Dieses Dokument ist leer. Es wurde nichts gesendet.', 'Este documento está vacío. No se envió nada.'],
    'This version of the app cannot share. Reload it and try again.': ['Diese App-Version kann nicht teilen. Laden Sie sie neu und versuchen Sie es erneut.', 'Esta versión de la aplicación no puede compartir. Recárguela y vuelva a intentarlo.'],
    'The sharing request was refused. Nothing was sent.': ['Die Anfrage zum Teilen wurde abgelehnt. Es wurde nichts gesendet.', 'Se rechazó la solicitud para compartir. No se envió nada.'],
    'Last confirmed receipt': ['Letzter bestätigter Beleg', 'Último recibo confirmado'],
    'Copy receipt': ['Beleg kopieren', 'Copiar recibo'],
    'Receipt copied.': ['Beleg kopiert.', 'Recibo copiado.'],
    'Select and copy the receipt above.': ['Markieren und kopieren Sie den Beleg oben.', 'Seleccione y copie el recibo de arriba.'],
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
  const roots = ['panel', 'fab', 'pdf-ph', 'chat-bubble', 'chat-head', 'chat-status', 'chat-form', 'chat-empty', 'share-status', 'share-confirm', 'share-result'];
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
