import { useEffect, useState } from 'react';
import { getWeatherSettings, searchWeatherCities, saveWeatherSettings, deleteWeatherSettings } from '../api';
import type { WeatherSettings, WeatherPlace } from '../types';

export function WeatherPane({ csrf, onHistoryCleared, onBusyChange, locked=false }: { csrf: string; onHistoryCleared: () => void; onBusyChange: (busy: boolean) => void; locked?:boolean }) {
  const [data, setData] = useState<WeatherSettings | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [city, setCity] = useState('');
  const [places, setPlaces] = useState<WeatherPlace[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  function load(next: WeatherSettings) { setData(next); setEnabled(next.enabled); setSelected(next.place?.id ?? null); setPlaces(next.place ? [next.place] : []); }
  useEffect(() => { let active = true; getWeatherSettings().then(next => { if (active) load(locked ? {...next, enabled:false} : next); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, []);
  async function run(operation: () => Promise<void>) {
    setBusy(true); onBusyChange(true); setError(''); setNotice('');
    try { await operation(); } catch (e) { setError(e instanceof Error ? e.message : '天气设置操作失败，请重试。'); }
    finally { setBusy(false); onBusyChange(false); }
  }
  if (!data) return <section className="workspace-pane"><h3>天气关怀</h3><p role={error ? 'alert' : undefined}>{error || '正在读取天气设置…'}</p></section>;
  return <section className="workspace-pane" aria-label="天气关怀设置">
    <h3>出门前，也照顾好自己。</h3>{locked && <p className="pane-notice">亲密度60分解锁使用。仍可关闭查询、删除已有城市。</p>}
    <p className="pane-description">天气查询默认关闭，开启后仅在聊天触发时查询。城市搜索会将输入的城市名发送给 Open-Meteo / GeoNames；查询天气仅发送城市坐标与时区，不发送聊天或记忆。不读取 GPS 或 IP 定位。</p>
    <label><input type="checkbox" checked={enabled} disabled={busy || locked} onChange={e => setEnabled(e.target.checked)} /> 允许天气查询</label>
    <p>当前城市：{data.place ? [data.place.name, data.place.admin1, data.place.country].filter(Boolean).join(' / ') : '未设置（可在聊天中提供临时城市）'}</p>
    <form className="memory-add" onSubmit={e => { e.preventDefault(); if (locked) return; void run(async () => { const result = await searchWeatherCities(city.trim()); setPlaces(result.items); setSelected(null); if (!result.items.length) setNotice('未找到城市，请补充国家/地区或换个名称。'); }); }}>
      <label htmlFor="weather-city">搜索城市（无需详细地址）</label>
      <input id="weather-city" value={city} maxLength={60} disabled={busy || locked} onChange={e => setCity(e.target.value)} placeholder="例如 Tokyo 或 Paris, France" />
      <button disabled={busy || locked || city.trim().length < 2}>搜索城市</button>
    </form>
    {!!places.length && <label>选择城市与地区 <select aria-label="选择城市与地区" value={selected ?? ''} disabled={busy} onChange={e => setSelected(Number(e.target.value) || null)}>
      <option value="">请选择，重名城市不会自动选择</option>
      {places.map(p => <option key={p.id} value={p.id}>{[p.name, p.admin1, p.country].filter(Boolean).join(' / ')} · {p.timezone}</option>)}
    </select></label>}
    <div className="memory-actions">
      <button disabled={busy} onClick={() => void run(async () => { const result = await saveWeatherSettings(enabled, selected, csrf); load(result.settings); onHistoryCleared(); setNotice('天气设置已保存，短期聊天已清空。'); })}>保存天气设置</button>
      <button className="quiet danger" disabled={busy} onClick={() => setConfirmDelete(true)}>删除天气设置</button>
    </div>
    {confirmDelete && <div role="alertdialog" aria-label="删除天气设置确认"><p>删除常用城市并关闭查询？短期聊天也会清空。</p><button disabled={busy} onClick={() => void run(async () => { const result = await deleteWeatherSettings(csrf); load(result.settings); setCity(''); onHistoryCleared(); setConfirmDelete(false); setNotice('城市已删除，天气查询已关闭。'); })}>确认删除</button><button className="quiet" disabled={busy} onClick={() => setConfirmDelete(false)}>取消</button></div>}
    {error && <p role="alert" className="pane-error">{error}</p>}
    {notice && <p role="status" className="pane-notice">{notice}</p>}
    <p className="pane-description">可问“明天天气怎么样？”或“明天去大阪，天气怎么样？”。临时目的地不会修改常用城市。支持当地今天起七天的整日预报或当前天气估计；不是官方灾害预警服务。更改或删除设置会撤销在途旧回复。</p>
    <p className="pane-description">天气数据：<a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a>（CC BY 4.0），地名：GeoNames。免费端点限非商业用途，无需天气密钥；天气模型可能存在误差。</p>
  </section>;
}
