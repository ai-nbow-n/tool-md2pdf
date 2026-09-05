# Live timeout investigation

Tested on 6 September 2026 using the locally supplied API key. The request was
“remove salzburg from the trip and make the diagram coherent”, with the full
current itinerary as context. All writes targeted temporary/output copies.

| Configuration | Model | Time | Result |
|---|---|---|---|
| Original 60-second timeout | GPT-5 | 61.22 s | HTTP 504 timeout |
| Original configuration | GPT-4.1 mini | 4.25 s | Valid edits, but missed Salzburg references |
| 180-second budget, low reasoning | GPT-5 | 40.62 s | 5 valid edits; Salzburg references removed; diagram rendered |
| 180-second budget, low reasoning | GPT-4.1 mini | 6.19 s | 3 valid edits, but missed Salzburg references; reasoning option is omitted for this model |
| Before correction handling | GPT-5 mini | 17.36 s | Overlapping edit ranges rejected; no save |
| With bounded correction handling | GPT-5 mini | 20.19 s | 7 valid edits; Salzburg references removed; diagram rendered |

Times are individual observations, not performance guarantees. The GPT-5 mini
failure contained a deletion within another replacement range. The backend now
asks for one corrected batch when validation fails, sharing the original
180-second time budget. A subsequent live request passed; a deterministic unit
test separately verifies the correction path.

The browser timeout is generated from backend settings and includes a 15-second
grace period. It displays elapsed time instead of appearing idle while the API
works. No original itinerary files were changed by these tests.

Raw timing summaries and edited test copies are in the ignored `data/output/`
directory. The key is never printed or included in reports; `apikey.txt` is
ignored by Git. See [chat.md](chat.md) for the live test command.
