import { useEffect, useRef, useState } from 'react';
import type { GrowthAccount } from '../types';

type Ability = keyof GrowthAccount['character']['abilities'];
export const ABILITIES: {key:Ability;label:string;description:(name:string)=>string}[] = [
  {key:'memory',label:'长期记忆',description:name=>`现在，${name}可以在你开启并确认后，记住重要经历，在以后的聊天里自然接上。`},
  {key:'weather',label:'天气关怀',description:name=>`现在，${name}可以在你允许后，结合所选城市的天气，在聊天需要时提醒添衣或带伞。`},
  {key:'emotion',label:'情绪关怀',description:name=>`现在，${name}可以在你允许后，参考最近的对话，用更贴合心情的方式陪你。不确定时会问你，你也可以纠正。`},
];

export function UnlockedAbilities({account}:{account?:GrowthAccount|null}) {
  const [selected,setSelected]=useState<Ability|null>(null);
  const dialog=useRef<HTMLDialogElement>(null);
  const name=account?.character.name ?? '沈砚';
  const available=ABILITIES.filter(item=>account?.character.abilities[item.key]);
  const item=available.find(item=>item.key===selected);
  useEffect(()=>{
    if(item&&!dialog.current?.open)dialog.current?.showModal();
    else if(!item&&dialog.current?.open)dialog.current.close();
  },[item]);
  if(!available.length)return null;
  return <div className="unlocked-abilities" aria-label="已解锁的陪伴方式">
    <span>现在可以</span>{available.map(item=><button key={item.key} type="button" className="ability-text" onClick={()=>setSelected(item.key)}>{item.label}</button>)}
    <dialog ref={dialog} aria-label="能力说明" onCancel={event=>{event.preventDefault();setSelected(null);}}>
      <h3>{item?.label}</h3><p>{item?.description(name)}</p><p>解锁不会自动开启。你可以在个人账户中授权，之后随时关闭、纠正或删除已有资料。</p>
      <div><button type="button" className="quiet" onClick={()=>setSelected(null)}>知道了</button></div>
    </dialog>
  </div>;
}

export function UnlockCelebration({account}:{account:GrowthAccount|null}) {
  // First snapshot is a baseline, not a new achievement. No profile/score is
  // written to localStorage; browser reloads never replay old celebrations.
  const seen=useRef(new Map<string,Set<Ability>>());
  const activeCharacter=useRef<string|null>(null);
  const [items,setItems]=useState<Ability[]>([]);
  const [paused,setPaused]=useState(false);
  useEffect(()=>{
    if(!account){
      if(seen.current.size){seen.current.clear();activeCharacter.current=null;setItems([]);setPaused(false);}
      return;
    }
    const id=account.character.id;
    const current=ABILITIES.filter(item=>account.character.abilities[item.key]).map(item=>item.key);
    const previous=seen.current.get(id);
    if(activeCharacter.current!==id){setItems([]);setPaused(false);activeCharacter.current=id;}
    if(!previous){seen.current.set(id,new Set(current));return;}
    const added=current.filter(key=>!previous.has(key));
    current.forEach(key=>previous.add(key));
    if(added.length)setItems(old=>[...new Set([...old,...added])]);
  },[account]);
  useEffect(()=>{
    if(!items.length||paused)return;
    const timer=window.setTimeout(()=>setItems([]),6000+(items.length-1)*3000);
    return()=>window.clearTimeout(timer);
  },[items,paused]);
  if(!items.length||!account)return null;
  const name=account.character.name;
  return <aside className="unlock-celebration" aria-label="新的陪伴方式" onMouseEnter={()=>setPaused(true)} onMouseLeave={()=>setPaused(false)} onFocusCapture={()=>setPaused(true)} onBlurCapture={event=>{if(!event.currentTarget.contains(event.relatedTarget))setPaused(false);}}>
    <div className="unlock-copy" role="status" aria-live="polite" aria-atomic="true">
      <span className="unlock-spark" aria-hidden="true">✧</span><p className="eyebrow">A LITTLE CLOSER</p><h3>相处，又近了一点。</h3>
      {ABILITIES.filter(item=>items.includes(item.key)).map(item=><div key={item.key}><strong>{item.label}已解锁</strong><p>{item.description(name)}</p></div>)}
      <small>之后可点击已解锁的能力文字，再次查看说明。是否开启，仍由你决定。</small>
    </div>
    <button type="button" className="quiet" aria-label="收起解锁提醒" onClick={()=>{setItems([]);setPaused(false);}}>收起</button>
  </aside>;
}
