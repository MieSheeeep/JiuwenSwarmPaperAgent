"""Registered local figure skills implementing publication guidelines.

Guideline provenance: scientific-visualization and matplotlib SKILL.md
(K-Dense, MIT). Rule integration is explicit Python, not arbitrary Markdown
execution. No remote image provider is configured or invoked.
"""
import hashlib
import json
from pathlib import Path

SKILLS = [
    {'id': 'scientific-visualization', 'name': 'Scientific visualization', 'enabled': True,
     'engine': 'Matplotlib', 'kind': 'Measured results', 'description': 'True-data plots; English labels, colorblind-safe colors, vector output and explicit sample sizes.'},
    {'id': 'architecture-vector', 'name': 'Editable architecture', 'enabled': True,
     'engine': 'Matplotlib + structured JSON', 'kind': 'Method diagram', 'description': 'Source-grounded stages; editable JSON plus SVG, PDF and PNG.'},
    {'id': 'scientific-schematics', 'name': 'Scientific schematics', 'enabled': False,
     'engine': 'External image model', 'kind': 'Optional AI illustration',
     'description': 'Requires a separately configured image-generation provider. The current DeepSeek text configuration does not provide images. No remote calls are made.'},
]
PROFILES = {'color': ['#009E73', '#0072B2', '#E69F00', '#CC79A7'],
            'mono': ['#333333', '#777777', '#999999', '#555555']}


def render_figures(summary, output, profile='color'):
    if profile not in PROFILES: raise ValueError('Unknown figure profile')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = [row for row in summary['methods'] if row['split'] == 'test' and row['budget'] == 256]
    if not rows: raise ValueError('No primary held-out data available')
    colors = PROFILES[profile]
    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.spines.top': False,
                         'axes.spines.right': False, 'pdf.fonttype': 42, 'svg.fonttype': 'none'}):
        fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.3), layout='constrained')
        names = [r['policy'].replace('_', ' ') for r in rows]
        y = list(range(len(rows)))
        for ax in axes: ax.set_yticks(y, names); ax.invert_yaxis(); ax.set_axisbelow(True); ax.grid(axis='x', alpha=.15)
        bars = axes[0].barh(y, [100*r['exact_accuracy'] for r in rows], color=colors[0], height=.6)
        axes[0].set_xlim(0, 116); axes[0].set_xlabel('Exact accuracy (%)')
        axes[0].set_title('(a) Primary held-out comparison', loc='left', fontsize=9)
        for bar, r in zip(bars, rows):
            axes[0].text(bar.get_width()+1, bar.get_y()+bar.get_height()/2,
                         f"{r['exact_correct']}/{r['tasks']}", va='center', fontsize=7)
        axes[1].barh(y, [r['actual_total_tokens']/r['tasks'] for r in rows], color=colors[1], height=.6)
        axes[1].set_xlabel('Provider tokens per task\n(including summaries)')
        axes[1].set_title('(b) Actual API usage', loc='left', fontsize=9)
        fig.supxlabel('256 proxy-token selected context; full history is unbounded. Descriptive point estimates only.', fontsize=7)
        for suffix in ('pdf', 'svg', 'png'): fig.savefig(output/f'results.{suffix}', dpi=220)
        plt.close(fig)
        stages = ['Append-only\nsource records', 'Effective and\nobserved cutoffs', 'Atomic version /\nconflict groups', 'Joined-text\nbudget packing', 'ReActAgent\nanswer + usage']
        spec = {'schema_version': 1, 'direction': 'left-to-right', 'stages': stages,
                'meaning': 'Source selection returns evidence records, not gold answers.'}
        (output/'architecture.json').write_text(json.dumps(spec, indent=2)+'\n', encoding='utf-8')
        fig, ax = plt.subplots(figsize=(6.5, 1.5)); ax.set(xlim=(0, 10), ylim=(0, 2)); ax.axis('off')
        for i, stage in enumerate(stages):
            x = .08+i*2
            ax.add_patch(FancyBboxPatch((x,.6),1.7,.85,boxstyle='round,pad=.05',facecolor='#F7F7F7',edgecolor=colors[i%len(colors)], linewidth=1.2))
            ax.text(x+.85,1.025,stage,ha='center',va='center',fontsize=8)
            if i < 4: ax.annotate('',xy=(x+1.96,1.025),xytext=(x+1.76,1.025),arrowprops={'arrowstyle':'->','color':'#555555'})
        ax.text(5,.2,spec['meaning'],ha='center',fontsize=7,color='#555555')
        for suffix in ('pdf','svg','png'): fig.savefig(output/f'architecture.{suffix}', dpi=220,bbox_inches='tight')
        plt.close(fig)
    manifest = {'skills': ['scientific-visualization','architecture-vector'], 'profile': profile,
                'target_width_inches':6.5,'minimum_font_points':7,
                'rules': ['English labels', 'actual primary held-out data', 'explicit denominators',
                          'no invented error bars or significance', 'full history marked unbounded',
                          'PDF/SVG vector exports', 'editable structured architecture'],
                'data_sha256': hashlib.sha256(json.dumps(summary,sort_keys=True).encode()).hexdigest(),
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()
                          if p.name.startswith(('architecture.', 'results.'))}}
    (output/'figure_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest
