import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { WeatherPane } from './WeatherPane';

const place = { id: 1, name: '合成东京', admin1: '东京', country: '日本', latitude: 35, longitude: 139, timezone: 'Asia/Tokyo' };
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const props = () => ({ csrf: 'csrf', onHistoryCleared: vi.fn(), onBusyChange: vi.fn() });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('shows default opt-out and never searches on load', async () => {
  const fetch = vi.fn().mockResolvedValue(response({ enabled: false, place: null })); vi.stubGlobal('fetch', fetch);
  render(<WeatherPane {...props()} />);
  expect(await screen.findByRole('checkbox', { name: '允许天气查询' })).not.toBeChecked();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.getByText(/不读取 GPS 或 IP/)).toBeVisible();
  expect(screen.getByText(/本轮聊天原文会发送给当前对话模型/)).toBeVisible();
});

it('searches, requires choosing a city and saves opt-in with CSRF', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(response({ enabled: false, place: null }))
    .mockResolvedValueOnce(response({ items: [place, { ...place, id: 2, country: '其他地区' }] }))
    .mockResolvedValueOnce(response({ settings: { enabled: true, place } }));
  vi.stubGlobal('fetch', fetch); const p = props(); render(<WeatherPane {...p} />); const user = userEvent.setup();
  await user.click(await screen.findByRole('checkbox', { name: '允许天气查询' }));
  fireEvent.change(screen.getByLabelText('搜索城市（无需详细地址）'), { target: { value: 'Tokyo' } });
  await user.click(screen.getByRole('button', { name: '搜索城市' }));
  expect(await screen.findByRole('combobox')).toHaveValue('');
  await user.selectOptions(screen.getByRole('combobox'), '1');
  await user.click(screen.getByRole('button', { name: '保存天气设置' }));
  await screen.findByText('天气设置已保存，短期聊天已清空。');
  expect(fetch.mock.calls[1][0]).toBe('/v1/weather/locations?q=Tokyo');
  expect(fetch.mock.calls[2][1]).toMatchObject({ method: 'PATCH', headers: expect.objectContaining({ 'X-CSRF-Token': 'csrf' }), body: JSON.stringify({ enabled: true, city_id: 1 }) });
  expect(p.onHistoryCleared).toHaveBeenCalledOnce();
});

it('updates consent independently of long term memory', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(response({ enabled: true, place })).mockResolvedValueOnce(response({ settings: { enabled: false, place } }));
  vi.stubGlobal('fetch', fetch); const p = props(); render(<WeatherPane {...p} />); const user = userEvent.setup();
  await user.click(await screen.findByRole('checkbox', { name: '允许天气查询' }));
  await user.click(screen.getByRole('button', { name: '保存天气设置' }));
  await screen.findByRole('status');
  expect(JSON.parse(fetch.mock.calls[1][1].body).enabled).toBe(false);
  expect(p.onHistoryCleared).toHaveBeenCalledOnce();
});

it('deletes settings only after confirmation and clears city', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(response({ enabled: true, place })).mockResolvedValueOnce(response({ settings: { enabled: false, place: null } }));
  vi.stubGlobal('fetch', fetch); const p = props(); render(<WeatherPane {...p} />); const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: '删除天气设置' }));
  expect(fetch).toHaveBeenCalledTimes(1);
  await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: '确认删除' }));
  expect(await screen.findByRole('status')).toHaveTextContent('城市已删除');
  expect(fetch.mock.calls[1]).toEqual(['/v1/weather/settings', expect.objectContaining({ method: 'DELETE', headers: { 'X-CSRF-Token': 'csrf' } })]);
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  expect(p.onHistoryCleared).toHaveBeenCalledOnce();
});

it('keeps selected settings on upstream failure and reports empty city results', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(response({ enabled: true, place }))
    .mockResolvedValueOnce(response({ detail: '天气服务响应超时' }, 503)).mockResolvedValueOnce(response({ items: [] }));
  vi.stubGlobal('fetch', fetch); const p = props(); render(<WeatherPane {...p} />); const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: '保存天气设置' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('超时'); expect(p.onHistoryCleared).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('搜索城市（无需详细地址）'), { target: { value: '不存在城市' } });
  await user.click(screen.getByRole('button', { name: '搜索城市' }));
  expect(await screen.findByRole('status')).toHaveTextContent('未找到城市');
});
