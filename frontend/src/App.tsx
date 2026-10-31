import { useEffect, useRef, useState } from 'react';
import { ApiError, clearSession, getSession, sendMessage } from './api';
import { Sidebar } from './components/Sidebar';
import { MessageList } from './components/MessageList';
import { Composer } from './components/Composer';
import { ResetDialog } from './components/ResetDialog';
import type { Message, SessionResponse } from './types';

export default function App() {
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
      const assistantMessage: Message = { role: 'assistant', content: data.reply };
      setMessages([...previous, userMessage, assistantMessage].slice(-24));
    } catch (reason) {
      setMessages(previous); setDraft(text);
      setError(reason instanceof ApiError ? reason.message : '发送失败，请稍后重试。');
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
  const disabled = busy || resetting;

  return (
    <div className="shell">
      <Sidebar character={session?.character} />
      <main>
        <header>
          <div><span className="eyebrow">A LITTLE SPACE FOR YOU</span><h2>留一点时间，给自己。</h2></div>
          <button className="quiet" disabled={!session || disabled} onClick={() => setResetOpen(true)}>↺ 开始新对话</button>
        </header>
        <div className="connection"><span>{status}</span><span>{session?.model}</span></div>
        <MessageList messages={messages} pending={busy} name={session?.character.name ?? '沈砚'} disabled={disabled}
          onSuggest={text => { setDraft(text); setFocusVersion(value => value + 1); }} />
        <Composer draft={draft} onChange={setDraft} onSend={() => void send()} disabled={disabled}
          canSend={Boolean(session && draft.trim() && !disabled)} error={error} focusVersion={focusVersion} />
      </main>
      <ResetDialog open={resetOpen} busy={resetting} onCancel={() => setResetOpen(false)} onConfirm={() => void reset()} />
    </div>
  );
}
