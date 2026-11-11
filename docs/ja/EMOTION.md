# M4 · 訂正できる気持ちの参考

[中文](../EMOTION.md) · [日本語](EMOTION.md)

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
