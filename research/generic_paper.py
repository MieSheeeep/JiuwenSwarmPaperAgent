"""Result-bound manuscript writer for registered experiments."""

import json
from pathlib import Path

from research.artifacts import atomic_write, digest, save_json


def _latex(text):
    return (str(text).replace('\\', r'\textbackslash{}').replace('&', r'\&')
            .replace('%', r'\%').replace('_', r'\_').replace('#', r'\#')
            .replace('{', r'\{').replace('}', r'\}'))


def write_paper(run_dir, paper_dir):
    run_dir, paper_dir = Path(run_dir), Path(paper_dir)
    plan = json.loads((run_dir / 'plan.json').read_text(encoding='utf-8'))
    summary = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8'))
    state = json.loads((run_dir / 'state.json').read_text(encoding='utf-8'))
    if state.get('status') != 'completed':
        raise ValueError('Only completed experiment runs can produce a paper')
    rows = [json.loads(line) for line in (run_dir / 'results.jsonl').read_text(encoding='utf-8').splitlines() if line]
    if any(row.get('result_hash') != digest({k: v for k, v in row.items() if k != 'result_hash'}) for row in rows):
        raise ValueError('Result hash mismatch')
    paper_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        '# Adaptive Evidence Stopping for a Small Multi-hop QA Benchmark', '',
        '> This is an automatically assembled short-paper draft. The benchmark is synthetic and the result does not establish general novelty.', '',
        '## Abstract', '',
        'We test whether stopping retrieval after the required evidence hops can preserve answer accuracy while avoiding unnecessary context. '
        f"The frozen run contains {len(rows)} scored method-task rows and uses the registered `adaptive-qa-v1` protocol.", '',
        '## Research question and hypothesis', '',
        'The question is whether an auditable evidence-coverage stop rule matches fixed two-passage retrieval on this task while using no more passages. '
        'The claim is falsified if adaptive stopping loses paired exact accuracy or uses more context.', '',
        '## Protocol', '',
        f"- Adapter: `{plan['adapter']}`; dataset: `{plan['protocol']['dataset']}`; seed: `{plan['protocol']['seed']}`.",
        f"- Methods: {', '.join('`' + method + '`' for method in plan['methods'])}.",
        '- The data, context selection, prompts, calls, and answer scores are stored in the run directory.', '',
        '## Results', '',
        '| Method | Exact accuracy | Evidence recall | Mean passages | Provider tokens |',
        '|---|---:|---:|---:|---:|',
    ]
    for method in summary['methods']:
        metric = summary['by_method'][method]
        lines.append(f"| `{method}` | {metric['exact_accuracy']:.2f} | {metric['evidence_recall']:.2f} | "
                     f"{metric['mean_context_passages']:.2f} | {metric['provider_tokens']} |")
    lines += ['', '## Limitations', '',
              '- The dataset is synthetic, small, and has a fixed two-hop structure.',
              '- The adapter is registered and safe, but it does not let a model invent and execute arbitrary new algorithms.',
              '- The run provides evidence for this protocol only; it is not a Stanford or expert review score.', '',
              '## Reproducibility', '',
              f"- Run manifest SHA-256: `{digest(json.loads((run_dir / 'manifest.json').read_text(encoding='utf-8')))}`.",
              '- Re-run with `python -m research.generic_runner` after configuring the same provider and budget.']
    markdown = '\n'.join(lines) + '\n'
    atomic_write(paper_dir / 'paper.md', markdown)
    tex_lines = [r'\documentclass{article}', r'\usepackage[margin=1in]{geometry}', r'\begin{document}',
                 r'\title{Adaptive Evidence Stopping for a Small Multi-hop QA Benchmark}', r'\date{}', r'\maketitle']
    tex_lines += [r'\section*{Abstract}', _latex(lines[6]), r'\section{Protocol}',
                 _latex('Synthetic benchmark; registered adaptive-qa-v1 adapter; exact answer scoring.'),
                 r'\section{Results}', r'\begin{tabular}{lrrrr}', r'Method & Accuracy & Evidence & Passages & Tokens\\ \hline']
    for method in summary['methods']:
        metric = summary['by_method'][method]
        tex_lines.append(_latex(method) + f" & {metric['exact_accuracy']:.2f} & {metric['evidence_recall']:.2f} & "
                         f"{metric['mean_context_passages']:.2f} & {metric['provider_tokens']}\\\\")
    tex_lines += [r'\end{tabular}', r'\section{Limitations}',
                  _latex('The data are synthetic and the registered adapter does not execute arbitrary generated code.'),
                  r'\end{document}', '']
    atomic_write(paper_dir / 'paper.tex', '\n'.join(tex_lines))
    metadata = {'status': 'written', 'paper': str(paper_dir / 'paper.md'),
                'rows': len(rows), 'run_manifest_sha256': digest(json.loads((run_dir / 'manifest.json').read_text(encoding='utf-8')))}
    save_json(paper_dir / 'paper_metadata.json', metadata)
    return metadata
