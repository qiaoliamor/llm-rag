# M4 · 訂正できる気持ちの参考

[中文](../EMOTION.md) · [日本語](EMOTION.md)

## 中日自己申告・トリガー意味理解（2026-11-12、作業分岐）

既定EMOTION_UNDERSTANDING_MODE=semantic、入口app/emotion_understanding.py、政策multilingual-emotion-v1です。旧emotion.pyは明示legacy再現のみ、失敗時の代替ではなく、旧Prompt／出所資料と封存は維持します。

90点＋個別許可後、**毎ターン**本輪原文／ID、有限のrole/content/user ID窓、現参考labels/source/basisを現在のモデルへ送り、自己申告／否定、変化、陪伴要求と本輪希望を理解します。長期記憶庫・連絡先・天気snapshotは送りません。窓は各500字・最大12ターン／24件、本輪原文は別途2000字上限。完全な推定だけが通常3ターン間隔・6ターン窓・冷却2ターンです。早期信号でも冷却を越えず、理解＋推定は既定6秒の共有予算で各最大1回、再試行なし。失敗推定も冷却を消費します。

EmotionDecisionのuse_emotion/confidence/report/shift/request_analysis/preference/preference_sourceは厳密型・余分禁止。申告と希望は現在原文の一意で非空白の連続引用、ラベルは固定・最大3・重複／unknown混在禁止です。本人／他人、引用／仮定、否定、皮肉はPromptが判断し、文字一致や高信頼は意味の正しさを保証しません。「悲しくない」は「うれしい」の証拠ではありません。拒否／不明なら推定せず、モデルに許可や設定変更権限はありません。

「悲しくない、ただ疲れてる」と「我不是难过，只是累了」は共通のreport.labels=[tired]例です。具体JSONは[中国語仕様](../EMOTION.md)を参照。結果はstatus=self_report、source=model、basis=self_reportとモデル信頼度で、本人確認を偽りません。source=userは画面の手動訂正だけです。新しい明確な申告／変化がなければ手動訂正を守り、新しい否定で旧ラベルを復活させません。API不明時は旧モデル参考を注入せず、手動訂正は閲覧用に残せます。希望listen等は本輪の文脈だけ、保存設定や手動資料を自動変更しません。

完全推定はSemanticEstimateの既存5項目にstrict/extra=forbid・証拠重複禁止を追加、非unknownには窓内user IDが必要です。閾値未満はunknown、失敗は推定なしで会話継続。モデル境界epochを検査し、生成と原子確定成功後だけ新参考を保存。参考は会話内10分／6ターンで再利用しても延長せず、訂正／許可取消／削除で失効し、DBや長期記憶へ分析結果を自動保存しません。

回答文脈には必要ラベル／信頼度／出所／希望だけを渡し、原文引用・証拠ID／時刻は渡しません。申告のAPI intensity=.5は互換用の仮値で回答モデルへは送らず、confidenceも解釈信頼で心理確率ではありません。入口0.8とUI結果閾値は別、結果閾値未満はunknown。旧情緒返答の局所検査／回復文は完全な多言語化ではありません。実schema・主語／否定／皮肉／信号精度、F1／校正／口調／費用は未受入。合成を実理解評価とはせず、失敗も[記録](TEST_HISTORY.md)へ。

## 機能と構造化出力

親密度90と個別許可が必要です。app/emotion.pyのEstimate、調度、自己申告、Prompt投影とEmotionPane.tsxで構成します。既定は3会話ごと／直近6会話／冷却2会話／信頼度しきい値0.6。本人の明示申告や訂正を優先し、推定は診断や「本当の心」ではありません。

```json
{"labels":["anger","sadness"],"intensity":0.8,"confidence":0.9,"evidence_message_ids":["u1"],"response_strategy":"listen"}
```

上記は合成例です。Pydanticが列挙、1〜3ラベル、0〜1の有限強度／信頼度、最大12証拠ID、strategyを検査します。重複やunknown/neutral混在も拒否します。SDKのparse(response_format=Estimate)で構造要求を指定し、自然文を正規表現でJSONに切り出しません。Estimateは現在extra=forbidではなく、全追加項目を拒否する実装ではありません。

assess()で再検証し、IDは窓内userだけ、非unknownは証拠必須です。低信頼はunknown/ask、解析・証拠・通信失敗はunavailable/nullにし、古い推定を穴埋めに使いません。構造が正しくても意味判断が正しいとは限りません。

プログラムがsource／turn／observed_atを補い、本ターンへlabels/intensity/confidence/source/strategyだけを投影します。本人の申告には推定強度・確率を付けません。成功後は会話内で最長10分または6会話だけ再利用し、長期記憶にしません。

## 管理とテスト

GET /v1/emotion、PATCH/DELETE /v1/emotion/settings、PATCH/DELETE /v1/emotion/assessment。保存するのは設定と本人の明示した好みだけです。変更・新会話・削除・取り消しは短期文脈と推定を消去し、epochで処理中応答も撤回します。ロック中も取り消しや削除は可能です。

M4歴史値は284通過／20PGスキップ、前端36、一時PG161（重複）。構造・証拠・混合・否定・本人優先・訂正・CRUD・隔離・期限・失敗を検証しました。実際のF1、信頼度校正、適切な寄り添いのブラインド評価は未完了です。

日本語はモデル入力として渡せますが、自己申告／早期トリガーのルールは中国語中心です。日本語の皮肉・婉曲・省略・最新否定は独立検証が必要です。手動訂正を残し、不確実なら決めつけません。[適応計画](JAPANESE_LOCALIZATION.md)を参照してください。
