import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { getLocale, setLocale, translate } from './i18n';
import ja from './locales/ja.json';
import { UnlockedAbilities, UnlockCelebration } from './components/AbilityExperience';
import { Composer } from './components/Composer';
import { MemoryPane } from './components/MemoryPane';
import { saveProfile } from './api';
import type { GrowthAccount } from './types';

const account: GrowthAccount = {profile:{name:'合成ユーザー',email:'synthetic@example.invalid',phone:''},coins:100,currency_mode:'demo',starting_coins:100,
  character:{id:'shen_yan',name:'沈砚',score:29,active_seconds:0,abilities:{memory:false,weather:false,emotion:false}},thresholds:{memory:30,weather:60,emotion:90},gifts:[],ledger:[]};
const session={csrf_token:'synthetic-csrf',provider:'gemini',configured:true,model:'synthetic-model',api_key_env:'GEMINI_API_KEY',
  character:{id:'shen_yan',name:'沈砚',subtitle:'听你说，也陪你慢慢想。',version:'synthetic'},messages:[],account};
const response=(body:unknown,status=200)=>({ok:status<400,status,json:async()=>body}) as Response;
afterEach(()=>{ act(()=>setLocale('zh-CN')); localStorage.clear(); vi.restoreAllMocks(); });

describe('Japanese presentation',()=>{
  it('covers authored copy and keeps interpolation variables in every translation',()=>{
    const dictionary:Record<string,string>=ja;
    for(const [source,target] of Object.entries(dictionary)){
      const vars=(value:string)=>[...value.matchAll(/\{(\d+)\}/g)].map(x=>x[1]).sort();
      expect(vars(target),source).toEqual(vars(source));
      expect(target.trim(),source).not.toBe('');
    }
    const sources=import.meta.glob<string>(['./App.tsx','./api.ts','./components/*.tsx','!./**/*.test.tsx'],{query:'?raw',import:'default',eager:true});
    for(const [path,text] of Object.entries(sources)){
      for(const match of text.matchAll(/\bt\(("(?:[^"\\]|\\.)*")/g)){
        const key:string=JSON.parse(match[1]);
        if(/[\u3400-\u9fff]/.test(key))expect(dictionary[key.trim()],path+': '+key).toBeDefined();
      }
    }
    expect(translate('ja-JP','距离{1}还有 {2} 分。',['気が合って',2])).toBe('「気が合って」まであと2点。');
  });

  it('switches and persists UI without extra requests, changing history or unlocking abilities',async()=>{
    const fetcher=vi.fn().mockResolvedValue(response({...session,messages:[{role:'user',content:'今天工作有点累'}]}));vi.stubGlobal('fetch',fetcher);
    const {unmount}=render(<App/>);
    await screen.findByRole('button',{name:'和沈砚聊天'});
    fireEvent.change(screen.getByLabelText('语言 / 言語'),{target:{value:'ja-JP'}});
    expect(screen.getByText('自分のために、少しだけ。')).toBeInTheDocument();
    expect(document.documentElement.lang).toBe('ja-JP');expect(document.title).toContain('心語');
    expect(localStorage.getItem('persona.ui.locale')).toBe('ja-JP');
    expect(screen.queryByRole('button',{name:'長期記憶'})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'沈硯と話す'}));
    expect(screen.getByText('今天工作有点累')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(1);
    unmount();render(<App/>);await screen.findByRole('button',{name:'沈硯と話す'});
    fireEvent.change(screen.getByLabelText('语言 / 言語'),{target:{value:'zh-CN'}});
    expect(screen.getByRole('button',{name:'和沈砚聊天'})).toBeInTheDocument();
  });

  it('sends Japanese locale and CSRF, preserves reply verbatim and restores failed draft without retry',async()=>{
    setLocale('ja-JP');const fetcher=vi.fn().mockResolvedValueOnce(response(session))
      .mockResolvedValueOnce(response({reply:'こんにちは。ゆっくり聞かせて。'}))
      .mockResolvedValueOnce(response({code:'timeout',detail:'private provider detail'},504));vi.stubGlobal('fetch',fetcher);
    render(<App/>);fireEvent.click(await screen.findByRole('button',{name:'沈硯と話す'}));
    const input=screen.getByLabelText('沈硯に話したいこと');
    fireEvent.change(input,{target:{value:'こんにちは'}});fireEvent.click(screen.getByRole('button',{name:/送信/}));
    expect(await screen.findByText('こんにちは。ゆっくり聞かせて。')).toBeInTheDocument();
    const options=fetcher.mock.calls[1][1];expect(JSON.parse(options.body)).toEqual({message:'こんにちは',locale:'ja-JP'});
    expect(options.headers['X-CSRF-Token']).toBe('synthetic-csrf');
    fireEvent.change(input,{target:{value:'今日は少し疲れた'}});fireEvent.click(screen.getByRole('button',{name:/送信/}));
    expect(await screen.findByRole('alert')).toHaveTextContent('今は少しつながりにくいみたい');
    expect(input).toHaveValue('今日は少し疲れた');expect(fetcher).toHaveBeenCalledTimes(3);
    expect(screen.queryByText('private provider detail')).not.toBeInTheDocument();
  });

  it('does not send an IME Enter or keyCode 229, then sends a committed Enter once',()=>{
    setLocale('ja-JP');const send=vi.fn();render(<Composer draft="こんにちは" onChange={vi.fn()} onSend={send} disabled={false} canSend error="" focusVersion={0}/>);
    const input=screen.getByLabelText('沈硯に話したいこと');
    fireEvent.keyDown(input,{key:'Enter',isComposing:true});fireEvent.keyDown(input,{key:'Enter',keyCode:229});expect(send).not.toHaveBeenCalled();
    fireEvent.keyDown(input,{key:'Enter'});expect(send).toHaveBeenCalledTimes(1);
  });

  it('explains only earned ability in Japanese without changing consent',()=>{
    setLocale('ja-JP');const next={...account,character:{...account.character,score:30,abilities:{memory:true,weather:false,emotion:false}}};
    render(<UnlockedAbilities account={next}/>);fireEvent.click(screen.getByRole('button',{name:'長期記憶'}));
    const dialog=screen.getByRole('dialog',{name:'機能の説明'});expect(dialog).toHaveTextContent('自動ではオンになりません');
    expect(screen.queryByRole('button',{name:'気持ちに寄り添う'})).not.toBeInTheDocument();
    fireEvent.keyDown(dialog,{key:'Escape'});fireEvent(dialog,new Event('cancel',{bubbles:true,cancelable:true}));
    expect(dialog).not.toHaveAttribute('open');
  });

  it('keeps Japanese unlock animation dismissal and does not replay the initial snapshot',()=>{
    setLocale('ja-JP');const {rerender}=render(<UnlockCelebration account={account}/>);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    rerender(<UnlockCelebration account={{...account,character:{...account.character,score:30,abilities:{memory:true,weather:false,emotion:false}}}}/>);
    expect(screen.getByRole('status')).toHaveTextContent('長期記憶が解放されました');
    fireEvent.click(screen.getByRole('button',{name:'解放のお知らせを閉じる'}));expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('handles disabled localStorage and rejects unsupported language choices',()=>{
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('synthetic storage disabled');});
    expect(()=>setLocale('ja-JP')).not.toThrow();expect(getLocale()).toBe('ja-JP');
    setLocale('invalid' as 'ja-JP');expect(getLocale()).toBe('ja-JP');
  });

  it('uses Japanese known-code errors without exposing an unknown server message',async()=>{
    setLocale('ja-JP');vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(response({code:'ability_locked',detail:'不能泄露的错误'},403))
      .mockResolvedValueOnce(response({code:'unknown',detail:'不能泄露的错误'},500)));
    await expect(saveProfile(account.profile,'csrf')).rejects.toThrow('親密度の条件');
    await expect(saveProfile(account.profile,'csrf')).rejects.toThrow('操作を完了できませんでした');
  });

  it('preserves Japanese memory text and uses Japanese delete confirmation without implicit edits',async()=>{
    setLocale('ja-JP');const fact='東京の「合成室」で面接がある。';
    const item={id:'synthetic-memory',fact,status:'confirmed',category:'event',event_date:null,source_kind:'manual',version:1,created_at:'2026-11-10T00:00:00Z',updated_at:'2026-11-10T00:00:00Z',source_message_id:'u1'};
    const fetcher=vi.fn().mockResolvedValueOnce(response({settings:{memory_enabled:true,timezone:'Asia/Tokyo',epoch:1},items:[item]}))
      .mockResolvedValueOnce(response({ok:true})).mockResolvedValueOnce(response({settings:{memory_enabled:true,timezone:'Asia/Tokyo',epoch:2},items:[]}));
    vi.stubGlobal('fetch',fetcher);const clear=vi.fn();render(<MemoryPane csrf="csrf" onHistoryCleared={clear}/>);
    expect(await screen.findByDisplayValue(fact)).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'記憶を削除'}));
    const dialog=screen.getByRole('alertdialog',{name:'記憶の削除確認'});fireEvent.click(within(dialog).getByRole('button',{name:'キャンセル'}));
    expect(fetcher).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'記憶を削除'}));
    fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button',{name:'削除する'}));
    await screen.findByText('記憶を削除しました。今後の検索には使いません。');expect(clear).toHaveBeenCalledOnce();
    expect(screen.queryByDisplayValue(fact)).not.toBeInTheDocument();expect(fetcher.mock.calls[1][0]).toContain('version=1');
  });
});
