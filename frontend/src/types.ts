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
  account?: GrowthAccount;
  csrf_token: string;
  messages: Message[];
  character: Character;
  provider: 'gemini' | 'openai' | 'mock';
  model: string;
  api_key_env: string;
  configured: boolean;
}

export interface ChatResponse {
  account?: GrowthAccount;
  reply: string;
  request_id: string;
  guarded: boolean;
  memory_candidates?: MemoryItem[];
  retrieved_memory_ids?: string[];
  weather?: WeatherEvidenceData | { status: 'disabled' | 'location_required' | 'ambiguous' | 'not_found' | 'date_unsupported' | 'timeout' | 'rate_limit' | 'unavailable' | 'invalid_response' | 'stale' | 'invalid_city' | 'understanding_unavailable' | 'clarification_required'; message: string } | null;
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

export type EmotionLabel='unknown'|'neutral'|'joy'|'sadness'|'anxiety'|'anger'|'tired';
export type SupportPreference='ask'|'listen'|'encourage'|'practical';
export interface EmotionSettings { enabled:boolean; interval:number; window:number; cooldown:number; threshold:number; preference:SupportPreference; }
export interface EmotionAssessment { labels:EmotionLabel[]; intensity:number; confidence:number; evidence_message_ids:string[]; response_strategy:SupportPreference; source:'user'|'model'; basis?:'self_report'; turn:number; observed_at:string; }
export interface EmotionData { settings:EmotionSettings; assessment:EmotionAssessment|null; }

export interface GrowthAccount {
  profile: { name: string; email: string; phone: string };
  coins: number;
  currency_mode: 'demo';
  starting_coins: number;
  character: { id: string; name: string; score: number; active_seconds: number; abilities: { memory: boolean; emotion: boolean; weather: boolean } };
  thresholds: { memory: number; emotion: number; weather: number };
  gifts: { id: 'bookmark' | 'tea' | 'lamp'; name: string; price: number; points: number; description: string }[];
  ledger: { request_id: string; action: string; character_id: string; coins_delta: number; points_delta: number; created_at: string }[];
}
