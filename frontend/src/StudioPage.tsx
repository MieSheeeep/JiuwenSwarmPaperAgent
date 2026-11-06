import { useEffect, useState } from 'react';
import { Code2, Download, FileText, History, Image, LoaderCircle, Save, ShieldCheck, WandSparkles } from 'lucide-react';
import { get, post, runUrl, type Overview } from './api';
import { Badge, Panel } from './components';

type Sections = Record<string, string>;
type Revision = { id: string; created_at: string; parent: string | null; changes: Record<string, { before: string; after: string; diff: string }> };
type Skill = { id: string; name: string; enabled: boolean; engine: string; description: string };
type Job = { id: string; kind: string; status: string; log: string[]; error?: string; files: Record<string, string>; profile: string };
type Detail = Revision & { sections: Sections; latex: string; jobs: Job[] };
type State = { revisions: Revision[]; latest: string | null; original_sections: Sections; skills: Skill[] };
const sectionNames: Record<string, string> = { abstract: 'Abstract · 摘要', introduction: 'Introduction · 引言', related_work: 'Related work · 相关工作', methods: 'Methods · 方法', discussion: 'Discussion · 讨论', conclusion: 'Conclusion · 结论' };

export default function StudioPage({ data }: { data: Overview }) {
  const base = `${runUrl(data.id)}/studio`;
  const [state, setState] = useState<State | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [selected, setSelected] = useState('original');
  const [sections, setSections] = useState<Sections>({});
  const [original, setOriginal] = useState<Sections>({});
  const [section, setSection] = useState('abstract');
  const [tab, setTab] = useState('prose');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState('color');
  const [job, setJob] = useState<Job | null>(null);
  const dirty = JSON.stringify(sections) !== JSON.stringify(original);
  const asset = (id: string, name: string) => `${base}/${selected}/jobs/${id}/files/${encodeURIComponent(name)}`;
  async function loadRevision(id: string, remote: State) {
    setBusy(true); setError(''); setMessage('');
    try {
    const next = id === 'original' ? null : await get<Detail>(`${base}/${id}`);
    setSelected(id); setDetail(next);
    const text = next?.sections || remote.original_sections;
    setSections(text); setOriginal(text);
    setJob(next?.jobs[0] || null);
    } finally { setBusy(false); }
  }
  useEffect(() => {
    const controller = new AbortController();
    get<State>(base, controller.signal).then(async remote => {
      if (controller.signal.aborted) return;
      setState(remote); await loadRevision(remote.latest || 'original', remote);
    }).catch(e => { if (e.name !== 'AbortError') setError(e.message); setBusy(false); });
    return () => controller.abort();
  }, [base]);
  useEffect(() => { window.dispatchEvent(new CustomEvent('workbench-dirty',{detail:dirty})); return () => { window.dispatchEvent(new CustomEvent('workbench-dirty',{detail:false})); }; },[dirty]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => get<Job>(`${base}/${selected}/jobs/${job.id}`, controller.signal).then(value => { setJob(value); setError(''); }).catch(e => { if (e.name !== 'AbortError') { setError(e.message); setJob(value => value ? {...value} : null); } }), 1200);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [job, selected, base]);
  async function save() {
    if (!state) return; setBusy(true); setError('');
    try {
      const revision = await post<Revision>(base, { sections, base_revision: state.latest });
      const remote = await get<State>(base); setState(remote); await loadRevision(revision.id, remote);
      setMessage('已保存新修订。原始送评 PDF 保持不变，新修订尚无外部评分。');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function start(kind: string) {
    setBusy(true); setError(''); setMessage('');
    try { setJob(await post<Job>(`${base}/${selected}/jobs`, { kind, profile })); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const running = !!job && ['queued','running'].includes(job.status);
  return <>{error && <div role="alert" className="notice warning">{error}</div>}{message && <div role="status" className="notice">{message}</div>}<div className="studio-banner"><div><div className="eyebrow">MANUSCRIPT & FIGURE STUDIO</div><h2>英文写作，版本化构建。</h2><p>编辑英文正文，生成 LaTeX 与论文图，在新修订中编译预览。</p></div><Badge tone="warning">新修订 · 未评审</Badge></div>{!state ? <div className="empty-state"><LoaderCircle className="spin"/>正在载入写作工作区…</div> : <><div className="studio-toolbar"><label>论文版本<select aria-label="论文版本" value={selected} disabled={busy || running || dirty} onChange={e => loadRevision(e.target.value, state).catch(e => setError(e.message))}><option value="original">原始送评稿（保留原评分）</option>{state.revisions.map(r => <option value={r.id} key={r.id}>{new Date(r.created_at).toLocaleString('zh-CN')} · {r.id.slice(-7)}</option>)}</select></label><button className="text-button" disabled={!dirty||busy} onClick={() => setSections(original)}>放弃未保存修改</button><span className={dirty ? 'dirty-label' : 'muted'}>{dirty ? '● 正文有未保存修改' : '所有编辑已保存'}</span><button className="button primary" disabled={busy || running || !Object.keys(sections).length || (!dirty && selected !== 'original')} onClick={save}><Save size={15}/>{selected === 'original' ? '保存为新修订' : '保存新版本'}</button></div><Panel title="论文编辑器" eyebrow="EVIDENCE-BOUND ENGLISH WRITING" action={<Badge tone="neutral">测量表格保持原始证据</Badge>}><div className="studio-tabs"><button className={tab==='prose'?'selected':''} onClick={() => setTab('prose')}><FileText size={14}/>英文正文</button><button className={tab==='latex'?'selected':''} onClick={() => setTab('latex')}><Code2 size={14}/>生成的 LaTeX</button><button className={tab==='diff'?'selected':''} onClick={() => setTab('diff')}><History size={14}/>版本差异</button></div>{tab==='prose' ? <div className="editor-grid"><nav aria-label="论文章节">{Object.entries(sectionNames).map(([key,label]) => <button className={key===section?'selected':''} key={key} onClick={() => setSection(key)}>{label}</button>)}</nav><div className="section-editor"><label htmlFor="section-prose">{sectionNames[section]}</label><textarea id="section-prose" aria-label="English section editor" lang="en" spellCheck disabled={busy} value={sections[section] || ''} maxLength={24000} onChange={e => setSections({...sections,[section]:e.target.value})}/><div className="editor-foot"><span>{(sections[section] || '').trim().split(/\s+/).filter(Boolean).length} words</span><span>英文纯文本 · 引用使用已登记的 [key]</span></div></div></div> : tab==='latex' ? <div className="source-view">{dirty && <p className="notice warning">此处为已保存版本，先保存正文以更新 LaTeX。</p>}<pre>{detail?.latex || '先保存为新修订，即可查看生成的 LaTeX。'}</pre>{detail && <a className="text-button" href={`${base}/${selected}/latex`} download>下载 LaTeX 源文件<Download size={14}/></a>}</div> : <div className="source-view">{detail && Object.keys(detail.changes).length ? Object.entries(detail.changes).map(([key,value]) => <div key={key}><h3>{sectionNames[key]}</h3><pre>{value.diff}</pre></div>) : <p className="empty-inline">当前版本与父版本没有正文差异，或正在查看原始稿。</p>}</div>}</Panel><div className="notice"><ShieldCheck size={17}/><p>正文按纯文本转义后生成 LaTeX；不执行自由输入的 TeX 命令。数字主张与文字修改仍需审查，图表从固定证据生成。已送评稿和原评分始终单独保留。</p></div><Panel title="绘图 Skill 与编译" eyebrow="REGISTERED LOCAL SKILLS" className="figure-panel"><div className="skill-grid">{state.skills.map(skill => <div className={`skill-card ${skill.enabled?'':'disabled'}`} key={skill.id}><div><WandSparkles size={17}/><Badge tone={skill.enabled?'':'neutral'}>{skill.enabled?'已接入 · 本地执行':'可选 · 未配置'}</Badge></div><h3>{skill.name}</h3><small>{skill.engine}</small><p>{skill.description}</p></div>)}</div><div className="build-toolbar"><label>图表风格<select aria-label="图表风格" value={profile} onChange={e => setProfile(e.target.value)} disabled={running}><option value="color">色觉友好 · Color</option><option value="mono">灰度 · Grayscale</option></select></label><button className="button subtle" disabled={selected==='original'||dirty||busy||running} onClick={() => start('figures')}><Image size={15}/>生成论文图</button><button className="button primary" disabled={selected==='original'||dirty||busy||running} onClick={() => start('compile')}>{running ? <LoaderCircle className="spin" size={15}/> : <Code2 size={15}/>}编译新修订 PDF</button></div>{selected==='original' && <p className="small-print">先保存新修订，再绘图或编译。所有生成均在新的构建目录完成。</p>}{job && <div className="job-panel"><div className="job-heading"><strong>{job.kind==='compile'?'论文编译':'图表生成'}</strong><Badge tone={job.status==='succeeded'?'':job.status==='failed'?'warning':'neutral'}>{job.status}</Badge><span>{job.profile}</span></div><pre role="log">{job.log.join('\n')}{job.error ? '\n'+job.error : ''}</pre><div className="job-downloads">{Object.keys(job.files).map(name => <a key={name} className="text-button" href={asset(job.id,name)} target={name==='paper.pdf'?'_blank':undefined} rel="noreferrer" download={name!=='paper.pdf'}>{name}<Download size={12}/></a>)}</div>{job.files['results.png'] && <div className="figure-previews"><img src={asset(job.id,'results.png')} alt="Primary held-out accuracy and actual provider tokens; generated from frozen evidence"/><img src={asset(job.id,'architecture.png')} alt="Versioned source-memory architecture"/></div>}{job.status==='succeeded' && job.files['paper.pdf'] && <><p className="notice warning">新修订 PDF 尚未送评，原始外部评分不适用于此版本。</p><iframe className="pdf-frame" title="Unreviewed revision PDF" src={asset(job.id,'paper.pdf')}/></>}</div>}</Panel></>}</>;
}
