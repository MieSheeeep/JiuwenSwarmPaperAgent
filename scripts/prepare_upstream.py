"""Initialize official source and safely apply our versioned extension patch.

No reset, clean, or overwrite is performed if local edits conflict with the patch.
Run from any working directory with Python 3.12; no third-party packages needed.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run(['git', 'submodule', 'update', '--init', 'upstream'], cwd=ROOT, check=True)
    patch = ROOT/'output/framework_contribution.patch'
    def check(*args):
        return subprocess.run(['git', 'apply', '--check', *args, str(patch)],
                              cwd=ROOT/'upstream', capture_output=True).returncode == 0
    if check():
        subprocess.run(['git', 'apply', str(patch)], cwd=ROOT/'upstream', check=True)
        print('JiuwenSwarm extension patch applied.')
    elif check('--reverse'):
        print('JiuwenSwarm extension already applied; local files preserved.')
    else:
        print('Patch conflicts with local source edits. Inspect upstream; no files were reset.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
