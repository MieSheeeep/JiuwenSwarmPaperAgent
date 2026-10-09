# Local baseline completed

Date: 2026-10-08 (Asia/Shanghai).

The saved DeepSeek configuration was used successfully with openJiuwen ReActAgent and the new opt-in JiuwenSwarm source rail. Main run: 24 synthetic tasks, four policies, 96 answers, 120 API calls including summaries, no API failures.

| Policy | Exact correct | API tokens including summaries |
|---|---:|---:|
| Full history | 24/24 | 74,665 |
| Recent window | 6/24 | 15,283 |
| Project retrieval | 24/24 | 4,212 |
| Retrieval + summary | 24/24 | 7,608 |

Nine tests passed. A final API smoke run verified response persistence. The English draft has a three-page ICLR-template PDF, LaTeX, reviewed prose and original model output. Source contribution is exported as a patch. README.md gives reproduction commands; resource_report.md includes all recorded stages.

This is a small static-history synthetic pilot. Explicit project identifiers favor lexical retrieval. The full GUI/Swarm assembler was not used. No official reviewer score, reviewer access token, published PR or competition submission is included.
