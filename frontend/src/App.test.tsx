import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import { getSession, sendMessage, clearSession } from './api';
import type { SessionResponse } from './types';

function response(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}
const session: SessionResponse = {
  csrf_token: 'test-csrf', messages: [],
  character: { id: 'shen_yan', name: '沈砚', subtitle: '听你说，也陪你慢慢想。', version: '1.0' },
  provider: 'gemini', model: 'test-gemini-model', api_key_env: 'GEMINI_API_KEY', configured: true,
};
function connect(data: SessionResponse = session) {
  const fetchMock = vi.fn().mockResolvedValueOnce(response(data));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}
async function ready() {
  await screen.findByText('● Gemini API · 已配置');
  return userEvent.setup();
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

describe('React chat', () => {
  it('restores server history and selected provider after page initialization', async () => {
    connect({ ...session, messages: [{ role: 'user', content: '之前的话' }, { role: 'assistant', content: '我还在听。' }] });
    render(<App />); await ready();
    expect(screen.getByText('之前的话')).toBeVisible();
    expect(screen.getByText('我还在听。')).toBeVisible();
    expect(screen.getByText('test-gemini-model')).toBeVisible();
    expect(screen.queryByText('今天，想从哪里说起？')).not.toBeInTheDocument();
  });

  it('fills suggestions, sends with Enter and uses the existing CSRF contract', async () => {
    const fetchMock = connect();
    fetchMock.mockResolvedValueOnce(response({ reply: '我在听，慢慢说。', request_id: 'test', guarded: false }));
    render(<App />); const user = await ready();
    await user.click(screen.getByRole('button', { name: '今天工作有点累' }));
    const input = screen.getByRole('textbox');
    expect(input).toHaveFocus();
    expect(input).toHaveValue('今天工作有点累');
    await user.keyboard('{Enter}');
    await screen.findByText('我在听，慢慢说。');
    expect(fetchMock.mock.calls[1][0]).toBe('/v1/chat');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST', credentials: 'same-origin', headers: { 'X-CSRF-Token': 'test-csrf' }, body: JSON.stringify({ message: '今天工作有点累' }) });
    expect(input).toHaveValue('');
    expect(input).toHaveFocus();
  });

  it('allows Shift+Enter and does not submit while composing Chinese', async () => {
    const fetchMock = connect(); render(<App />); const user = await ready();
    const input = screen.getByRole('textbox');
    await user.type(input, '第一行');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    expect(input).toHaveValue('第一行\n');
    fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 229 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('shows waiting state and prevents duplicate requests and draft races', async () => {
    const fetchMock = connect(); const pending = deferred<Response>();
    fetchMock.mockReturnValueOnce(pending.promise);
    render(<App />); const user = await ready();
    await user.type(screen.getByRole('textbox'), '请听我说');
    await user.click(screen.getByRole('button', { name: /发送/ }));
    expect(screen.getByText('正在想怎么回答你…')).toBeVisible();
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: /↺/ })).toBeDisabled();
    fireEvent.submit(screen.getByRole('textbox').closest('form')!);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await act(async () => pending.resolve(response({ reply: '嗯。', request_id: 'test', guarded: false })));
    expect(await screen.findByText('嗯。')).toBeVisible();
  });

  it('keeps previous messages and restores draft on API errors', async () => {
    const fetchMock = connect({ ...session, messages: [{ role: 'assistant', content: '之前的回复' }] });
    fetchMock.mockResolvedValueOnce(response({ detail: 'API 配额不足，请稍后重试。' }, 429));
    render(<App />); const user = await ready();
    await user.type(screen.getByRole('textbox'), '今天有点紧张');
    await user.click(screen.getByRole('button', { name: /发送/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('API 配额不足');
    expect(screen.getByRole('textbox')).toHaveValue('今天有点紧张');
    expect(screen.getByText('之前的回复')).toBeVisible();
    expect(within(screen.getByRole('region', { name: '对话消息' })).queryByText('今天有点紧张')).not.toBeInTheDocument();
  });

  it('renders model content as text rather than HTML', async () => {
    const text = '<img src=x onerror=alert(1)>';
    connect({ ...session, messages: [{ role: 'assistant', content: text }] });
    const { container } = render(<App />); await ready();
    expect(screen.getByText(text)).toBeVisible();
    expect(container.querySelector('.bubble img')).toBeNull();
  });

  it('confirms or cancels clearing, using DELETE on the same session route', async () => {
    const fetchMock = connect({ ...session, messages: [{ role: 'user', content: '测试旧消息' }] });
    fetchMock.mockResolvedValueOnce(response({ ok: true }));
    render(<App />); const user = await ready();
    await user.click(screen.getByRole('button', { name: /↺/ }));
    await user.click(screen.getByRole('button', { name: '再聊一会儿' }));
    expect(screen.getByText('测试旧消息')).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: /↺/ }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: '开始新对话' }));
    await screen.findByText('今天，想从哪里说起？');
    expect(screen.queryByText('测试旧消息')).not.toBeInTheDocument();
    expect(fetchMock.mock.calls[1]).toEqual(['/v1/session', expect.objectContaining({ method: 'DELETE', headers: { 'X-CSRF-Token': 'test-csrf' } })]);
  });

  it('retains history when clearing fails and closes the dialog', async () => {
    const fetchMock = connect({ ...session, messages: [{ role: 'user', content: '仍需保留的消息' }] });
    fetchMock.mockResolvedValueOnce(response({ detail: '会话已过期，请刷新网页。' }, 401));
    render(<App />); const user = await ready();
    await user.click(screen.getByRole('button', { name: /↺/ }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: '开始新对话' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('会话已过期');
    expect(screen.getByText('仍需保留的消息')).toBeVisible();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows missing-key instructions for the selected provider only', async () => {
    connect({ ...session, configured: false }); render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('GEMINI_API_KEY');
    expect(screen.getByText('○ Gemini API · 等待本地密钥')).toBeVisible();
    expect(screen.queryByText(/OPENAI_API_KEY/)).not.toBeInTheDocument();
  });

  it('keeps the composer disabled if session bootstrap fails', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('network failure'));
    vi.stubGlobal('fetch', fetchMock); render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('无法连接本地服务');
    expect(screen.getByRole('button', { name: /发送/ })).toBeDisabled();
  });

  it('preserves mock mode labeling and input length limits', async () => {
    connect({ ...session, provider: 'mock', model: '离线演示' }); render(<App />);
    expect(await screen.findByText('● 离线演示 · 非真实模型回复')).toBeVisible();
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('maxlength', '2000');
    fireEvent.change(input, { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: /发送/ })).toBeDisabled();
  });
});

describe('typed API client', () => {
  it('handles invalid JSON without displaying internal server text', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => { throw new SyntaxError('private stack'); } }));
    await expect(getSession()).rejects.toThrow('无法读取的响应');
  });

  it('handles validation arrays with the user-friendly fallback', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: [{ input: 'private' }] }, 422)));
    await expect(sendMessage('你好', 'token')).rejects.toThrow('输入无效');
  });

  it('uses only relative same-origin endpoints without accepting a key', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true })); vi.stubGlobal('fetch', fetchMock);
    await clearSession('csrf');
    expect(fetchMock).toHaveBeenCalledWith('/v1/session', expect.objectContaining({ credentials: 'same-origin', method: 'DELETE' }));
  });
});


it('attaches weather evidence to the sent reply and clears it on new conversation', async () => {
  const fetchMock=connect();render(<App />);const user=await ready();
  fetchMock.mockResolvedValueOnce(response({reply:'那边估计六度左右，外套多带一件吧。',weather:{status:'ok',source:'Open-Meteo',location:'合成巴黎',timezone:'Europe/Paris',date:'2026-11-01',kind:'current',fetched_at:'2026-11-01T05:40:00Z',cached:false,temperature_c:6.3}}));
  fireEvent.change(screen.getByRole('textbox'),{target:{value:'现在天气如何'}});
  await user.click(screen.getByRole('button',{name:/发送/}));
  expect(await screen.findByText('天气依据 · 当前天气为模型估计（非地面实测）')).toBeVisible();
  fetchMock.mockResolvedValueOnce(response({ok:true}));
  await user.click(screen.getByRole('button',{name:/开始新对话/}));
  await user.click(within(screen.getByRole('dialog')).getByRole('button',{name:'开始新对话'}));
  expect(screen.queryByText(/天气依据/)).not.toBeInTheDocument();
});
