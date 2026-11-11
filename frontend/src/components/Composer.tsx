import { errorText, t } from '../i18n';
import { useEffect, useRef } from 'react';

export function Composer({ draft, onChange, onSend, disabled, canSend, error, focusVersion }: {
  draft: string;
  onChange: (text: string) => void;
  onSend: () => void;
  disabled: boolean;
  canSend: boolean;
  error: string;
  focusVersion: number;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (focusVersion > 0) input.current?.focus();
  }, [focusVersion]);

  return (
    <div className="composer-area">
      {error && <p id="error" role="alert">{errorText(error)}</p>}
      <form onSubmit={event => { event.preventDefault(); onSend(); }}>
        <label htmlFor="message" className="sr-only">{t("想对沈砚说的话")}</label>
        <textarea ref={input} id="message" placeholder={t("把今天的心事，慢慢说给我听…")} maxLength={2000} rows={2} required
          value={draft} disabled={disabled} onChange={event => onChange(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.nativeEvent.keyCode !== 229) {
              event.preventDefault();
              if (canSend) onSend();
            }
          }} />
        <div className="composer-footer">
          <span>{draft.length} / 2000</span>
          <button type="submit" disabled={!canSend}>{t("发送 ")}<span>↑</span></button>
        </div>
      </form>
      <p className="footnote">{t("Enter 发送 · Shift + Enter 换行 ")}<span>{t("AI 角色生成内容可能有误，请勿输入敏感信息。")}</span></p>
    </div>
  );
}
