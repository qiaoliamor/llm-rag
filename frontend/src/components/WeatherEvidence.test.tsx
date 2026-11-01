import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it } from 'vitest';
import { MessageList } from './MessageList';
import type { WeatherEvidenceData } from '../types';

const weather: WeatherEvidenceData = { status:'ok', source:'Open-Meteo', location:'合成巴黎', timezone:'Europe/Paris', date:'2026-11-01', kind:'current', fetched_at:'2026-11-01T05:40:00Z',valid_at:'2026-11-01T06:30:00+01:00',cached:false,temperature_c:6.3,feels_like_c:3.8,humidity_pct:85 };
const props={pending:false,name:'沈砚',onSuggest:()=>{},disabled:false};
afterEach(cleanup);

it('separates warm dialogue from explicit model estimate and attribution', async () => {
  render(<MessageList {...props} messages={[{role:'assistant',content:'那边估计六度左右，外套多带一件吧。',weather}]} />);
  expect(screen.getByText('那边估计六度左右，外套多带一件吧。')).toBeVisible();
  const summary=screen.getByText('天气依据 · 当前天气为模型估计（非地面实测）');expect(summary).toBeVisible();
  await userEvent.setup().click(summary);
  expect(screen.getByText(/相对湿度 85%/)).toBeVisible();
  expect(screen.getByRole('link',{name:'Open-Meteo'})).toHaveAttribute('href','https://open-meteo.com/');
  expect(screen.getByText(/此为该轮回复使用的天气快照/)).toBeVisible();
});

it('labels daily forecasts without implying current measurements or humidity', async () => {
  const forecast: WeatherEvidenceData={...weather,kind:'forecast',date:'2026-11-02',valid_at:undefined,temperature_c:undefined,feels_like_c:undefined,humidity_pct:undefined,min_c:13,max_c:20,rain_probability_pct:90};
  render(<MessageList {...props} messages={[{role:'assistant',content:'明天出门，伞放包里吧。',weather:forecast}]} />);
  await userEvent.setup().click(screen.getByText('天气依据 · 当地整日预报（非当前实况）'));
  expect(screen.getByText(/预报目标日期：2026-11-02/)).toBeVisible();
  expect(screen.queryByText(/相对湿度/)).not.toBeInTheDocument();
});

it('does not mislabel demo data and removes metadata when history is cleared', () => {
  const {rerender}=render(<MessageList {...props} messages={[{role:'assistant',content:'这是演示天气。',weather:{...weather,source:'mock（合成）'}}]} />);
  expect(screen.getByText('天气依据 · 合成演示，非真实天气')).toBeVisible();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  rerender(<MessageList {...props} messages={[]} />);
  expect(screen.queryByText(/天气依据/)).not.toBeInTheDocument();
});

it('never creates an evidence card for ordinary or failed weather replies', () => {
  render(<MessageList {...props} messages={[{role:'assistant',content:'这会儿还看不准，等一下再试吧。'},{role:'user',content:'今天有点累'}]} />);
  expect(screen.queryByText(/天气依据/)).not.toBeInTheDocument();
});
