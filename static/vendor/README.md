# Bundled browser dependencies

`codemirror/` contains CodeMirror **5.65.16** (editor script, Markdown mode,
base stylesheet and Dracula theme), downloaded from
<https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/>. Its upstream MIT
license is in `codemirror/LICENSE`. Keeping these assets here lets the hosted
editor load without contacting a third-party CDN.

`mermaid.min.js` is Mermaid **12.0.0**, downloaded from
<https://cdn.jsdelivr.net/npm/mermaid@12.0.0/dist/mermaid.min.js>.
Its upstream MIT license is in `mermaid.LICENSE`; bundled dependency notices
are preserved in the JavaScript.

SHA-256: `28fca7ae6ebc7ed7bb63bde63136a74bfef14f296a57e403657eeb8b32836073`

Hosted conversion loads this application asset locally. It never downloads
JavaScript, images, fonts or other resources requested by a document. When
updating the bundle, pin an explicit version, update this checksum and run
`python -m unittest discover -s tests -p test_hosted_renderer.py`.
