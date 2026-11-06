import type { ReactNode } from 'react';
import { ArrowUpRight, Download, Check, Circle, FileText } from 'lucide-react';
import { fileUrl, number, percent, type Artifact, type Method, type Overview } from './api';

export const policyNames: Record<string, string> = { versioned: 'Versioned', lexical: 'Lexical', bm25: 'BM25', recent: 'Recent', full: 'Full history', no_time: 'No time', no_conflict: 'No conflict', lexical_summary: 'Lexical + summary' };
export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) { return <span className={`badge ${tone}`}>{children}</span>; }
export function Panel({ title, eyebrow, action, children, className = '' }: { title: string; eyebrow?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-head"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2></div>{action}</div>{children}</section>;
}
export function Stat({ label, value, suffix, note, icon, accent }: { label: string; value: ReactNode; suffix?: string; note: string; icon: ReactNode; accent?: boolean }) {
  return <div className={`stat ${accent ? 'accent' : ''}`}><div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><div className="stat-value">{value}<small>{suffix}</small></div><div className="stat-note">{note}</div></div>;
}
export function Comparison({ methods }: { methods: Method[] }) {
  const sorted = [...methods].sort((a, b) => b.exact_accuracy - a.exact_accuracy || (a.policy === 'versioned' ? -1 : b.policy === 'versioned' ? 1 : a.policy.localeCompare(b.policy)));
  return <div className="comparison"><div className="chart-scale"><span>Exact match accuracy</span><span>0 — 100%</span></div>{sorted.map(m => <div className={`bar-row ${m.policy === 'versioned' ? 'highlight' : ''}`} key={m.policy}><span className="bar-label">{policyNames[m.policy] || m.policy}{m.policy === 'full' && <small>无上限参照</small>}</span><div className="bar-track"><div className="bar-fill" style={{ width: `${m.exact_accuracy * 100}%` }} /></div><span className="bar-number">{percent(m.exact_accuracy)}</span><span className="bar-fraction">{m.exact_correct}/{m.tasks}</span></div>)}</div>;
}
export function Workflow({ data }: { data: Overview }) {
  const stages = [ ['研究规划', '固定课题与实验协议', data.tasks > 0], ['实验执行', `${number(data.grid_count)} 个条件 · ${data.model || '模型未知'}`, data.complete], ['证据校验', '独立复算与产物关联', data.complete], ['英文论文', 'Manuscript & LaTeX', data.availability.paper], ['外部评审', data.review.score == null ? '等待新稿评测' : `Stanford AI · ${data.review.score}/${data.review.scale}`, data.availability.review] ] as const;
  return <div className="workflow">{stages.map(([title, sub, done], i) => <div className="workflow-step" key={title}><div className={`step-icon ${done ? 'done' : ''}`}>{done ? <Check size={13}/> : <Circle size={13}/>}</div><div><strong>{title}</strong><p>{sub}</p></div><span className="step-order">0{i + 1}</span></div>)}</div>;
}
export function FileLink({ run, file, compact = false }: { run: string; file: Artifact; compact?: boolean }) {
  return <a className={`file-link ${compact ? 'compact' : ''}`} href={fileUrl(run, file.id)} download={file.id !== 'paper'} target={file.id === 'paper' ? '_blank' : undefined} rel="noreferrer"><div className="file-icon"><FileText size={19}/></div><div><strong>{file.title}</strong><span>{file.filename} · {file.bytes > 1048576 ? (file.bytes / 1048576).toFixed(1) + ' MB' : Math.ceil(file.bytes / 1024) + ' KB'}{file.private ? ' · 含私有评审 Token' : ''}</span></div>{file.id === 'paper' ? <ArrowUpRight size={17}/> : <Download size={17}/>}</a>;
}
