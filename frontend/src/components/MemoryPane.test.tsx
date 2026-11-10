import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { MemoryPane } from './MemoryPane';
import type { MemoryItem, MemoryList } from '../types';

const item: MemoryItem = { id:'test-id', fact:'我下周二有合成面试', category:'event',status:'candidate',event_date:'2026-11-03', source_message_id:'test-message',source_kind:'chat',version:1,created_at:'2026-10-31T00:00:00Z',updated_at:'2026-10-31T00:00:00Z',conflicts:[] };
function list(items: MemoryItem[] = [], enabled = true): MemoryList { return {items,settings:{memory_enabled:enabled,timezone:'Asia/Tokyo',epoch:1}}; }
function response(body: unknown,status=200) {return {ok:status===200,status,json:async()=>body} as Response;}

it('enables memory only after explicit action and clears stale history', async () => {
  const fetchMock=vi.fn().mockResolvedValueOnce(response(list([],false))).mockResolvedValueOnce(response({})).mockResolvedValueOnce(response(list()));
  vi.stubGlobal('fetch',fetchMock);const clear=vi.fn();render(<MemoryPane csrf="csrf" onHistoryCleared={clear} />);
  const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'开启长期记忆'}));
  await screen.findByRole('button',{name:'关闭长期记忆'});
  expect(clear).toHaveBeenCalledOnce();
  expect(fetchMock.mock.calls[1]).toEqual(['/v1/settings',expect.objectContaining({method:'PATCH',body:JSON.stringify({memory_enabled:true,timezone:'Asia/Tokyo'}),headers:expect.objectContaining({'X-CSRF-Token':'csrf'})})]);
});

it('requires confirmation for candidates and uses versioned corrections', async () => {
  const fetchMock=vi.fn().mockResolvedValueOnce(response(list([item]))).mockResolvedValueOnce(response({})).mockResolvedValueOnce(response(list([{...item,status:'confirmed',version:2}])));
  vi.stubGlobal('fetch',fetchMock);const clear=vi.fn();render(<MemoryPane csrf="csrf" onHistoryCleared={clear}/>);
  const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'确认记住'}));
  await screen.findByRole('button',{name:'保存纠正'});
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({version:1,confirm:true,replace_conflicts:false});
  expect(clear).toHaveBeenCalledOnce();
});

it('edits confirmed memory and keeps the list on version conflicts', async () => {
  const fetchMock=vi.fn().mockResolvedValueOnce(response(list([{...item,status:'confirmed'}]))).mockResolvedValueOnce(response({detail:'记忆已被更新，请刷新列表。'},409));
  vi.stubGlobal('fetch',fetchMock);const clear=vi.fn();render(<MemoryPane csrf="csrf" onHistoryCleared={clear}/>);
  const user=userEvent.setup();const input=await screen.findByLabelText('记忆内容');
  fireEvent.change(input,{target:{value:'我下周三有面试'}});
  await user.click(screen.getByRole('button',{name:'保存纠正'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('记忆已被更新');
  expect(input).toHaveValue('我下周三有面试');expect(clear).not.toHaveBeenCalled();
});

it('supports deletion while memory is disabled, with explicit confirmation', async () => {
  const fetchMock=vi.fn().mockResolvedValueOnce(response(list([{...item,status:'confirmed'}],false))).mockResolvedValueOnce(response({})).mockResolvedValueOnce(response(list([],false)));
  vi.stubGlobal('fetch',fetchMock);const clear=vi.fn();render(<MemoryPane csrf="csrf" onHistoryCleared={clear}/>);
  const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'删除记忆'}));
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await user.click(within(screen.getByRole('alertdialog')).getByRole('button',{name:'确认删除'}));
  await screen.findByText('还没有记忆。开启后聊聊重要经历，或在上方手动添加。');
  expect(fetchMock.mock.calls[1][0]).toBe('/v1/memories/test-id?version=1');
  expect(clear).toHaveBeenCalledOnce();
});

it('adds manual candidates without automatically confirming', async () => {
  const fetchMock=vi.fn().mockResolvedValueOnce(response(list())).mockResolvedValueOnce(response({item})).mockResolvedValueOnce(response(list([item])));
  vi.stubGlobal('fetch',fetchMock);render(<MemoryPane csrf="csrf" onHistoryCleared={vi.fn()}/>);
  const user=userEvent.setup();const input=await screen.findByLabelText('也可以手动添加重要经历（最多300字）');
  await user.type(input,'我下周二有合成面试');await user.click(screen.getByRole('button',{name:'添加候选'}));
  await screen.findByRole('button',{name:'确认记住'});
  expect(fetchMock.mock.calls[1][0]).toBe('/v1/memories');expect(fetchMock.mock.calls[1][1].method).toBe('POST');
});
