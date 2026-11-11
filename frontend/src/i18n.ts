import { useSyncExternalStore } from 'react';
import ja from './locales/ja.json';

export type Locale = 'zh-CN' | 'ja-JP';
const key = 'persona.ui.locale';
function savedLocale(): Locale {
  try { return localStorage.getItem(key) === 'ja-JP' ? 'ja-JP' : 'zh-CN'; } catch { return 'zh-CN'; }
}
let locale: Locale = savedLocale();
const listeners = new Set<() => void>();
export const getLocale = () => locale;
export function setLocale(next: Locale) {
  if (next !== 'ja-JP' && next !== 'zh-CN') return;
  locale = next;
  try { localStorage.setItem(key, next); } catch { /* UI still works without storage. */ }
  document.documentElement.lang = next;
  document.title = next === 'ja-JP' ? '心語 · あなたと過ごす時間' : '心语 · Persona RAG';
  listeners.forEach(listener => listener());
}
export function useLocale() {
  return useSyncExternalStore(listener => { listeners.add(listener); return () => listeners.delete(listener); }, getLocale);
}
export function translate(language: Locale, source: string, values: readonly unknown[] = []): string {
  const dict: Readonly<Record<string, string>> = ja;
  const text = language === 'ja-JP' ? dict[source.trim()] ?? source : source;
  return text.replace(/\{(\d+)\}/g, (_, index: string) => String(values[Number(index) - 1] ?? ''));
}
// Only authored UI copy is passed here. Never translate chat, memories, names or places implicitly.
export const t = (source: string, values: readonly unknown[] = []) => translate(locale, source, values);

// Error bodies can contain supplier/server text. Japanese UI uses a safe fallback.
export function errorText(source: string): string {
  if (locale !== 'ja-JP' || !source) return source;
  const dictionary: Readonly<Record<string, string>> = ja;
  if (dictionary[source.trim()]) return t(source);
  if (/[ぁ-んァ-ヶ]/.test(source)) return source;
  return '操作を完了できませんでした。設定や接続を確認してください。';
}
