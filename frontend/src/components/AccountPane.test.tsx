import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { AccountPane } from './AccountPane';
import { BondProgress } from './BondProgress';
import { MemoryPane } from './MemoryPane';
import type { GrowthAccount } from '../types';

const initial:GrowthAccount={profile:{name:'',email:'',phone:''},coins:100,currency_mode:'demo',starting_coins:100,
 character:{id:'shen_yan',name:'沈砚',score:0,active_seconds:0,abilities:{memory:false,emotion:false,weather:false}},thresholds:{memory:30,weather:60,emotion:90},
 gifts:[{id:'bookmark',name:'纸页书签',price:20,points:5,description:'一份小心意'},{id:'lamp',name:'暖光小灯',price:120,points:20,description:'一点暖光'}],ledger:[]};
const response=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status});
function props(){return {csrf:'csrf',onUpdate:vi.fn(),onManage:vi.fn(),onBusyChange:vi.fn()};}

it('shows optional profile, character-specific bond, demo balance and capability consent',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(initial)));
 render(<AccountPane {...props()}/>);
 expect(await screen.findByText('100')).toBeVisible();
 expect(screen.getByLabelText('邮箱（选填）')).toHaveValue('');
 expect(screen.getByText(/尚不支持跨设备登录/)).toBeVisible();
 expect(screen.getByText(/解锁后不会自动开启/)).toBeVisible();
 expect(screen.getByRole('button',{name:'送出暖光小灯'})).toBeDisabled();
});

it('saves a profile without sending points, balance or player identity',async()=>{
 const saved={...initial,profile:{name:'合成小雨',email:'synthetic@example.invalid',phone:''}};
 const fetchMock=vi.fn().mockResolvedValueOnce(response(initial)).mockResolvedValueOnce(response(saved));
 vi.stubGlobal('fetch',fetchMock);const p=props();render(<AccountPane {...p}/>);
 const input=await screen.findByLabelText('名字');fireEvent.change(input,{target:{value:'合成小雨'}});
 fireEvent.change(screen.getByLabelText('邮箱（选填）'),{target:{value:'synthetic@example.invalid'}});
 await userEvent.setup().click(screen.getByRole('button',{name:'保存资料'}));
 expect(await screen.findByRole('status')).toHaveTextContent('已保存');
 expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual(saved.profile);
 expect(fetchMock.mock.calls[1][1].headers['X-CSRF-Token']).toBe('csrf');
});

it('confirms a gift and updates coins and score from the server only',async()=>{
 const next={...initial,coins:80,character:{...initial.character,score:5}};
 const fetchMock=vi.fn().mockResolvedValueOnce(response(initial)).mockResolvedValueOnce(response(next));
 vi.stubGlobal('fetch',fetchMock);const p=props();render(<AccountPane {...p}/>);const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:'送出纸页书签'}));
 expect(fetchMock).toHaveBeenCalledTimes(1);
 const dialog=screen.getByRole('alertdialog',{name:'账户操作确认'});
 expect(within(dialog).getByText(/扣除 20 演示币/)).toBeVisible();
 await user.click(within(dialog).getByRole('button',{name:'确认送出'}));
 expect(await screen.findByRole('status')).toHaveTextContent('礼物已送达');
 expect(p.onUpdate).toHaveBeenLastCalledWith(next);
 expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({gift_id:'bookmark',request_id:expect.any(String)});
 expect(fetchMock.mock.calls[1][0]).toBe('/v1/characters/shen_yan/gifts');
});

it('retains the same idempotency key on an explicit retry after a network failure',async()=>{
 const fetchMock=vi.fn().mockResolvedValueOnce(response(initial)).mockRejectedValueOnce(new TypeError('synthetic network failure'))
   .mockResolvedValueOnce(response({...initial,coins:80,character:{...initial.character,score:5}}));
 vi.stubGlobal('fetch',fetchMock);render(<AccountPane {...props()}/>);const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:'送出纸页书签'}));
 await user.click(screen.getByRole('button',{name:'确认送出'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('无法连接');
 expect(fetchMock).toHaveBeenCalledTimes(2);
 await user.click(screen.getByRole('button',{name:'确认送出'}));await screen.findByRole('status');
 expect(fetchMock.mock.calls[1][1].body).toBe(fetchMock.mock.calls[2][1].body);
});

it('shows recharge as demo-only and does not request payment on cancel',async()=>{
 const fetchMock=vi.fn().mockResolvedValue(response(initial));vi.stubGlobal('fetch',fetchMock);
 render(<AccountPane {...props()}/>);const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:'充值通道'}));
 expect(screen.getByText(/不收款、不创建付款订单/)).toBeVisible();
 await user.click(screen.getByRole('button',{name:'取消'}));expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('credits exactly once after confirmation using the demo endpoint',async()=>{
 const fetchMock=vi.fn().mockResolvedValueOnce(response(initial)).mockResolvedValueOnce(response({...initial,coins:200}));
 vi.stubGlobal('fetch',fetchMock);render(<AccountPane {...props()}/>);const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:'充值通道'}));
 await user.click(screen.getByRole('button',{name:'确认领取'}));
 expect(await screen.findByRole('status')).toHaveTextContent('没有产生真实扣款');
 expect(fetchMock.mock.calls[1][0]).toBe('/v1/account/demo-credit');
 expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({request_id:expect.any(String)});
});

it('clears contact information with confirmation and preserves the wallet',async()=>{
 const fetchMock=vi.fn().mockResolvedValueOnce(response({...initial,profile:{name:'合成',email:'synthetic@example.invalid',phone:'+8100000000'}})).mockResolvedValueOnce(response(initial));
 vi.stubGlobal('fetch',fetchMock);render(<AccountPane {...props()}/>);const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:'清除个人资料'}));
 await user.click(screen.getByRole('button',{name:'确认清除'}));await screen.findByRole('status');
 expect(screen.getByLabelText('邮箱（选填）')).toHaveValue('');
 expect(fetchMock.mock.calls[1][1].method).toBe('DELETE');
});

it('shows intimacy tiers without previewing abilities',()=>{
 const {rerender}=render(<BondProgress account={{...initial,character:{...initial.character,score:29}}}/>);
 expect(screen.getByText(/距离渐熟还有 1 分/)).toBeVisible();
 rerender(<BondProgress account={{...initial,character:{...initial.character,score:100}}}/>);
 expect(screen.getByText(/现在是知心/)).toBeVisible();
 expect(screen.getByRole('progressbar')).toHaveAttribute('value','100');
});

it('keeps deletion accessible when the memory capability is locked',async()=>{
 const item={id:'m',fact:'合成记忆',status:'confirmed',version:1,source_kind:'manual',created_at:'2026-11-10T00:00:00Z'};
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({settings:{memory_enabled:false,timezone:'Asia/Tokyo'},items:[item]})));
 render(<MemoryPane csrf="csrf" locked onHistoryCleared={vi.fn()}/>);
 expect(await screen.findByRole('button',{name:'开启长期记忆'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'删除记忆'})).not.toBeDisabled();
 expect(screen.getByRole('button',{name:'添加候选'})).toBeDisabled();
});
