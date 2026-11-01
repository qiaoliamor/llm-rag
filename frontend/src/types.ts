export interface Message {
  role: 'user' | 'assistant';
  content: string;
  weather?: WeatherEvidenceData;
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
  weather?: WeatherEvidenceData | { status: 'disabled' | 'location_required' | 'ambiguous' | 'not_found' | 'date_unsupported' | 'timeout' | 'rate_limit' | 'unavailable' | 'invalid_response' | 'stale' | 'invalid_city'; message: string } | null;
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

export interface WeatherPlace {
  id: number;
  name: string;
  country: string;
  admin1: string;
  latitude: number;
  longitude: number;
  timezone: string;
}
export interface WeatherSettings {
  enabled: boolean;
  place: WeatherPlace | null;
}


export interface WeatherEvidenceData {
  status: 'ok';
  source: string;
  location: string;
  timezone: string;
  date: string;
  kind: 'current' | 'forecast';
  fetched_at: string;
  valid_at?: string;
  cached: boolean;
  temperature_c?: number;
  feels_like_c?: number;
  humidity_pct?: number;
  min_c?: number;
  max_c?: number;
  rain_probability_pct?: number;
}
