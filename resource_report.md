# Resource report

Model: deepseek-flash; official DeepSeek API.

| Stage | API calls | Input tokens | Output tokens | Total tokens | Cached input tokens |
|---|---:|---:|---:|---:|---:|
| smoke | 5 | 4151 | 90 | 4241 | 0 |
| baseline | 120 | 99644 | 2124 | 101768 | 3328 |
| smoke_verified | 5 | 4151 | 85 | 4236 | 3328 |
| paper | 1 | 2777 | 1275 | 4052 | 0 |

All stages: 131 calls, 114297 API-reported tokens.

Cached tokens are a subset of input tokens. Summary calls are included.
The main experiment used 120 calls and 101,768 tokens. Its recorded workload wall time was 43.851 seconds, excluding imports, environment setup, drafting and compilation.
SDK zero-valued cost fields are not an invoice and do not establish free usage. Check actual charges in the DeepSeek console.
Response persistence was strengthened after the main run; policies, task data and model inputs were unchanged. The smoke_verified run validates the final instrumentation.
No failed calls or retries occurred. Local CPU/Python execution; no local GPU inference.
