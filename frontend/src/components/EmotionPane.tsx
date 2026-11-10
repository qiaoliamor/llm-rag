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
  async function run(operation:()=>Promise<unknown>,message:string){setBusy(true);onBusyChange(true);setError('');setNotice('');try{await operation();onHistoryCleared();load(await getEmotion());setNotice(message);}catch(e){setError(e instanceof Error?e.message:'操作失败，请重试。');}finally{setBusy(false);onBusyChange(false);}}
  if(!data||!config)return <section className="workspace-pane"><h3>情绪关怀</h3><p role={error?'alert':undefined}>{error||'正在读取设置…'}</p></section>;
  return <section className="workspace-pane" aria-label="情绪关怀设置"><h3>怎么陪你，由你决定。</h3>{locked&&<p className="pane-notice">亲密度90分解锁使用。仍可关闭分析、清空临时推测及删除设置。</p>}
    <p className="pane-description">默认关闭。开启后，最近几轮聊天会额外发送给当前模型做情绪估计；不是读心或诊断。推测只在本次对话内短期保留，不写成长期记忆。你的自述和纠正优先，分析失败仍可正常聊天。保存、纠正、清空或删除会清空当前短期聊天，避免旧推测继续影响回应。</p>
    <label><input type="checkbox" checked={config.enabled} disabled={busy||locked} onChange={e=>setConfig({...config,enabled:e.target.checked})}/> 允许情绪分析</label>
    <div className="memory-settings">
      <label>每几轮分析 <input aria-label="每几轮分析" type="number" min={1} max={10} disabled={busy} value={config.interval} onChange={e=>setConfig({...config,interval:Number(e.target.value)})}/></label>
      <label>分析最近几轮 <input aria-label="分析最近几轮" type="number" min={1} max={12} disabled={busy} value={config.window} onChange={e=>setConfig({...config,window:Number(e.target.value)})}/></label>
      <label>冷却轮数 <input aria-label="冷却轮数" type="number" min={1} max={10} disabled={busy} value={config.cooldown} onChange={e=>setConfig({...config,cooldown:Number(e.target.value)})}/></label>
      <label>推测置信阈值 <input aria-label="推测置信阈值" type="number" min={0} max={1} step={0.1} disabled={busy} value={config.threshold} onChange={e=>setConfig({...config,threshold:Number(e.target.value)})}/></label>
      <label>平时希望怎样陪你 <select aria-label="平时希望怎样陪你" value={config.preference} disabled={busy} onChange={e=>setConfig({...config,preference:e.target.value as SupportPreference})}>{Object.entries(preferences).map(([key,value])=><option value={key} key={key}>{value}</option>)}</select></label>
    </div>
    <button disabled={busy} onClick={()=>void run(()=>saveEmotionSettings(config,csrf),'设置已保存，短期聊天与旧推测已清空。')}>保存情绪设置</button>
    <h4>当前临时参考</h4>
    {data.assessment?<p>{data.assessment.source==='user'?'你的自述/纠正':'模型推测，可纠正'}：{data.assessment.labels.map(x=>labels[x]).join('、')}。{data.assessment.source==='model'&&`工具置信度 ${Math.round(data.assessment.confidence*100)}%（不是校准过的真实概率）。`}</p>:<p>暂无有效情绪参考；不会替你下结论。</p>}
    <p className="pane-description">刷新后可重新读取；新对话、撤回或清空时移除，最多10分钟或6轮后失效。否认难过并不等于开心，会保留其他心情未知。</p>
    <label>我现在的心情 <select aria-label="我现在的心情" value={label} disabled={busy||locked||!data.settings.enabled} onChange={e=>setLabel(e.target.value as EmotionLabel)}>{Object.entries(labels).map(([key,value])=><option value={key} key={key}>{value}</option>)}</select></label>
    <label>这会儿希望怎样陪我 <select aria-label="这会儿希望怎样陪我" value={preference} disabled={busy||locked||!data.settings.enabled} onChange={e=>setPreference(e.target.value as SupportPreference)}>{Object.entries(preferences).map(([key,value])=><option value={key} key={key}>{value}</option>)}</select></label>
    <div className="memory-actions"><button disabled={busy||locked||!data.settings.enabled} onClick={()=>void run(()=>correctEmotion(label,preference,csrf),'已以你的纠正为准，旧对话和推测已清除。')}>以我说的为准</button><button className="quiet" disabled={busy} onClick={()=>void run(()=>clearEmotion(csrf),'临时推测与短期聊天已清空。')}>清空临时推测</button><button className="quiet danger" disabled={busy} onClick={()=>setDeleting(true)}>删除情绪设置</button></div>
    {deleting&&<div role="alertdialog" aria-label="删除情绪设置确认"><p>删除偏好与设置，关闭分析并清空短期聊天和推测？</p><button disabled={busy} onClick={()=>void run(async()=>{await deleteEmotionSettings(csrf);setDeleting(false);},'设置已删除，分析已关闭。')}>确认删除</button><button className="quiet" disabled={busy} onClick={()=>setDeleting(false)}>取消</button></div>}
    {error&&<p role="alert" className="pane-error">{error}</p>}{notice&&<p role="status" className="pane-notice">{notice}</p>}
    <p className="pane-description">明确自述或手动纠正会直接以你说的为准；强烈表达可能提前分析，其余默认每3轮分析最近6轮，冷却2轮。关闭后仍保留普通对话与自然关心；设置变更会撤销在途旧回复。</p>
  </section>;
}
