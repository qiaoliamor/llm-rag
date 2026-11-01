import type { WeatherEvidenceData } from '../types';

export function WeatherEvidence({ weather }: { weather: WeatherEvidenceData }) {
  const demo = weather.source.startsWith('mock');
  return <details className="weather-evidence">
    <summary>天气依据 · {demo ? '合成演示，非真实天气' : weather.kind === 'current' ? '当前天气为模型估计（非地面实测）' : '当地整日预报（非当前实况）'}</summary>
    <p>此为该轮回复使用的天气快照，{weather.location} · {weather.timezone}。</p>
    <p>{weather.kind === 'current' ? '数据有效时间' : '预报目标日期'}：{weather.valid_at ?? weather.date}；获取时间：{weather.fetched_at}{weather.cached ? '（缓存）' : ''}。</p>
    <p>{weather.temperature_c !== undefined ? `气温 ${weather.temperature_c}°C` : `温度范围 ${weather.min_c}–${weather.max_c}°C`}
      {weather.feels_like_c !== undefined && ` · 体感 ${weather.feels_like_c}°C`}
      {weather.humidity_pct !== undefined && ` · 相对湿度 ${weather.humidity_pct}%`}
      {weather.rain_probability_pct !== undefined && ` · 整日降水概率 ${weather.rain_probability_pct}%`}</p>
    <p>{demo ? '来源：离线合成天气。' : <>来源：<a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a>（CC BY 4.0）；地名 GeoNames。模型估计或预报存在误差。</>}</p>
  </details>;
}
