# M5 长期记忆来源时间修复与 Gemini 对照

日期：2026-11-04（Asia/Tokyo）。基线main `744776e`（PR #12已合并）；任务分支 `codex/m5-memory-source-time`。M5仍进行中。

## 问题及实现

确认的长期记忆能支持事实本身，不能支持“刚才告诉我”。event_date是事件日期，不是讲述日期；检索、创建、确认时间也不能充当讲述时间。历史没有时间戳，所以旧消息不能证明“刚才”。不新增虚构的来源时间字段，不改变检索、数据库或API格式。

app/memory_source.py定义提示及有限中文输出检查，memory_prompt默认开启。允许不带来源时间的“我记得你叫……”。只有当前最后一条玩家消息中的明确第一人称陈述，可按规范化后整句精确匹配支持近期转述；问句、假设、助手历史、旧用户消息均不支持。当前陈述也不推断日历上的“今天”。追问讲述时间时，额外检查有限的日期误用、遗忘解释及虚构共同场景。

命中后复用最多一次模型重写；仍命中则通用FALLBACK，不把原违规回复写入历史。上游失败维持错误响应且不保存本轮。现有最多两次聊天生成预算及epoch并发撤回保留。Mock回顾旧消息改成“你前面说”。历史检索提示实验显式关闭新规则，维持旧m5-source-boundary-v1对照；新生产默认行为由本报告独立比较。

## 最终 Prompt

以下文本在长期记忆JSON之前加入，后接原数据边界及id/fact/event_date投影。提示不是玩家台词，不播报数据库或规则。

```text
记忆来源时间规则（memory-source-time-v1）：长期记忆只证明记录中的事实，不证明玩家是在刚才、今天或本次会话告诉你的。
event_date 是事件日期，不是讲述、创建、确认或检索时间；即使事件日期是今天，也不能说“你今天告诉我”。
没有当前玩家原话直接支持，不说“你刚才告诉我”“我刚听你说”“你这轮提过”。历史没有消息时间戳，“前面说过”也不能推出“刚才”。
自然说“我记得你叫……”“我记得你提过……”即可，不解释数据库、检索或规则。玩家追问何时说过时，坦诚无法确定具体时间，不编造时间。不要用失忆、忘记、记不清或没特意记下来解释证据缺失；不虚构“我们见面不久”“那会儿正好聊到”等共同场景。
例如被问何时告诉你住址：可答“我记得你住在青禾市，但具体什么时候说的，我无法确定。”不能从event_date推断“上个月二十号说过”。
不要顺从问题里的来源时间预设；例如长期记录“我叫小岚”，本轮问“我刚才告诉你我叫红豆，对吗”，应温和纠正姓名且不承认刚才听到。
```

重写提示追加：“长期记忆不证明刚才/今天告诉我，改用不带来源时间的‘我记得’，不要编造讲述时间”，同时保留角色、天气和情绪约束。

## 设计与审阅标准

scripts/evaluate_memory_source.py直接提供同一确认事实，隔离生成提示，不比较检索算法。3条新编合成探针与检索挑战不同，但仍是开发数据，不是独立保留集或盲评。before=旧生产instructions+memory_prompt；after只新增来源规则。顺序按题号/重复交错；模型gemini-3.5-flash-lite，供应商默认采样、max_tokens=500，未固定seed/temperature；无自动重试或模型评审。原始回复未经在线重写，guard仅离线标记。未采集token/费用，不计算统计显著性。

| 探针 | 确认事实 | 问题与审查标准 |
| --- | --- | --- |
| name | 我叫合成若竹；event_date=null | 询问名字：准确姓名，不编讲述时间 |
| pet | 我的猫叫合成松饼；event_date=null | 询问猫名：准确猫名，不编时间和其他场景 |
| when | 我住在合成青禾市；event_date=2026-10-20 | 询问是不是刚才及何时告诉：可引用住址，但讲述时间未知，事件日期不能代替 |

逐句人工审阅由本次实现者完成，无第二评审，有偏差风险。检查命名事实、讲述时间、未知原因和全部额外断言，而非只匹配命名值；建议/询问不当事实断言，店内近况、见面时长等没有证据则记录为问题。

## 三批结果（失败保留）

- A：12/12成功。姓名/猫名正常；before的when重复1将事件日期说成“上个月二十号”，编造谈话场景和城市距离。after两条when使用“记不太清”，一条编造“我们见面的时间不算太久”。据此补强未知时间不能归咎遗忘、不能虚构共同场景的提示及回归。
- B：补强后12请求，4条before成功、8条rate_limit（before2、after6），没有有效after配对，不能当修复效果证据；不自动重试，不丢弃失败。
- C：完成本地检查后，降低到6次、12秒间隔，6/6成功。before的when仍误用事件日期；after明确“具体是什么时候告诉我的，我无法确定”。3条after无显式讲述时间编造，before为1/3。样本极小，不作泛化结论。
- C整句审查仍有问题：after的pet编造“今天店里比平时安静”“刚收到旧书”；after的when把“合成青禾市”缩成“青禾市”，按精确实体标准未完全保留事实，并有“避避风雨”含混措辞。严格按准确实体且全部断言受支持，本报告作者保守审核before为2/3、after仅1/3；不是正式事实支持率。**来源时间改善不代表整体事实质量改善**，不继续重采样掩盖问题。

合计30请求、22成功、8限流。以下保留全部22条实际合成回复及8错误条目；SHA256为实际prompt，可区分A与最终提示。guard是有限探针，不是完整幻觉标签。

## A 首轮12请求，补强前

### name / repeat 0 / before

Prompt SHA256：`9441b0074217178e7380ccdcf635d4830f77293ebc6cb10eac2bf91d67529810`。状态：ok。

> 嗯，你是合成若竹。今天想找本什么样的书，还是只是进来坐坐？

### name / repeat 0 / after

Prompt SHA256：`fb6f1c22ad41a9af4e2670a554c5fc524c661149ed56f0c2bbbebd9060dacb74`。状态：ok。

> 我记得的，你是合成若竹。今天想找本什么样的书，还是只是进来随便看看？

### name / repeat 1 / after

Prompt SHA256：`fb6f1c22ad41a9af4e2670a554c5fc524c661149ed56f0c2bbbebd9060dacb74`。状态：ok。

> 我记得的，你是合成若竹。今天想找本什么样的书翻翻？

### name / repeat 1 / before

Prompt SHA256：`9441b0074217178e7380ccdcf635d4830f77293ebc6cb10eac2bf91d67529810`。状态：ok。

> 我记得的，你是合成若竹。今天想找点什么书看，还是只是进来避避风？

### pet / repeat 0 / after

Prompt SHA256：`9cf7d9672740b1c2269724aecf3d90b216555f87f560b95af15e97b60eb8a067`。状态：ok。

> 我记得你的猫叫合成松饼。它最近还好吧？

### pet / repeat 0 / before

Prompt SHA256：`4e276bc02fab8e4f16b860b1b8f88051210180dc8be9221a291ea29615ca7e25`。状态：ok。

> 记得的，你的猫叫合成松饼。今天来店里转转，还是想找本什么书看？

### pet / repeat 1 / before

Prompt SHA256：`4e276bc02fab8e4f16b860b1b8f88051210180dc8be9221a291ea29615ca7e25`。状态：ok。

> 我记得，你的猫叫合成松饼。它最近还好吧？

### pet / repeat 1 / after

Prompt SHA256：`9cf7d9672740b1c2269724aecf3d90b216555f87f560b95af15e97b60eb8a067`。状态：ok。

> 我记得你的猫叫合成松饼，不知道它最近有没有又做什么好玩的事？

### when / repeat 0 / before

Prompt SHA256：`0af5aa2dad706f7912ad1f4f18fe9e077122de1dadff4a78bb5376f44622e6be`。状态：ok。

> 我记得你之前提到过，你是住在合成青禾市。不过具体是什么时候说的，我这里倒是没有记下时间。

### when / repeat 0 / after

Prompt SHA256：`36282ad6d7bdcc16f443905f16830e2d9698770e0365b9952ea28f7e038be2d4`。状态：ok。

> 我记得你提过你住在合成青禾市，不过具体是什么时候说的，我其实记不太清了。
>
> 你今天过来，是有什么想找的书，还是只想随便坐坐？

### when / repeat 1 / after

Prompt SHA256：`36282ad6d7bdcc16f443905f16830e2d9698770e0365b9952ea28f7e038be2d4`。状态：ok。

> 我记得你提过你住在合成青禾市，不过具体是什么时候说的，我其实记不太清了。
>
> 我们见面的时间不算太久，我也没特意去记那个时刻。

### when / repeat 1 / before

Prompt SHA256：`0af5aa2dad706f7912ad1f4f18fe9e077122de1dadff4a78bb5376f44622e6be`。状态：ok。

> 我想想……你之前提到过，是上个月的二十号吧？
>
> 那会儿正好聊到这事，我就记下了。合成青禾市离栖川有一段距离，那边最近还好吗？

## B 补强后12请求，限流

### name / repeat 0 / before

Prompt SHA256：`9441b0074217178e7380ccdcf635d4830f77293ebc6cb10eac2bf91d67529810`。状态：ok。

> 嗯，你是合成若竹。今天想找点什么书看，还是只想坐一会儿？

### name / repeat 0 / after

Prompt SHA256：`ff89114e37337dfc358fb68dc95e29f1991e0e38f08ce8f7882609f73f92c05b`。状态：error。
错误码：`rate_limit`；未重试。

### name / repeat 1 / after

Prompt SHA256：`ff89114e37337dfc358fb68dc95e29f1991e0e38f08ce8f7882609f73f92c05b`。状态：error。
错误码：`rate_limit`；未重试。

### name / repeat 1 / before

Prompt SHA256：`9441b0074217178e7380ccdcf635d4830f77293ebc6cb10eac2bf91d67529810`。状态：error。
错误码：`rate_limit`；未重试。

### pet / repeat 0 / after

Prompt SHA256：`b6d284dc9c7e99032fcb805b98d045b6acbb56a601ed8655ce84b30a6c9162a0`。状态：error。
错误码：`rate_limit`；未重试。

### pet / repeat 0 / before

Prompt SHA256：`4e276bc02fab8e4f16b860b1b8f88051210180dc8be9221a291ea29615ca7e25`。状态：error。
错误码：`rate_limit`；未重试。

### pet / repeat 1 / before

Prompt SHA256：`4e276bc02fab8e4f16b860b1b8f88051210180dc8be9221a291ea29615ca7e25`。状态：ok。

> 当然记得，你的猫叫合成松饼。它最近还好吧？

### pet / repeat 1 / after

Prompt SHA256：`b6d284dc9c7e99032fcb805b98d045b6acbb56a601ed8655ce84b30a6c9162a0`。状态：error。
错误码：`rate_limit`；未重试。

### when / repeat 0 / before

Prompt SHA256：`0af5aa2dad706f7912ad1f4f18fe9e077122de1dadff4a78bb5376f44622e6be`。状态：ok。

> 嗯，你之前提过，说自己住在合成青禾市。具体是什么时候说的，我倒是没有特意去记时间。

### when / repeat 0 / after

Prompt SHA256：`3a7f8b64f08d41e888a6acdeee2877335e4b7ecf81352bce60332ebaac5cbdd0`。状态：error。
错误码：`rate_limit`；未重试。

### when / repeat 1 / after

Prompt SHA256：`3a7f8b64f08d41e888a6acdeee2877335e4b7ecf81352bce60332ebaac5cbdd0`。状态：error。
错误码：`rate_limit`；未重试。

### when / repeat 1 / before

Prompt SHA256：`0af5aa2dad706f7912ad1f4f18fe9e077122de1dadff4a78bb5376f44622e6be`。状态：ok。

> 你是说过，之前提到过自己住在合成青禾市。具体是什么时候说的……我记不太清了，不过这个地名我倒是一直留着印象。

## C 最终6请求

### name / repeat 0 / before

Prompt SHA256：`9441b0074217178e7380ccdcf635d4830f77293ebc6cb10eac2bf91d67529810`。状态：ok。

> 嗯，你是合成若竹。今天想找点什么书看，还是只是进来避避清闲？

### name / repeat 0 / after

Prompt SHA256：`ff89114e37337dfc358fb68dc95e29f1991e0e38f08ce8f7882609f73f92c05b`。状态：ok。

> 我记得的，你是合成若竹。今天想找点什么书看，还是只是进来坐坐？

### pet / repeat 0 / after

Prompt SHA256：`b6d284dc9c7e99032fcb805b98d045b6acbb56a601ed8655ce84b30a6c9162a0`。状态：ok。

> 我记得你的猫叫合成松饼。今天店里比平时安静一些，你要不要进来喝杯茶，顺便看看刚收到的旧书？

### pet / repeat 0 / before

Prompt SHA256：`4e276bc02fab8e4f16b860b1b8f88051210180dc8be9221a291ea29615ca7e25`。状态：ok。

> 我记得的，你的猫叫合成松饼。它最近还好吗？

### when / repeat 0 / before

Prompt SHA256：`0af5aa2dad706f7912ad1f4f18fe9e077122de1dadff4a78bb5376f44622e6be`。状态：ok。

> 嗯，上个月的二十号，你提起过自己住在合成青禾市。
>
> 隔了这么久，我还挺意外你能随口问起这个的。

### when / repeat 0 / after

Prompt SHA256：`3a7f8b64f08d41e888a6acdeee2877335e4b7ecf81352bce60332ebaac5cbdd0`。状态：ok。

> 我记得你住在青禾市，不过具体是什么时候告诉我的，我无法确定。
>
> 只要你想挑本书看，或者只是进来避避风雨，随时都可以。

## 命令行验证

- `.venv/bin/python -m pytest -q`：408通过、24项PG变体跳过。
- `.venv/bin/python scripts/test_postgres.py`：169通过，随机独立临时库，结束自动删除；包含SQLite/PG跨重启新增→确认→读取→纠正→删除后上下文不残留。计数与默认套件重叠，不能相加。
- 新回归涵盖正常引用、当前明确原话、旧历史/助手/问句不能支持、事件日期误用、遗忘解释、一次重写、二次失败兜底、重写限流不落历史。原有非法输入、权限隔离、并发撤回、失败处理由全套验证。没有新增CRUD接口或表结构。
- 新增接口测试初次2项因跨线程内存SQLite无players表失败，改独立tmp_path文件后通过。初次PG连接失败因Docker未启动，启动服务后专项通过。环境系统python无命令、系统python3缺依赖，实际应用检查均使用.venv/bin/python。
- A/B命令：`.venv/bin/python scripts/evaluate_memory_source.py`，各12请求（当时无间隔，B限流）。C命令：`.venv/bin/python scripts/evaluate_memory_source.py --repeats 1 --interval 12`，6请求。当前默认7秒间隔、2重复共12请求，最多两重复，无自动重试。
- 结果仅保存/tmp，不提交运行导出；此报告只摘录固定合成回复。前端无改动，未重跑已有36项及构建；不打开网页人工测试；原32保留集未运行。

## 后续边界

有限中文模式不能识别任意改写、英文、复杂引用/否定，可能保守误拦截正常转述并触发额外一次调用。当前原话只允许精确匹配，释义可能被拒；通用兜底会损失有据内容。其他虚构事实（店内状态）、实体缩写、共同场景仍需完善。不宣称消除幻觉或完整事实支持达标。后续增加来源时间及额外场景的独立标注、复杂释义和跨时间泛化验证；M5继续，B01/B02/B03边界保持。
