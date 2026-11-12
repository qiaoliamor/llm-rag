# M3 · 天气查询与个性化关怀

[中文](WEATHER.md) · [日本語](ja/WEATHER.md)

状态：触发、城市澄清、天气上下文与自然关怀已实现；W01/W02实现修复已交付，不代表正式语义/语气验收通过。

## 中日语义理解（2026-11-12，任务分支）

默认`WEATHER_UNDERSTANDING_MODE=semantic`，理解入口为`app/weather_understanding.py`，策略`multilingual-weather-v1`。`legacy`仅显式回放旧中文规则，不是失败回退；原`app/weather.py`及其历史审计证据保持不变。

亲密度60且独立授权后，每轮将**本轮原文**和有效的待澄清日期结构交给当前对话模型；不发送长期记忆、账户资料、助手历史或保存城市。模型判断天气需求、隐喻/引用/否定、城市级地点与日期关系；不是出现地名就查天气。只询问不确定项，不推断住址或省略地名。模型失败/低置信不查天气，不重试；普通聊天继续。全离线mock无理解模型时返回理解不可用，不偷偷运行旧正则。

结构字段：`action=none/decline/query/clarify`、`confidence`、`city`、`kind=current/forecast`、`date`、`use_pending`。非query不能携带查询字段；query需≥0.8置信度，字段不允许额外属性。城市为当前原文中唯一出现的连续片段，不能由模型生成坐标/ID；Unicode字母/组合标记及有限分隔符、长度校验支持假名与中英文，拒绝数字门牌/URL/控制字符。**字符合法不证明城市级语义、主体、否定或日期理解正确**，这些仍须独立评测。

```json
{"action":"query","confidence":0.95,"city":"さいたま市","kind":"forecast","date":{"kind":"relative_days","expression":"明日","absolute":null,"days":1,"week_offset":null,"weekday":null},"use_pending":false}
```

合成输入「さいたま市の明日の天気は？」与「广州明天下雨吗？」分别保留城市原文及明日/明天证据；模型只给关系，程序按地名服务返回的目的地IANA时区计算日期。`today`为当地今天，`relative_days`/明确周偏移及星期/带年份absolute由程序计算；历史、七天范围之外、模糊/多日期/小时级不预报。current必须当地今天，不能把未来日当当前天气。

没有城市则使用本人手选城市，否则创建仅含策略、原请求UTC锚点、日期结构和kind的会话内pending，10分钟过期。本轮明确补城市才可续用；跨午夜仍按原请求锚点解释“明日”。取消、闲聊、失败、过期、清空会话或设置变化会清除pending。临时目的地不保存，不读取IP/GPS。地名结果为0/多个时不取首项，先提示；地名仅发城市，预报仅发坐标/时区。授权/epoch在分析后、地名后、预报前后复查，撤回使后续工具和旧回复失效。

理解超时默认4秒、无自动重试，新增状态`understanding_unavailable`/`clarification_required`已本地化。原有工具数值/单位/时效校验、固定URL、缓存/限流及W01/W02保持。本轮迁移的是**意图/地点/日期**，未迁移全部回复词面检查或情绪规则；日语回复审查/回退口吻与真实理解质量仍未验收。合成/PG命令、原失败和未验证项见[测试记录](TEST_HISTORY.md)。

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
