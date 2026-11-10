import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { BondProgress } from './BondProgress';
import { UnlockedAbilities, UnlockCelebration } from './AbilityExperience';
import type { GrowthAccount } from '../types';

function account(score:number,id='shen_yan'):GrowthAccount {
  return {profile:{name:'',email:'',phone:''},coins:100,currency_mode:'demo',starting_coins:100,
    character:{id,name:'沈砚',score,active_seconds:0,abilities:{memory:score>=30,weather:score>=60,emotion:score>=90}},
    thresholds:{memory:30,weather:60,emotion:90},gifts:[],ledger:[]};
}
afterEach(()=>vi.useRealTimers());

it('shows only intimacy tiers before unlock, never future ability names',()=>{
  render(<><BondProgress account={account(29)}/><UnlockedAbilities account={account(29)}/></>);
  expect(screen.getByText('0 · 初识')).toBeVisible();
  expect(screen.getByText('30 · 渐熟')).toBeVisible();
  expect(screen.getByText('60 · 默契')).toBeVisible();
  expect(screen.getByText('90 · 知心')).toBeVisible();
  for(const label of ['长期记忆','天气关怀','情绪关怀'])expect(screen.queryByText(label)).not.toBeInTheDocument();
});

it('clicks an unlocked ability to read explanation, closes without enabling or fetching',()=>{
  const fetchMock=vi.fn();vi.stubGlobal('fetch',fetchMock);
  render(<UnlockedAbilities account={account(60)}/>);
  expect(screen.queryByRole('button',{name:'情绪关怀'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'天气关怀'}));
  const dialog=screen.getByRole('dialog',{name:'能力说明'});
  expect(dialog).toHaveTextContent('结合所选城市的天气');
  expect(dialog).toHaveTextContent('解锁不会自动开启');
  fireEvent.click(screen.getByRole('button',{name:'知道了'}));
  expect(dialog).not.toHaveAttribute('open');
  expect(fetchMock).not.toHaveBeenCalled();
});

it('supports keyboard Escape through native dialog cancel',()=>{
  render(<UnlockedAbilities account={account(30)}/>);
  fireEvent.click(screen.getByRole('button',{name:'长期记忆'}));
  const dialog=screen.getByRole('dialog',{name:'能力说明'});
  fireEvent(dialog,new Event('cancel',{cancelable:true}));
  expect(dialog).not.toHaveAttribute('open');
});

it('does not replay existing unlocks on first snapshot or remount',()=>{
  const view=render(<UnlockCelebration account={account(90)}/>);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  view.unmount();render(<UnlockCelebration account={account(90)}/>);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('celebrates a new threshold without stealing focus and expires automatically',()=>{
  vi.useFakeTimers();
  const view=render(<><input aria-label="聊天草稿"/><UnlockCelebration account={account(29)}/></>);
  screen.getByRole('textbox').focus();
  view.rerender(<><input aria-label="聊天草稿"/><UnlockCelebration account={account(30)}/></>);
  expect(screen.getByRole('status')).toHaveTextContent('长期记忆已解锁');
  expect(screen.getByRole('textbox')).toHaveFocus();
  act(()=>vi.advanceTimersByTime(6000));
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('merges multiple thresholds into one notice with more reading time',()=>{
  vi.useFakeTimers();const view=render(<UnlockCelebration account={account(29)}/>);
  view.rerender(<UnlockCelebration account={account(90)}/>);
  expect(screen.getAllByLabelText('新的陪伴方式')).toHaveLength(1);
  expect(screen.getByRole('status')).toHaveTextContent('长期记忆已解锁');
  expect(screen.getByRole('status')).toHaveTextContent('天气关怀已解锁');
  expect(screen.getByRole('status')).toHaveTextContent('情绪关怀已解锁');
  act(()=>vi.advanceTimersByTime(6000));expect(screen.getByRole('status')).toBeVisible();
  act(()=>vi.advanceTimersByTime(6000));expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('pauses auto-dismiss while reading with mouse or keyboard',()=>{
  vi.useFakeTimers();const view=render(<UnlockCelebration account={account(29)}/>);
  view.rerender(<UnlockCelebration account={account(30)}/>);
  fireEvent.mouseEnter(screen.getByLabelText('新的陪伴方式'));
  act(()=>vi.advanceTimersByTime(20000));expect(screen.getByRole('status')).toBeVisible();
  fireEvent.mouseLeave(screen.getByLabelText('新的陪伴方式'));
  fireEvent.focus(screen.getByRole('button',{name:'收起解锁提醒'}));
  act(()=>vi.advanceTimersByTime(20000));expect(screen.getByRole('status')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'收起解锁提醒'}));
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('ignores duplicate responses and stale lower-score snapshots after dismissal',()=>{
  vi.useFakeTimers();const view=render(<UnlockCelebration account={account(29)}/>);
  view.rerender(<UnlockCelebration account={account(30)}/>);
  act(()=>vi.advanceTimersByTime(6000));
  view.rerender(<UnlockCelebration account={account(30)}/>);
  view.rerender(<UnlockCelebration account={account(29)}/>);
  view.rerender(<UnlockCelebration account={account(30)}/>);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('keeps character baselines separate and resets them when account disappears',()=>{
  const view=render(<UnlockCelebration account={account(29)}/>);
  view.rerender(<UnlockCelebration account={account(30)}/>);
  expect(screen.getByRole('status')).toBeVisible();
  view.rerender(<UnlockCelebration account={account(60,'synthetic-other')}/>);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  view.rerender(<UnlockCelebration account={account(30)}/>);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  view.rerender(<UnlockCelebration account={null}/>);
  view.rerender(<UnlockCelebration account={account(29)}/>);
  view.rerender(<UnlockCelebration account={account(30)}/>);
  expect(screen.getByRole('status')).toHaveTextContent('长期记忆已解锁');
});
