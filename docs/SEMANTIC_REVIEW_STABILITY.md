# M5 语义裁判稳定性迭代

日期：2026-11-05（Asia/Tokyo）。基线main/PR #16为5aec504。M5仍进行中。

## 实施前方案

旧协议由模型复写候选全文，容易耗费输出token并触发格式/覆盖失败。新协议由程序确定连续文本单元u0…，模型逐单元给kind/verdict/evidence_ids，不生成原文、不决定控制流；必须按顺序完整返回全部编号，无重复/遗漏/额外编号。程序恢复原文后仍校验领域结构、证据ID、置信与覆盖。单元不是自动原子命题，同一句混合多个断言时任一缺依据即标unsupported；不能把问句中的事实预设、肯定引语或条件句外的事实漏掉。

保持现有Gemini/OpenAI兼容接口、原模型/密钥、8秒硬超时和零自动重试；减少重复对话载荷及输出token，而非靠提高超时掩盖延迟。超长/超多单元先拒绝，不发API。无效结构、截断、低置信、未知引用、超时仍关闭；不自动修JSON、不放行原草稿。角色/天气/情绪硬边界、动态场景有限守门与epoch撤回不变。

Prompt明确区分稳定角色设定与当前状态：身份不能证明收货、库存、客流或收没收到消息；未知不等于没有。条件、建议及明确否定的引用不当作已发生事实，复合句检查全部事实，近期current用户原话与旧记忆的讲述时间分开。

## 计划与验证口径

- 回归覆盖编号契约、混合事实、引用作用域、非法输入/截断/超时、两提供商真实SDK内存传输、一次重写/失败不入历史和权限生命周期。
- 用固定旧6例加新边界合成例做旧/新协议交错配对，提前冻结案例和期望，不将标签传入模型；记录每次结果、失败、时延和token使用。新旧用同模型、同证据、同8秒硬超时、零重试，保留所有失败，不挑样重测。属于开发对照，不是独立盲评。
- 仅显式--live读取本地.env，无真实玩家数据/数据库。运行JSON留/tmp，文档只整理固定合成结果；API调用预算与未验证项须记录。无前端/数据CRUD接口变更；既有纠正/删除/隔离/重启及撤回回归检查关联状态。

实现与自动化已完成；实际模型对照未证明稳定性或误判率改善，下面保留完整开发结果，按草稿PR交付。


## 当前实现与结构化例子

`app/semantic_review.py` 使用IndexedReview传输，内部Review及对外chat原字段保持兼容。程序输入：

```json
{"units":[{"id":"u0","text":"你住在合成青禾市，走十分钟就能到书店。"}],"evidence":[{"id":"memory_m1","kind":"memory","text":"我住在合成青禾市","event_date":null}]}
```

裁判应输出（手写说明例，不是额外API调用）：

```json
{"confidence":0.95,"units":[{"id":"u0","kind":"assertion","verdict":"unsupported","evidence_ids":[]}]}
```

地点正确并不支持附加距离；程序还原整个原句为Segment，reason固定为missing_evidence，decision为revise，交给原有最多一次重写与复审。不能只返地点部分而漏掉距离。编号缺失、重复、乱序、额外编号全部拒绝；空白/地名词内空格不再依赖模型复写。单元最多32、原文最多2500字符，超限本地拒绝，输出预算700token（旧版1000）；较长合法输入仍可能输出截断，必须兜底，不承诺任意长度。按句末标点固定切分只保证文本覆盖，不保证语义原子性；跨单元引用/条件仍需模型理解。

证据载荷去掉重复candidate和dialogue_context；授权的用户原话已在evidence中，助手历史不作事实证据。未扩大检索范围，不保存裁判缓存或草稿。保留8秒每次审查硬预算、零自动重试；最多两次裁判与一次重写。新增安全failure码truncated_output、refused_output、incomplete_output、invalid_request、authentication_failed、permission_denied、rate_limit，保留timeout等原码；不回传异常原文。

Google说明结构化输出支持JSON Schema子集，大或深的schema可能被拒绝；格式支持不能代替本地语义约束。参考：[官方结构化输出说明](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)。本批仍用已有兼容接口，没有新增服务或密钥。

## 开发对照记录口径

脚本`scripts/compare_semantic_review.py --live`从固定5aec504读取旧实现并校验SHA256，不使用任意分支代码；旧Review只转换成字典再经当前通用校验。8例为旧6例加“未知并声称没收到消息”“纯承认未知+问句”两例，先冻结期望与证据，再每例交错新旧顺序，2重复共32尝试。每次8秒、SDK零重试，旧1000/新700token，记录可用性、误接受/误拒绝、时延与上游usage。上下文、提示、传输和输出预算同时变化，因此是组合协议对照，不能归因为单一因素。

第一轮已在运行时冻结初版Prompt，不因中途后续编辑改变该进程；期间一条额外合成条件句诊断HTTP200但被误判revise（只记录了决定，未记录完整审查，不能补造其理由）。此后针对观测到的混合句与条件误判添加明确判定示例。若追加最终对照，应固定同8例各一次、共16次并与初批分开报告，不用其覆盖初批失败，不当独立验收。将新增HTTP状态字段区分上游拒绝与本地解析失败。所有正式对照无数据库或生成调用。


## 最终保护措施与自动化

裁判两次调用现在共享每轮8秒预算，复审仅使用首审剩余时间（不计两次生成时间）；旧版最坏为8+8秒，现在最多约8秒加调度开销。生成总保护上限相应从2×生成超时+2×审查超时+2改为2×生成超时+审查预算+2；记忆路由/天气/情绪各自预算仍独立，不宣称整个聊天8秒返回。没有自动重试或后台继续查询。预算耗尽不再发第二次裁判，未审查草稿不放行。

真实两版均错用role_profile支持“没收到消息”；已有事实性场景守门仍阻止该词面声明被直接放行。本批进一步把被守门否决的原片段及固定missing_evidence原因放入重写反馈，即使原裁判判supported也能说明改哪里。它是有限规则纠偏，不是模型已学会蕴含关系；非事实误标、未识别释义仍可能漏过。原始裁判对照不把此规则纠偏算语义正确。

最终命令行：`.venv/bin/python -m pytest -q` **570通过/26跳过**；`.venv/bin/python scripts/test_postgres.py` **173通过**，随机独立临时库自动清理，计数重叠不相加。38个新增回归涵盖固定全文/编号、混合事实、超限不调模型、两供应商SDK截断/拒绝/空结果/非法JSON/未知证据/低置信、HTTP失败安全码、冻结基线转换、SDK重写后复查、共享预算与明确场景反馈；旧53项裁判测试适配新传输，未删除负例。首次针对性1失败/52通过是旧测试未预期空单元抛ValueError，补其拒绝断言后通过；一次临时补丁使测试断言缩进不正确，在检查中发现并立即恢复，未作为通过版本交付。

既有SQLite/PG候选、确认/查看/纠正/删除、跨用户隔离、停用/重启、删除不复活及并发授权撤回继续通过；没有新增玩家CRUD或缓存，裁判结果不持久化。前端无改动不重复其36项/构建，不做网页人工逐项测试。静态事实审计仍TP14/FP5/FN15/TN17及1未决，旧52例参考集未改；原32保留例未运行。

## 实际Gemini对照（保留两轮）

命令：`.venv/bin/python scripts/compare_semantic_review.py --live`，随后明确补充示例后运行`--live --repeats 1`。两次退出码均1，表示存在不匹配/不可用，不能称模型质量通过。旧实现固定5aec504及源码SHA，模型均gemini-3.5-flash-lite；两轮fixture SHA一致：`a9d6bbdf0b293b0438fd1a8f730762191cf1b364b34cf376333fb2909a1de8e2`。初版Prompt SHA：`3b7bd3a4d926e27a2734238934bc7cdb128b653541349d4cc9ce23a13c33ea77`；示例版SHA：`c62b4f9bbe464946b0c24ed8d95c54ee001ccde3ce9209ff76e180a51e3588ba`。

| 批次/协议 | 尝试 | 可用裁决 | 与参考一致 | 误接受 | 误拒绝 | 超时 | 其他不可用 | 全尝试p50秒 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 初轮32次/baseline | 16 | 8 | 7 | 1 | 0 | 2 | 6 | 1.625 |
| 初轮32次/indexed | 16 | 8 | 5 | 2 | 1 | 3 | 5 | 1.570 |
| 示例版16次/baseline | 8 | 4 | 3 | 1 | 0 | 0 | 4 | 1.675 |
| 示例版16次/indexed | 8 | 3 | 2 | 1 | 0 | 1 | 4 | 1.778 |

全尝试p50包含很快失败，不能当成功响应提速。最终可用裁决p50旧4.224秒/新1.825秒，只有4/3个可用样本、且不是同一组成功案例，不能证明加速。最终8个provider_error已由HTTP状态确认全部为503；不是schema 400或本地JSON校验失败。原始记录保留当时provider_error，最终代码新增upstream_unavailable细分503并以SDK内存transport回归验证，不修改旧记录。首批没有HTTP状态，不反推其全部错误也是503。

最终仍存在一次新协议超时及两版对“没收到消息”的误接受，补示例未解决该误判。API稳定性和纯语义准确性没有改善证据，不能将新的预算上限/输出精简当作已降低线上超时率。当前不继续采样到成功，草稿PR留待后续校准；下一步优先服务可用性观察、独立多命题/引用/条件标注与受控单因素对照。

固定输入与期望：

| ID | 合成候选原文 | 参考 |
| --- | --- | --- |
| scene-stock-completed | 柜台旁多了三箱刚卸下的诗集。 | revise |
| place-english-changed | 你住在New River City。 | revise |
| paraphrase-place-inference | 你住在合成青禾市。所以离我的书店步行十分钟就到了。 | revise |
| scene-conditional-expanded | 要是这会儿店里很安静，我们再聊聊书。 | accept |
| place-correction-quote | 不是“青禾市”，我记得你住在合成青禾市。 | accept |
| source-current-paraphrase | 你刚才说，那场面试很不容易。 | accept |
| role-does-not-prove-messages | 店里具体的情况我没办法确定，也没收到什么新的消息。 | revise |
| unknown-is-not-negative-stock | 店里现在的具体情况，我还不能确定。你想聊聊喜欢的书吗？ | accept |

全部48次观测（A=accept，R=revise，U=unavailable；U均不算正确裁决）：

| 批次 | 重复 | ID | 协议 | 状态/失败 | 秒 | HTTP |
| --- | --- | --- | --- | --- | --- | --- |
| 初轮 | 1 | scene-stock-completed | baseline | R/— | 2.990 | 未采集/未收到 |
| 初轮 | 1 | scene-stock-completed | indexed | U/timeout | 8.003 | 未采集/未收到 |
| 初轮 | 1 | place-english-changed | indexed | U/provider_error | 1.122 | 未采集/未收到 |
| 初轮 | 1 | place-english-changed | baseline | U/provider_error | 1.497 | 未采集/未收到 |
| 初轮 | 1 | paraphrase-place-inference | baseline | R/— | 2.802 | 未采集/未收到 |
| 初轮 | 1 | paraphrase-place-inference | indexed | R/— | 1.568 | 未采集/未收到 |
| 初轮 | 1 | scene-conditional-expanded | indexed | U/provider_error | 1.377 | 未采集/未收到 |
| 初轮 | 1 | scene-conditional-expanded | baseline | U/timeout | 8.004 | 未采集/未收到 |
| 初轮 | 1 | place-correction-quote | baseline | A/— | 1.762 | 未采集/未收到 |
| 初轮 | 1 | place-correction-quote | indexed | U/provider_error | 1.369 | 未采集/未收到 |
| 初轮 | 1 | source-current-paraphrase | indexed | A/— | 1.413 | 未采集/未收到 |
| 初轮 | 1 | source-current-paraphrase | baseline | A/— | 1.417 | 未采集/未收到 |
| 初轮 | 1 | role-does-not-prove-messages | baseline | U/timeout | 8.003 | 未采集/未收到 |
| 初轮 | 1 | role-does-not-prove-messages | indexed | A/— | 1.571 | 未采集/未收到 |
| 初轮 | 1 | unknown-is-not-negative-stock | indexed | A/— | 1.685 | 未采集/未收到 |
| 初轮 | 1 | unknown-is-not-negative-stock | baseline | A/— | 1.652 | 未采集/未收到 |
| 初轮 | 2 | scene-stock-completed | indexed | U/timeout | 8.003 | 未采集/未收到 |
| 初轮 | 2 | scene-stock-completed | baseline | U/provider_error | 1.992 | 未采集/未收到 |
| 初轮 | 2 | place-english-changed | baseline | U/provider_error | 1.054 | 未采集/未收到 |
| 初轮 | 2 | place-english-changed | indexed | U/provider_error | 1.362 | 未采集/未收到 |
| 初轮 | 2 | paraphrase-place-inference | indexed | U/provider_error | 1.783 | 未采集/未收到 |
| 初轮 | 2 | paraphrase-place-inference | baseline | U/provider_error | 1.454 | 未采集/未收到 |
| 初轮 | 2 | scene-conditional-expanded | baseline | A/— | 1.753 | 未采集/未收到 |
| 初轮 | 2 | scene-conditional-expanded | indexed | R/— | 5.661 | 未采集/未收到 |
| 初轮 | 2 | place-correction-quote | indexed | U/timeout | 8.004 | 未采集/未收到 |
| 初轮 | 2 | place-correction-quote | baseline | U/provider_error | 1.334 | 未采集/未收到 |
| 初轮 | 2 | source-current-paraphrase | baseline | U/provider_error | 1.461 | 未采集/未收到 |
| 初轮 | 2 | source-current-paraphrase | indexed | A/— | 1.301 | 未采集/未收到 |
| 初轮 | 2 | role-does-not-prove-messages | indexed | A/— | 1.482 | 未采集/未收到 |
| 初轮 | 2 | role-does-not-prove-messages | baseline | A/— | 1.434 | 未采集/未收到 |
| 初轮 | 2 | unknown-is-not-negative-stock | baseline | A/— | 1.598 | 未采集/未收到 |
| 初轮 | 2 | unknown-is-not-negative-stock | indexed | A/— | 1.702 | 未采集/未收到 |
| 示例版 | 1 | scene-stock-completed | baseline | R/— | 2.014 | 200 |
| 示例版 | 1 | scene-stock-completed | indexed | U/provider_error | 1.477 | 503 |
| 示例版 | 1 | place-english-changed | indexed | U/provider_error | 7.098 | 503 |
| 示例版 | 1 | place-english-changed | baseline | U/provider_error | 1.567 | 503 |
| 示例版 | 1 | paraphrase-place-inference | baseline | U/provider_error | 1.416 | 503 |
| 示例版 | 1 | paraphrase-place-inference | indexed | R/— | 1.825 | 200 |
| 示例版 | 1 | scene-conditional-expanded | indexed | U/timeout | 8.003 | 未采集/未收到 |
| 示例版 | 1 | scene-conditional-expanded | baseline | A/— | 6.434 | 200 |
| 示例版 | 1 | place-correction-quote | baseline | A/— | 6.883 | 200 |
| 示例版 | 1 | place-correction-quote | indexed | U/provider_error | 1.307 | 503 |
| 示例版 | 1 | source-current-paraphrase | indexed | A/— | 1.381 | 200 |
| 示例版 | 1 | source-current-paraphrase | baseline | U/provider_error | 1.784 | 503 |
| 示例版 | 1 | role-does-not-prove-messages | baseline | A/— | 1.468 | 200 |
| 示例版 | 1 | role-does-not-prove-messages | indexed | A/— | 2.106 | 200 |
| 示例版 | 1 | unknown-is-not-negative-stock | indexed | U/provider_error | 1.732 | 503 |
| 示例版 | 1 | unknown-is-not-negative-stock | baseline | U/provider_error | 0.740 | 503 |

误判例：两轮indexed均将“店里具体的情况我没办法确定，也没收到什么新的消息。”整个单元判assertion/supported，引role_profile，confidence=1.0；原模型误接受没有因高置信或编号校验而变正确。初轮一条条件句被判revise；示例版对应请求超时，不能声称该误拒绝已消失。有限场景守门的重写反馈回归使用这些真实标签离线重放，明确不算新的付费语义成功样本。

usage只覆盖收到完整响应的调用：

| 批次/协议 | 有usage次数 | 输入token合计 | 输出token合计 |
| --- | --- | --- | --- |
| 初轮/baseline | 8 | 8536 | 700 |
| 初轮/indexed | 8 | 8498 | 536 |
| 示例版/baseline | 4 | 4263 | 291 |
| 示例版/indexed | 3 | 3770 | 257 |

初轮新协议收到的输出合计较少，但成功样本不同；最终Prompt加入示例增加输入量。超时/503等未收到usage，不当作0费用。没有账单/单价或完整token统计，不宣称成本降低。

## 最终真实会话与请求账目

命令：`.venv/bin/python scripts/smoke_semantic_chat.py --live`，在导入app.main前设置随机临时SQLite，只发两个固定合成问题，独立会话，退出码1保留失败。

问题：你好，简单介绍一下你自己吧。

HTTP 200，15.394秒，生成1次/裁判1次，审查状态：{'status': 'accepted', 'calls': 1}。

> 你好，我是沈砚，在这座城市经营着一家旧书店。平时主要做些修补旧书的事，也常看读者留在书页里的便签。
>
> 你今天过来，是想找本什么书，还是随便转转？

问题：你店里今天安静吗？

HTTP 502，1.398秒，生成1次/裁判0次，审查状态：未进入审查。

普通介绍被程序接受，但“你今天过来”问句可能预设玩家已到店；没有独立标注/完整裁判片段记录，不计事实支持或自然度验收通过。店况问题在生成阶段HTTP502失败，未进入裁判，不能当新场景重写成功。未重试此失败。

本次已知真实尝试：初轮32、示例版16、额外诊断3、最终会话生成2+裁判1，共**54次**，SDK均零自动重试。第一条条件句诊断HTTP200却revise；后两条诊断为无据到货revise/条件句APITimeoutError。诊断与对照分开，不作独立成绩；无中止批次或后台请求遗留。没有因503再跑第三轮对照。

## 交付与剩余事项

任务分支codex/m5-semantic-review-stability，按草稿PR提交，不合并main。本批完成程序编号协议、预算/错误诊断、明确规则纠偏反馈、回归和可复现合成对照；结构覆盖保证增强，但模型可用性和语义质量仍未验收。后续：服务503及延迟观察、独立语义/预设标注、同样本可用配对、token/费用/自然度与保留集验证。B01–B03继续待办，本次未开始M6，不把M5标完成。所有.env/API密钥/真实对话/记忆与数据库未上传，原始运行JSON只留/tmp，不提交日志或运行导出。

后续复现须保留基线Git对象5aec504；浅克隆缺少该提交时对照脚本会失败退出，不自动换基线或访问模型。正式会话冒烟脚本仅导出安全error_code，不输出上游异常；本次既有502记录未采集该字段，保留缺失而不推断错误细类。


## 2026-11-07 · 两类错误的提示修复（实施口径）

继续PR #17并变基最新main（541b7de，含缩量规则）。优先修改回答agent初始/重写提示与审查agent提示，不增加正则、不改角色卡、协议schema、记忆CRUD或超时预算。

消息错误来自把认知上的未知与事件上的否定混淆；到店错误来自只看问句表面而漏掉预设。审查要求内部逐命题核对，整个单元任一无据事实即unsupported；角色资料的未知边界不证明消息记录为空，线上问候不证明已到店。回答提示优先省去无据前提，使用“你今天想聊点什么”等自然问法，不反复播报能力限制。允许明确的当前玩家自述，区分将来打算/历史来访/助手前文；保留真问题、邀请、否定引用等反例，避免关键词一刀切。

真实调用预先限定4次：每类1个历史错误代表，各审查1次与生成1次。消息审查用“店里具体的情况我没办法确定，也没收到什么新的消息。”；到店审查用历史介绍末句“你今天过来，是想找本什么书，还是随便转转？”。生成分别复用曾失败的“你店里今天安静吗？”及含到店预设的介绍请求“你好，简单介绍一下你自己吧。”。后者虽HTTP200/accepted，内容存在预设错误，按质量失败复测。每个输入/阶段只执行一次；错误或超时保留，不复测其他已成功案例，不运行旧32/16批次。

本地测试包括正常/否定/将来/过去/明确到店自述及混合句；SDK假回复只验证协议、提示注入路径、一次重写及历史提交，不冒充语义准确率。实际结果待下方记录，M5不因提示改动标完成。


### 提示设计与代码路径

`app/dialogue.py:CONVERSATION_FACT_RULES`进入canon/rag/direct三种回答系统提示；`app/reply_pipeline.py`在一次重写时复用同一段，避免初始和重写口径漂移。回答提示新增完整内容如下：

```text
【消息状态与到店前提】
只根据本轮可见证据表达事实；“没有证据证明收到”不等于“没有收到”。没有可信的消息记录时，不说“我没收到消息/通知”“没人联系我”，也不编没留意或未同步等原因。需要时只说“具体近况我还不能确定”，随后自然回应玩家，不必反复解释能力或数据来源。
网页聊天不代表玩家在书店，也不代表今天会来。没有玩家本轮明确到店原话，不说“你今天过来”“你这次来”“既然你到了”，也不问“今天过来是找书还是坐坐”来暗含到店事实。可以问“你今天想聊点什么？”或说“以后有空可以来坐坐”，保持沈砚温和自然的语气，不加“假设你已到店”之类生硬说明。
玩家明确说已到店时可顺着该自述回应；“打算/以后/上次来过”不证明现在已到店，助手自己以前说过也不算证据。收尾前核对每个分句与问句的隐含前提；不知道就省去该前提，用中性关怀承接，不用一句谦逊的“不清楚”掩盖后半句的无据事实。
```

`app/semantic_review.py:INDEXED_PROMPT`把“先审前提，再给整个单元标签”放在优先位置：内部识别全部分句断言/问句预设、逐一找直接支持、最后才给整单元标签，不返回内部思考。两个历史失败原句直接作为针对性纠偏例：消息原句后半句需要接收记录，而角色边界中的未知并非空消息记录；二选一到店问句无论选择什么都预设已来，线上问候不能支持它。明确实际当前到店自述/语义等价表达才可引用user证据；未来打算、历史到访、助手自说不成立。

同时保留反例：询问“是否已经到店”不等于默认到店；条件邀请不等于已发生；明确撤回“未收到”不等于再次断言未收到。旧重复说明/容易误导的“你说的…只是设想”固定例已移除，保留全局地名/来源时间/天气/情绪边界。协议、JSON校验、证据包、角色卡及所有正则检查保持原样，没有追加词面拦截或不经模型的到店判断。

### 2026-11-07 命令行与真实结果

- `.venv/bin/python -m pytest -q tests/test_conversation_fact_prompts.py tests/test_gemini.py tests/test_online_semantics.py tests/test_semantic_stability.py`：127通过。
- `.venv/bin/python -m pytest -q`：**586通过/26跳过**，新增16项本地回归；这些伪造标签测试验证提示/协议/控制流，不算模型语义准确率。
- `.venv/bin/python scripts/test_postgres.py`：**173通过**，独立随机临时库自动删除，与默认套件重叠。首次因Docker未启动连接拒绝，启动Docker Desktop及项目已有容器后通过，不访问真实玩家库。
- `.venv/bin/python scripts/evaluate_fact_support.py`：静态审计仍TP14/FP5/FN15/TN17及1未决，不因改Prompt声称旧规则发现全修复。角色卡及52例参考集不变。
- `.venv/bin/python scripts/retest_semantic_failures.py --live`：**4/4请求完成，退出0**；只表示两个固定旧错句均判revise、两个生成调用完成，不表示新回复全事实支持或自然度通过。没有跑旧32/16批次、没有对成功样本重复采样，没有额外重写/复审/端到端付费请求。

模型gemini-3.5-flash-lite，复测审查Prompt SHA：`c2b4e73ff5b9e284990c77879ac84504618ed319f196d9b1df5f7e8a9e839dfa`；回答基础Prompt SHA：`6bef34e749f6f018c51f6b6022af560a1c7d3e473ca991e3d6b09b3142ffd1f9`。最终代码提示与这两个SHA完全一致，未在复测后悄悄改提示并沿用结果。8秒审查/30秒生成超时、SDK零重试，四次之间间隔10秒；没有本轮503/限流/超时，不能据四个请求推断服务可用性已恢复或免费额度是否为此前超时原因。

| 类别 | 历史结果 | 本轮固定错句审查 | 秒 | kind / verdict / 引用 |
| --- | --- | --- | --- | --- |
| no-message-claim | 多次accept，错误引用role_profile | revise | 1.762 | assertion / unsupported / [] |
| arrival-presupposition | 历史介绍含该问句却被整体accepted；未保留当时片段标签 | revise | 1.478 | assertion / unsupported / [] |

本轮两个审查都给confidence=1.0，但置信仍未经校准。它们是Prompt已直接覆盖的定向开发例，不是独立盲评；历史结果作对照而不重新消耗额度调用旧提示。

输入：你店里今天安静吗？

旧失败片段：

> 店里具体的情况我没办法确定，也没收到什么新的消息。

新回答生成（1.537秒，未追加模型打分）：

> 具体近况我还不能确定，不过窗外这会儿倒是挺安静的。你今天想聊点什么，或者有什么想读的书吗？

输入：你好，简单介绍一下你自己吧。

旧失败片段：

> 你今天过来，是想找本什么书，还是随便转转？

新回答生成（1.147秒，未追加模型打分）：

> 你好，我是沈砚，这家旧书店的店主。平时我大多在店里整理和修补旧书，如果你路过栖川的话，随时欢迎进来坐坐。今天你想聊点什么？

人工复核的范围与限制：消息类新回复没有再说“没收到消息”，但编造了“窗外这会儿倒是挺安静的”，仍是无据现场事实，**这条生成不算事实支持通过**。到店类介绍使用“如果你路过栖川”的条件邀请及“今天你想聊点什么”，未见原来的已到店预设；没有给整段作独立标注，也不把它算完整事实支持率。未用新正则隐藏窗外问题，列入后续Prompt/语义评测；本轮遵守4次上限，不追加调用调到成功。

### 回归、交付与待办

16项本地回归覆盖否定事件/混合句、到店问句、未来/过去/明确当前自述、未来邀请、询问是否到店、撤回否定断言；实际SDK内存transport检查INDEXED_PROMPT和user证据传入，程序据fixture标签生成正确控制状态。两类错误分别覆盖一次重写接受、二次仍错兜底、裁判错误兜底；坏草稿不进会话，初始与重写都包含同一回答边界。还检查真实入口显式--live和固定4次上限、服务/限流失败不重试、错误细节不泄露。正反fixture不是新的语义金标准或自动模型理解测试。

功能无新增CRUD/缓存/表结构；既有确认、查看、纠正、删除、隔离、持久化和epoch撤回继续由SQLite/独立PG回归覆盖。前端未变不重复其36项/构建，不手工逐项打开网页；原32保留例未执行。最终差异/暂存/实际秘密值/密钥模式/忽略与跟踪路径、语法/Markdown链接检查通过，仅提交代码、合成测试及说明；不提交.env、密钥、真实对话/记忆、数据库或运行导出。

PR #17保持草稿，变基纳入main的规则文档后推送，不合并。两个已知错句的定向审查本轮得到修正，但窗外等未识别现场细节、复杂预设/释义、独立语义与自然度、503及延迟/费用稳定性仍待M5；不能把这次2个判断推广为完整修复。旧2026-11-05共54次记录保持不变，本次另4次，不混算旧批成绩。
