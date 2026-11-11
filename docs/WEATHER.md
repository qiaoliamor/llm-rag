# M3 · 天气查询与个性化关怀

[中文](WEATHER.md) · [日本語](ja/WEATHER.md)

状态：触发、城市澄清、天气上下文与自然关怀已实现；W01/W02实现修复已交付，不代表正式语义/语气验收通过。

## 功能、授权与供应商

亲密度60解锁资格，再独立授权；只根据玩家显式城市或保存城市查询，不用IP/GPS/记忆猜位置。天气/气温/带伞等明确表达触发，常见隐喻不触发；缺城市/重名先澄清，临时目的地不覆盖常用城市。城市当地IANA时区决定日期：当前估计或未来7天整日预报，历史/模糊多日期需澄清。

现有适配为Open-Meteo非商业免费端点，无天气Key；这只是项目采用方案及2026-11-01核验记录，不保证当前配额/许可仍相同，商业化前重新核验。提供方/署名说明保留在天气依据UI，历史官方资料：[预报](https://open-meteo.com/en/docs)、[地名](https://open-meteo.com/en/docs/geocoding-api)、[条款](https://open-meteo.com/en/terms)。离线用`WEATHER_PROVIDER=mock`并标明合成；真实失败不替换为假天气。

## 数据流与Prompt

固定HTTPS地名search/get端点接收城市名/id，forecast端点只接收坐标/时区；不发送完整聊天或记忆。服务端验证坐标、时区、单位、数值范围及有效时间，绝不将完整上游JSON交给LLM。

| 类型 | 模型上下文必要字段 |
| --- | --- |
| 共通 | status、必要message、location、timezone、date、kind、condition、demo |
| current | temperature_c、feels_like_c、可用humidity_pct、precipitation_mm、wind_kmh |
| forecast | min_c、max_c、rain_probability_pct、wind_kmh |

只投影可用字段，不补缺失湿度，不把当前湿度用于未来预报。完整响应另含source/attribution/fetched_at/valid_at/cached等供UI；这些元数据及weather_code不作为模型事实JSON的一部分。

合成模型上下文示例：

```json
{"status":"ok","location":"合成东京","timezone":"Asia/Tokyo","date":"2026-11-10","kind":"current","temperature_c":16,"feels_like_c":15,"humidity_pct":65,"condition":"多云或阴","demo":true}
```

W01：current是模型当前估计，非地面实测；台词可用“大概/左右”，UI常显数据性质，forecast另标整日预报。W02：像沈砚自然回应玩家明确安排，轻带一两条温度/湿度建议，不播报“根据Open-Meteo在某日提供的数据”，不用客服称呼，不编恋人身份、接送或共同过去。`weather-care-v2.1`及检查/回退在`app/weather.py`，UI为`WeatherPane.tsx`、`WeatherEvidence.tsx`。

## 接口、缓存与失败

- `GET /v1/weather/settings`、`GET /v1/weather/locations?q=...`、`PATCH/DELETE /v1/weather/settings`；设置支持增查改删、归属/CSRF保护，锁定时仍能关闭/删除。
- HTTP每次5秒，零自动重试/重定向；本地限流60/分钟、4500/小时、9000/日，不等于供应商账户限额保证。缓存TTL600秒、最多128项；current有效时间超过90分钟不用。
- 缓存只有公开天气，无身份键；设置保存到weather_profiles，删除/修改设置清缓存并撤销旧回复。无磁盘天气缓存；在途请求可能填回无身份公共数据，但不会恢复已删设置。
- 超时/限流/失效/非法响应只给状态和简短失败说明，不夹带旧数字；历史天气卡片只供UI恢复，不充当本轮天气证据。

## 验证与保留项

W01/W02修订时后端241通过/19跳过，天气67默认+1PG；覆盖触发/不触发、城市和日期、单位/湿度/缺失字段、取整、来源投影、失败、设置CRUD/隔离/撤回/持久化及UI卡片。初期自动评审3次JSON解析失败，曾遗漏“模型估计”措辞和客服口吻；修订方法与所有前后原文保留在[历史M3报告](TEST_HISTORY.md#历史原文索引)。

真实小样本对照不等于独立人类盲评；复杂中文数字、否定、地名和泛化尚未全面验证。最新合成回归见[测试总表](TEST_HISTORY.md)，本次不调用真实天气或模型API。
