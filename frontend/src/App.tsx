import { useEffect, useRef, useState } from 'react';
import { ApiError, clearSession, getSession, sendMessage } from './api';
import { Sidebar } from './components/Sidebar';
import { MessageList } from './components/MessageList';
import { Composer } from './components/Composer';
import { MemoryPane } from './components/MemoryPane';
import { EmotionPane } from './components/EmotionPane';
import { WeatherPane } from './components/WeatherPane';
import { ResetDialog } from './components/ResetDialog';
import { AccountPane } from './components/AccountPane';
import { BondProgress } from './components/BondProgress';
import { UnlockedAbilities, UnlockCelebration } from './components/AbilityExperience';
import type { GrowthAccount, Message, SessionResponse } from './types';

export default function App() {
  const [view, setView] = useState<'characters' | 'account' | 'memories' | 'weather' | 'emotion'>('characters');
  const [chatOpen, setChatOpen] = useState(false);
  const [account, setAccount] = useState<GrowthAccount | null>(null);
  const [candidateCount, setCandidateCount] = useState(0);
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [focusVersion, setFocusVersion] = useState(0);
  // Guards the interval before React commits a state update as well.
  const inFlight = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    getSession(controller.signal).then(data => {
      if (controller.signal.aborted) return;
      setSession(data);
      if (data.account) setAccount(data.account);
      setMessages(data.messages);
      if (!data.configured) setError(`请在项目 .env 中填写 ${data.api_key_env} 并重启服务。密钥仅由本地后端读取。`);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '无法连接本地服务，请刷新重试。');
    });
    return () => controller.abort();
  }, []);

  async function send() {
    const text = draft.trim();
    if (!text || !session || inFlight.current) return;
    inFlight.current = true;
    setBusy(true); setError(''); setDraft('');
    const previous = messages;
    const userMessage: Message = { role: 'user', content: text };
    setMessages([...previous, userMessage]);
    try {
      const data = await sendMessage(text, session.csrf_token);
      const assistantMessage: Message = { role: 'assistant', content: data.reply, ...((data.weather?.status === 'ok' && 'source' in data.weather) ? { weather: data.weather } : {}) };
      setMessages([...previous, userMessage, assistantMessage].slice(-24));
      setCandidateCount(data.memory_candidates?.length ?? 0);
      if (data.account) setAccount(data.account);
    } catch (reason) {
      setMessages(reason instanceof ApiError && reason.code === 'memory_changed' ? [] : previous); setDraft(text);
      const transient = reason instanceof ApiError && (reason.status === 0 || (!reason.code && [502, 503, 504].includes(reason.status)) || ['timeout', 'connection', 'upstream_error', 'rate_limit', 'review_busy'].includes(reason.code ?? ''));
      setError(transient ? '这会儿连接有点慢，先别急，等一会儿再发给我，好吗？' : reason instanceof ApiError ? reason.message : '发送失败，请稍后重试。');
    } finally {
      inFlight.current = false; setBusy(false); setFocusVersion(value => value + 1);
    }
  }

  async function reset() {
    if (!session || inFlight.current) return;
    inFlight.current = true; setResetting(true);
    try {
      await clearSession(session.csrf_token);
      setMessages([]); setDraft(''); setError('');
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '清空失败，请稍后重试。');
    } finally {
      inFlight.current = false; setResetting(false); setResetOpen(false);
    }
  }

  const provider = session?.provider === 'gemini' ? 'Gemini API' : 'OpenAI API';
  const status = !session ? '正在连接本地服务…' : session.provider === 'mock' ? '● 离线演示 · 非真实模型回复'
    : `${session.configured ? '●' : '○'} ${provider} · ${session.configured ? '已配置' : '等待本地密钥'}`;
  const disabled = busy || resetting || memoryBusy;

  return (
    <div className="shell">
      <Sidebar character={session?.character} />
      <main>
        <header>
          <div><span className="eyebrow">A LITTLE SPACE FOR YOU</span><h2>留一点时间，给自己。</h2></div>
          <button className="quiet" disabled={!session || disabled} onClick={() => setResetOpen(true)}>↺ 开始新对话</button>
        </header>
        <div className="connection"><span>{status}</span><span>{session?.model}</span></div>
        <nav className="workspace-nav" aria-label="功能导航">
          <button disabled={disabled} aria-current={view === 'characters' ? 'page' : undefined} onClick={() => setView('characters')}>角色选择</button>
          <button disabled={disabled || !session} aria-current={view !== 'characters' ? 'page' : undefined} onClick={() => setView('account')}>个人账户</button>
        </nav>
        {error && !(view === 'characters' && chatOpen) && <p role="alert" className="pane-error">{error}</p>}
        {view === 'characters' && !chatOpen && <section className="workspace-pane character-picker" aria-label="角色选择">
          <p className="eyebrow">SOMEONE TO SHARE YOUR DAY WITH</p><h3>从一句你好，慢慢靠近。</h3>
          <p className="pane-description">选择一位聊天对象。相处的时间与小小心意，会慢慢点亮更多陪伴方式。</p>
          <article className="character-card"><div className="character-art" aria-hidden="true">栖川<br/><span>旧书店的暖灯，一直留着。</span></div><div><span className="eyebrow">THE BOOKSTORE KEEPER</span><h4>{session?.character.name ?? '沈砚'}</h4><p>温和、沉稳，喜欢修补旧书。也愿意听你慢慢说。</p><BondProgress account={account}/><UnlockedAbilities account={account}/><button disabled={!session || disabled} onClick={() => setChatOpen(true)}>和沈砚聊天</button></div></article>
          <p className="pane-description">当前开放沈砚。更多角色尚未开放；亲密度按角色分别保存。</p>
        </section>}
        {view === 'characters' && chatOpen && <div className="chat-growth"><button className="quiet" disabled={disabled} onClick={() => setChatOpen(false)}>返回角色选择</button><BondProgress account={account}/><UnlockedAbilities account={account}/><button className="quiet" disabled={disabled} onClick={() => setView('account')}>送一份心意 / 个人账户</button></div>}
        {view === 'account' && session && <AccountPane csrf={session.csrf_token} onUpdate={setAccount} onManage={setView} onBusyChange={value => { inFlight.current=value;setMemoryBusy(value); }} />}
        {['memories','weather','emotion'].includes(view) && <div className="privacy-heading"><button className="quiet" disabled={disabled} onClick={() => setView('account')}>返回个人账户</button></div>}
        {view === 'memories' && session && <MemoryPane csrf={session.csrf_token} locked={account ? !account.character.abilities.memory : false}
          onBusyChange={value => { inFlight.current = value; setMemoryBusy(value); }}
          onHistoryCleared={() => { setMessages([]); setCandidateCount(0); setError(''); }} />}
        {view === 'emotion' && session && <EmotionPane csrf={session.csrf_token} locked={account ? !account.character.abilities.emotion : false} onBusyChange={value => { inFlight.current=value;setMemoryBusy(value); }} onHistoryCleared={() => {setMessages([]);setCandidateCount(0);setError('');}} />}
        {view === 'weather' && session && <WeatherPane csrf={session.csrf_token} locked={account ? !account.character.abilities.weather : false} onBusyChange={value => { inFlight.current = value; setMemoryBusy(value); }} onHistoryCleared={() => { setMessages([]); setCandidateCount(0); setError(''); }} />}
        <div className="chat-workspace" hidden={view !== 'characters' || !chatOpen}>
        {candidateCount > 0 && <button className="memory-hint" onClick={() => { setView('memories'); setCandidateCount(0); }}>发现 {candidateCount} 条待确认记忆，点击查看（尚未用于长期回应）</button>}
        <MessageList messages={messages} pending={busy} name={session?.character.name ?? '沈砚'} disabled={disabled}
          onSuggest={text => { setDraft(text); setFocusVersion(value => value + 1); }} />
        <Composer draft={draft} onChange={setDraft} onSend={() => void send()} disabled={disabled}
          canSend={Boolean(session && draft.trim() && !disabled)} error={error} focusVersion={focusVersion} />
        </div>
      </main>
      <ResetDialog open={resetOpen} busy={resetting} onCancel={() => setResetOpen(false)} onConfirm={() => void reset()} />
      <UnlockCelebration account={account}/>
    </div>
  );
}
