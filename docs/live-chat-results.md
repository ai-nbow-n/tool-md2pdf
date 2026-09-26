# Live results: small models on the production VPS

Measured on 25–26 September 2026 against the server's own Ollama (0.16.3) on
the VPS's 2 vCPUs (AMD EPYC 9354P, AVX-512, no GPU, 7.9 GB RAM, no swap). Ollama
used both threads. The assistant replaced an earlier OpenAI-based one on these
dates; those results no longer apply.

## Licences first

| Model | Licence | Hosted use on nbow.io |
|---|---|---|
| `qwen3:1.7b` | Apache 2.0 | yes: the default |
| `qwen2.5:1.5b` | Apache 2.0 | allowed, but see its results below |
| `qwen2.5:3b` | Qwen RESEARCH LICENSE: "research or evaluation purposes only"; commercial use needs a licence from Alibaba Cloud | **no** |

Read a model's licence with `ollama show <model> --license` before configuring it.

## Raw speed of qwen2.5:3b

One request on an 84-line, 2,700-character itinerary with the edit schema as
Ollama's structured output:

| Prompt format | Prompt tokens | Reading | Writing | Total |
|---|---|---|---|---|
| numbered lines, line-range edits | 1,117 | 88 s (12.7 tok/s) | 150 tok in 28 s (5.4 tok/s) | 137 s, incl. 17 s model load |
| plain document, find/replace edits | 841 | 58 s (14.4 tok/s) | 219 tok in 44 s (5.0 tok/s) | 107 s, model warm |

The line-range answer deleted the wrong ranges (parts of four days instead of
Salzburg's). That is why the app uses find/replace edits.

## End to end, through `services/llm.py`

`scripts/live_chat_smoke.py`: a 1,600-character itinerary, three requests, each
on a fresh copy.

| Request | qwen2.5:3b | qwen2.5:1.5b | qwen3:1.7b |
|---|---|---|---|
| Change the title | 65 s (cold), correct | 24 s, claimed a change and returned no edit | 43 s (cold), changed, but dropped the `#` heading marker |
| Remove Salzburg's day, fix the totals | 32 s, left Salzburg's table rows in | 27 s, no usable edits; nothing changed | 22 s, correct: heading, text, table row and totals |
| How many cities, which is last? | 14 s, wrong (counted five) | 17 s, correct, but also rewrote the totals line | 9 s, correct, no edit |

qwen3:1.7b is the default: licence-clean, the fastest, and the only one to get
the multi-part edit right. The 3B figures were measured before the review
removed whitespace-tolerant matching; the other two after.

Times are single observations, not guarantees. A small model still slips (the
dropped `#`); editor Undo reverses a chat edit. Larger models (7B and up) would
be more accurate but at least twice as slow on this hardware, which does not fit
the 180 s budget.

## Empty documents (26 September 2026)

On nbow.io, "Provide anatomy of human neuron" on an empty document came back as
an answer in the chat, and the file received only the prompt's own
`<document name="untitled-2.md">` wrapper. Reproduced on a workstation CPU with
the same `qwen3:1.7b` build (Q4_K_M, about 10.7 output tokens/s; the VPS will be
somewhat slower), through `/api/llm/chat`:

| Empty document, request | Edit prompt (before) | Own write prompt (now) |
|---|---|---|
| Provide anatomy of human neuron | chat answer pasted as one flat paragraph | title, three sections, lists; 439 tokens, 46 s |
| Write a short poem about the sea | one run-on line | titled poem; 207 tokens, 21 s |
| What is photosynthesis? | flat paragraph | titled explainer with sections; 230 tokens, 23 s |
| Explain the causes of the French Revolution | HTTP 502: quoted its own answer as `find` | three sections of lists; 293 tokens, 29 s |
| Schreibe einen kurzen Text über Bienen. | — | German document and German reply |
| hello | — | wrote a placeholder document, although told not to |

Tried first and dropped: rewording the one edit prompt so that requests for
text go into the document, with an empty `find` or a separate `append` field
for new text. The model then copied its edits into `reply`, edited documents in
answer to plain questions ("How many stanzas?" deleted the title), and looped
on tab characters. Only the separate empty-document prompt improved writing
without making questions worse.

Documents with content keep the edit prompt, plus one line on the empty `find`.
`scripts/live_chat_smoke.py` gave the same results as in the table above (title
changed without its `#`, Salzburg removed correctly, question answered without
an edit). Still wrong with either prompt: "Add a Friday evening: dinner at
Figlmueller." inserted the line twice.
