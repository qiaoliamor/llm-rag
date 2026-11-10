import { useEffect, useRef, useState } from 'react';
import { clearProfile, demoCredit, getAccount, saveProfile, sendGift } from '../api';
import type { GrowthAccount } from '../types';
import { BondProgress } from './BondProgress';

export function AccountPane({csrf,onUpdate,onManage,onBusyChange}:{csrf:string;onUpdate:(data:GrowthAccount)=>void;onManage:(pane:'memories'|'weather'|'emotion')=>void;onBusyChange:(busy:boolean)=>void}) {
  const [data,setData]=useState<GrowthAccount|null>(null);
  const [profile,setProfile]=useState({name:'',email:'',phone:''});
  const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
  const [pending,setPending]=useState<{kind:'gift'|'credit'|'clear';gift?:GrowthAccount['gifts'][number];key:string}|null>(null);
  const lock=useRef(false);
  function load(next:GrowthAccount){setData(next);setProfile(next.profile);onUpdate(next);}
  useEffect(()=>{let active=true;getAccount().then(next=>{if(active)load(next);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  async function run(operation:()=>Promise<GrowthAccount>,message:string,close=false){
    if(lock.current)return;lock.current=true;setBusy(true);onBusyChange(true);setError('');setNotice('');
    try{load(await operation());setNotice(message);if(close)setPending(null);}catch(e){setError(e instanceof Error?e.message:'操作失败，请重试。');}
    finally{lock.current=false;setBusy(false);onBusyChange(false);}
  }
  function confirm(){
    if(!pending||!data)return;
    if(pending.kind==='gift'&&pending.gift)void run(()=>sendGift(data.character.id,pending.gift!.id,pending.key,csrf),'礼物已送达，相处进度已更新。',true);
    else if(pending.kind==='credit')void run(()=>demoCredit(pending.key,csrf),'已领取100演示币，没有产生真实扣款。',true);
    else void run(()=>clearProfile(csrf),'姓名和联系方式已清除；相处进度与钱包保留。',true);
  }
  return <section className="workspace-pane account-pane" aria-label="个人账户">
    <p className="eyebrow">YOUR LITTLE CORNER</p><h3>关于你，慢慢认识。</h3>
    <p className="pane-description">本地体验账户，尚不支持跨设备登录或身份恢复。邮箱和电话为选填资料，未验证，不用于付款或发送消息。</p>
    {error&&<p role="alert" className="pane-error">{error}</p>}{notice&&<p role="status" className="pane-notice">{notice}</p>}
    {!data?<p>正在读取账户…</p>:<>
      <div className="account-grid"><form className="profile-card" onSubmit={e=>{e.preventDefault();void run(()=>saveProfile(profile,csrf),'个人资料已保存。');}}>
        <h4>个人资料</h4>{(['name','email','phone'] as const).map(key=><label key={key}>{({name:'名字',email:'邮箱（选填）',phone:'电话（选填）'})[key]}<input aria-label={key==='name'?'名字':key==='email'?'邮箱（选填）':'电话（选填）'} type={key==='email'?'email':key==='phone'?'tel':'text'} value={profile[key]} maxLength={key==='name'?40:key==='email'?254:24} disabled={busy} onChange={e=>setProfile({...profile,[key]:e.target.value})}/></label>)}
        <div className="memory-actions"><button disabled={busy}>保存资料</button><button type="button" className="quiet" disabled={busy} onClick={()=>setPending({kind:'clear',key:crypto.randomUUID()})}>清除个人资料</button></div>
      </form><section className="wallet-card"><span className="eyebrow">A LITTLE GIFT</span><h4>我的钱包</h4><strong className="coin-balance">{data.coins}<small> 演示币</small></strong><p>首次赠送100币。当前没有真实支付；演示币仅供本地体验，不可提现或转让。</p><button disabled={busy} onClick={()=>setPending({kind:'credit',key:crypto.randomUUID()})}>充值通道</button><p>演示领取每次100币，每日最多500币（按UTC日更新）。</p></section></div>
      <BondProgress account={data}/>
      <h4>送一份小心意</h4><p className="pane-description">礼物用演示币购买并直接送出。送礼并非必需，不送礼也能通过有效对话时长解锁全部能力；不会因离开而扣分。有效相处每分钟1分，每日最多10分（UTC）；挂机、失败回复和等待模型不计入。</p>
      <div className="gift-grid">{data.gifts.map(gift=><article className="gift-card" key={gift.id}><span aria-hidden="true">{gift.id==='bookmark'?'❀':gift.id==='tea'?'♧':'✧'}</span><h4>{gift.name}</h4><p>{gift.description}</p><small>{gift.price} 币 · 亲密度最多 +{gift.points}</small><button disabled={busy||data.coins<gift.price||data.character.score>=100} onClick={()=>setPending({kind:'gift',gift,key:crypto.randomUUID()})}>送出{gift.name}</button></article>)}</div>
      <h4>角色能力与隐私</h4><p className="pane-description">解锁后不会自动开启。由你决定是否记住经历、分析情绪或查询天气；基础聊天一直可用。已有资料的查看、撤回和删除始终开放。</p>
      <div className="ability-controls"><button className="quiet" disabled={busy} onClick={()=>onManage('memories')}>{data.character.abilities.memory?'管理长期记忆':'查看或删除已有记忆 · 30分解锁使用'}</button><button className="quiet" disabled={busy} onClick={()=>onManage('emotion')}>{data.character.abilities.emotion?'管理情绪关怀':'情绪隐私设置 · 60分解锁使用'}</button><button className="quiet" disabled={busy} onClick={()=>onManage('weather')}>{data.character.abilities.weather?'管理天气关怀':'天气隐私设置 · 90分解锁使用'}</button></div>
      <h4>最近的礼物与钱包记录</h4>{!data.ledger.length?<p className="pane-description">还没有记录。</p>:<ul className="wallet-ledger">{data.ledger.map(entry=><li key={entry.request_id}><span>{entry.action==='demo_credit'?'演示币领取':data.gifts.find(gift=>'gift:'+gift.id===entry.action)?.name ?? '礼物'}</span><span>{entry.coins_delta>0?'+':''}{entry.coins_delta} 币{entry.points_delta>0?` · 亲密度 +${entry.points_delta}`:''}</span></li>)}</ul>}
    </>}
    {pending&&<div role="alertdialog" aria-label="账户操作确认" className="account-confirm"><h4>{pending.kind==='gift'?`送给沈砚：${pending.gift?.name}`:pending.kind==='credit'?'演示充值':'清除个人资料'}</h4><p>{pending.kind==='gift'?`将扣除 ${pending.gift?.price} 演示币，亲密度增加 ${Math.min(pending.gift?.points??0,100-(data?.character.score??0))} 分。`:pending.kind==='credit'?'领取100演示币。此处不接真实支付，不收款、不创建付款订单。':'清除名字、邮箱与电话，不删除记忆、亲密度和钱包。'}</p><button disabled={busy} onClick={confirm}>确认{pending.kind==='gift'?'送出':pending.kind==='credit'?'领取':'清除'}</button><button className="quiet" disabled={busy} onClick={()=>setPending(null)}>取消</button></div>}
  </section>;
}
