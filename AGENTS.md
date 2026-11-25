# 项目操作规则

开始任务，以及修改、检查、提交、推送、变基或合并前，先阅读本文件；遵守其中与当前操作相关的规则。

## 1. 检查原则

- 默认通过终端命令、自动化测试和代码运行验证功能；不逐个打开网页做人工交互测试，除非用户明确要求。
- 每项功能都要完整检查适用的增、查、改、删及它们之间的状态变化；不适用的操作说明原因。
- 覆盖正常流程、非法输入、权限隔离、失败处理和持久化；涉及删除时验证关联数据、检索结果和缓存不会残留或复活。
- 修复缺陷后补相关回归测试，运行受影响的检查与必要构建；失败不能算完成，不无理由重复已通过的测试。
- 测试使用合成数据及独立临时库，不操作真实玩家数据。记录命令、结果和未验证项，更新任务清单及版本测试记录。
- 真实模型 API 测试节省免费额度：只复测此前出错的合成案例（含误判、非法结构、超时或接口失败），不重复已成功的回复；每类默认选 1 个代表案例、只执行 1 次，确有必要才增加数量并说明理由。
- 真实 API 测试前明确本次失败案例及调用上限；遇到限流、超时或服务错误时保留结果，不连续重试或反复采样直到成功。免费额度或服务限制可能影响超时，但未经验证不认定为原因。
- 上述缩量仅适用于真实 API 调用；本地自动化回归和模拟接口测试仍按受影响范围完整检查，保留必要的正常流程及增删改查覆盖。

## 2. Git 原则

**一个任务一个分支；先检查再提交；通过 PR 合并；最后同步清理。**

1. 新环境才 `git clone`；已有仓库先执行 `git status`，确认分支、远端和未提交内容，不覆盖他人工作。
2. 开始修改前创建任务分支：`git switch -c <task-branch>`；不直接在 `main` 开发或推送功能修改。
3. 完成修改与测试后检查 `git diff`，明确暂存文件，再检查 `git diff --cached` 和 `git diff --cached --check`。
4. 优先 `git add <file>`；只有确认全部变更都属于本任务且无秘密/运行数据时，才使用 `git add .`。
5. 用清晰的信息提交：`git commit -m "<message>"`，推送任务分支：`git push -u origin <task-branch>`。
6. 远端 `main` 更新时，先确保工作区干净，再 `git fetch origin`、`git rebase origin/main`；处理冲突后重新检查差异并运行受影响的测试。
7. 已推送分支变基后，用 `git push --force-with-lease origin <task-branch>`，不使用裸 `-f`；不得强推 `main` 或擅自改写共享分支历史。
8. 通过 Pull Request 由管理员 **squash and merge** 到 `main`，不绕过 PR 直接合并或推送 `main`。
9. PR 合并后，确认无未保存工作：`git switch main`、`git pull --ff-only origin main`。确认成果已进入 `main` 后，删除远端任务分支。
10. 本地分支优先用 `git branch -d <task-branch>`；若 squash 导致不能删除，核对成果已合并后才用 `-D`，或用 `git branch -m <task-branch> archive/<task-branch>_backup` 保留。
11. 最后 `git fetch --prune`、`git status`，确认本地文件、分支与 GitHub 状态一致。`fetch` 只更新远端跟踪引用，不会自动更新当前本地分支。

## 3. 提交边界

- 不显示或提交 `.env`、API 密钥、数据库凭据、真实对话、真实记忆、数据库、日志或运行导出；配置模板只留空值或安全示例。
- 推送前检查暂存内容及忽略规则；不要仅凭 `.gitignore` 假定文件安全，已跟踪文件仍会被提交。
- 功能、缺陷修复和文档保持对应；完成汇报说明改动、测试、分支/PR及剩余事项，不把未实现或未验证内容标为完成。


## 4. 状态更新

- 每个M也就是模块完成之后，更新docs里面的相关文件。

## 5. 项目知识与维护入口

- 技术入口：`frontend/src/`是React + TypeScript；`app/main.py`编排FastAPI，`app/config.py`是默认配置来源；`scripts/start.sh`构建并启动本地8000端口。`app/static/`为忽略的生成产物，不手改。SQLAlchemy使用PostgreSQL/pgvector或离线SQLite，短期会话/天气缓存仍是单进程内存。
- 默认`companion`自然聊天，旧`audit`供历史对照。普通环境、声音、光线、翻书等允许虚构；重点核对角色明确正史/边界、已确认记忆与近期本人原话、检索来源及真实工具数据；未设定闲聊留白按最新创作者标准允许即兴。亲近语气不等于确立恋人关系；优先修改回答/审查Prompt并补真实缺陷回归，避免继续堆逐句正则。裁判与选择入口均不保证理解全部事实。
- 长期记忆按需检索，候选须玩家确认才入检索；最新自述/纠正优先，助手历史不是玩家事实，事件日期不证明“刚才告诉我”。B01字符哈希非训练嵌入、B02提取保守、B03浏览器Cookie身份三项边界仍保留。
- 亲密度30/60/90分别解锁记忆/天气/情绪资格，解锁后仍需独立授权。首页仅显示档位，新解锁轻动效后可点击文字重看；基础聊天始终开放。锁定/关闭不能阻止查看、删除旧资料及撤回授权。钱包仅演示币，不将其描述为真实支付或正式账户。
- 持久化修改注意身份归属、版本和epoch：撤回使在途旧回复失效；删除原文/向量，非文本撤销指纹防止自动复活。成长积分/候选记忆原子提交后再保存本轮历史；钱包幂等按用户+请求ID，跨日旧请求不能重置当日积分额度。
- 测试口径：旧回归显式`audit`/关闭成长，新默认路径须显式`companion`/开启成长；不能把所有通过数都称为生产默认覆盖。PG只用`scripts/test_postgres.py`创建的临时库；不需要为纯文档改动重复全部应用测试，但须检查链接、被测试读取的文档证据、封存和来源指纹。
- 文档唯一入口为`docs/README.md`；每个模块一份综合文档，功能/设计/源码/测试/边界放同处。`docs/PLAN.md`只维护阶段与后续顺序，`TODOLIST.md`只维护交付和待办，`docs/TEST_HISTORY.md`维护测试基线/失败/历史原文索引，避免向多个文档追加重复长报告。
- 历史事实不因整理文档消失：旧原回复/耗时/失败保留固定Git版本入口；`docs/SCENE_PLACE_GROUNDING.md`被测试逐字读取，不能随意精简/迁移。封存v1/v2及来源哈希绑定内容不得静默改写；有政策变化需新版本并说明理由。公开作者已见集、结构校验、实现者评审不能冒充独立金标准或质量验收；截至2026-11-10，M5尚未整体验收、M6未开始；后续以`docs/PLAN.md`为准。

- 中日语言入口：UI文案在`frontend/src/i18n.ts`/`locales/ja.json`，生成语言在`app/localization.py`；可选`chat.locale`仅允许zh-CN/ja-JP。切换不改身份/正史/授权/记忆原文/地点或UTC额度日，日语UI不代表中文规则已支持日语语义。维护中文模块时同步`docs/ja/`对应页与双语README/TODO；权威操作规则和历史证据保留单份，不能翻译改写封存原文。

- 多语言记忆默认`MEMORY_UNDERSTANDING_MODE=semantic`，理解/日期/候选/证据选择在`app/memory_understanding.py`；`legacy`仅用于显式历史回放，不是失败回退。语义失败不检索/自动提候选，手动保留原文/未知日期。旧回归显式固定legacy，新回归须显式semantic并覆盖真实默认路径。Prompt不能代替权限、原文/证据白名单、逐条确认、日期运算、epoch/版本/事务校验；本轮未完成天气/情绪/回复等全部语言规则迁移。

- 天气意图/城市/日期默认`WEATHER_UNDERSTANDING_MODE=semantic`，入口`app/weather_understanding.py`；60分且独立授权后才发送本轮原文给当前模型，地名/预报提供方只接收城市或坐标/时区。城市/日期必须绑定原文，目的地时区与七天范围由程序计算；pending仅原UTC锚点和日期结构，10分钟有效，取消/闲聊/失败/设置变化即清除。分析后与工具调用边界检查epoch，失败不回退旧正则。历史weather.py/源绑定证据不改；新增天气测试显式semantic/companion/growth=true，临时PG用`--semantic-weather`。这是理解入口迁移，不代表日语回复词面检查、情绪规则或真实模型质量已验收。

- 默认semantic天气回复用`app/weather_presentation.py`的回答/审查/重写Prompt，语言由请求locale传入；旧中文关键词展示检查只留legacy。天气审查证据增加程序计算的demo和reply_locale；本版role_issues也含天气展示遗漏/主体语言错误，事实与表达不能互相抵消。程序只对纯天气归属片段比较数字/单位，玩家分数、引语和混合句须语义区分，不能遍历全回复把全部百分比当湿度。无judge/关闭review用当前语言的weather_safe_fallback，不将mock或结构测试当真实语义验收。新策略独立冻结，旧Prompt/封存不改。

- 情绪自述/触发默认`EMOTION_UNDERSTANDING_MODE=semantic`，入口`app/emotion_understanding.py`；90分且独立授权后每轮做语义入口判断，完整估计仍由程序interval/window/cooldown/threshold调度，两步共用默认6秒、无重试，失败估计占冷却。模型解释自述须原文非空/唯一绑定，source=model+basis=self_report，不能伪标玩家确认；source=user仅页面手动纠正。新否认/变化不能复活旧推测，失败不注入旧模型结果，手动纠正优先/可查看；本轮陪伴偏好不持久化。旧emotion.py/Prompt只明示legacy，新增套件显式semantic/companion/growth=true，PG用`--semantic-emotion`。结构/ID合法不是理解真值，旧情绪输出局部检查/兜底仍有语言边界。

- 默认情绪回复用`app/emotion_presentation.py`组合回答/审查Prompt和locale安全兜底，语义区分引用/否定/归因与读心/诊断，不再把中文词当通行条件。emotion_current只投影必要参考，emotion_policy仅语言/偏好/状态，程序拒绝将其当事实证据；off时不送旧参考。有效参考/失败或拒绝状态审查，普通waiting无参考不为情绪强制额外审查；共享一次重写/原预算，无judge或关review用安全短句。天气+倾听兜底保留天气事实、不强加建议。旧正则只明示legacy；语义误判、真实口吻/成本仍须独立验收，勿把合成accept当准确率。

- 人物/来源时间/地点回复默认`REPLY_UNDERSTANDING_MODE=semantic`，`app/fact_presentation.py`组合正史与中日回答/审查/重写Prompt；绕过旧conflicts/source_time/place/scene词面检查及中文选择入口，legacy仅显式历史回放。自由回复统一共享一次审查/至多一次重写，不另调语义选择器；仅首次生成当前locale的完整可信短句且无强制审查/记忆/天气/有效情绪才跳过，不按关键词或子串放行。无judge/关闭review非模板用同语言安全兜底。reply_policy是语言控制，不能引为事实证据；证据ID/覆盖/预算/epoch/权限/天气数值校验保留。event_date不证明讲述时间、助手历史不证明玩家事实，允许引用/否定与自然氛围；真实语义/自然度及新增审查成本未验收。新套件显式semantic/companion/growth=true，PG用`--semantic-reply`；旧多语言套件在根conftest固定reply legacy，不冒称新默认覆盖。

- 日语口吻`shen-yan-ja-care-v3`在localization.py，旧JAPANESE_PROMPT_V1/V2保留；记忆当前`same-language-memory-v6`，查询仍使用原样v5，保留PLAN_PROMPT_V1/V2/V3/V4/V5与SELECT_PROMPT_V1/V3/V4/V5，实际发送独立精简版；查询/选择优先同语言主体、属性和时间，替代旧版跨语言关键词扩展建议，不以人工给定plan当模型预测。`scripts/evaluate_japanese.py`只用临时SQLite评实际字符候选召回；人工改写/类型是oracle，候选Recall不等于最终选择/回答准确率，无答案候选误召回要保留。12条公开编辑回复仅盲评流程校准，非Gemini输出或独立正式集。prepare只在仓库外写空评分双人包和私有mapping，score_annotations.py --japanese复用片段/证据/一致率校验，母语/独立性自述不认证，结果始终not_assessed；不自动填评分或联络评审。旧封存v1/v2不改，真实人评/模型质量和B01–B03未验收。中日口吻审查v2允许简短/省略/常体，不将普通氛围拒答与未知库存/预约的诚实留保混淆；Prompt或评分指南更新后新建哈希绑定空包，旧包不重绑，合成脚本不证明母语自然度。

- 日语记忆四层离线回放入口`evaluate_japanese.py --memory-layers`，实现`app/japanese_memory_layers.py`与独立memory_layers_v1开发集；子进程禁读.env、强制mock/临时SQLite，用真实FastAPI聊天接口和实际选择/Prompt/回复管线观察。人工plan/选择/回复/裁判是假设与故障注入，不当模型预测或质量分数；基准与故障分别报告，已知合法ID也可能语义错，不能只验ID。上下文审计核对实际注入ID/原文/event_date，回复按作者完整命题及实际来源可用性标注，未知文本unrated。保留跨语言候选未命中和故障负例，null未执行不当空集成功，503/504/409无已发布回复；PG只用脚本临时库，母语盲评/独立验收仍待完成，不改旧盲评绑定或封存。

- 当前记忆目标按用户要求是中文检索中文、日文检索日文，不把日问中记忆未命中当当前缺陷；历史跨语言观察不删除。查询不猜未知值，选择区分本人/亲属/宠物、童年/现在、昵称/本名，本轮已给答案无需查旧库。`evaluate_japanese.py --same-language-memory`独立10例/26合成回放，人工plan/选择/回复不作Gemini效果；旧31回放单列，不把两者混成前后提升。没有新增语言硬过滤/隔离字段，切换不删记忆；Prompt变更后新建外部空包，旧包不重绑。

- 记忆预算：MEMORY_UNDERSTANDING_TIMEOUT_SECONDS现为查询/候选分析阶段上限，默认8秒；MEMORY_SELECTION_TIMEOUT_SECONDS为选择上限，默认8秒。MemoryCallBudget统一供网页和实测脚本使用，合计deadline为两者之和（默认16秒，计入本地检索），选择取自身cap与剩余时间较小值；SDK选择不得再沿用查询cap。旧.env显式4只限查询，未改真实.env。无新调用/重试，epoch边界不变。memory_reply_context在请求记忆但无证据时使用当前memory-canon-focus-v2；旧memory-open-world-v1留作历史。未设定宠物状态的闲聊推测（含原“否认养狗”句）不再仅因缺证据判错；已确认记忆/当前原话或正史明确相反时仍检查矛盾。FactAnalysisProvider审查与回答Prompt同步当前标准。真实裁判仍可能误放行，离线脚本标签不作质量保证。

- 当前创作标准（2026-11-17用户更正）：主要验中问中/日问日的已确认记忆取用及男主已有背景一致性，不对未设定闲聊逐句索证，不把养狗旧句再列缺陷。不能把即兴说成检索命中/正史，不能覆盖明确记忆/当前自述，助手即兴不回写为玩家记忆。旧判断/原回复与封存不重写；标准改变不是模型修复。retest_memory_canon.py仅固定旧失败，日语主体可走真实理解/选证/审查，中文503只复用旧成功选证补审查；--case可独立指定，最多3/1/1调用，总5，遇错不重试。当前人工标注格式对新创作范围还需校准，旧12编辑文/空包不是新标准质量金标准，母语盲评未完成。

- 日语主体失败复测：v5查询保留「妹 面接」，查询8秒/选择6秒，总14秒，无重试。2026-11-17真实查询成功后选择仍超时，未验证选证/最终回答；retest_memory_canon.py --selection-only仅复用该次成功的合成plan，再实际召回/选择，最多1调用，不重做查询/审查。复用plan不是新模型预测，未选中保持null而非成功空集；本轮只离线验证此模式，真实复测需另授权。

- 选择v6（2026-11-17）：查询v5原样966字，选择305→237字，默认8+8=16秒。复用成功合成plan、真实候选/单次Gemini选择1.979秒返回sister且通过结构/ID校验；不是新query或最终回复验证、不是稳定性或Prompt因果评测，confidence=1不是准确率。历史6.001秒timeout保留，母语盲评未完成；旧绑定包不重绑，Prompt变更另建外部空包。

- 当前政策双语矩阵（2026-11-18）：`evaluations/current_policy/bilingual_memory_acceptance_v1.json`是作者已见16例/50回放，`evaluate_japanese.py --current-policy-matrix`复用四层真实API观测，标注supported/contradicted/unsupported/permitted_scene/nonfactual分开。旧31/26回放、封存和审计源快照不重写；新文件放独立目录不冒充旧审计覆盖。prior_dialogue仅合成夹具，种入正确epoch后核对旧话与最新纠正；source/片段合法不是语义真值。fact-care-v3保留ANSWER/REVIEW V2，回答按主体/现状，审查明确反证用contradicted+C01/C02，氛围不能证明玩家在场。新的providers钩子仅供临时库回放，不是线上接口。
- `retest_bilingual_acceptance.py --live`最多3真实调用：日语妹妹案例复用PR #44成功plan/选择后真实生成+审查2次、旧正史反证审查1次；无查询/选择API、无重试/真实重写，遇错停。额外重写在发出请求前以test_call_budget阻止并单列blocked。陌生生成文本即使模型accept仍unrated，canonical exact fixture匹配不是独立金标准；中文本轮仅离线，母语盲评待完成。CLI尾部单例成功须HTTP200、semantic_review=accepted且有审查输出，200安全兜底/审查未完成须退出1，不以传输成功充当流程完成。

- 陌生合成回复离线入口`evaluate_observed_replies.py`/`app/observed_reply_evaluation.py`：读取current_policy下Gemini转录与独立保存的开发参考，复用annotation_scoring.Claim/check_claims，不把原模型accept当参考。原文SHA/不可变Git文档、源场景/声明选证/角色证据、完整Unicode分片/来源白名单与逐片缺失校验；模型判断仅作分歧观察。声明选证与文档转录不是供应商签名或语义真值。无参考unrated；有作者参考也not_assessed，主观分数不自动填，母语盲评仍待完成。prepare与汇总只写仓库外新文件，评分原件不提交。
- fact-care-v5使用独立短版并保留V3/V4：V4实测源码022d47c中中文持久纠正完整4阶段完成；日语无答案空选正确，但review invalid_output、HTTP200安全兜底、退出1，8/8调用后停。最终V5只离线验证空选不模拟失忆/讲述来源、unit顺序/唯一编号/三种kind等契约，不声称真实修复。`retest_memory_generalization.py`最多两类各4调用、每阶段至多一次，任错停、不真实重写；日语选择cap仍8秒。新实际模型钩子只用于临时库回放，analysis_calls可真模型/回放，须看memory_stage_source，不与旧复用plan实测混淆。

- V5审查组装`fact-review-context-v1`在fact_presentation.py：V5回答/事实附加文字不变，旧完整组装保留review_prompt_v5_full；新短JSON结构引导+V5+记忆政策，weather_current或emotion_current/emotion_policy存在且相应semantic模式时才附工具政策。逐请求只读拼接不修改共享provider；权限/覆盖/证据/置信度/天气数值/epoch与调用预算不变。当前仅可信完整短句跳过，其余自由回复仍审查；这是缩减请求，不是已经实现语义按需审查，不能偷偷用中日关键词决定放行。
- retest_japanese_review.py --live固定旧日语无答案尾部：复用PR #46成功合成plan/空选，最多生成1+审查1，不重新理解/选证、不真实重写或重试；测试诊断仅固定错误类型，不能导出SDK原始异常/input。2026-11-18实2调用生成12.619秒、审查8.002秒timeout，HTTP503且未保存草稿；V5已真实尝试但未成功验证，旧invalid_output仍未排除，不能说已修复。旧失败/封存/母语盲评待完成保留，新空包另建不重绑。

- 当前用户优先级（2026-11-24）：先验证普通中日陪伴可用、人设基本一致、亲密度资格与自然体贴语气，不把旧研究性细节审计作为本轮体验阻塞。旧失败/封存/独立盲评待办不删，不冒称正式质量验收；本轮M6仍不开始。
- 默认REPLY_REVIEW_POLICY=contextual：仅companion+semantic回复、无记忆请求或已请求但检索确认无候选，且无选证/天气/有效情绪上下文时，普通自由回复生成一次直接返回prompt_only/calls0，角色背景问题同样靠角色Prompt，不做额外语义裁判或关键词门禁。能力上下文和full/audit仍走原审查/数据边界；不是关闭权限或宣称逐句可靠。full供明确旧审查回放；根conftest与japanese_memory_layers历史回放显式固定full，新默认测试在tests/practical。
- companion-closeness-v1只将服务器亲密度档位映射为语气控制，数字/钱包/联系方式不送模型。低分也温柔，熟悉后可更体贴/轻轻打趣，不自动确立关系或替代30/60/90资格与独立授权。smoke_companion.py --live固定4个合成普通场景，各1次生成、总4、任错停、无能力API/裁判/重试；临时库、关闭授权，原文/耗时保留，不以小样本宣称稳定性或消除幻觉。

- 2026-11-25 日语生命周期验证用同一玩家的三个全新会话与独立临时 SQLite。确认和纠正后真实召回通过，删除后的生成上下文为空，旧审查触发重写并被预算拦截。contextual 仅对 selection=empty 的成功空召回放开一次生成，保留命中、未决或失败选证以及工具审查。删除后的新路径仍待实测。
