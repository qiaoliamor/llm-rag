import { t } from '../i18n';
import { useEffect, useRef } from 'react';

export function ResetDialog({ open, busy, onCancel, onConfirm }: {
  open: boolean;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
    else if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  return (
    <dialog ref={dialog} aria-labelledby="reset-title" onCancel={event => { event.preventDefault(); if (!busy) onCancel(); }}>
      <h3 id="reset-title">{t("翻开新的一页？")}</h3><p>{t("当前对话会被清空，无法恢复。")}</p>
      <div>
        <button className="quiet" disabled={busy} onClick={onCancel}>{t("再聊一会儿")}</button>
        <button id="confirm-reset" disabled={busy} onClick={onConfirm}>{busy ? t("正在清空…") : t("开始新对话")}</button>
      </div>
    </dialog>
  );
}
