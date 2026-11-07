"""Import selected, unmodified Open Research Skills at a pinned commit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

COMMIT='c79bac60f882b626e1754bff95101441e165e4ec'
SKILLS=('prepare-conference-manuscripts','run-cold-review-panel','research-publication-pipeline')
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    source=args.source.resolve()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if head!=COMMIT:raise ValueError('Source checkout does not match pinned commit')
    if subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():
        raise ValueError('Source checkout contains local changes')
    target=ROOT/'research/skillpacks/open-research-skills'
    candidates=[source/name for name in ('LICENSE','NOTICE','THIRD_PARTY.md')]
    for name in SKILLS:candidates.extend(p for p in (source/'skills'/name).rglob('*') if p.is_file())
    entries={}
    for path in sorted(candidates):
        relative=path.relative_to(source)
        dest=target/relative
        # Import Git blobs, not a Windows checkout's CRLF-converted working bytes.
        content=subprocess.check_output(['git','show',COMMIT+':'+relative.as_posix()],cwd=source)
        if dest.exists() and dest.read_bytes() not in (content,path.read_bytes()):
            raise ValueError('Refusing to replace locally modified vendor resource: '+str(relative))
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists() or dest.read_bytes()!=content:dest.write_bytes(content)
        entries[relative.as_posix()]={'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size}
    manifest={'repository':'https://github.com/gxCaesar/open-research-skills','commit':COMMIT,
              'skills':list(SKILLS),'upstream_files_modified':False,'files':entries}
    # Import metadata is generated; upstream files remain byte-identical to the source checkout.
    (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'commit':COMMIT,'files':len(entries),'bytes':sum(v['bytes'] for v in entries.values())}))


if __name__=='__main__':main()
