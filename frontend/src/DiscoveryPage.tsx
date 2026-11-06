import { useEffect, useState } from 'react';
import { get } from './api';
import { Badge, Panel } from './components';

type Paper = { id: string; title: string; url: string; reading_scope: string };
type Discovery = { id: string; topic: string; status: string; reason?: string; resources: {api_calls?: number; known_api_tokens?: number}; bundle: null | { sources: Paper[]; literature_review: {comparison: string; papers: {paper_id: string; method: string; evaluation: string; limitations: string; evidence: {chunk_id: string; quote: string}[]}[]}; question_formulation: {selected_id: string; candidates: {id: string; question: string; hypothesis: string; motivation: string; falsification: string}[]}; experiment_design: Record<string, unknown>; closest_work: {status: string; papers: Paper[]}; handoff: {status: string} } };

export default function DiscoveryPage() {
  const [rows, setRows] = useState<Discovery[]>([]), [error, setError] = useState(''), [busy, setBusy] = useState(true);
  const [selected, setSelected] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    get<Discovery[]>('/api/discovery', controller.signal).then(value => { setRows(value); setSelected(value[0]?.id || ''); })
      .catch(e => { if (e.name !== 'AbortError') setError(e.message); }).finally(() => setBusy(false));
    return () => controller.abort();
  }, []);
  const row = rows.find(r => r.id === selected), bundle = row?.bundle;
  return <>
    <div className="studio-banner"><div><div className="eyebrow">LITERATURE → QUESTION → EXPERIMENT</div><h2>先查文献，再决定做什么实验。</h2><p>每个问题保留来源和可推翻它的实验标准；有限检索不能证明创新。</p></div></div>
    {busy && <p role="status">正在读取文献与研究方案…</p>}
    {error && <p role="alert" className="notice warning">{error}</p>}
    {!busy && !error && !rows.length && <p>尚无研究方案。通过 research.discovery 命令运行后刷新；本页面不会启动模型调用。</p>}
    {!!rows.length && <label>研究方案 <select className="run-select" value={selected} onChange={e => setSelected(e.target.value)}>{rows.map(r => <option key={r.id} value={r.id}>{r.id}</option>)}</select></label>}
    {row && <Panel title={row.topic} eyebrow="RESEARCH DESIGN"><p><Badge tone={row.status === 'completed' ? '' : 'warning'}>{row.status === 'completed' ? '方案已生成 · 实验未执行' : row.status}</Badge> 已记录 {row.resources.api_calls ?? 0} 次调用 / {row.resources.known_api_tokens ?? 0} tokens</p>{row.reason && <p role="alert">{row.reason}</p>}</Panel>}
    {bundle && <>
      <Panel title="1 · 文献阅读与比较" eyebrow="SOURCE EVIDENCE"><p>{bundle.literature_review.comparison}</p>{bundle.sources.map(p => {
        const note = bundle.literature_review.papers.find(n => n.paper_id === p.id);
        return <details key={p.id}><summary>{p.title} · {p.reading_scope === 'abstract_only' ? '仅摘要' : '正文摘录'}</summary><p><a href={p.url} target="_blank" rel="noreferrer">原始论文</a></p><p>方法：{note?.method}</p><p>评测：{note?.evaluation}</p><p>局限：{note?.limitations}</p>{note?.evidence.map((e, i) => <blockquote key={i}>{e.quote}<br/>{e.chunk_id}</blockquote>)}</details>;
      })}</Panel>
      <Panel title="2 · 问题与假设" eyebrow="UNVERIFIED CANDIDATES">{bundle.question_formulation.candidates.map(c => <details key={c.id} open={c.id === bundle.question_formulation.selected_id}><summary>{c.question}{c.id === bundle.question_formulation.selected_id ? '（本轮选择）' : ''}</summary><p>依据与推断：{c.motivation}</p><p>假设：{c.hypothesis}</p><p>推翻条件：{c.falsification}</p></details>)}</Panel>
      <Panel title="3 · 最近工作复查" eyebrow="CLOSEST WORK"><p>{bundle.closest_work.status} · 检索命中仍需阅读，不能据此认定无人做过。</p><ul>{bundle.closest_work.papers.map(p => <li key={p.id}><a href={p.url} target="_blank" rel="noreferrer">{p.title}</a></li>)}</ul></Panel>
      <Panel title="4 · 实验设计与交接" eyebrow="EXPERIMENT PLAN"><p>{bundle.handoff.status === 'registered_protocol_ready' ? '已有实验器支持此固定方案；尚未启动实验。' : '方案需要新增实验实现；不会拿旧实验冒充验证。'}</p><details><summary>查看完整实验方案</summary><pre style={{whiteSpace:'pre-wrap', overflowWrap:'anywhere'}}>{JSON.stringify(bundle.experiment_design, null, 2)}</pre></details></Panel>
    </>}
  </>;
}
