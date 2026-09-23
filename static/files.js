/* Browser file import and downloads work both locally and behind the website. */
(() => {
  const upload = document.getElementById('file-upload');
  function download(blob, name) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = name;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  async function createFile(name, content) {
    if (chatApplying) return;
    if (dirty && current && !await save(true)) return;
    if (!name.toLowerCase().endsWith('.md')) name += '.md';
    name = name.slice(0, -3) + '.md';
    // Import a separate copy when a name exists; never overwrite it silently.
    for (let copy = 0; copy < 100; copy++) {
      const filename = copy ? name.slice(0, -3) + '-' + copy + '.md' : name;
      const body = {content, create_only: true};
      if (inDir()) body.dir = inDir();
      const response = await fetch(window.md2pdfUrl('/api/file/' + encodeURIComponent(filename)), {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
      });
      const result = await response.json();
      if (response.status === 409) continue;
      if (!response.ok) throw new Error(result.error || 'Could not open the Markdown file.');
      await loadFiles();
      document.getElementById('file-select').value = filename;
      await openFile(filename);
      return;
    }
    throw new Error('Choose a different file name.');
  }
  async function run(action) {
    try { await action(); }
    catch (error) { setStatus(error.message || 'File operation failed.', 'err'); }
  }
  document.getElementById('btn-new').addEventListener('click', () => run(async () => {
    const name = prompt('Markdown file name', 'untitled.md');
    if (name && name.trim()) await createFile(name.trim(), '');
  }));
  document.getElementById('btn-open').addEventListener('click', () => upload.click());
  upload.addEventListener('change', () => run(async () => {
    const file = upload.files[0];
    upload.value = '';
    if (!file) return;
    if (!/\.md$/i.test(file.name)) throw new Error('Choose a .md Markdown file.');
    if (hosted && file.size > 1024 * 1024) throw new Error('Choose a Markdown file smaller than 1 MB.');
    await createFile(file.name, await file.text());
  }));
  document.getElementById('btn-download-md').addEventListener('click', () => {
    if (current) download(new Blob([cm.getValue()], {type: 'text/markdown;charset=utf-8'}), current);
  });
  document.getElementById('btn-download-pdf').addEventListener('click', () => run(async () => {
    if (!current) return;
    const name = current.replace(/\.md$/, '.pdf');
    const query = outDir() ? '?dir=' + encodeURIComponent(outDir()) : '';
    const response = await fetch(window.md2pdfUrl('/pdf/' + encodeURIComponent(name)) + query);
    if (!response.ok) throw new Error('Compile the document before downloading its PDF.');
    download(await response.blob(), name);
  }));
})();
