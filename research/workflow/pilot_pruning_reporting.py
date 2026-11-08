"""Deterministic, source-checked reporting for the fixed-look pruning audit.

Count outcomes are integration states, never experimental replications. All
reported costs are illustrative decision units rather than runtime or money.
"""
from collections import defaultdict
import csv
import itertools
import json
import math
from pathlib import Path

from research.artifacts import digest, file_digest, save_json

MIXTURES = ('equal', 'futile3x', 'useful3x')
COSTS = tuple(itertools.product((.05, .25, 1.), (.25, 1., 4.), (1., 4., 16.)))
LIMITATIONS = [
    'This is a conditional decision-policy audit; no statistical novelty is claimed. Classical fixed-look interval and futility machinery is prior art.',
    'Integrated multinomial states are not independent replications. Separate fixed sample sizes are not optional repeated looks.',
    'Empirical paired-correctness distributions are conditional finite-benchmark references, not population ground truth. Seeds, pairs and fitted models share data.',
    'Paired-normal coverage is approximate. Conservative joint Clopper-Pearson coverage uses a classical marginal union bound at a single fixed look.',
    'Boundary gains equal to delta are neither useful nor futile. Error masses exclude these boundaries, while automatic coverage and deferral include them.',
    'Costs are illustrative decision units, not measured tokens or money. Deferring everything incurs its full nonzero deferral cost.',
    'Equal-regime, futile3x and useful3x mixtures are sensitivity analyses, not estimated deployment prevalences. Random deferral is matched across each heterogeneous mixture, not within each truth category.',
]


def _write_csv(path, rows):
    fields = sorted({key for row in rows for key in row})
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _validate(rows):
    if not rows:
        raise ValueError('No saved rows to report')
    seen = set()
    for row in rows:
        identity = tuple(row[k] for k in ('case_id', 'n', 'delta', 'interval', 'policy'))
        if identity in seen:
            raise ValueError('Duplicate saved condition')
        seen.add(identity)
        if row['kind'] not in ('synthetic', 'empirical'):
            raise ValueError('Unknown saved row kind')
        expected_truth = ('boundary' if abs(row['gain']-row['delta']) <= 1e-12
                          else 'useful' if row['gain'] > row['delta'] else 'futile')
        if row['truth'] != expected_truth:
            raise ValueError('Saved truth conflicts with gain and delta')
        for key in ('p_go', 'p_no_go', 'p_defer', 'ci_coverage',
                    'false_go_probability', 'false_prune_probability'):
            value = row[key]
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not -1e-10 <= value <= 1+1e-10:
                raise ValueError(f'Invalid probability: {key}')
        if abs(sum(row[k] for k in ('p_go', 'p_no_go', 'p_defer'))-1.) > 1e-8:
            raise ValueError('Saved decision probability mass is not one')
        for key, expected in [('false_go_probability', row['p_go'] if expected_truth == 'futile' else 0.),
                              ('false_prune_probability', row['p_no_go'] if expected_truth == 'useful' else 0.)]:
            if abs(row[key]-expected) > 1e-8:
                raise ValueError(f'Saved {key} conflicts with truth')


def cost_sweep(metrics):
    """Retain every registered cost setting; charge all three action losses."""
    return [{**row, 'c_defer': cd, 'c_false_go': cg, 'c_false_prune': cp,
             'expected_cost': cd*row['p_defer'] + cg*row['false_go_probability'] +
                              cp*row['false_prune_probability']}
            for row in metrics for cd, cg, cp in COSTS]


def _frontier(costs):
    groups = defaultdict(list)
    for row in costs:
        key = tuple(row[k] for k in ('kind', 'n', 'delta', 'interval', 'mixture',
                                    'c_defer', 'c_false_go', 'c_false_prune'))
        groups[key].append(row)
    frontier = []
    for _, group in sorted(groups.items(), key=lambda item: str(item[0])):
        best = min(row['expected_cost'] for row in group)
        first = group[0]
        frontier.append({k: first[k] for k in ('kind', 'n', 'delta', 'interval', 'mixture',
                                             'c_defer', 'c_false_go', 'c_false_prune')} |
                        {'minimum_expected_cost': best,
                         'minimizers': '|'.join(sorted(row['policy'] for row in group
                                                      if abs(row['expected_cost']-best) <= 1e-12))})
    return frontier


def analyze(study, protocol):
    """Read actual results after study audit; never run models or regenerate data."""
    audit = study.audit(protocol)
    if isinstance(audit, dict) and (audit.get('passed') is False or audit.get('ok') is False):
        raise ValueError('Study source audit failed')
    source = Path(study.root)/'results.json'
    saved = json.loads(source.read_text(encoding='utf-8'))
    rows = saved['rows']
    rows_hash = digest(rows)
    if saved.get('rows_sha256') != rows_hash:
        raise ValueError('Saved result rows hash mismatch')
    _validate(rows)
    from .pilot_pruning_study import mixture_summary
    derived_rows = [{**row, 'automatic_coverage': row['p_go']+row['p_no_go']} for row in rows]
    metrics = []
    for mixture in MIXTURES:
        for row in mixture_summary(derived_rows, mixture=mixture):
            metrics.append({**row, 'mixture': mixture,
                            'automatic_coverage': row['p_go']+row['p_no_go']})
    metrics.sort(key=lambda row: tuple(str(row[k]) for k in
                                     ('kind', 'delta', 'n', 'interval', 'mixture', 'policy')))
    costs = cost_sweep(metrics)
    frontier = _frontier(costs)
    out = Path(study.directory)/'analysis'
    out.mkdir(parents=True, exist_ok=True)
    for name, values in [('all_metrics', rows), ('mixture_metrics', metrics),
                         ('cost_sweep', costs), ('cost_frontier', frontier)]:
        _write_csv(out/f'{name}.csv', values)
    empirical = sorted({r['dataset'] for r in rows if r['kind'] == 'empirical'})
    scope = {'saved_rows': len(rows), 'regimes': len({(r['kind'], r['case_id']) for r in rows}),
             'empirical_datasets': empirical,
             'empirical_dataset_count': len(empirical),
             'integration_is_replication': False}
    summary = (f"The source-checked file contains {len(rows)} decision-probability rows across "
               f"{scope['regimes']} conditional regimes and {len(empirical)} empirical datasets. "
               'Integrated count states and overlapping seeds are not independent replications. '
               'All saved conditions appear in all_metrics.csv. Mixture probabilities, both error '
               'directions, automatic coverage and interval coverage appear in mixture_metrics.csv. '
               'Every registered combination of nonzero deferral and error costs appears in cost_sweep.csv; '
               'cost_frontier.csv retains all tied minimizers at each cost setting. '
               'This audit makes no statistical novelty claim. ')
    summary += ('Empirical replay is conditional on finite benchmark predictions, shared splits and fits.'
                if empirical else 'No empirical replay rows were saved; no empirical outcomes are asserted.')
    evidence = {'results_path': str(source.resolve()), 'results_sha256': file_digest(source),
                'rows_sha256': rows_hash,
                'tables': {path.name: file_digest(path) for path in sorted(out.glob('*.csv'))}}
    value = {'metrics': metrics, 'costs': costs, 'cost_frontier': frontier,
             'rows_hash': rows_hash, 'audit': audit, 'resources': saved.get('resources', {}),
             'scope': scope, 'evidence': evidence, 'evidence_summary': summary,
             'claims': [{'status': 'SUPPORTED', 'kind': 'observed',
                         'claim': f'{len(rows)} saved rows were source-checked and tabulated without selecting favorable outcomes.',
                         'evidence': rows_hash}],
             'limitations': LIMITATIONS,
             'tables': make_tables(metrics),
             'figures': make_figures(study, metrics, costs, protocol.get('figure_formats', ['pdf', 'png']))}
    (out/'evidence_summary.md').write_text(summary+'\n\n'+'\n\n'.join(LIMITATIONS)+'\n', encoding='utf-8')
    save_json(out/'summary.json', value)
    return value


MAIN_POLICIES = ('legacy_binary', 'delta_binary', 'tri_state', 'matched_random_delta_binary')


def _display_delta(metrics):
    values = sorted({r['delta'] for r in metrics})
    return .02 if .02 in values else values[0]


def make_tables(metrics):
    delta = _display_delta(metrics)
    tables = []
    for kind in ('synthetic', 'empirical'):
        selected = [r for r in metrics if r['kind'] == kind and r['delta'] == delta
                    and r['mixture'] == 'equal' and r['n'] in (32, 128, 256)
                    and r['policy'] in MAIN_POLICIES]
        if not selected:
            continue
        keys = ('n', 'interval', 'policy', 'automatic_coverage', 'false_go_probability',
                'false_prune_probability', 'p_defer')
        tables.append({'section': 'Results',
            'columns': ['n', 'Interval', 'Policy', 'Coverage', 'False GO', 'False prune', 'Defer'],
            'rows': [[round(r[k], 3) if isinstance(r[k], float) else r[k] for k in keys] for r in selected],
            'caption': f'{kind.capitalize()} equal-regime mixture, delta={delta:g}. Display n=32,128,256 was fixed before outcomes. Errors are unconditional mixture masses; boundary cases have neither error direction. Coverage here means automatic action, not interval coverage. All cells, diagnostic policies, both coverage definitions and mixtures remain in the CSV files. Empirical values are conditional finite-benchmark references.'})
    return tables


def make_figures(study, metrics, costs, formats):
    """Three displays fixed before final outcomes; full results remain in CSV.

    Tiny execution fixtures may use their available delta/n, explicitly labelled.
    """
    if not formats or any(fmt not in ('pdf', 'svg', 'png') for fmt in formats):
        raise ValueError('Figure formats must be pdf, svg or png')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    out = Path(study.directory)/'figures'
    out.mkdir(parents=True, exist_ok=True)
    figures = []
    delta = _display_delta(metrics)
    colors = ('#0072B2', '#E69F00', '#009E73', '#CC79A7')
    markers = ('o', 's', '^', 'D')
    styles = ('-', '--', '-.', ':')

    def save(fig, name, caption):
        paths = {}
        for fmt in formats:
            path = out/f'{name}.{fmt}'
            fig.savefig(path, dpi=300, bbox_inches='tight', metadata={'Creator': 'pilot_pruning_reporting'})
            paths[fmt] = {'path': path.relative_to(study.directory).as_posix(), 'sha256': file_digest(path)}
        plt.close(fig)
        primary = paths.get('png', next(iter(paths.values())))
        figures.append({'section': 'Results', **primary, 'formats': paths, 'caption': caption})

    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 9,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'}):
        for kind in ('synthetic', 'empirical'):
            selected = [r for r in metrics if r['kind'] == kind and r['delta'] == delta
                        and r['mixture'] == 'equal' and r['policy'] in MAIN_POLICIES]
            if not selected:
                continue
            fig, axes = plt.subplots(3, 2, figsize=(8, 7), layout='constrained')
            for col, interval in enumerate(('paired_normal', 'exact_joint')):
                for policy, color, marker, style in zip(MAIN_POLICIES, colors, markers, styles):
                    points = sorted([r for r in selected if r['interval'] == interval and r['policy'] == policy],
                                    key=lambda r: r['n'])
                    for row, key in enumerate(('automatic_coverage', 'false_prune_probability', 'false_go_probability')):
                        axes[row, col].plot([r['n'] for r in points], [r[key] for r in points],
                            color=color, marker=marker, linestyle=style, markersize=4,
                            label=policy.replace('_', ' '))
                axes[0, col].set_title(interval.replace('_', ' '))
                axes[2, col].set_xlabel('Fixed pilot size n')
                for row, label in enumerate(('Automatic coverage', 'False prune mass', 'False GO mass')):
                    axes[row, col].set_ylabel(label)
                    axes[row, col].set_ylim(-.02, 1.02)
                    axes[row, col].grid(alpha=.2)
            handles, labels = axes[0, 0].get_legend_handles_labels()
            fig.legend(handles, labels, loc='outside lower center', ncol=2, fontsize=8)
            fig.suptitle(f'{kind.capitalize()} reference: equal mixture, delta={delta:g}')
            save(fig, f'{kind}_fixed_n',
                 f'{kind.capitalize()} equal-regime mixture at delta={delta:g}. Both interval methods and the same four prespecified policies are shown over all available fixed n. Automatic coverage and both error directions are displayed together. Matched random deferral uses the tri-state aggregate defer rate across the mixture. Curves connect separate fixed-budget designs, not sequential looks. Points are integrated probabilities; count states and shared seeds are not independent replications, so no replication-based error bars apply. All conditions and interval coverage remain in the CSV files.')
        display_n = 256 if any(r['n'] == 256 for r in metrics) else max(r['n'] for r in metrics)
        selected = [r for r in costs if r['delta'] == delta and r['n'] == display_n
                    and r['interval'] == 'exact_joint' and r['mixture'] == 'equal']
        by_policy = defaultdict(dict)
        for row in selected:
            by_policy[(row['kind'], row['policy'])][(row['c_defer'], row['c_false_go'], row['c_false_prune'])] = row['expected_cost']
        keys = sorted(by_policy)
        if keys:
            data = [[by_policy[key][cost] for cost in COSTS] for key in keys]
            fig, ax = plt.subplots(figsize=(13, max(4, .3*len(keys))), layout='constrained')
            im = ax.imshow(data, cmap='cividis', aspect='auto', vmin=0)
            ax.set_yticks(range(len(keys)), [' '.join(key).replace('_', ' ') for key in keys])
            ax.set_xticks(range(27), [f'{cd:g}/{cg:g}/{cp:g}' for cd, cg, cp in COSTS], rotation=65, ha='right')
            ax.set_xlabel('Cost setting: deferral / false GO / false prune (decision units)')
            ax.set_title(f'Equal mixture, exact joint interval, n={display_n}, delta={delta:g}')
            fig.colorbar(im, ax=ax, label='Expected cost (decision units)')
            save(fig, 'cost_sensitivity',
                 f'All policies and all 27 registered cost triples at prespecified n={display_n}, delta={delta:g}, exact-joint interval and equal-regime mixture. All nonzero deferral costs are charged. Exact values, all other n/delta/mixtures and all tied minimum-cost policies are in cost_sweep.csv and cost_frontier.csv. Costs are illustrative decision units, not measured resources. Always-defer is a diagnostic rather than a free-benefit comparator.')
    return figures
