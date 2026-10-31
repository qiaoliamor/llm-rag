import { useEffect, useState } from 'react';
import { getProject } from '../api';

export function ProjectPane() {
  const [data, setData] = useState<{todo: string; plan: string} | null>(null);
  const [view, setView] = useState<'todo' | 'plan'>('todo');
  const [error, setError] = useState('');
  useEffect(() => { let active = true; getProject().then(next => { if (active) setData(next); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, []);
  return <section className="workspace-pane" aria-label="项目计划与进度">
    <h3>项目计划与进度</h3><p className="pane-description">直接读取项目根目录 TODOLIST.md 和 docs/PLAN.md。[x] 表示完成，[ ] 表示待完成。此处只读。</p>
    <div className="memory-actions"><button onClick={() => setView('todo')} aria-pressed={view === 'todo'}>任务清单</button><button className="quiet" onClick={() => setView('plan')} aria-pressed={view === 'plan'}>实施计划</button></div>
    {error && <p role="alert">{error}</p>}<pre className="project-document">{data ? data[view] : '正在读取文档…'}</pre>
  </section>;
}
