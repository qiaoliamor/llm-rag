import { useEffect, useRef } from 'react';
import { WeatherEvidence } from './WeatherEvidence';
import type { Message } from '../types';

const suggestions = ['今天工作有点累', '介绍一下你的书店吧', '明天有面试，有些紧张'];

export function MessageList({ messages, pending, name, onSuggest, disabled }: {
  messages: Message[];
  pending: boolean;
  name: string;
  onSuggest: (text: string) => void;
  disabled: boolean;
}) {
  const container = useRef<HTMLElement>(null);
  useEffect(() => {
    if (container.current) container.current.scrollTop = container.current.scrollHeight;
  }, [messages, pending]);

  return (
    <section ref={container} id="messages" className="messages" aria-label="对话消息" aria-live="polite" aria-busy={pending}>
      {messages.length === 0 && !pending && (
        <div className="welcome">
          <div className="book-icon">书</div>
          <p className="eyebrow">WELCOME TO QICHUAN</p>
          <h3>今天，想从哪里说起？</h3>
          <p>门还开着，给你留了一个靠窗的位置。<br />聊聊今天的小事，或者只是待一会儿。</p>
          <div className="suggestions">{suggestions.map(text => (
            <button type="button" key={text} disabled={disabled} onClick={() => onSuggest(text)}>{text}</button>
          ))}</div>
        </div>
      )}
      {messages.map((message, i) => (
        <div className={`message ${message.role}`} key={i}>
          <span className="who">{message.role === 'user' ? '你' : name}</span>
          <div className="bubble">{message.content}</div>
          {message.role === 'assistant' && message.weather?.status === 'ok' && <WeatherEvidence weather={message.weather} />}
        </div>
      ))}
      {pending && <div className="message assistant pending"><span className="who">{name}</span><div className="bubble">正在想怎么回答你…</div></div>}
    </section>
  );
}
