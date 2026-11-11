import { t } from '../i18n';
import type { WeatherEvidenceData } from '../types';

export function WeatherEvidence({ weather }: { weather: WeatherEvidenceData }) {
  const demo = weather.source.startsWith('mock');
  return <details className="weather-evidence">
    <summary>{t("天气依据 · ")}{demo ? t("合成演示，非真实天气") : weather.kind === 'current' ? t("当前天气为模型估计（非地面实测）") : t("当地整日预报（非当前实况）")}</summary>
    <p>{t("此为该轮回复使用的天气快照，")}{weather.location} · {weather.timezone}。</p>
    <p>{weather.kind === 'current' ? t("数据有效时间") : t("预报目标日期")}：{weather.valid_at ?? weather.date}{t("；获取时间：")}{weather.fetched_at}{weather.cached ? t("（缓存）") : ''}。</p>
    <p>{weather.temperature_c !== undefined ? t("气温 {1}°C", [weather.temperature_c]) : t("温度范围 {1}–{2}°C", [weather.min_c, weather.max_c])}
      {weather.feels_like_c !== undefined && t(" · 体感 {1}°C", [weather.feels_like_c])}
      {weather.humidity_pct !== undefined && t(" · 相对湿度 {1}%", [weather.humidity_pct])}
      {weather.rain_probability_pct !== undefined && t(" · 整日降水概率 {1}%", [weather.rain_probability_pct])}</p>
    <p>{demo ? t("来源：离线合成天气。") : <>{t("来源：")}<a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a>{t("（CC BY 4.0）；地名 GeoNames。模型估计或预报存在误差。")}</>}</p>
  </details>;
}
