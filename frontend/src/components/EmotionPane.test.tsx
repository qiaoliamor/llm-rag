import { fireEvent,render,screen,within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect,it,vi } from 'vitest';
import { EmotionPane } from './EmotionPane';
const config={enabled:false,interval:3,window:6,cooldown:2,threshold:.6,preference:'ask'};
const assessment={labels:['anxiety'],source:'model',confidence:.7};
const response=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status});
const props=()=>({csrf:'csrf',onHistoryCleared:vi.fn(),onBusyChange:vi.fn()});

it('starts disabled and describes extra model processing',async()=>{
 const fetch=vi.fn().mockResolvedValue(response({settings:config,assessment:null}));vi.stubGlobal('fetch',fetch);render(<EmotionPane {...props()}/>);
 expect(await screen.findByRole('checkbox',{name:'允许情绪分析'})).not.toBeChecked();
 expect(screen.getByRole('button',{name:'以我说的为准'})).toBeDisabled();
 expect(screen.getByText(/每轮会把本轮原文/)).toBeVisible();
 expect(screen.getByText(/完整估计默认每3轮/)).toBeVisible();expect(fetch).toHaveBeenCalledTimes(1);
});
it('saves consent, interval and preference with CSRF',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce(response({settings:config,assessment:null})).mockResolvedValueOnce(response({})).mockResolvedValueOnce(response({settings:{...config,enabled:true,interval:4,preference:'listen'},assessment:null}));
 vi.stubGlobal('fetch',fetch);const p=props();render(<EmotionPane {...p}/>);const user=userEvent.setup();
 await user.click(await screen.findByRole('checkbox',{name:'允许情绪分析'}));fireEvent.change(screen.getByLabelText('每几轮分析'),{target:{value:'4'}});await user.selectOptions(screen.getByLabelText('平时希望怎样陪你'),'listen');
 await user.click(screen.getByRole('button',{name:'保存情绪设置'}));await screen.findByRole('status');
 expect(fetch.mock.calls[1][0]).toBe('/v1/emotion/settings');expect(fetch.mock.calls[1][1].headers['X-CSRF-Token']).toBe('csrf');
 expect(JSON.parse(fetch.mock.calls[1][1].body)).toMatchObject({enabled:true,interval:4,preference:'listen'});expect(p.onHistoryCleared).toHaveBeenCalledOnce();
});
it('lets user correct a model guess and choose listening',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce(response({settings:{...config,enabled:true},assessment})).mockResolvedValueOnce(response({})).mockResolvedValueOnce(response({settings:{...config,enabled:true},assessment:{labels:['joy'],source:'user',confidence:1}}));vi.stubGlobal('fetch',fetch);
 const p=props();render(<EmotionPane {...p}/>);const user=userEvent.setup();await screen.findByText(/模型推测，可纠正/);
 await user.selectOptions(screen.getByLabelText('我现在的心情'),'joy');await user.selectOptions(screen.getByLabelText('这会儿希望怎样陪我'),'listen');await user.click(screen.getByRole('button',{name:'以我说的为准'}));
 expect(await screen.findByText(/你的自述\/纠正：开心/)).toBeVisible();expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({label:'joy',preference:'listen'});expect(p.onHistoryCleared).toHaveBeenCalledOnce();
});
it('clears transient estimates separately from deleting settings',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce(response({settings:{...config,enabled:true},assessment})).mockResolvedValueOnce(response({})).mockResolvedValueOnce(response({settings:{...config,enabled:true},assessment:null}));vi.stubGlobal('fetch',fetch);
 const p=props();render(<EmotionPane {...p}/>);const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'清空临时推测'}));expect(await screen.findByRole('status')).toHaveTextContent('已清空');
 expect(fetch.mock.calls[1]).toEqual(['/v1/emotion/assessment',expect.objectContaining({method:'DELETE'})]);expect(screen.getByRole('checkbox')).toBeChecked();
});
it('requires confirmation before removing preferences and disabling',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce(response({settings:{...config,enabled:true},assessment})).mockResolvedValueOnce(response({})).mockResolvedValueOnce(response({settings:config,assessment:null}));vi.stubGlobal('fetch',fetch);
 render(<EmotionPane {...props()}/>);const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'删除情绪设置'}));expect(fetch).toHaveBeenCalledTimes(1);
 await user.click(within(screen.getByRole('alertdialog')).getByRole('button',{name:'确认删除'}));await screen.findByRole('status');expect(screen.getByRole('checkbox')).not.toBeChecked();expect(fetch.mock.calls[1][0]).toBe('/v1/emotion/settings');
});
it('preserves visible assessment and reports invalid settings on failure',async()=>{
 const fetch=vi.fn().mockResolvedValueOnce(response({settings:{...config,enabled:true},assessment})).mockResolvedValueOnce(response({detail:'设置输入无效'},422));vi.stubGlobal('fetch',fetch);
 const p=props();render(<EmotionPane {...p}/>);await userEvent.setup().click(await screen.findByRole('button',{name:'保存情绪设置'}));expect(await screen.findByRole('alert')).toHaveTextContent('无效');expect(screen.getByText(/模型推测，可纠正/)).toBeVisible();expect(p.onHistoryCleared).not.toHaveBeenCalled();
});
