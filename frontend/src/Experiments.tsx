import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Filter, Search, X, ArrowUpDown, Check, CircleAlert, LoaderCircle } from 'lucide-react';
import { get, number, percent, runUrl, type Case, type Overview } from './api';
import { Badge, Panel, policyNames } from './components';

const families: Record<string, string> = { static: '静态事实', late_stale: '迟到旧事实', historical: '历史查询', conflict: '事实冲突', deletion_no_answer: '删除 / 无答案', paraphrase_distractors: '改写与干扰' };

export default function Experiments({ data }: { data: Overview }) {
  const [rows, setRows] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [split, setSplit] = useState('test');
  const [budget, setBudget] = useState('256');
  const [policy, setPolicy] = useState('all');
  const [status, setStatus] = useState('all');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState(false);
  const [selected, setSelected] = useState<Case | null>(null);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    get<Case[]>(`${runUrl(data.id)}/cases`, controller.signal).then(setRows).catch(e => { if (e.name !== 'AbortError') setError(e.message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [data.id, retry]);
  useEffect(() => setPage(0), [split, budget, policy, status, query, sort]);
  const filtered = useMemo(() => {
    const text = query.trim().toLowerCase();
    const matched = rows.filter(r => (split === 'all' || r.split === split) && (budget === 'all' || r.budget === +budget) && (policy === 'all' || r.policy === policy) && (status === 'all' || (status === 'correct' ? r.score?.exact === true : status === 'wrong' ? r.score?.exact === false : r.status !== 'ok')) && (!text || [r.task_id, r.family, families[r.family], r.policy, r.task?.question].join(' ').toLowerCase().includes(text)));
    return sort ? matched.sort((a, b) => (b.proxy_tokens || 0) - (a.proxy_tokens || 0)) : matched;
  }, [rows, split, budget, policy, status, query, sort]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / 10));
  const current = Math.min(page, pageCount - 1);
  const correct = filtered.filter(r => r.score?.exact).length;
  function reset() { setSplit('test'); setBudget('256'); setPolicy('all'); setStatus('all'); setQuery(''); setSort(false); }
  return <><div className="experiment-banner"><span className="outlined-icon"><Filter size={19}/></span><div><strong>冻结协议 · 独立运行 · 原始证据</strong><p>上下文预算使用 proxy tokenizer；实际 API 用量包含摘要开销。Full history 不受上下文预算限制。</p></div><Badge tone="neutral">{number(rows.length)} 条记录</Badge></div><Panel title="实验记录" eyebrow="EXPERIMENT EXPLORER" action={<button className="text-button" onClick={reset}>重置筛选</button>}><div className="filter-toolbar"><label className="search-box"><Search size={17}/><span className="sr-only">搜索任务</span><input value={query} placeholder="搜索任务、场景或问题…" onChange={e => setQuery(e.target.value)}/></label><label className="filter-select"><span>数据集</span><select aria-label="数据集" value={split} onChange={e => setSplit(e.target.value)}><option value="test">留出集</option><option value="dev">开发集</option><option value="all">全部</option></select></label><label className="filter-select"><span>预算</span><select aria-label="预算" value={budget} onChange={e => setBudget(e.target.value)}><option value="256">256 tokens</option><option value="512">512 tokens</option><option value="all">全部</option></select></label><label className="filter-select"><span>策略</span><select aria-label="策略" value={policy} onChange={e => setPolicy(e.target.value)}><option value="all">全部策略</option>{Object.entries(policyNames).map(([key, name]) => <option value={key} key={key}>{name}</option>)}</select></label><label className="filter-select"><span>结果</span><select aria-label="结果" value={status} onChange={e => setStatus(e.target.value)}><option value="all">全部结果</option><option value="correct">正确</option><option value="wrong">错误</option><option value="failed">运行失败 / 未执行</option></select></label></div><div className="filter-summary"><span>匹配 <strong>{filtered.length}</strong> 个条件</span><span>精确正确 <strong>{correct}/{filtered.length}</strong></span><span>当前条件准确率 <strong>{filtered.length ? percent(correct / filtered.length) : '—'}</strong></span></div>{loading ? <div className="empty-state" role="status"><LoaderCircle className="spin" size={25}/>正在读取实验记录…</div> : error ? <div className="empty-state" role="alert"><h3>实验记录暂不可用</h3><p>{error}</p><button className="button subtle" onClick={() => setRetry(n => n + 1)}>重试</button></div> : !filtered.length ? <div className="empty-state"><Search size={30}/><h3>没有匹配的实验</h3><p>试试其他策略或预算，或清空搜索词。</p><button className="button subtle" onClick={reset}>重置筛选</button></div> : <><div className="table-scroll"><table><thead><tr><th>任务 / 场景</th><th>选择策略</th><th>精确匹配</th><th>源证据召回</th><th><button className="table-sort" onClick={() => setSort(!sort)} aria-pressed={sort}>上下文 token <ArrowUpDown size={13}/></button></th><th><span className="sr-only">查看详情</span></th></tr></thead><tbody>{filtered.slice(current * 10, current * 10 + 10).map((r, i) => <tr key={`${r.task_id}-${r.policy}-${r.budget}-${i}`}><td><strong>{families[r.family] || r.family}</strong><small className="mono task-id">{r.task_id}</small></td><td><Badge tone={r.policy === 'versioned' ? '' : 'neutral'}>{policyNames[r.policy] || r.policy}</Badge></td><td>{r.status !== 'ok' ? <Badge tone="warning">{r.status}</Badge> : r.score ? <span className={`result-status ${r.score.exact ? 'correct' : 'incorrect'}`}>{r.score.exact ? <Check size={14}/> : <X size={14}/>} {r.score.exact ? '正确' : '错误'}</span> : <span className="muted">未评分</span>}</td><td className="mono">{percent(r.score?.evidence_recall)}</td><td className="mono">{number(r.proxy_tokens)}</td><td><button className="text-button" aria-label={`查看 ${r.task_id} ${r.policy} 详情`} onClick={() => setSelected(r)}>详情<ChevronRight size={13}/></button></td></tr>)}</tbody></table></div><div className="pagination"><span>第 {current * 10 + 1}–{Math.min((current + 1) * 10, filtered.length)} 条，共 {filtered.length} 条</span><div><button className="icon-button" aria-label="上一页" disabled={current === 0} onClick={() => setPage(current - 1)}><ChevronLeft size={17}/></button><span>{current + 1} / {pageCount}</span><button className="icon-button" aria-label="下一页" disabled={current + 1 >= pageCount} onClick={() => setPage(current + 1)}><ChevronRight size={17}/></button></div></div></>}</Panel><div className="notice"><CircleAlert size={18}/><p>源证据召回反映所需记录是否进入上下文，不等于答案正确率或引用忠实度。不同预算使用的任务子集不同，不能直接比较百分比推断预算收益。</p></div>{selected && <CaseDialog row={selected} close={() => setSelected(null)}/>}</>;
}

function CaseDialog({ row, close }: { row: Case; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const current = dialog.current!; current.showModal(); const old = document.body.style.overflow; document.body.style.overflow = 'hidden'; return () => { current.close(); document.body.style.overflow = old; }; }, []);
  const records = row.task?.records?.filter(record => row.selected_ids?.includes(String(record.id))) || [];
  return <dialog ref={dialog} className="case-dialog" onCancel={close} aria-labelledby="case-title"><div className="dialog-head"><div><div className="eyebrow">EXPERIMENT DETAIL</div><h2 id="case-title">{families[row.family] || row.family}</h2><p className="mono">{row.task_id}</p></div><button className="icon-button" onClick={close} aria-label="关闭详情"><X size={21}/></button></div><div className="dialog-body"><div className="detail-badges"><Badge>{policyNames[row.policy]}</Badge><Badge tone="neutral">{row.budget} proxy tokens</Badge><Badge tone="neutral">{row.split === 'test' ? '留出集' : '开发集'}</Badge></div><h3>原始问题 / Question</h3><p className="english-text">{row.task?.question || '原始问题不可用'}</p><div className="answer-grid"><div><h3>模型回答 / Model response</h3><pre>{prettyAnswer(row.answer)}</pre></div><div><h3>参考答案 / Ground truth</h3><pre>{row.task ? JSON.stringify(row.task.gold, null, 2) : '参考答案不可用'}</pre></div></div><h3>实际上下文 / Selected context</h3><p className="muted">{row.context_text ? '以下为该条件实际提供给模型的内容。' : '上下文未保存。'}{row.selected_ids?.length ? ` 所选源记录 ${row.selected_ids.length} 条。` : ''}</p><pre className="context-pre">{row.context_text || '—'}</pre><details><summary>所选源记录的结构化字段（{records.length} 条）</summary><pre>{JSON.stringify(records, null, 2)}</pre></details></div></dialog>;
}
function prettyAnswer(answer?: string) { if (!answer) return '无回答'; try { return JSON.stringify(JSON.parse(answer), null, 2); } catch { return answer; } }
