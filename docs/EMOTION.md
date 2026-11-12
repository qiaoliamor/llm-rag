# M4 · 情绪参考与个性化回应

[中文](EMOTION.md) · [日本語](ja/EMOTION.md)

状态：PR #8交付独立授权、分析、纠正与偏好闭环；情绪真实准确率、F1和置信度校准未验收。

## 中日语义自述与触发（2026-11-12，任务分支）

默认`EMOTION_UNDERSTANDING_MODE=semantic`，入口`app/emotion_understanding.py`、策略`multilingual-emotion-v1`；旧emotion.py的自述/触发/Mock规则只在显式legacy回放，不用于失败回退。旧Prompt、源绑定测试/封存不改。以下旧实现说明仍供历史查阅，当前语义路径以本节为准。

1. **权限与输入**：90分资格+独立授权后，每轮先调用一次`EmotionDecision`理解自述/否认、强烈变化、陪伴/分析请求与本轮陪伴偏好。只传本轮完整原文及ID、配置窗口的有限role/content/user ID、当前参考的labels/source/basis，不附长期记忆库、账户、天气快照或原始工具元数据。窗口每条最多500字、最多12轮/24条；本轮原文另受聊天2000字上限。不是只每3轮才发模型，UI中日说明已同步。
2. **结构与语义边界**：字段use_emotion（allow/decline/uncertain）、confidence、report（source_text/labels或null）、shift、request_analysis、preference/preference_source。严格类型/extra=forbid、标签枚举/互斥/去重、0–1有限置信、原文唯一连续引用且非空白由程序检查。拒绝/不确定不触发，模型无权授予授权、改轮次或设置。主体/引用/否定/讽刺/混合心情由Prompt判断，不能把朋友、歌词或假设当本人心情；“不难过”不证明开心，结构合法并不证明理解正确。
3. **保留调度**：模型给信号，程序按interval/window/cooldown/threshold执行。默认完整估计每3轮、最近6轮、冷却2轮；提前信号也不能绕过冷却。直接自述解释不再额外做完整估计。理解+需要时的完整估计共用默认6秒总预算，最多各1次，无自动重试；失败的完整估计也占冷却，生成失败不回滚last_attempt以防反复消耗分析。
4. **来源与优先级**：语义自述返回status=self_report，assessment.source=model、basis=self_report、模型原置信度，不伪标user或confidence=1。source=user仅用于页面手动纠正；无新明确自述/变化时保留该纠正，API失败不拿模型覆盖它。最新明确自述/否认可更新参考，否认但其他心情不明为unknown；旧参考在新自述/变化确认后清掉，失败不复活。手动纠正或自述缓存最多10分钟/6轮，复用不续期。本轮listen等偏好只投影到回答，不自动写设置或改旧手动资料。
5. **完整估计与失败**：`SemanticEstimate`复用原五字段，但新增strict/extra=forbid及证据去重，非unknown必须有窗口内user ID，不接受助手/外部ID。低于阈值改unknown。无模型、超时、结构/引用错误不回退中文规则或拿旧推测充结果，普通聊天继续；不确定/不可用不注入旧模型心情，手动纠正可留在会话供玩家查看。新推测只在本轮生成和成长/记忆原子提交成功后remember；epoch在模型边界复查，撤回/纠正使旧结果失效。

合成例「悲しくない、ただ疲れてる」与「我不是难过，只是累了」使用同一结构（不是实际模型输出）：

```json
{"use_emotion":"allow","confidence":0.95,"report":{"source_text":"悲しくない、ただ疲れてる","labels":["tired"]},"shift":false,"request_analysis":false,"preference":null,"preference_source":null}
```

程序生成`self_report/model/basis=self_report`，证据仅当前user ID；上下文不带原文引用、ID、observed_at。自述的API intensity=.5仅兼容占位，不传给回答模型当测量；confidence是理解置信而非心理概率。入口置信门槛0.8和UI结果阈值独立，低于结果阈值则unknown。投影只给必要标签/来源/置信/本轮偏好，追加中日“可纠正、非诊断、不读心”的Prompt。旧情绪回复局部检查/兜底尚未全部多语言化，本轮不宣称所有日语情绪回应质量完成。真实schema/识别/否认/讽刺/信号准确率、F1/校准/口吻/费用未验收；命令、失败见[测试记录](TEST_HISTORY.md)。

## 功能与框架

亲密度90获得资格，另行授权后才分析。`app/emotion.py`负责Estimate契约、模型分析、调度、自述和Prompt投影；`app/main.py`负责授权、epoch与会话；网页为`EmotionPane.tsx`。复用当前Gemini/OpenAI的结构化兼容接口，mock仅用于合成验证。

默认每3轮、最近6轮窗口、冷却2轮、置信阈值0.6；强烈表达/请求陪聊可提前触发。明确玩家自述先于模型推测，纠正优先于旧推测；不靠天气、地点或性别推断心情。缓存仅会话内10分钟或6轮，访问时判过期，分析原文/推测不持久化或自动进入长期记忆。

## 结构化输出→校验→注入

输入（合成）：玩家`u1`说“太棒了，又失败了。准备那么久还是被否定，陪我聊一会儿吧。”，窗口带role/content/id；助手消息仅作语境，不能作为本人证据。

LLM估计的五字段示例：

```json
{"labels":["anger","sadness"],"intensity":0.8,"confidence":0.9,"evidence_message_ids":["u1"],"response_strategy":"listen"}
```

1. **格式契约**：Pydantic `Estimate`约束标签枚举、1–3个标签、0–1有限浮点强度/置信度、最多12个证据ID和ask/listen/encourage/practical策略。`model_validator`拒绝重复标签及unknown/neutral与其他标签混用。
2. **SDK解析**：`client.beta.chat.completions.parse(..., response_format=Estimate)`将类型转换为结构化输出要求，解析成对象；业务不靠关键词或正则从自然语言“挖JSON”。temperature=0不能保证格式成功。当前Estimate未设extra=forbid，不能宣称拒绝全部额外字段。
3. **业务校验**：`assess()`再次`Estimate.model_validate(...)`，要求证据ID都属于窗口内user消息，非unknown必须有证据。合法结构不代表正确理解心情。
4. **降级**：低于阈值改unknown/ask；解析、证据、超时或接口失败为unavailable/assessment=null，不借用旧推测补结果，也不阻断正常聊天。
5. **服务端装饰**：补充source=model、turn及observed_at；这些由程序生成，不要求模型填写。返回可为`{"status":"analyzed","assessment":{...}}`。
6. **本轮与后续**：本轮立即由`emotion_prompt()`投影给回复模型；成功后保存临时会话参考，后续轮次按有效期/冷却复用或更新，而非只在下一轮生效。

模型推测的上下文投影（合成）：

```json
{"status":"analyzed","assessment":{"labels":["anger","sadness"],"intensity":0.8,"confidence":0.9,"source":"model","response_strategy":"listen"},"player_preference":"ask"}
```

模型结果只带labels/intensity/confidence/source/strategy；玩家自述/纠正只带labels/source/strategy，不把人为confidence=1当心理测量。证据ID、observed_at和分析原文不注入。附带指令要求“可纠正参考、非诊断、不报标签分数、听起来等试探表达”；尊重倾听偏好，不强迫安慰、报备或亲密关系。

## 接口、隐私与CRUD

| 接口 | 功能 |
| --- | --- |
| `GET /v1/emotion` | 设置与当前临时参考 |
| `PATCH/DELETE /v1/emotion/settings` | 授权/调度/偏好；物理删除设置 |
| `PATCH /v1/emotion/assessment` | 玩家纠正label与偏好 |
| `DELETE /v1/emotion/assessment` | 清空推测，保留设置 |

设置持久化在emotion_profiles；新对话、关闭/删除、纠正等会清理相关状态/历史并用epoch撤回在途回复。锁定时仍能查看、清理和撤回；写接口需身份归属/同源/CSRF。删除设置不恢复旧推测；完整账户/备份删除仍未实现。

## 测试与边界

M4初次交付284默认通过/20PG跳过、前端36通过、临时PG161通过（重叠）。覆盖混合/引用/否认、自述优先、非法结构/证据/数值、调度/缓存/过期、纠正、授权CRUD、隔离、失败、撤回及持久化；不把情绪推测写为长期事实。旧真实合成冒烟及失败保留在[测试索引](TEST_HISTORY.md#历史原文索引)，最新回归见[测试总表](TEST_HISTORY.md)。

真实情绪是主观且可变的；模型或规则均不能保证读懂“真实内心”。独立多标签参考、宏F1、unknown与置信度可靠性、适切性盲评及数值验收门槛仍待完成。
