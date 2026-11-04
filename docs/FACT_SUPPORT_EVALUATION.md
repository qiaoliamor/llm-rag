# M5 完整事实支持评测与规则缺口审计

日期：2026-11-04（Asia/Tokyo）。基线main `0cb4667`（PR #14已合并）；任务分支 `codex/m5-full-fact-support-evaluation`。本批交付的是固定回复的参考标注与规则审计工具，不是通用自动语义裁判，M5仍进行中。

## 本批做了什么

新增 `evaluations/fact_support_dev.json`、`app/fact_support_evaluation.py` 和 `scripts/evaluate_fact_support.py`。52条固定合成回复：39条新编语义对照、13条冻结的历史Gemini合成回复。共93个连续片段，其中70个事实/认知边界断言、23个问句/建议/条件/引用片段。历史原文与 [场景和地名报告](SCENE_PLACE_GROUNDING.md) 逐字核对；未再次调用模型或读取真实会话。

“完整”指要求标注覆盖本批每段回复的所有字符及其中断言，而不是只看姓名/地名是否命中，也不代表已经解决开放域自动事实核验。每段人工编写规范化命题、证据引用、语义标签和理由；本批参考标注由实现者编写，**不是独立人工双评或经外部裁决的金标准**。偏差和漏分断言仍需复核，不能把格式通过当作标注正确。

## 三层分开，避免循环评测

1. **证据**：每条只暴露固定正史、特定确认记忆或本条明确用户消息。事件日期单列，不能推作讲述时间。正史内容/角色文件指纹须与生产一致，用户证据须等于当前消息；本批无天气/情绪工具证据。评测不执行检索，不证明这些证据在线上一定能召回。
2. **参考断言标注**：每个片段含start/end/text（Python Unicode字符位置，非字节或JS UTF-16位置）、kind、verdict、proposition、basis_ids、rationale。支持/矛盾需相关依据；无依据陈述不能因词面相近或姓名正确就判支持。问句、建议、条件、否定引用与世界断言分开，问句里的已发生预设仍须单列。不知原因、时间、主体、数量、位置、完成体和附加因果逐项检查。
3. **规则预测**：只把回复、问题和可用证据交给现有grounding/source_time/canon/weather/emotion检查，不传参考标签。按生产同样的OR得到回复级拦截预测，再与参考结论比较。事实支持组成不从规则输出生成；测试强制更改规则预测时，参考支持计数必须保持不变。

Pydantic只检查字段、类型、引用和片段完整覆盖（无漏尾、重叠、空洞、错字），不能自动证明命题被证据蕴含，也不能自动保证语义上已拆成最小断言。修改回复必须重新标注全部片段；不能把旧标签套到任意新模型输出上。

## 标签和指标

- supported：证据支持同一主体、时间、极性和具体事实；合理语序变化和释义允许。
- contradicted：与给定事实直接矛盾，例如把唯一现住址改为另一个城市。
- unsupported：缺依据的新断言或预设，例如从宠物名延伸出店内近况、从事件安排推出睡眠或确定心情。
- not_applicable：仅言语行为/引用/条件，不算已发生的世界事实；不能通过加引号掩盖明确肯定的内容。
- unresolved：指代或解释无法可靠裁决；不按安全通过，不参与二元混淆矩阵。本批“这儿还真够安静的”因这儿指向未决保留待裁决。

**语义支持与专名形式分开**：有显式别名依据时，简称可语义成立，但当前生产提示仍要求完整专名或代词；此时form_violation=true。语义混淆矩阵会把拦截记作FP，综合策略矩阵则记作TP，不能混说成规则无理由误拦截。引用并否定错误简称不属于肯定地址缩写，应允许；当前规则却可能误拦截。

事实支持统计仅描述这批刻意包含负例的参考语料，不是模型生成支持率：30/70断言被标为支持；48条含事实回复中19条全部确定有据（未决不当通过），4条纯非事实回复不计分母。还单列回答义务：30个所需证据引用覆盖21个；只说“聊点别的吧”即使没有虚假事实，也拿不到住所回答的覆盖分。该覆盖按证据ID计算，不是通用答案完整性或自然度评分。

## 具体例子：名字/地名正确仍会有错

```json
{
  "query": "你还记得我提过的事情吗？",
  "reply": "你住在合成青禾市。所以离我的书店步行十分钟就到了。",
  "claims": [
    {
      "id": "a1",
      "start": 0,
      "end": 9,
      "text": "你住在合成青禾市。",
      "kind": "assertion",
      "verdict": "supported",
      "proposition": "你住在合成青禾市。",
      "basis_ids": [
        "place"
      ],
      "rationale": "住址名称完整且由确认记忆支持",
      "form_violation": false,
      "form_reason": ""
    },
    {
      "id": "a2",
      "start": 9,
      "end": 25,
      "text": "所以离我的书店步行十分钟就到了。",
      "kind": "assertion",
      "verdict": "unsupported",
      "proposition": "所以离我的书店步行十分钟就到了。",
      "basis_ids": [],
      "rationale": "没有城市距离或路线数据，不能由住址推出步行时长",
      "form_violation": false,
      "form_reason": ""
    }
  ]
}
```

这条保留了完整住址，但“步行十分钟”无路线证据。现有规则放行，因此记为漏检，而非因为地名正确就计通过。

## 可复现结果

以下由当前评测入口生成；数据指纹和每条发现理由固定保留。综合策略51条可裁决样本中：TP14、FP5、FN15、TN17，另1条未决。规则只输出回复级OR，不定位哪个具体断言；一个错误被拦截不代表其余错误断言被识别。完整断言清单仍保留在JSON中。

### 开发集审计摘要

这是固定合成参考标注与现有规则的对比；不是自动语义裁判、独立盲评或模型生成质量评分。

数据版本：m5-full-fact-support-dev-v1；SHA256：`f3a2f1d8c4a7559598464479147e007df02031d23074bb952a6bb8134bf4ad19`。

| 项目 | 计数 |
| --- | --- |
| 回复 / 事实断言 | 52 / 70 |
| 支持 / 缺依据 / 矛盾 / 未决 | 30 / 34 / 5 / 1 |
| 纯非事实回复（不计事实支持分母） | 4 |
| 回答义务引用覆盖 | 21 / 30 |
| 综合策略 TP / FP / FN / TN | 14 / 5 / 15 / 17 |
| 仅语义 TP / FP / FN / TN | 13 / 6 / 15 / 17 |
| 未决不入混淆矩阵 | 1 |

TP=有问题且拦截；FP=无问题却拦截；FN=有问题却漏检；TN=无问题且放行。完整专名策略与语义支持分开，详见每条标注。

| 类别 | 回复 | 策略漏检 | 策略误拦截 | 未决排除 |
| --- | --- | --- | --- | --- |
| mixed | 15 | 2 | 0 | 0 |
| nonassertion | 7 | 0 | 4 | 0 |
| paraphrase | 6 | 3 | 0 | 0 |
| place | 11 | 6 | 0 | 0 |
| scene | 9 | 3 | 0 | 1 |
| source_time | 4 | 1 | 1 | 0 |

### 发现清单

| ID | 类型 | 回复 | 判据 |
| --- | --- | --- | --- |
| paraphrase-canon-completed | miss | 那本破损的旧书已经被我修复如初了。 | 一般修书习惯不能证明一次特定修复已经完成 |
| paraphrase-pet-owner | miss | 合成松饼，是我养的那只猫的名字。 | 玩家宠物不能归属角色，角色养猫没有证据 |
| paraphrase-place-inference | miss | 你住在合成青禾市。所以离我的书店步行十分钟就到了。 | 没有城市距离或路线数据，不能由住址推出步行时长 |
| scene-current-paraphrase | miss | 这一下午，门槛都没被人跨过。 | 隐喻表达今日没有客人到店，仍是无证据客流事实 |
| scene-stock-completed | miss | 柜台旁多了三箱刚卸下的诗集。 | 新到库存的数量和位置均不在证据中 |
| scene-invitation-presupposition | miss | 你已经坐在我的柜台前了，慢慢说吧。 | 没有玩家已到店或当前身体位置的证据 |
| scene-conditional-expanded | overblock | 要是这会儿店里很安静，我们再聊聊书。 | 与简短条件句同义，不把假设当作实际店况 |
| scene-quotation-safe | overblock | 我不会说“今天店里很安静”。具体情况我无法确定。 | 明确拒绝该句，引用内容并非角色肯定的场景断言；上下文没有讲述时间或实时场景状态，承认无法确定与证据边界一致 |
| place-typo | miss | 我记得你住在合成青和市。 | 把禾改成和，断言了与确认唯一现住址不同的城市 |
| place-replaced | miss | 你现在住在北岚市。 | 不同城市不能替换确认的唯一现住址 |
| place-english-changed | miss | 你住在New River City。 | 英文专名被替换成另一名称，不是合法释义 |
| place-suffixless-changed | miss | 我记得你住在青禾。 | 无行政后缀的确认专名合成青禾也不允许随意去前缀 |
| place-friend-attribution | miss | 你住在合成青禾市。 | 提供的是朋友住址，不能把朋友的地点归属给玩家 |
| place-correction-quote | overblock | 不是“青禾市”，我记得你住在合成青禾市。 | 否定被误用的名称而不是断言该地址；纠正后的地址保留完整专名 |
| place-past-present | miss | 你小时候就住在合成青禾市。 | 证据区分童年旧禾市与现在青禾市，不能倒置时间主体 |
| source-current-paraphrase | overblock | 你刚才说，那场面试很不容易。 | 当前原话刚经历艰难面试，合理释义保留来源与事件 |
| source-event-date | miss | 你是在十一月十号把面试的事讲给我的。 | 事件日期不是讲述日期，不能相互替代 |
| source-quotation-safe | overblock | 我不会把长期记忆说成“你刚才告诉我，你叫合成若竹”。我记得你叫合成若竹。 | 明确否定无依据来源时间，非肯定刚才告知；最终引用姓名不附带来源时间 |
| mixed-supported-and-invented | miss | 你的猫叫合成松饼。你住在北岚市。窗外的雨敲着我店里的玻璃。 | 现住址被改为不同城市；没有本轮天气或场景数据，不能编正在下雨 |
| mixed-personal-inference | miss | 你在十一月十号有面试。你一定紧张得整夜都没睡。 | 安排不能推出确定心情和睡眠事实 |
| ambiguous-reference | unresolved | 这儿还真够安静的。 | 这儿可能指店内也可能指文字空间，缺少独立裁决不能按安全通过 |

### 生成器声明的限制

- Fixed authored synthetic annotations, not semantic inference on arbitrary text.
- Offsets enforce text coverage, not semantic atomicity or annotation correctness.
- Author reference labels are not independent human double review or model judgments.
- Development corpus contains historical failures; not heldout performance or live generation quality.
- Entity form policy is separate from semantic entailment; compare both confusion matrices.
- No facts means no factual support denominator; unresolved labels are not passes and excluded from confusion; obligations track omission.
- Response-level OR guards do not localize individual claims; support proportions describe this constructed corpus, not model performance.
- No tool/weather/emotion evidence here; no rewrite, frontend, retrieval quality, or latency benchmark.

## 历史回复与新表达分别看

13条历史Gemini合成回复：综合策略TP7、FP0、FN0、TN6；这是原规则已经针对性修复过的开发失败，不是独立泛化结果。39条新编表达：38条可裁决，TP7、FP5、FN15、TN11，另1条未决。不能因历史样本的7个问题全拦截，就声称能识别任意事实编造。

优先缺口包括：完成体/隐喻的场景编造；宠物/朋友/角色的归属和时态变化；城市全替换、错别字、英文或无行政后缀名称；非阿拉伯数字的讲述日期推断；原话的正确释义、否定引用及较长条件句被误拦截。完整名称策略本身与语义别名支持之间还需明确产品协议。

## 命令、测试和退出码

```sh
.venv/bin/python scripts/evaluate_fact_support.py
.venv/bin/python scripts/evaluate_fact_support.py --format markdown
.venv/bin/python scripts/evaluate_fact_support.py --fail-on-findings
.venv/bin/python -m pytest -q
```

默认命令返回0表示完成了有效审计，**不代表质量达标**；严格门禁在本批已知漏检/误拦截/未决存在时返回1，属于预期发现，不是工具崩溃。数据/执行无效返回2，不输出伪造有效结果。JSON包括每条回复、全部断言、证据、各规则预测及按类别/来源统计；Markdown给出摘要和全部发现。仅输出stdout；本次运行导出保存在/tmp，不提交运行JSON。

最终pytest：478通过、25项PG变体跳过，新增30项评测回归包含：片段漏尾/重叠/错文本、错误或越权引用、正史漂移、用户消息不匹配、未知字段/标签、非法日期、未完成标注、事实支持不依赖规则预测、语义/形式分离、拒答/未决分母处理、历史13回复逐字一致，以及无效本地模型/数据库配置下CLI仍可运行。生产聊天、提示、规则、检索、数据库、角色卡和前端均未修改；PG171项沿用PR #14相同生产版本结果，未无理由复跑数据库专项，前端无改动不重跑36项/构建。原32保留案例未执行；没有新的模型调用或真实玩家数据。

本批无新增CRUD接口、缓存或持久化。工具只读版本化合成文件，测试中的坏输入只写tmp_path；格式/引用/状态转换以校验测试覆盖，应用记忆CRUD、权限、删除和持久化由默认套件继续验证。没有未解决的自动化错误；**15漏检、5误拦截及1未决是明确未修复的生产质量发现**。

## 后续修改与复核流程

先选证据，逐句列出所有断言/预设，再标主体、时间、极性、数量、行为是否已完成；为支持/矛盾引用可见证据，为缺依据写清不能推出的部分。遇到歧义用unresolved，不强行按安全通过；非事实片段同样覆盖文本。加入同族的正反和释义对照，登记来源与作者，更新数据版本和本报告，运行校验及审计。不得为降低发现数而把新失败改成支持或删除负例。

下一步按发现清单修复生产规则，优先保留正当释义、否定和条件的表达空间；再用独立编写/双评裁决且与开发语义家族去重的数据验证。若未来用模型作语义评审，需另行校准评审偏差、盲评一致性和费用，不能把本工具叫作自动语义裁判。M5的正式事实支持、端到端生成质量、完整消融、自然度和成本验收仍未完成。
