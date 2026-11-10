import type { ChatResponse, SessionResponse } from './types';

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code?: string) {
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
    const code = typeof body === 'object' && body !== null && 'code' in body && typeof body.code === 'string' ? body.code : undefined;
    throw new ApiError(typeof detail === 'string' ? detail : '输入无效，请检查消息长度后重试。', response.status, code);
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

export const getMemories = () => request<import('./types').MemoryList>('/v1/memories');
export const addMemory = (fact: string, csrf: string) => request('/v1/memories', {
  method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify({ fact }),
});
export const editMemory = (id: string, version: number, fact: string, confirm: boolean, replace: boolean, csrf: string, keepBoth = false) => request(`/v1/memories/${id}`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
  body: JSON.stringify({ version, fact, confirm, replace_conflicts: replace, keep_both: keepBoth }),
});
export const deleteMemory = (id: string, version: number, csrf: string) => request(`/v1/memories/${id}?version=${version}`, {
  method: 'DELETE', headers: { 'X-CSRF-Token': csrf },
});
export const deleteAllMemories = (csrf: string) => request('/v1/memories', { method: 'DELETE', headers: { 'X-CSRF-Token': csrf } });
export const setMemorySettings = (memory_enabled: boolean, timezone: string, csrf: string) => request('/v1/settings', {
  method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify({ memory_enabled, timezone }),
});

export const getWeatherSettings = () => request<import('./types').WeatherSettings>('/v1/weather/settings');
export const searchWeatherCities = (city: string) => request<{ items: import('./types').WeatherPlace[] }>(`/v1/weather/locations?q=${encodeURIComponent(city)}`);
export const saveWeatherSettings = (enabled: boolean, city_id: number | null, csrf: string) => request<{ settings: import('./types').WeatherSettings }>('/v1/weather/settings', {
  method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify({ enabled, city_id }),
});
export const deleteWeatherSettings = (csrf: string) => request<{ settings: import('./types').WeatherSettings }>('/v1/weather/settings', {
  method: 'DELETE', headers: { 'X-CSRF-Token': csrf },
});

export const getEmotion=()=>request<import('./types').EmotionData>('/v1/emotion');
export const saveEmotionSettings=(config:import('./types').EmotionSettings,csrf:string)=>request('/v1/emotion/settings',{method:'PATCH',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(config)});
export const deleteEmotionSettings=(csrf:string)=>request('/v1/emotion/settings',{method:'DELETE',headers:{'X-CSRF-Token':csrf}});
export const correctEmotion=(label:import('./types').EmotionLabel,preference:import('./types').SupportPreference,csrf:string)=>request('/v1/emotion/assessment',{method:'PATCH',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({label,preference})});
export const clearEmotion=(csrf:string)=>request('/v1/emotion/assessment',{method:'DELETE',headers:{'X-CSRF-Token':csrf}});

export const getAccount=()=>request<import('./types').GrowthAccount>('/v1/account');
export const saveProfile=(profile:import('./types').GrowthAccount['profile'],csrf:string)=>request<import('./types').GrowthAccount>('/v1/account/profile',{
  method:'PATCH',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(profile),
});
export const clearProfile=(csrf:string)=>request<import('./types').GrowthAccount>('/v1/account/profile',{method:'DELETE',headers:{'X-CSRF-Token':csrf}});
export const demoCredit=(request_id:string,csrf:string)=>request<import('./types').GrowthAccount>('/v1/account/demo-credit',{
  method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({request_id}),
});
export const sendGift=(character:string,gift_id:string,request_id:string,csrf:string)=>request<import('./types').GrowthAccount>(`/v1/characters/${encodeURIComponent(character)}/gifts`,{
  method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({gift_id,request_id}),
});
