# Context management baseline

The user approved completing the previously recommended context-management baseline.

Use the locally configured DeepSeek model through openJiuwen. Add a reusable context-budget selector and an AgentRail to the checked-out JiuwenSwarm source. Run an openJiuwen ReActAgent with that rail, rather than treating a GUI chat response as an experiment.

Generate 24 deterministic synthetic configuration-history tasks: lookup, revision, and partial update; eight each. Evaluate full history (unbounded reference), recent history (512 estimated tokens), lexical project retrieval (512 estimated tokens), and retrieval followed by model summarization (summary capped at 256 estimated tokens). A cl100k_base tokenizer is a budget proxy, not the DeepSeek tokenizer. System and question tokens are outside the history budget. Count all API-reported tokens, including summary calls.

Keep answer keys outside agent inputs. Use the same tasks and model settings for all methods, randomize method order within each task with a fixed seed, and use isolated agent sessions. Score exact parsed JSON fields, separately record API failures, and retain all inputs and outputs. This is a small synthetic pilot, not a novel validated research claim or a competition-ready submission.

Generate an English ICLR-template draft from measured results and verified reference metadata. Save model-written sections before review; bind numerical results through generated tables. Deliver code, tests, dataset, call logs, result tables, resource report, source patch, reproduction guide, and paper PDF. Never copy credentials into output artifacts.
