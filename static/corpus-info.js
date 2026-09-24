/* Markdown corpus information, kept inside the editor beside the sharing controls.
 * Copy follows website/src/i18n/dict/{en,de,es}.ts: codeAgents.corpus.
 * Sharing limits follow the website corpus defaults; this panel sends no data.
 */
(() => {
  "use strict";

  const translations = {
  "en": {
    "title": "The Markdown corpus",
    "tagline": "Optional, anonymous, three documents an hour",
    "intro": "We are studying how people write technical Markdown: how long documents get, which features they use, and where converters break. You can help by sharing a document. Sharing with this research corpus is optional, requires separate confirmation, and is independent of the temporary processing needed to use the hosted editor.",
    "howTitle": "How it works",
    "how1": "In md2pdf, press <strong>Share with nbow.io</strong>. A window opens on nbow.io.",
    "how2": "That window needs your cookie consent at the <strong>Statistics + Experience</strong> level. Without it, nothing can be sent — the button stays disabled.",
    "how3": "The window shows the complete text to be added to the corpus and asks you to confirm twice: that you have read it, and that it contains no personal or confidential information.",
    "how4": "Only then is the document added to the corpus. You get a receipt code, which is the only way anyone — including us — can find that corpus document again.",
    "storedTitle": "What we store, exactly",
    "stored1": "the Markdown text you approved, as you approved it;",
    "stored2": "its measurements: byte size, lines, words, and how many headings, code blocks, Mermaid diagrams, tables, links, images and footnotes it contains;",
    "stored3": "which tool sent it, the interface language, and the time and level of your consent;",
    "stored4": "the SHA-256 of your receipt code, so an erasure request can find the row.",
    "notStoredTitle": "What we never store",
    "notStored1": "your IP address;",
    "notStored2": "your browser identification or the page you came from;",
    "notStored3": "the file name — often the most revealing part of a document, and simply not part of what the tool sends;",
    "notStored4": "anything that links the document to you. There is no account and no visitor identifier.",
    "limitsTitle": "Limits and retention",
    "limitsBody": "At most three documents per hour and 256 kB each. Documents are kept for 24 months and then deleted automatically. You can erase one at any time with its receipt code, without identifying yourself.",
    "warningTitle": "Please read this before sharing",
    "warningBody": "The full text of the document is stored and read by us. Do not share anything confidential, anything covered by an NDA, or anything containing personal data about you or anyone else — a name, an address, a salary, a medical detail, a client's terms. Once you have sent a document you cannot unsee it on our side; you can only have it deleted.",
    "shareButton": "Open the sharing window",
    "eraseButton": "Erase a document with its receipt",
    "legalNote": "Sharing is processed on the basis of your consent, GDPR Art. 6(1)(a). The full details are in our <a href=\"/{lang}/privacy\" class=\"text-orange-600 hover:underline\">privacy policy</a> and <a href=\"/{lang}/cookies\" class=\"text-orange-600 hover:underline\">cookie policy</a>."
  },
  "de": {
    "title": "Der Markdown-Korpus",
    "tagline": "Freiwillig, anonym, drei Dokumente pro Stunde",
    "intro": "Wir untersuchen, wie technisches Markdown geschrieben wird: wie lang Dokumente werden, welche Funktionen genutzt werden und wo Konverter scheitern. Sie können helfen, indem Sie ein Dokument teilen. Das Teilen mit diesem Forschungskorpus ist freiwillig, erfordert eine separate Bestätigung und ist unabhängig von der temporären Verarbeitung im Online-Editor.",
    "howTitle": "So funktioniert es",
    "how1": "Drücken Sie in md2pdf auf <strong>Mit nbow.io teilen</strong>. Ein Fenster auf nbow.io öffnet sich.",
    "how2": "Dieses Fenster braucht Ihre Cookie-Einwilligung auf der Stufe <strong>Statistiken + Erlebnis</strong>. Ohne sie kann nichts gesendet werden — die Schaltfläche bleibt gesperrt.",
    "how3": "Das Fenster zeigt den vollständigen Text, der dem Korpus hinzugefügt würde, und bittet um zwei Bestätigungen: dass Sie ihn gelesen haben und dass er keine persönlichen oder vertraulichen Informationen enthält.",
    "how4": "Erst dann wird das Dokument dem Korpus hinzugefügt. Sie erhalten einen Belegcode, mit dem allein jeder — auch wir — dieses Korpus-Dokument wiederfinden kann.",
    "storedTitle": "Was wir genau speichern",
    "stored1": "den Markdown-Text, den Sie freigegeben haben, so wie Sie ihn freigegeben haben;",
    "stored2": "seine Maße: Größe in Bytes, Zeilen, Wörter sowie die Anzahl der Überschriften, Codeblöcke, Mermaid-Diagramme, Tabellen, Links, Bilder und Fußnoten;",
    "stored3": "welches Werkzeug es gesendet hat, die Sprache der Oberfläche sowie Zeitpunkt und Stufe Ihrer Einwilligung;",
    "stored4": "den SHA-256 Ihres Belegcodes, damit ein Löschverlangen den Datensatz finden kann.",
    "notStoredTitle": "Was wir nie speichern",
    "notStored1": "Ihre IP-Adresse;",
    "notStored2": "Ihre Browser-Kennung oder die Seite, von der Sie kamen;",
    "notStored3": "den Dateinamen — oft der aussagekräftigste Teil eines Dokuments und einfach nicht Teil dessen, was das Werkzeug sendet;",
    "notStored4": "nichts, was das Dokument mit Ihnen verbindet. Es gibt kein Konto und keine Besucherkennung.",
    "limitsTitle": "Grenzen und Speicherdauer",
    "limitsBody": "Höchstens drei Dokumente pro Stunde und je 256 kB. Dokumente werden 24 Monate aufbewahrt und dann automatisch gelöscht. Sie können eines jederzeit mit seinem Belegcode löschen, ohne sich auszuweisen.",
    "warningTitle": "Bitte lesen Sie das, bevor Sie teilen",
    "warningBody": "Der vollständige Text des Dokuments wird gespeichert und von uns gelesen. Teilen Sie nichts Vertrauliches, nichts, das einer Verschwiegenheitsvereinbarung unterliegt, und nichts mit personenbezogenen Daten über Sie oder andere — einen Namen, eine Adresse, ein Gehalt, eine Gesundheitsangabe, die Konditionen eines Kunden. Ein gesendetes Dokument können wir nicht ungesehen machen; Sie können nur seine Löschung verlangen.",
    "shareButton": "Fenster zum Teilen öffnen",
    "eraseButton": "Ein Dokument mit seinem Beleg löschen",
    "legalNote": "Das Teilen erfolgt auf Grundlage Ihrer Einwilligung, Art. 6 Abs. 1 lit. a DSGVO. Alle Einzelheiten stehen in unserer <a href=\"/{lang}/privacy\" class=\"text-orange-600 hover:underline\">Datenschutzerklärung</a> und der <a href=\"/{lang}/cookies\" class=\"text-orange-600 hover:underline\">Cookie-Richtlinie</a>."
  },
  "es": {
    "title": "El corpus de Markdown",
    "tagline": "Opcional, anónimo, tres documentos por hora",
    "intro": "Estudiamos cómo se escribe Markdown técnico: cuánto crecen los documentos, qué funciones se usan y dónde fallan los conversores. Puede ayudarnos compartiendo un documento. Compartir con este corpus de investigación es opcional, exige una confirmación aparte y es independiente del tratamiento temporal necesario para usar el editor en línea.",
    "howTitle": "Cómo funciona",
    "how1": "En md2pdf, pulse <strong>Compartir con nbow.io</strong>. Se abre una ventana en nbow.io.",
    "how2": "Esa ventana necesita su consentimiento de cookies en el nivel <strong>Estadísticas + Experiencia</strong>. Sin él no se puede enviar nada: el botón queda desactivado.",
    "how3": "La ventana muestra el texto completo que se añadiría al corpus y pide dos confirmaciones: que lo ha leído y que no contiene datos personales ni información confidencial.",
    "how4": "Solo entonces se añade el documento al corpus. Recibe un código de recibo, que es la única forma de que cualquiera —incluidos nosotros— encuentre de nuevo ese documento del corpus.",
    "storedTitle": "Qué guardamos, exactamente",
    "stored1": "el texto Markdown que usted aprobó, tal como lo aprobó;",
    "stored2": "sus medidas: tamaño en bytes, líneas, palabras y cuántos encabezados, bloques de código, diagramas Mermaid, tablas, enlaces, imágenes y notas al pie contiene;",
    "stored3": "qué herramienta lo envió, el idioma de la interfaz y la hora y el nivel de su consentimiento;",
    "stored4": "el SHA-256 de su código de recibo, para que una solicitud de supresión pueda encontrar el registro.",
    "notStoredTitle": "Qué no guardamos nunca",
    "notStored1": "su dirección IP;",
    "notStored2": "la identificación de su navegador ni la página de procedencia;",
    "notStored3": "el nombre del archivo, a menudo la parte más reveladora de un documento y que simplemente no forma parte de lo que envía la herramienta;",
    "notStored4": "nada que vincule el documento con usted. No hay cuenta ni identificador de visitante.",
    "limitsTitle": "Límites y conservación",
    "limitsBody": "Como máximo tres documentos por hora y 256 kB cada uno. Los documentos se conservan 24 meses y luego se eliminan automáticamente. Puede borrar uno en cualquier momento con su código de recibo, sin identificarse.",
    "warningTitle": "Lea esto antes de compartir",
    "warningBody": "El texto completo del documento se almacena y lo leemos. No comparta nada confidencial, nada cubierto por un acuerdo de confidencialidad, ni nada que contenga datos personales suyos o de terceros: un nombre, una dirección, un sueldo, un dato médico, las condiciones de un cliente. Una vez enviado un documento no podemos dejar de haberlo visto; solo puede pedir que se elimine.",
    "shareButton": "Abrir la ventana para compartir",
    "eraseButton": "Borrar un documento con su recibo",
    "legalNote": "Compartir se trata sobre la base de su consentimiento, art. 6.1.a RGPD. Los detalles completos están en nuestra <a href=\"/{lang}/privacy\" class=\"text-orange-600 hover:underline\">política de privacidad</a> y en la <a href=\"/{lang}/cookies\" class=\"text-orange-600 hover:underline\">política de cookies</a>."
  }
};

  const shareButton = document.getElementById("share-open");
  if (!shareButton) return;
  const details = document.createElement("details");
  details.id = "markdown-corpus";
  const summary = document.createElement("summary");
  const content = document.createElement("div");
  content.className = "corpus-info-content";
  details.append(summary, content);
  shareButton.before(details);

  let renderedLanguage;

  function paragraph(text, className) {
    const node = document.createElement("p");
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function heading(text) {
    const node = document.createElement("h4");
    node.textContent = text;
    return node;
  }

  function list(copy, prefix, ordered = false) {
    const node = document.createElement(ordered ? "ol" : "ul");
    for (let index = 1; index <= 4; index++) {
      const item = document.createElement("li");
      // These are trusted UI translations, never document or user content.
      if (ordered) item.innerHTML = copy[`${prefix}${index}`];
      else item.textContent = copy[`${prefix}${index}`];
      node.append(item);
    }
    return node;
  }

  function render() {
    const language = Object.hasOwn(translations, document.documentElement.lang)
      ? document.documentElement.lang : "en";
    if (language === renderedLanguage) return;
    renderedLanguage = language;
    const copy = translations[language];
    const siteBase = shareButton.dataset.shareBase || "https://nbow.io";
    const siteUrl = path => new URL(`/${language}${path}`, siteBase).href;

    summary.textContent = copy.title;
    const warning = document.createElement("section");
    warning.className = "corpus-info-warning";
    warning.append(heading(copy.warningTitle), paragraph(copy.warningBody));

    const erase = document.createElement("a");
    erase.href = siteUrl("/products/aiconsulting/code-agents/share#erase-form");
    erase.target = "_blank";
    erase.rel = "noopener";
    erase.textContent = copy.eraseButton;

    const legal = document.createElement("p");
    legal.className = "corpus-info-legal";
    legal.innerHTML = copy.legalNote.replaceAll("{lang}", language);
    for (const link of legal.querySelectorAll("a")) {
      link.href = new URL(link.getAttribute("href"), siteBase).href;
      link.target = "_blank";
      link.rel = "noopener";
      link.removeAttribute("class");
    }

    content.replaceChildren(
      paragraph(copy.tagline, "corpus-info-tagline"),
      paragraph(copy.intro),
      warning,
      heading(copy.howTitle), list(copy, "how", true),
      heading(copy.storedTitle), list(copy, "stored"),
      heading(copy.notStoredTitle), list(copy, "notStored"),
      heading(copy.limitsTitle), paragraph(copy.limitsBody),
      erase, legal,
    );
  }

  function revealFromHash() {
    if (location.hash !== "#markdown-corpus") return;
    const panel = document.getElementById("panel");
    if (panel && panel.classList.contains("hidden")) {
      document.getElementById("fab")?.click();
    }
    details.open = true;
    // Wait until the panel has measurable dimensions, including on mobile.
    requestAnimationFrame(() => {
      summary.focus({preventScroll: true});
      details.scrollIntoView({block: "start"});
    });
  }

  render();
  new MutationObserver(render).observe(document.documentElement, {
    attributes: true, attributeFilter: ["lang"],
  });
  window.addEventListener("hashchange", revealFromHash);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", revealFromHash, {once: true});
  } else {
    revealFromHash();
  }
})();
