import { errorText, t } from '../i18n';
import { useEffect, useRef, useState } from 'react';
import { clearProfile, demoCredit, getAccount, saveProfile, sendGift } from '../api';
import type { GrowthAccount } from '../types';
import { BondProgress } from './BondProgress';
import { UnlockedAbilities } from './AbilityExperience';

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
    try{load(await operation());setNotice(message);if(close)setPending(null);}catch(e){setError(e instanceof Error?e.message:t("操作失败，请重试。"));}
    finally{lock.current=false;setBusy(false);onBusyChange(false);}
  }
  function confirm(){
    if(!pending||!data)return;
    if(pending.kind==='gift'&&pending.gift)void run(()=>sendGift(data.character.id,pending.gift!.id,pending.key,csrf),t("礼物已送达，相处进度已更新。"),true);
    else if(pending.kind==='credit')void run(()=>demoCredit(pending.key,csrf),t("已领取100演示币，没有产生真实扣款。"),true);
    else void run(()=>clearProfile(csrf),t("姓名和联系方式已清除；相处进度与钱包保留。"),true);
  }
  return <section className="workspace-pane account-pane" aria-label={t("个人账户")}>
    <p className="eyebrow">YOUR LITTLE CORNER</p><h3>{t("关于你，慢慢认识。")}</h3>
    <p className="pane-description">{t("本地体验账户，尚不支持跨设备登录或身份恢复。邮箱和电话为选填资料，未验证，不用于付款或发送消息。")}</p>
    {error&&<p role="alert" className="pane-error">{errorText(error)}</p>}{notice&&<p role="status" className="pane-notice">{t(notice)}</p>}
    {!data?<p>{t("正在读取账户…")}</p>:<>
      <div className="account-grid"><form className="profile-card" onSubmit={e=>{e.preventDefault();void run(()=>saveProfile(profile,csrf),t("个人资料已保存。"));}}>
        <h4>{t("个人资料")}</h4>{(['name','email','phone'] as const).map(key=><label key={key}>{({name:t("名字"),email:t("邮箱（选填）"),phone:t("电话（选填）")})[key]}<input aria-label={key==='name'?t("名字"):key==='email'?t("邮箱（选填）"):t("电话（选填）")} type={key==='email'?'email':key==='phone'?'tel':'text'} value={profile[key]} maxLength={key==='name'?40:key==='email'?254:24} disabled={busy} onChange={e=>setProfile({...profile,[key]:e.target.value})}/></label>)}
        <div className="memory-actions"><button disabled={busy}>{t("保存资料")}</button><button type="button" className="quiet" disabled={busy} onClick={()=>setPending({kind:'clear',key:crypto.randomUUID()})}>{t("清除个人资料")}</button></div>
      </form><section className="wallet-card"><span className="eyebrow">A LITTLE GIFT</span><h4>{t("我的钱包")}</h4><strong className="coin-balance">{data.coins}<small>{t(" 演示币")}</small></strong><p>{t("首次赠送100币。当前没有真实支付；演示币仅供本地体验，不可提现或转让。")}</p><button disabled={busy} onClick={()=>setPending({kind:'credit',key:crypto.randomUUID()})}>{t("充值通道")}</button><p>{t("演示领取每次100币，每日最多500币（按UTC日更新）。")}</p></section></div>
      <BondProgress account={data}/><UnlockedAbilities account={data}/>
      <h4>{t("送一份小心意")}</h4><p className="pane-description">{t("礼物用演示币购买并直接送出。送礼并非必需，不送礼也能通过有效对话时长解锁全部能力；不会因离开而扣分。有效相处每分钟1分，每日最多10分（UTC）；挂机、失败回复和等待模型不计入。")}</p>
      <div className="gift-grid">{data.gifts.map(gift=><article className="gift-card" key={gift.id}><span aria-hidden="true">{gift.id==='bookmark'?'❀':gift.id==='tea'?'♧':'✧'}</span><h4>{t(gift.name)}</h4><p>{t(gift.description)}</p><small>{gift.price}{t(" 币 · 亲密度最多 +")}{gift.points}</small><button disabled={busy||data.coins<gift.price||data.character.score>=100} onClick={()=>setPending({kind:'gift',gift,key:crypto.randomUUID()})}>{t("送出")}{t(gift.name)}</button></article>)}</div>
      <h4>{t("由你决定的陪伴")}</h4><p className="pane-description">{t("解锁后不会自动开启。由你决定是否记住经历、分析情绪或查询天气；基础聊天一直可用。已有资料的查看、撤回和删除始终开放。")}</p>
      <details className="privacy-tools"><summary>{t("隐私与已有资料")}</summary><p className="pane-description">{t("即使能力尚未解锁，仍可查看、撤回或删除已有资料。")}</p><div className="ability-controls"><button className="quiet" disabled={busy} onClick={()=>onManage('memories')}>{t("记忆资料与授权")}</button><button className="quiet" disabled={busy} onClick={()=>onManage('weather')}>{t("天气资料与授权")}</button><button className="quiet" disabled={busy} onClick={()=>onManage('emotion')}>{t("情绪资料与授权")}</button></div></details>
      <h4>{t("最近的礼物与钱包记录")}</h4>{!data.ledger.length?<p className="pane-description">{t("还没有记录。")}</p>:<ul className="wallet-ledger">{data.ledger.map(entry=><li key={entry.request_id}><span>{entry.action==='demo_credit'?t("演示币领取"):data.gifts.find(gift=>'gift:'+gift.id===entry.action)?.name ? t(data.gifts.find(gift=>'gift:'+gift.id===entry.action)!.name) : t("礼物")}</span><span>{entry.coins_delta>0?'+':''}{entry.coins_delta}{t(" 币")}{entry.points_delta>0?t(" · 亲密度 +{1}", [entry.points_delta]):''}</span></li>)}</ul>}
    </>}
    {pending&&<div role="alertdialog" aria-label={t("账户操作确认")} className="account-confirm"><h4>{pending.kind==='gift'?t("送给沈砚：{1}", [t(pending.gift?.name ?? '')]):pending.kind==='credit'?t("演示充值"):t("清除个人资料")}</h4><p>{pending.kind==='gift'?t("将扣除 {1} 演示币，亲密度增加 {2} 分。", [pending.gift?.price, Math.min(pending.gift?.points??0,100-(data?.character.score??0))]):pending.kind==='credit'?t("领取100演示币。此处不接真实支付，不收款、不创建付款订单。"):t("清除名字、邮箱与电话，不删除记忆、亲密度和钱包。")}</p><button disabled={busy} onClick={confirm}>{t("确认")}{pending.kind==='gift'?t("送出"):pending.kind==='credit'?t("领取"):t("清除")}</button><button className="quiet" disabled={busy} onClick={()=>setPending(null)}>{t("取消")}</button></div>}
  </section>;
}
