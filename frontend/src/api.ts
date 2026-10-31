import type { ChatResponse, SessionResponse } from './types';

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { credentials: 'same-origin', ...options });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('无法连接本地服务，请确认服务已启动后重试。', 0);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError('服务返回了无法读取的响应，请稍后重试。', response.status);
  }
  if (!response.ok) {
    const detail = typeof body === 'object' && body !== null && 'detail' in body ? body.detail : null;
    throw new ApiError(typeof detail === 'string' ? detail : '输入无效，请检查消息长度后重试。', response.status);
  }
  return body as T;
}

export const getSession = (signal?: AbortSignal) => request<SessionResponse>('/v1/session', { signal });

export const sendMessage = (message: string, csrf: string) => request<ChatResponse>('/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
  body: JSON.stringify({ message }),
});

export const clearSession = (csrf: string) => request<{ ok: boolean }>('/v1/session', {
  method: 'DELETE', headers: { 'X-CSRF-Token': csrf },
});
