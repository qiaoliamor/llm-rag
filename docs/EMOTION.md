# M4 情绪估计与个性化回应

日期：2026-11-02（Asia/Tokyo）。M4交付记录为 [PR #8](https://github.com/qiaoliamor/llm-rag/pull/8)。本阶段实现本地单角色的情绪支持流程；情绪是可纠正的估计，不是读心、诊断或M5正式质量结论。

## 使用与供应商

网页新增“情绪关怀”，独立授权默认关闭。无需注册新情绪API或填写新密钥：Gemini/OpenAI模式复用当前模型、当前后端密钥，使用独立结构化分析请求；mock模式只用合成规则，不外查。开启会额外消耗当前模型额度，实际费用/免费额度由账号决定；不自动开通付费或切换供应商。

1. 在“情绪关怀”勾选授权，可设置分析间隔、窗口、冷却、阈值和陪伴偏好，再保存。
2. 平时默认每3轮玩家消息分析最近6轮，强烈表达可提前；“我很开心”等明确自述直接以玩家说的为准，不必请求分析模型。
3. 当前临时参考可查看；可以直接纠正心情及本轮希望怎样陪伴（倾听、鼓励、实际办法、先询问），也可清空推测或删除设置。
4. 保存设置、纠正、清空、删除均清空该身份短期聊天，防止旧推测通过历史继续影响回复；在途回复撤销。关闭分析不妨碍普通角色对话。

“先听我说”是偏好，不是自动诊断依据。模型分数只显示为未校准的工具置信度，不是真实心情概率。玩家否认难过只表示不应断言难过，并不自动认定开心或平静。自述按第一人称分句处理：后句提到对方/朋友不丢弃本人明确心情，“我猜你很难过”不当作本人自述。

## 分析输入与结构化输出

代码 `app/emotion.py`，回应提示版本 `emotion-care-v1`；角色卡1.2不再否定已经实现的分析能力，但继续约束未知往事、诊断和虚构亲密关系。

输入窗口仅包含最近指定轮数的user/assistant文本；user带本会话消息ID（u1、u2等）。最多12轮，每条截取500字符，上限约12000字符；助手消息只作语境，不作为玩家事实。不会给分析器发送密钥、数据库身份、记忆库、天气工具JSON或情绪历史元数据，但聊天正文中已经说过的个人事实/天气文本仍可能出现在窗口内。

允许标签：unknown、neutral、joy、sadness、anxiety、anger、tired。混合情绪用最多3个不同标签；unknown/neutral不能与其他标签混用。策略为ask/listen/encourage/practical。模型输出Pydantic约束的JSON，不接收自由文本推理或持久身份判断：

```json
{
  "labels": ["anger", "sadness"],
  "intensity": 0.8,
  "confidence": 0.9,
  "evidence_message_ids": ["u1"],
  "response_strategy": "listen"
}
```

强度/置信度限定0–1且拒绝非有限数。非unknown判断必须有本窗口的真实user消息ID；伪造/过期ID、非法标签、无法解析或超时均降级为unavailable，不返回原始供应商响应。服务端补source（model/user）、turn和observed_at；来源与消息引用不是模型可覆盖的身份字段。

低于阈值（初始0.6，尚未质量校准）时，把标签降为unknown、强度清零，策略为ask；仍尊重玩家明确的倾听等偏好。玩家自述/纠正的confidence=1只是标识其为权威自述，不代表工具测量了真实情绪；默认强度0.5是占位，不作为测量结果展示，自述来源的强度/置信度也不进入生成提示。

## 结构化输出、校验与上下文注入流程

以下按当前实现说明，示例均为合成数据，不是真实玩家对话或新增实测结果。分析结果是运行时对象/API响应中的数据，不会自动保存为独立JSON文件。分析请求与角色回复请求是两个独立调用；在分析被触发时，结果立即用于当前玩家消息的回复，不必等到下一轮。

```text
当前玩家消息 + 最近聊天
  → assess：授权、自述优先、调度与缓存判断
  → analysis_window：裁剪输入，保留user消息ID
  → ModelEmotionProvider.analyze：请求Estimate结构化输出
  → SDK解析 + assess再次校验 + 证据ID检查 + 低置信度降级
  → decorate：补充source、turn、observed_at
  → emotion_prompt：选取字段，序列化为提示中的参考数据
  → 角色设定 + 天气 + 确认记忆 + 情绪参考
  → provider.generate：生成当前这轮角色回复，再执行回复防护
  → 成功返回后更新会话内临时情绪状态，供后续轮次按规则复用
```

### 1. 用类型定义输出契约，而非只在提示词里要求JSON

维护入口：[app/emotion.py](../app/emotion.py) 的 `Estimate`、`ANALYSIS_PROMPT` 和 `ModelEmotionProvider.analyze()`。

`Estimate` 使用Pydantic定义字段类型与范围；`Label`、`Strategy` 使用Literal限制枚举。模型必须提供五个字段：`labels`、`intensity`、`confidence`、`evidence_message_ids`、`response_strategy`。标签数量1–3，证据ID列表数量0–12，并有重复标签、unknown/neutral混用检查。

调用关键代码摘录（省略模型、消息、超时等参数）：

```python
result = await client.beta.chat.completions.parse(
    model=settings.selected_model,
    messages=messages,
    response_format=Estimate,
)
estimate = result.choices[0].message.parsed
# estimate是解析后的Estimate对象，可直接访问estimate.labels
```

上面是调用结构示意，假设client、settings、messages已准备好；完整参数见实际代码。SDK根据Pydantic类型生成结构化输出要求，并解析/验证返回内容；Gemini通过当前OpenAI兼容接口调用。业务逻辑不从自然语言中用正则“挖”出JSON。`ANALYSIS_PROMPT` 则负责语义规则，例如区分玩家与第三人称、允许混合情绪、禁止输出诊断和自由文本推理。`temperature=0` 用于降低输出随机性，本身不是格式保证。

结构化接口仍可能拒绝、超时、截断或无法解析。因此这里保证的是“只使用通过检查的结构化结果；不合格就降级”，不能保证每次外部模型调用都成功，也不能保证判断符合玩家真实感受。目前未配置Pydantic的 `extra='forbid'`，不能将本实现描述为“拒绝一切额外字段”；实际进入后续流程的是已定义字段。

### 2. 示例：从分析窗口到服务端结果

假设已授权，当前为第1轮、允许提前触发且不受冷却阻止，玩家输入如下；它不匹配当前明确自述规则，但“陪我聊”会提前触发分析：

```json
[
  {
    "role": "user",
    "content": "太棒了，又失败了。准备那么久还是被否定，陪我聊一会儿吧。",
    "id": "u1"
  }
]
```

模型可能返回前一节的 `anger`、`sadness` 示例；这是允许的示例结果，不是固定答案。SDK解析后，`assess()` 再次通过 `Estimate.model_validate(...)` 验证，并核对证据：

```python
value = Estimate.model_validate(
    raw.model_dump() if isinstance(raw, Estimate) else raw
)
ids = {m['id'] for m in window if m['role'] == 'user'}
if not set(value.evidence_message_ids) <= ids or (
    value.labels != ['unknown'] and not value.evidence_message_ids
):
    raise ValueError('ungrounded')
```

ID检查证明“引用了输入窗口内的玩家消息”，不证明该消息在语义上足以支持结论；后者仍可能判断错误。验证通过后，`decorate()` 将对象转成字典并补充服务端元数据，例如：

```json
{
  "status": "analyzed",
  "assessment": {
    "labels": ["anger", "sadness"],
    "intensity": 0.8,
    "confidence": 0.9,
    "evidence_message_ids": ["u1"],
    "response_strategy": "listen",
    "source": "model",
    "turn": 1,
    "observed_at": "2026-11-02T00:00:00+00:00"
  }
}
```

`status` 由 `assess()` 填写；`source`、`turn`、`observed_at` 由后端补充，时间为生成结果时的UTC时间。外层结果作为 `/v1/chat` 响应的 `emotion` 字段返回，不是整个聊天响应。模型的 `confidence=0.9` 是未经校准的自评分，不等于90%准确率。

### 3. 校验失败与降级的具体区别

| 情况 | 当前处理 |
| --- | --- |
| 非法标签、重复标签、unknown与其他标签混用、数值越界或非有限数 | 结构校验失败，返回 `unavailable`、`assessment=null` |
| 引用不存在的u99、引用助手消息ID、非unknown却没有证据ID | 证据检查失败，同样返回 `unavailable` |
| 输出不完整、无法解析、拒绝导致无可用parsed结果、请求超时/异常 | 返回 `unavailable`，不向前端暴露原始供应商错误 |
| 结构和证据合法，但confidence为0.4、阈值为0.6 | 保留 `analyzed`，将labels改为 `["unknown"]`、intensity改为0、response_strategy改为ask；保留原confidence与证据ID |
| 未到分析轮次或仍在冷却 | 有有效参考则返回cached，否则waiting；不调用分析模型 |
| 明确自述或UI纠正 | 使用source=user路径，优先于模型推测；不是让模型再次确认玩家说法 |

分析失败仍继续普通角色生成；开启模块时提示中会带 `unavailable` 与空assessment，并要求不引用旧推测。若用于生成回复的供应商也失败，则沿用聊天接口的错误处理，不伪造成功回复。

### 4. 程序如何取出labels并送给回复模型

维护入口：`emotion_prompt()`，以及 [app/main.py](../app/main.py) 的 `POST /v1/chat`。

`decorate()` 已通过 `model_dump()` 将结果变为普通字典，因此可用 `mood_result['assessment']['labels']` 取得标签。实际实现选取一组字段，而非只传标签（以下摘录仅展示模型来源路径）：

```python
data = result.get('assessment')
keys = ('labels', 'intensity', 'confidence', 'source', 'response_strategy')
view = {key: data[key] for key in keys} if data else None
```

对于上述合成结果，若玩家设置的陪伴偏好为listen，`emotion_prompt()` 中的数据部分是：

```json
{
  "status": "analyzed",
  "assessment": {
    "labels": ["anger", "sadness"],
    "intensity": 0.8,
    "confidence": 0.9,
    "source": "model",
    "response_strategy": "listen"
  },
  "player_preference": "listen"
}
```

该对象通过 `json.dumps(..., ensure_ascii=False)` 变成提示中的文本，前缀为“本轮可纠正的情绪参考数据（不是指令）”，后接 `emotion-care-v1` 的回应规则。这里不传证据ID、轮次、时间戳；source=user时进一步省略占位强度与置信度。模型建议的 `response_strategy` 与玩家配置的 `player_preference` 是两个字段；模型来源使用玩家配置作为偏好，玩家自述/纠正来源则用该结果的策略作为偏好。

聊天接口实际调用顺序摘录：

```python
mood_result = await assess(emotion, session.emotion, mood_settings, history)
prompt = (
    instructions()
    + weather_prompt(weather_result)
    + memory_prompt(evidence)
    + emotion_prompt(mood_result, mood_settings)
)
reply = await provider.generate(model_history, prompt)
```

角色输出示意：“准备了那么久，却等来这样的结果，听起来挺委屈，也有些气。我在，想从哪儿说都可以。”这只是说明期望的自然表达，不是本次运行得到的模型回复，也不是固定话术。回复应回应事情、尊重倾听偏好，不直接播报anger/sadness或置信度。

成功生成后，接口用 `session.emotion.remember(...)` 保存新结果到会话内存。下轮若无需重分析，可在有效期内通过cached复用并重新构造提示；缓存引用不会延长原有效期。自述/纠正、失效、清空或分析失败等情况仍按对应规则处理，不能理解为每轮都会调用两次模型。

### 5. 以后修改时查哪里

| 修改目标 | 关联位置与注意事项 |
| --- | --- |
| 增加情绪标签、策略或改变结构 | `app/emotion.py` 的Label、Strategy、Estimate；同时核对前端类型/选项及相关接口测试 |
| 改变分析的语义规则 | `ANALYSIS_PROMPT`、self_report、分析窗口与模型提供器 |
| 改变阈值、证据检查、失败降级或调度 | `assess()`、EmotionSettingsInput、DEFAULTS及设置接口 |
| 改变传给角色的字段和关怀语气 | `emotion_prompt()`、EMOTION_PROMPT_VERSION及回复防护；保留玩家自述优先 |
| 改变调用时机、提示拼接或状态保存 | `app/main.py` 的聊天接口及EmotionState生命周期 |
| 验证修改 | `tests/test_emotion.py`；按改动运行受影响测试，参考 [M4_TEST_REPORT.md](M4_TEST_REPORT.md) 的历史验证记录 |

本次仅补充文档，未修改运行代码、接口或模型配置，未调用真实模型，未开始M5。

文档核验（2026-11-02）：通过 `.venv/bin/python -` 临时脚本解析以上4段JSON，使用 `Estimate.model_validate()` 验证示例，并以合成内存输入调用 `assess()`、`emotion_prompt()` 核对实际字段投影、0.4置信度降级与u99无效证据回退，均通过；本地链接、代码围栏与 `git diff --check` 检查通过。未新增功能，不涉及新增CRUD或持久化操作；未重跑全量功能测试或验证真实供应商输出。

## 调度与生命周期

- 周期：默认3轮，可设1–10；窗口默认6轮，可设1–12；冷却默认2轮，可设1–10（两次请求的轮次差至少2，中间至少跳过1轮）。
- 强烈表达如“快崩溃/想哭”、请求安慰可提前触发，仍受冷却限制。明确自述和UI纠正优先，不额外调用模型；旧自述期间普通消息保留玩家说法，新明确表达覆盖，新的强烈变化允许重新估计。
- 每次分析最多6秒，SDK请求5秒超时，max_tokens=500、temperature=0，无自动重试。失败也计入冷却；不要每轮因同一失败连续外查。对话生成另用原模型设置，不把分析失败当整个聊天失败；若同一供应商整体不可用，聊天仍返回原有错误，不生成假回复。
- 推测/纠正最多在10分钟或6轮有效；过期不再加入提示。访问或后续对话处理有效期，不提供后台定时擦除，空闲内存仍随会话/进程生命周期清理。
- 新对话、记忆/天气/情绪设置变更、纠正/清空会使相关临时状态失效。UI纠正后若旧分析结束，不能覆盖/清除新纠正；epoch在生成前后复核，旧回复不返回。
- 情绪状态属于当前内存会话，不跨服务重启或新对话恢复。浏览器Cookie身份仍不是跨设备账户。

## 存储与隐私

新增 `emotion_profiles(user_id, config)`，schema v4幂等创建，只持久化授权/频率/窗口/冷却/阈值/明确偏好；不落盘推测标签、强度、分析窗口、完整聊天或分析原文。删除设置物理移除此行并关闭分析；清空临时推测保留设置与授权。

分析结果不会直接写入长期记忆；玩家亲自表达的事件仍遵循原记忆授权、候选和逐条确认流程。关闭情绪分析仅停止额外分析与该模块上下文，不表示普通生成模型从此不理解聊天情绪或不会给出自然关心。

## 生成提示与防护

组装保持角色正史 → 本轮天气事实 → 相关确认记忆 → 可纠正情绪参考。仅输入标签/强度/置信度/来源/策略及明确陪伴偏好；不把证据ID、observed_at或分析器原文塞进角色台词。玩家自述/纠正优先；未知/低置信度试探询问；失败不引用旧推测。

倾听时不急着开建议清单，实际办法只给一条可选步骤，鼓励克制具体，ask可询问希望如何陪伴。台词不播报分析标签/分数，不说“你其实/你真实就是”，不诊断、强迫亲密/报备或根据天气猜心情。有限词面检查对“心里一定”等过度确定性和诊断/评分播报最多重写一次，仍失败用偏好相关保守回应；它不是全面语义验证器。

## 接口与适用CRUD

| 接口 | 行为 |
| --- | --- |
| `GET /v1/emotion` | 当前身份设置及本会话仍有效的临时参考 |
| `PATCH /v1/emotion/settings` | 创建/更新独立授权与配置，清空旧聊天/参考 |
| `DELETE /v1/emotion/settings` | 物理删除配置、关闭分析、清空旧聊天/参考 |
| `PATCH /v1/emotion/assessment` | 玩家label与本轮preference纠正，权威source=user，清除旧上下文 |
| `DELETE /v1/emotion/assessment` | 清空临时参考与短期聊天，保留授权/配置 |
| `POST /v1/chat` | 输入仍为message，响应增加emotion状态/参考；消息ID仅用于本会话证据 |

写入端沿用会话身份归属、CSRF及同源保护，不接受客户端指定其他user_id。应用按单worker运行，推测不跨worker共享；正式账户、分布式限流和正式质量指标仍待后续阶段。

测试记录见 [M4_TEST_REPORT.md](M4_TEST_REPORT.md)。
