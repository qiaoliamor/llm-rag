import { errorText, t } from '../i18n';
import { useEffect, useState } from 'react';
import { getEmotion, saveEmotionSettings, deleteEmotionSettings, correctEmotion, clearEmotion } from '../api';
import type { EmotionData, EmotionSettings, EmotionLabel, SupportPreference } from '../types';

const labels: Record<EmotionLabel,string>={unknown:'还不能确定',neutral:'平静',joy:'开心',sadness:'难过',anxiety:'焦虑/紧张',anger:'生气',tired:'疲惫'};
const preferences: Record<SupportPreference,string>={ask:'先问我想怎么聊',listen:'先听我说',encourage:'温和鼓励',practical:'一起想办法'};
export function EmotionPane({csrf,onHistoryCleared,onBusyChange,locked=false}:{csrf:string;onHistoryCleared:()=>void;onBusyChange:(busy:boolean)=>void;locked?:boolean}) {
  const [data,setData]=useState<EmotionData|null>(null);
  const [config,setConfig]=useState<EmotionSettings|null>(null);
  const [label,setLabel]=useState<EmotionLabel>('unknown');
  const [preference,setPreference]=useState<SupportPreference>('ask');
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const [deleting,setDeleting]=useState(false);
  function load(next:EmotionData){setData(next);setConfig(locked ? {...next.settings, enabled:false} : next.settings);}
  useEffect(()=>{let active=true;getEmotion().then(x=>{if(active)load(x);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  async function run(operation:()=>Promise<unknown>,message:string){setBusy(true);onBusyChange(true);setError('');setNotice('');try{await operation();onHistoryCleared();load(await getEmotion());setNotice(message);}catch(e){setError(e instanceof Error?e.message:t("操作失败，请重试。"));}finally{setBusy(false);onBusyChange(false);}}
  if(!data||!config)return <section className="workspace-pane"><h3>{t("情绪关怀")}</h3><p role={error?'alert':undefined}>{errorText(error)||t("正在读取设置…")}</p></section>;
  return <section className="workspace-pane" aria-label={t("情绪关怀设置")}><h3>{t("怎么陪你，由你决定。")}</h3>{locked&&<p className="pane-notice">{t("亲密度90分解锁使用。仍可关闭分析、清空临时推测及删除设置。")}</p>}
    <p className="pane-description">{t("默认关闭。解锁并开启后，每轮会把本轮原文、有限近期聊天和当前参考标签发送给当前模型，理解自述及是否需要分析；完整估计仍受间隔与冷却控制，两步共用6秒默认预算。不是读心或诊断，模型理解的自述也可能出错，可手动纠正。参考仅短期保留，不写入长期记忆；失败仍可聊天。保存、纠正、清空或删除会清空短期聊天及相关参考。")}</p>
    <label><input type="checkbox" checked={config.enabled} disabled={busy||locked} onChange={e=>setConfig({...config,enabled:e.target.checked})}/>{t(" 允许情绪分析")}</label>
    <div className="memory-settings">
      <label>{t("每几轮分析 ")}<input aria-label={t("每几轮分析")} type="number" min={1} max={10} disabled={busy} value={config.interval} onChange={e=>setConfig({...config,interval:Number(e.target.value)})}/></label>
      <label>{t("分析最近几轮 ")}<input aria-label={t("分析最近几轮")} type="number" min={1} max={12} disabled={busy} value={config.window} onChange={e=>setConfig({...config,window:Number(e.target.value)})}/></label>
      <label>{t("冷却轮数 ")}<input aria-label={t("冷却轮数")} type="number" min={1} max={10} disabled={busy} value={config.cooldown} onChange={e=>setConfig({...config,cooldown:Number(e.target.value)})}/></label>
      <label>{t("推测置信阈值 ")}<input aria-label={t("推测置信阈值")} type="number" min={0} max={1} step={0.1} disabled={busy} value={config.threshold} onChange={e=>setConfig({...config,threshold:Number(e.target.value)})}/></label>
      <label>{t("平时希望怎样陪你 ")}<select aria-label={t("平时希望怎样陪你")} value={config.preference} disabled={busy} onChange={e=>setConfig({...config,preference:e.target.value as SupportPreference})}>{Object.entries(preferences).map(([key,value])=><option value={key} key={key}>{t(value)}</option>)}</select></label>
    </div>
    <button disabled={busy} onClick={()=>void run(()=>saveEmotionSettings(config,csrf),t("设置已保存，短期聊天与旧推测已清空。"))}>{t("保存情绪设置")}</button>
    <h4>{t("当前临时参考")}</h4>
    {data.assessment?<p>{data.assessment.source==='user'?t("你的自述/纠正"):t("模型推测，可纠正")}：{data.assessment.labels.map(x=>t(labels[x])).join('、')}。{data.assessment.source==='model'&&t("工具置信度 {1}%（不是校准过的真实概率）。", [Math.round(data.assessment.confidence*100)])}</p>:<p>{t("暂无有效情绪参考；不会替你下结论。")}</p>}
    <p className="pane-description">{t("刷新后可重新读取；新对话、撤回或清空时移除，最多10分钟或6轮后失效。否认难过并不等于开心，会保留其他心情未知。")}</p>
    <label>{t("我现在的心情 ")}<select aria-label={t("我现在的心情")} value={label} disabled={busy||locked||!data.settings.enabled} onChange={e=>setLabel(e.target.value as EmotionLabel)}>{Object.entries(labels).map(([key,value])=><option value={key} key={key}>{t(value)}</option>)}</select></label>
    <label>{t("这会儿希望怎样陪我 ")}<select aria-label={t("这会儿希望怎样陪我")} value={preference} disabled={busy||locked||!data.settings.enabled} onChange={e=>setPreference(e.target.value as SupportPreference)}>{Object.entries(preferences).map(([key,value])=><option value={key} key={key}>{t(value)}</option>)}</select></label>
    <div className="memory-actions"><button disabled={busy||locked||!data.settings.enabled} onClick={()=>void run(()=>correctEmotion(label,preference,csrf),t("已以你的纠正为准，旧对话和推测已清除。"))}>{t("以我说的为准")}</button><button className="quiet" disabled={busy} onClick={()=>void run(()=>clearEmotion(csrf),t("临时推测与短期聊天已清空。"))}>{t("清空临时推测")}</button><button className="quiet danger" disabled={busy} onClick={()=>setDeleting(true)}>{t("删除情绪设置")}</button></div>
    {deleting&&<div role="alertdialog" aria-label={t("删除情绪设置确认")}><p>{t("删除偏好与设置，关闭分析并清空短期聊天和推测？")}</p><button disabled={busy} onClick={()=>void run(async()=>{await deleteEmotionSettings(csrf);setDeleting(false);},t("设置已删除，分析已关闭。"))}>{t("确认删除")}</button><button className="quiet" disabled={busy} onClick={()=>setDeleting(false)}>{t("取消")}</button></div>}
    {error&&<p role="alert" className="pane-error">{errorText(error)}</p>}{notice&&<p role="status" className="pane-notice">{t(notice)}</p>}
    <p className="pane-description">{t("中日自述、否认和提前触发由模型理解，只有页面手动纠正标为你的确认。完整估计默认每3轮、最近6轮、冷却2轮；提前触发也不能绕过冷却。本轮明确陪伴偏好不自动修改已保存设置。关闭后仍可普通聊天，设置变更会撤销在途旧回复。")}</p>
  </section>;
}
