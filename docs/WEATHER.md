# M3 天气查询与个性化关怀

更新日期：2026-11-01。M3 实现天气工具闭环；M4 独立情绪分析尚未实现。M2 的 B01–B03 边界保持不变。

## 供应商与是否需要注册

本地非商业原型使用 **Open-Meteo**，无需注册、API Key 或信用卡，不需要再填天气密钥。原有 Gemini 密钥继续只在后端本地读取。

核验于2026-11-01：[官方首页](https://open-meteo.com/)、[预报文档](https://open-meteo.com/en/docs)、[地名文档](https://open-meteo.com/en/docs/geocoding-api)、[使用条款](https://open-meteo.com/en/terms)、[价格](https://open-meteo.com/en/pricing)。免费端点仅限非商业用途，条款为每日少于10000次、每小时5000次、每分钟600次；不保证可用性。未来收费游戏、广告或商业活动须重新选定许可/付费方案，不能因为仓库开源就假定可以商用免费端点。天气数据遵守 CC BY 4.0 署名，地名来自 GeoNames。

API覆盖全球，官方列出日本JMA、中国CMA等模型；数据覆盖和精度不等于每座城市均已实测。本轮真实连通冒烟使用公开测试城市 Tokyo，不发送用户位置或真实经历。城市会重名，不能取第一条就当作玩家所在地。

## 网页使用

1. 启动方式不变：项目根目录执行 `./scripts/start.sh`，打开 `http://127.0.0.1:8000`。
2. 打开“天气关怀”，勾选“允许天气查询”（默认关闭），可搜索城市并按国家/地区选择，再点击“保存天气设置”。城市搜索是明确的外部查询操作，界面提前说明；仅开启、不选城市也可以，查询时会问地点。
3. 聊天示例：“明天天气怎么样？”、“现在天气如何？”、“明天去大阪参加面试，天气怎么样？”。有重名时请在设置中选择具体城市。临时目的地只影响本轮，不覆盖常用城市。
4. 缺少城市时会问地点，下一条可只回复城市名；取消、开始新对话或无关消息会结束该澄清。不同浏览器不共享设置；同一浏览器身份重启后保留设置。
5. 关闭后不查询；删除设置会物理删除常用城市并关闭查询。修改/关闭/删除设置会清空该身份的短期对话，并通过 epoch 撤销在途回复；关闭已有城市的授权无需访问天气服务，离线也可完成。已显示在其他窗口的旧文字需刷新清除。

默认 `WEATHER_PROVIDER=openmeteo`。离线演示可设置 `WEATHER_PROVIDER=mock`，城市和天气均为合成数据，回复必须标明合成演示；模型供应商独立选择，完全离线可同时设置 `CHAT_PROVIDER=mock`。不自动从失败的真实服务降级为假天气。

## 请求与必要字段投影

| 阶段 | 固定地址 | 发出的参数 | 接受的必要字段 |
| --- | --- | --- | --- |
| 城市搜索 | `https://geocoding-api.open-meteo.com/v1/search` | 城市名、count=5、language=zh、format=json | id、name、country、admin1、latitude、longitude、timezone |
| 选择城市校验 | `https://geocoding-api.open-meteo.com/v1/get` | 选定城市id、language=zh | 同上，服务端验证id/坐标范围/IANA时区 |
| 天气查询 | `https://api.open-meteo.com/v1/forecast` | 城市坐标、城市时区、7天、摄氏度/公里每小时/毫米、指定current/daily字段 | 当前或目标日期对应的字段；不传完整上游JSON |

聊天文本不会作为搜索词整体发出；仅提取显式城市片段，活动如“参加面试”被剔除。城市输入不接受URL、数字地址或常见对话/隐私字段；这里只做保守规则过滤，并非通用地址/隐私识别器。不访问 GPS/IP，不使用长期记忆推断位置。天气供应商按城市名或坐标可获知所查询的城市与服务器IP；并非匿名网络访问。

成功预报的服务端/API投影示例（以下完全合成；W01/W02修复后，来源和时间戳给UI，模型只接收下文所列事实字段）：

```json
{
  "status": "ok",
  "source": "Open-Meteo",
  "attribution": "Weather: Open-Meteo (CC BY 4.0); location: GeoNames",
  "location": "合成东京 / 东京 / 日本",
  "timezone": "Asia/Tokyo",
  "date": "2026-11-03",
  "kind": "forecast",
  "fetched_at": "2026-11-01T15:30:00+00:00",
  "cached": false,
  "min_c": 11,
  "max_c": 19,
  "rain_probability_pct": 20,
  "wind_kmh": 13,
  "weather_code": 3,
  "condition": "多云或阴"
}
```

`kind=current` 使用 `temperature_c`、`feels_like_c`、可选`humidity_pct`（current相对湿度0–100%）、`precipitation_mm`、`wind_kmh`、`weather_code`、`condition`、`valid_at` 替代整日温度范围/降水概率；是天气模型的当前估计，不是地面观测。`fetched_at` 是取数时间，`valid_at` 是数据有效时间，不能互相替代。坐标、人口、邮编、原始供应商错误、完整小时序列不进入模型的工具上下文。

无证据时只传 `{"status":"timeout","message":"天气服务响应超时，暂时无法确认天气，请稍后再试。"}` 一类结果，不附带旧温度或天气数字。状态包括 disabled、location_required、ambiguous、not_found、date_unsupported、timeout、rate_limit、unavailable、invalid_response、stale、invalid_city。

## 触发、日期与关怀规则

- 中文天气/气温/下雨/带伞/穿什么/冷不冷等直接表达触发，部分隐喻如“心里下雨”“冷笑话”“风雨同舟”不触发。采用规则意图基线，不是通用语义理解，复杂表达可能需改写；单说“出门”不自动外查。
- 只用显式临时城市或用户保存的城市；没有城市时问清楚。重名不静默选首项。地点澄清仅保留一轮。
- 城市自身 IANA 时区决定今天/明天/后天或 `YYYY-MM-DD`。支持当地今天起七天内的整日预报；现在/实时等用当前天气估计。历史、周末、多日期或小时级表达提示澄清，不把整日概率当某小时结论。
- 提示顺序：角色卡与正史约束 → 本轮结构化天气证据 → 相关已确认记忆，模型同时接收短期聊天。天气字段是数据，不能执行其中的指令或改写角色。没有有效本轮证据时不引用历史天气当当前事实。
- 关怀只结合本轮明确安排和相关已确认记忆，如面试出行、个人倾听偏好，给一条自然建议；不猜心情、不做诊断、不编共同过去、不保证一定下雨。台词以“估计/大概/左右”自然表达不确定，不播报供应商和完整数据日期，不用客服称呼。独立“天气依据”常显当前模型估计/非地面实测或整日预报类型，展开查看署名、地点、时间与数值。角色检查仍是有限规则，未对所有真实生成质量作保证。

## W01/W02：天气事实与角色台词分离

生产提示版本 `weather-care-v2.1`，角色卡1.1。提示选择status/message、地点/时区/目标日期/kind、温度/体感/可用当前湿度/降水/风/condition及demo标记；不向模型天气JSON传source、attribution、fetched_at、valid_at、cached、weather_code。来源仍可从独立UI依据查看，遵守署名要求；温度取整按四舍五入，未来不借用当前湿度。不编恋人身份或现实接送，只提供自然体贴的语气。完整生产Prompt和前后原文见 [M3记录第7节](M3_TEST_REPORT.md#7-w01w02修复把天气依据与沈砚的关心分开)。

输出检查发现来源播报/客服称呼/通用祝词、current缺不确定表达、数字区间错误取整等时最多重写一次，再失败保守回退。历史消息附带weather仅用于UI恢复；调用生成供应商前每条history仅取role/content，避免SDK收到额外元数据。正则不是完整事实验证器。

## 缓存、超时与存储

每次HTTP请求5秒超时，不重试、不跟随重定向，只有三个固定HTTPS端点。进程内限制60次/分钟、4500次/小时、9000次/日（包括地名搜索/解析）；进程重启会重置计数，多个应用/进程/IP共享额度仍以供应商为准，不等于账户计费保证。

天气缓存按城市id/目标日期/类型，TTL 600秒，最多128条，只有公开天气投影，无身份或聊天。当前数据有效时间超过90分钟不采用；缓存也复核该时间。修改或删除设置清空进程天气缓存。成功回复的天气依据另随最近12轮短期聊天保存在内存，刷新可恢复，清空/撤回时一起清除。无磁盘天气缓存，不缓存失败；在途公共天气请求可能重新填充公共缓存，但不会恢复任何已删除身份设置或向已撤销会话返回旧回复。

`weather_profiles` 表只存 user_id、enabled、选定城市的必要字段；新增表及 schema v3 自动幂等创建，不修改已有记忆向量。设置使用当前浏览器身份，与记忆授权分开。完整账户/备份删除和跨设备恢复仍待后续阶段。

## 接口

| 接口 | 输入/结果 | 保护 |
| --- | --- | --- |
| `GET /v1/weather/settings` | 当前身份 enabled、place；默认 false/null | 会话与身份归属 |
| `GET /v1/weather/locations?q=Tokyo` | 最多5个城市候选，不自动保存 | 会话、城市校验、外部限流 |
| `PATCH /v1/weather/settings` | enabled、可选city_id；返回settings、history_cleared | 同源、CSRF、身份、服务端城市解析 |
| `DELETE /v1/weather/settings` | 删除城市且关闭，返回默认settings | 同源、CSRF、身份；物理删除 |
| `POST /v1/chat` | 请求仍只有message；响应新增weather（未触发为null） | 原会话保护和epoch撤销；天气失败仍可对话 |

测试证据见 [M3测试记录](M3_TEST_REPORT.md)。
