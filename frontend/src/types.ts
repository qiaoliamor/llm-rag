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
  memory_candidates?: MemoryItem[];
  retrieved_memory_ids?: string[];
}

export interface MemorySettings {
  memory_enabled: boolean;
  timezone: string;
  epoch: number;
}

export interface MemoryItem {
  id: string;
  fact: string;
  category: string;
  status: 'candidate' | 'confirmed';
  event_date: string | null;
  timezone?: string;
  source_message_id: string;
  source_kind: string;
  created_at: string;
  updated_at: string;
  version: number;
  conflicts?: string[];
  expired?: boolean;
}

export interface MemoryList {
  items: MemoryItem[];
  settings: MemorySettings;
}
