export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface Character {
  id: string;
  name: string;
  subtitle: string;
  version: string;
}

export interface SessionResponse {
  csrf_token: string;
  messages: Message[];
  character: Character;
  provider: 'gemini' | 'openai' | 'mock';
  model: string;
  api_key_env: string;
  configured: boolean;
}

export interface ChatResponse {
  reply: string;
  request_id: string;
  guarded: boolean;
}
