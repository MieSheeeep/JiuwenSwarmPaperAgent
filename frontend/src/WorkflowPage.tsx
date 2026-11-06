import { useEffect, useState } from 'react';
import { get } from './api';
import { Badge, Panel } from './components';

type Project = {
  directory: string; topic: string; status: string; next_stage?: string | null;
  usage?: { calls: number; tokens: number }; limits?: { calls: number; tokens: number };
  stages: Record<string, string>; revisions?: number; interrupted?: boolean; last_event?: string;
};
const labels: Record<string, string> = {
  topic: '方向与约束', literature: '文献检索与阅读', question: '问题与假设',
  design: '实验设计', implementation: '方法实现', pilot: '小规模验证',
  experiment: '正式实验', analysis: '分析与证据', writing: '提纲与论文',
  review: '审查与修订', export: '编译与导出',
};
const states: Record<string, string> = {
  completed: '已完成', pending: '待处理', ready: '就绪', running: '执行中',
  paused: '已暂停', needs_input: '等待处理', revision_limit: '达到修订上限',
  budget_exceeded: '预算需要核对', invalid: '产物校验失败',
};

export default function WorkflowPage({ refresh = 0 }: { refresh?: number }) {
  const [rows, setRows] = useState<Project[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true); setError('');
    get<Project[]>('/api/workflows', controller.signal).then(setRows)
      .catch(e => { if (e.name !== 'AbortError') setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [refresh]);
  return <>
    <div className="studio-banner"><div><div className="eyebrow">RESEARCH WORKFLOW</div>
      <h2>跟踪一整个科研项目。</h2>
      <p>查看各阶段交接、修订轮次和预算。刷新只读取本地产物。</p></div></div>
    {busy && <p role="status">正在读取科研项目…</p>}
    {error && <p role="alert" className="notice warning">{error}</p>}
    {!busy && !error && !rows.length && <Panel title="尚无统一流程项目" eyebrow="PROJECTS">
      <p>通过 research.workflow 初始化项目后，即可在这里查看阶段状态。</p></Panel>}
    {rows.map(row => <Panel key={row.directory} title={row.topic} eyebrow={row.directory}>
      <p><Badge tone={row.status === 'completed' ? '' : 'neutral'}>{states[row.status] || row.status}</Badge>
        {' '}下一步：{row.next_stage ? labels[row.next_stage] || row.next_stage : row.status === 'completed' ? '流程已结束' : '需要核对'}</p>
      <p>调用 {row.usage?.calls ?? 0} / {row.limits?.calls ?? '—'} 次 · Token {row.usage?.tokens ?? 0} / {row.limits?.tokens ?? '—'} · 修订 {row.revisions ?? 0} 轮</p>
      {row.interrupted && <p className="notice warning">存在中断阶段；需要核对调用账本后才能续跑。</p>}
      <ol style={{ paddingLeft: 24 }}>{Object.entries(row.stages).map(([stage, status]) =>
        <li key={stage} style={{ marginBottom: 10 }}>{labels[stage] || stage} · {states[status] || status}</li>)}</ol>
    </Panel>)}
  </>;
}
