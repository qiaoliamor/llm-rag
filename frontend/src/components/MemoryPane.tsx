import { useEffect, useState } from 'react';
import { addMemory, deleteAllMemories, deleteMemory, editMemory, getMemories, setMemorySettings } from '../api';
import type { MemoryItem, MemoryList } from '../types';

function MemoryCard({ item, disabled, canEdit, onEdit, onDelete }: {
  item: MemoryItem;
  disabled: boolean;
  canEdit: boolean;
  onEdit: (item: MemoryItem, fact: string, confirm: boolean, replace: boolean, keepBoth: boolean) => void;
  onDelete: (item: MemoryItem) => void;
}) {
  const [fact, setFact] = useState(item.fact);
  const [replace, setReplace] = useState(false);
  const [keepBoth, setKeepBoth] = useState(false);
  return <article className="memory-card">
    <div className="memory-meta"><strong>{item.expired ? '已过期 · 不再检索' : item.status === 'confirmed' ? '已确认' : '待你确认'}</strong><span>{item.event_date ? `事件日期 ${item.event_date} · ${item.timezone ?? 'Asia/Tokyo'}` : '未确定具体日期'}</span></div>
    <label htmlFor={`fact-${item.id}`} className="sr-only">记忆内容</label>
    <textarea id={`fact-${item.id}`} value={fact} maxLength={300} rows={3} disabled={disabled || !canEdit} onChange={e => setFact(e.target.value)} />
    <p className="memory-source">{item.source_kind === 'manual' ? '手动添加' : item.source_kind === 'corrected' ? '玩家纠正' : '本轮对话提取'} · {new Date(item.created_at).toLocaleDateString()} · 版本 {item.version}</p>
    {!!item.conflicts?.length && <div><label className="memory-conflict"><input type="checkbox" checked={replace} onChange={e => { setReplace(e.target.checked); if (e.target.checked) setKeepBoth(false); }} /> 同类旧记忆存在；我确认替换旧内容</label><label className="memory-conflict"><input type="checkbox" checked={keepBoth} onChange={e => { setKeepBoth(e.target.checked); if (e.target.checked) setReplace(false); }} /> 这是独立经历，保留两条</label></div>}
    <div className="memory-actions">
      <button disabled={disabled || !canEdit || !fact.trim()} onClick={() => onEdit(item, fact, item.status === 'candidate', replace, keepBoth)}>
        {item.status === 'candidate' ? '确认记住' : '保存纠正'}
      </button>
      {item.status === 'candidate' && fact !== item.fact && <button className="quiet" disabled={disabled || !canEdit || !fact.trim()} onClick={() => onEdit(item, fact, false, false, false)}>只修改候选</button>}
      <button className="quiet danger" disabled={disabled} onClick={() => onDelete(item)}>{item.status === 'candidate' ? '不保存' : '删除记忆'}</button>
    </div>
  </article>;
}

export function MemoryPane({ csrf, onHistoryCleared, onBusyChange }: { csrf: string; onHistoryCleared: () => void; onBusyChange?: (busy: boolean) => void }) {
  const [data, setData] = useState<MemoryList | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState('');
  const [timezone, setTimezone] = useState('Asia/Tokyo');
  const [deleting, setDeleting] = useState<MemoryItem | 'all' | null>(null);
  async function refresh() {
    const next = await getMemories(); setData(next); setTimezone(next.settings.timezone);
  }
  useEffect(() => { let active = true; getMemories().then(next => { if (active) { setData(next); setTimezone(next.settings.timezone); } }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, []);
  async function run(operation: () => Promise<unknown>, clearsHistory: boolean, message: string) {
    onBusyChange?.(true);
    setBusy(true); setError(''); setNotice('');
    try {
      await operation();
      if (clearsHistory) onHistoryCleared();
      await refresh(); setNotice(message);
    } catch (reason) { setError(reason instanceof Error ? reason.message : '记忆操作失败，请重试。'); }
    finally { setBusy(false); setDeleting(null); onBusyChange?.(false); }
  }
  if (!data) return <section className="workspace-pane"><h3>长期记忆</h3><p role={error ? 'alert' : undefined}>{error || '正在读取本地记忆…'}</p></section>;
  const enabled = data.settings.memory_enabled;
  return <section className="workspace-pane" aria-label="长期记忆管理">
    <h3>让重要的事，被好好记住。</h3>
    <p className="pane-description">默认关闭。开启后只提取本轮明确表达的重要信息，先形成候选；你确认后，角色才会跨对话引用。健康或创伤等内容也不会自动确认。</p>
    <div className="memory-settings">
      <button disabled={busy} onClick={() => void run(() => setMemorySettings(!enabled, timezone, csrf), true, enabled ? '长期记忆已关闭，已有确认记忆保留但不再检索。' : '长期记忆已开启，候选仍需逐条确认。')}>{enabled ? '关闭长期记忆' : '开启长期记忆'}</button>
      <label>事件时区 <select aria-label="事件时区" value={timezone} disabled={busy} onChange={e => setTimezone(e.target.value)}>
        <option value="Asia/Tokyo">日本 · 东京</option><option value="Asia/Shanghai">中国 · 上海</option><option value="UTC">UTC</option>
      </select></label>
      <button className="quiet" disabled={busy || timezone === data.settings.timezone} onClick={() => void run(() => setMemorySettings(enabled, timezone, csrf), true, '时区已更新；已有事件日期保留，新事件使用新时区。')}>保存时区</button>
    </div>
    <p className="pane-description">“开始新对话”只清空聊天，记忆保留。纠正、删除或更改记忆授权会清空当前身份的短期聊天，防止旧信息继续影响回复。清除浏览器 Cookie 会失去当前本地身份，记忆不会转移到新身份。</p>
    {error && <p role="alert" className="pane-error">{error}</p>}
    {notice && <p role="status" className="pane-notice">{notice}</p>}
    <form className="memory-add" onSubmit={e => { e.preventDefault(); if (!draft.trim() || busy) return; void run(async () => { await addMemory(draft.trim(), csrf); setDraft(''); }, false, '已加入候选，请在下方确认。'); }}>
      <label htmlFor="new-memory">也可以手动添加重要经历（最多300字）</label>
      <textarea id="new-memory" value={draft} rows={2} maxLength={300} disabled={!enabled || busy} onChange={e => setDraft(e.target.value)} placeholder="例如：我下周二有一场设计师面试。" />
      <button type="submit" disabled={!enabled || busy || !draft.trim()}>添加候选</button>
    </form>
    {deleting && <div role="alertdialog" aria-label="删除记忆确认" className="memory-delete-confirm">
      <p>{deleting === 'all' ? '清空所有候选和确认记忆？' : '删除这条记忆？'}删除后无法恢复，并会清空短期聊天。</p>
      <button disabled={busy} onClick={() => void run(() => deleting === 'all' ? deleteAllMemories(csrf) : deleteMemory(deleting.id, deleting.version, csrf), true, '记忆已删除，不再参与检索。')}>确认删除</button>
      <button className="quiet" disabled={busy} onClick={() => setDeleting(null)}>取消</button>
    </div>}
    <div className="memory-list-heading"><h4>我的记忆 · {data.items.length}</h4><button className="quiet danger" disabled={busy || data.items.length === 0} onClick={() => setDeleting('all')}>清空全部记忆</button></div>
    {!data.items.length && <p className="pane-description">还没有记忆。开启后聊聊重要经历，或在上方手动添加。</p>}
    {data.items.map(item => <MemoryCard key={`${item.id}-${item.version}`} item={item} disabled={busy} canEdit={enabled}
      onEdit={(m, fact, confirm, replace, keepBoth) => void run(() => editMemory(m.id, m.version, fact.trim(), confirm, replace, csrf, keepBoth), true, '记忆已更新，旧上下文已清空。')}
      onDelete={setDeleting} />)}
    {!enabled && data.items.length > 0 && <p className="pane-description">记忆关闭时仍可逐条或全部删除；开启后可逐条编辑。</p>}
  </section>;
}
