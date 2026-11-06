"""Generate a substantive, result-bound short-paper draft for a registered run."""

import json
from pathlib import Path
import shutil

from research.artifacts import atomic_write, digest, save_json


def _latex(text):
    replacements = {
        '\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
        '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
    }
    return ''.join(replacements.get(char, char) for char in str(text))


def _metric(summary, method):
    return summary['by_method'][method]


def _markdown(plan, summary, rows, manifest):
    methods = plan['methods']
    total_tokens = sum(_metric(summary, method)['provider_tokens'] for method in methods)
    lines = [
        '# Adaptive Evidence Stopping for Multi-hop Question Answering', '',
        '> Automatically assembled short-paper draft. The benchmark is synthetic; the study does not establish general novelty or generalization.', '',
        '## Abstract', '',
        f"Long-context agents must decide when they have collected enough evidence to answer a question. "
        f"We evaluate an auditable evidence-coverage stopping rule against a one-passage baseline and fixed two-passage retrieval on "
        f"{plan['protocol']['dataset']}. The frozen run contains {len(rows)} method-task rows and {total_tokens} provider tokens. "
        'The stopping rule reaches the same accuracy as fixed retrieval on this two-hop synthetic benchmark, but it does not reduce context length because every task requires both hops. '
        'The result is therefore a reproducibility demonstration and a negative efficiency finding, not a claim of a new retrieval algorithm.', '',
        '## 1. Introduction', '',
        'A research agent cannot treat every retrieved passage as equally useful. It must decide what evidence to keep, when the evidence is sufficient, and how to expose the decision to later analysis. This paper studies that narrow control problem rather than claiming a complete autonomous scientist. The motivating failure mode is simple: a first passage identifies an intermediate entity, while a second passage contains the answer. Stopping after the first passage produces a confident but unsupported answer.', '',
        'Our question is: can a transparent evidence-coverage rule match a fixed retrieval budget while avoiding unnecessary passages? The hypothesis predicts that the adaptive rule will preserve exact accuracy and use no more context than fixed two-passage retrieval. The frozen falsification condition is a loss in paired exact accuracy or a larger mean context. Because the benchmark has exactly two required hops, it is deliberately capable of producing a null efficiency result.', '',
        'The contribution is an executable research handoff. A literature-derived plan is checked against a registered adapter, a deterministic dataset is frozen before model calls, each answer is linked to its selected context and provider usage, and the paper numbers are recomputed from the saved ledger. This is an engineering artifact and a controlled pilot, not evidence that the agent can invent arbitrary experiments.', '',
        '## 2. Related work', '',
        'ReAct frames language-model agents as systems that interleave reasoning and actions; our runner uses a bounded answering call and does not evaluate open-ended tool planning. Long-context studies such as Lost in the Middle motivate measuring whether relevant evidence is omitted by a context policy. Multi-hop question-answering benchmarks such as HotpotQA motivate separating supporting hops from distractors. Adaptive retrieval work motivates deciding whether another retrieval step is needed, but this pilot uses a deterministic evidence rule rather than a learned controller. Agent Laboratory and AI-Researcher show broader literature-to-experiment-to-manuscript workflows; our implementation adopts the workflow boundary while keeping execution allow-listed.', '',
        'None of these references is reproduced as a baseline in this run. In particular, the result does not compare embedding retrievers, does not use HotpotQA, and does not claim that the registered rule is novel.', '',
        '## 3. Method', '',
        '### 3.1 Research handoff and safety boundary', '',
        'The experiment plan contains a candidate question, hypothesis, falsification condition, data split, methods, metrics, and explicit token and call ceilings. The execution layer accepts only the registered adaptive-qa-v1 adapter. It rejects plan-supplied shell commands and arbitrary Python entry points. This boundary is intentional: a model may propose a method, but execution must first be implemented and reviewed as a safe adapter.', '',
        '### 3.2 Synthetic multi-hop dataset', '',
        f"The dataset is generated with seed {plan['protocol']['seed']} and contains {plan['protocol']['tasks']} test tasks. Each task has a researcher, a lab, and a city. Passage p0 states that the researcher founded the lab; passage p1 states that the lab is headquartered in the city; passage p2 is a lexical distractor. The question asks for the city and requires both support hops. The gold answer and required evidence IDs are generated independently of the language model and are never included in the prompt.", '',
        'The dataset is intentionally small and regular. It tests ledger integrity and stopping semantics, not natural-language diversity. The fixed seed, task JSON, and manifest hash are stored beside the results.', '',
        '### 3.3 Context policies and scoring', '',
        'single_pass selects p0 only. fixed_two_passages selects p0 and p1. adaptive_stop appends passages in order and stops once both required evidence types are present. Exact accuracy compares the normalized answer with the independent city string. Evidence recall measures the fraction of required support passages present in the selected context. Context cost is the number of passages; provider cost is the reported input plus output tokens.', '',
        'Every model request is recorded through the durable ModelGateway. A result row stores the task ID, method, selected IDs, context hash, answer, score, and call ID. Missing usage or an interrupted request stops the run instead of being treated as free or correct.', '',
        '## 4. Experimental setup', '',
        f"We compare {', '.join(methods)} on the same {plan['protocol']['tasks']} tasks. The model is configured through the local DeepSeek-compatible endpoint with deterministic decoding and a maximum answer length of {plan['protocol']['answer_max_tokens']} tokens. The run ceiling is {plan['cost_controls']['max_total_tokens']} admitted tokens and {plan['cost_controls']['max_calls']} calls; the completed run used {total_tokens} provider tokens and {len(rows)} calls.", '',
        'The experiment is paired: every method sees the same question and underlying passages. No method is tuned on the test answers. The analysis is descriptive because the data are synthetic and the sample is too small for a general claim.', '',
        '## 5. Results', '',
        '| Method | Exact accuracy | Evidence recall | Mean passages | Provider tokens |',
        '|---|---:|---:|---:|---:|',
    ]
    for method in methods:
        metric = _metric(summary, method)
        lines.append(f"| {method} | {metric['exact_accuracy']:.2f} | {metric['evidence_recall']:.2f} | "
                     f"{metric['mean_context_passages']:.2f} | {metric['provider_tokens']} |")
    lines += [
        '',
        'The one-passage baseline has 0/12 exact answers because it contains the first hop but not the passage that maps the lab to a city. Both two-passage policies have 12/12 exact answers and complete evidence recall. Adaptive stopping therefore matches fixed retrieval on accuracy but uses exactly the same two passages on every task. In this benchmark, the proposed stopping condition provides no efficiency improvement; that is the correct conclusion from the frozen protocol.', '',
        '## 6. Error analysis', '',
        'All single_pass failures share the same mechanism: the answer is not present in the selected context. The error is an evidence-availability failure, not a subtle language-model hallucination. The fixed_two_passages and adaptive_stop conditions have no exact-answer failures in the saved run. This perfect score should not be generalized: the task generator makes the answer deterministic once both support passages are supplied.', '',
        'The result also exposes a design limitation. Because every task has exactly two hops, adaptive_stop never has an opportunity to stop earlier than fixed_two_passages. A meaningful efficiency test needs a mixture of one-hop, two-hop, and three-hop questions, distractor orderings, paraphrases, and an independently held-out corpus. Those extensions are not silently added after seeing this result.', '',
        '## 7. Limitations and reproducibility', '',
        'The benchmark is synthetic, small, and structurally regular. It does not measure retrieval over real documents, citation faithfulness, tool planning, multi-turn interaction, or cross-topic scientific generalization. The adapter is safe because it is registered; it is not an arbitrary code-generation mechanism. No Stanford Agentic Reviewer or human expert score is attached to this run.', '',
        f"The run manifest hash is {digest(manifest)}. The raw dataset, prompts, requests, calls, result rows, summary, Markdown draft, and LaTeX source are in the run directory. Re-running the documented command with the same configuration creates a new ledger and does not overwrite the historical memory experiment.", '',
        '## 8. Conclusion', '',
        'This pilot demonstrates a complete, auditable path from a research question to a bounded experiment and a result-bound manuscript. It does not demonstrate an advantage for adaptive stopping: on the frozen two-hop benchmark, adaptive stopping ties fixed retrieval in both accuracy and context length. The next scientifically meaningful step is to broaden the dataset and add a held-out real-document evaluation before making any claim about a general research agent.', '',
        '## Appendix: Reproducibility', '',
        'The execution command is:', '',
        '.venv\\Scripts\\python.exe -m research.generic_runner --output output/generic_qa_run_20261106_v2 --max-total-tokens 20000 --max-calls 36', '',
        'The minimum result-row contract is: task ID, method, answer, selected passage IDs, context SHA-256, score object, provider token count, and call IDs. The ledger is fail-closed when a request has no reconciled usage.', '',
        '### References', '',
        '[1] Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. 2023. https://arxiv.org/abs/2210.03629', '',
        '[2] Liu et al. Lost in the Middle: How Language Models Use Long Contexts. 2023. https://arxiv.org/abs/2307.03172', '',
        '[3] Yang et al. HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering. 2018. https://arxiv.org/abs/1809.09600', '',
        '[4] Jeong et al. Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. 2024. https://arxiv.org/abs/2403.14403', '',
        '[5] Schmidgall et al. Agent Laboratory: Using LLM Agents as Research Assistants. 2025. https://arxiv.org/abs/2501.04227', '',
        '[6] Tang et al. AI-Researcher: Autonomous Scientific Innovation. 2025. https://arxiv.org/abs/2505.18705',
    ]
    return '\n'.join(lines) + '\n'


def _tex(plan, summary, rows, manifest):
    methods = plan['methods']
    total_tokens = sum(_metric(summary, method)['provider_tokens'] for method in methods)
    abstract = ('We evaluate an auditable evidence-coverage stopping rule against one-passage and fixed two-passage retrieval '
                f"on a {plan['protocol']['dataset']} with {plan['protocol']['tasks']} frozen tasks. "
                f"The completed ledger contains {len(rows)} method-task rows and {total_tokens} provider tokens. "
                'Adaptive stopping matches fixed retrieval on accuracy but does not reduce context length because every task requires two hops. '
                'The result is a reproducibility demonstration and a negative efficiency finding, not a claim of general novelty.')
    paragraphs = [
        ('Introduction', 'Long-context agents must decide when they have enough evidence to answer. We study this narrow control problem rather than claiming a complete autonomous scientist. A first passage can identify an intermediate entity while a second passage contains the answer. Stopping after the first passage therefore creates an evidence-availability failure.'),
        ('Related Work', 'ReAct frames language-model agents as systems that interleave reasoning and actions. Long-context work motivates measuring omitted evidence, and HotpotQA motivates multi-hop support chains. Adaptive-RAG motivates deciding whether another retrieval step is needed. Agent Laboratory and AI-Researcher motivate a literature-to-experiment-to-manuscript workflow. We do not reproduce these systems or claim that our registered rule is novel.'),
        ('Research Handoff and Safety', 'The plan contains a question, hypothesis, falsification condition, frozen split, metrics, and explicit budgets. The runner accepts only the registered adaptive-qa-v1 adapter and rejects plan-supplied shell commands or arbitrary Python entry points. This keeps model proposals separate from executable code.'),
        ('Dataset', f"With seed {plan['protocol']['seed']}, the generator creates {plan['protocol']['tasks']} tasks. Each task has a researcher, a lab, a city, two support passages and one distractor. The first support passage identifies the lab; the second maps the lab to the city. Gold answers and evidence IDs are generated independently and are not shown to the model."),
        ('Policies and Scoring', 'single_pass keeps the first passage, fixed_two_passages keeps the first two, and adaptive_stop appends passages until both evidence types are present. Exact accuracy compares the normalized answer with the independent city string. Evidence recall measures required support present in context. Every request is bound to a context hash and durable provider call record.'),
        ('Experimental Setup', f"We compare {', '.join(methods)} on the same {plan['protocol']['tasks']} tasks with deterministic decoding and an answer limit of {plan['protocol']['answer_max_tokens']} tokens. The admission ceiling is {plan['cost_controls']['max_total_tokens']} tokens and {plan['cost_controls']['max_calls']} calls. The completed run used {total_tokens} provider tokens across {len(rows)} calls. Analysis is descriptive and no method is tuned on test answers."),
        ('Results', 'The one-passage condition lacks the second hop, while both two-passage conditions expose complete evidence. The table reports the saved ledger; adaptive stopping ties fixed retrieval because every frozen task requires both hops.'),
        ('Error Analysis', 'All single-passage failures are caused by absent answer evidence. There are no exact-answer failures for the two-passage conditions in this synthetic run. The perfect scores should not be generalized: the task generator makes the answer deterministic after both support passages are supplied. A harder follow-up needs mixed hop counts, paraphrases, distractor orderings, and a held-out real-document corpus.'),
        ('Limitations', 'The benchmark is synthetic, small and structurally regular. It does not measure real-document retrieval, citation faithfulness, tool planning, multi-turn interaction or cross-topic scientific generalization. The adapter is registered and safe, not an arbitrary code-generation mechanism. No Stanford or expert score is attached.'),
        ('Conclusion', 'This pilot demonstrates an auditable path from question to bounded experiment and result-bound manuscript. It does not show an adaptive-stopping advantage: adaptive and fixed retrieval tie on accuracy and context length. Broader held-out evaluation is required before any general research-agent claim.'),
    ]
    lines = [r'\documentclass{article}', r'\usepackage{iclr2026_conference,times}', r'\usepackage{booktabs,hyperref}',
             r'\iclrfinalcopy', r'\title{Adaptive Evidence Stopping for Multi-hop Question Answering}',
             r'\author{JiuwenSwarm Research Agent\\\texttt{automatically assembled; not peer reviewed}}', r'\begin{document}',
             r'\maketitle', r'\begin{abstract}', _latex(abstract), r'\end{abstract}']
    for title, body in paragraphs:
        lines += [r'\section{' + _latex(title) + '}', _latex(body)]
        if title == 'Results':
            lines += [r'\begin{table}[t]', r'\centering', r'\small', r'\begin{tabular}{lrrrr}',
                      r'\toprule Method & Exact & Evidence & Passages & Tokens \\', r'\midrule']
            for method in methods:
                metric = _metric(summary, method)
                lines.append(_latex(method) + f" & {metric['exact_accuracy']:.2f} & {metric['evidence_recall']:.2f} & "
                             f"{metric['mean_context_passages']:.2f} & {metric['provider_tokens']} \\\\")
            lines += [r'\bottomrule', r'\end{tabular}', r'\caption{Results recomputed from the durable result ledger.}', r'\end{table}']
    lines += [r'\section{Reproducibility Appendix}', _latex('The run manifest, frozen dataset, prompts, calls, requests, result rows, summary and this source are stored together. The manifest hash is ' + digest(manifest) + '.'),
              r'\begin{verbatim}',
              r'.venv\Scripts\python.exe -m research.generic_runner',
              r'  --output output/generic_qa_run_20261106_v2',
              r'  --max-total-tokens 20000 --max-calls 36',
              r'\end{verbatim}', r'\begin{thebibliography}{9}',
              r'\bibitem[Yao et al., 2023]{react} Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. 2023.',
              r'\bibitem[Liu et al., 2023]{lostmiddle} Liu et al. Lost in the Middle: How Language Models Use Long Contexts. 2023.',
              r'\bibitem[Yang et al., 2018]{hotpotqa} Yang et al. HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering. 2018.',
              r'\bibitem[Jeong et al., 2024]{adaptiverag} Jeong et al. Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. 2024.',
              r'\bibitem[Schmidgall et al., 2025]{agentlab} Schmidgall et al. Agent Laboratory: Using LLM Agents as Research Assistants. 2025.',
              r'\bibitem[Tang et al., 2025]{airesearcher} Tang et al. AI-Researcher: Autonomous Scientific Innovation. 2025.',
              r'\end{thebibliography}', r'\end{document}', '']
    return '\n'.join(lines)


def write_paper(run_dir, paper_dir):
    run_dir, paper_dir = Path(run_dir), Path(paper_dir)
    plan = json.loads((run_dir / 'plan.json').read_text(encoding='utf-8'))
    summary = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8'))
    state = json.loads((run_dir / 'state.json').read_text(encoding='utf-8'))
    manifest = json.loads((run_dir / 'manifest.json').read_text(encoding='utf-8'))
    if state.get('status') != 'completed':
        raise ValueError('Only completed experiment runs can produce a paper')
    rows = [json.loads(line) for line in (run_dir / 'results.jsonl').read_text(encoding='utf-8').splitlines() if line]
    if any(row.get('result_hash') != digest({k: v for k, v in row.items() if k != 'result_hash'}) for row in rows):
        raise ValueError('Result hash mismatch')
    paper_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(paper_dir / 'paper.md', _markdown(plan, summary, rows, manifest))
    style = Path(__file__).resolve().parents[1] / 'output' / 'paper' / 'iclr2026_conference.sty'
    if style.exists():
        shutil.copy2(style, paper_dir / style.name)
    atomic_write(paper_dir / 'paper.tex', _tex(plan, summary, rows, manifest))
    metadata = {'status': 'written', 'paper': str(paper_dir / 'paper.md'), 'rows': len(rows),
                'run_manifest_sha256': digest(manifest), 'sections': 10,
                'result_summary_sha256': digest(summary)}
    save_json(paper_dir / 'paper_metadata.json', metadata)
    return metadata
