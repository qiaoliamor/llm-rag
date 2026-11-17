# プロジェクト文書

[中文](../README.md) · [日本語](README.md)

2026-11-17。M1〜M4の機能フローは実装済み、M5は品質検証中、M6は未着手です。日本語UI／基本対話の実装は日本語の全機能品質の合格を意味しません。

| 読む目的 | 文書 |
| --- | --- |
| 実行方法 | [プロジェクトREADME](../../README.ja.md) |
| 進捗・次の作業 | [計画](PLAN.md)・[TODO](../../TODOLIST.ja.md) |
| システム全体 | [アーキテクチャ](ARCHITECTURE.md) |
| M1 | [対話と画面](M1_CHAT.md) |
| M2 | [長期記憶](M2_MEMORY.md) |
| M3 | [天気の気遣い](WEATHER.md) |
| M4 | [気持ちの参考](EMOTION.md) |
| M5 | [評価・判定・受入条件](M5_EVALUATION.md) |
| 成長 | [親密度・アカウント・ギフト](RELATIONSHIP_GROWTH.md) |
| 日本語への適応 | [実装範囲と改善計画](JAPANESE_LOCALIZATION.md) |
| データ | [プライバシー](DATA_PRIVACY.md) |
| 結果・失敗・過去の原文 | [テスト記録](TEST_HISTORY.md) |

各モジュールに機能・設計・実装入口・検証範囲をまとめます。数値や仕様を変更したら日中文書を同期します。過去の合成応答は改訳せず固定Git版で共有します。逐字回帰に使う旧SCENE_PLACE_GROUNDINGとM3リンク互換入口は中国語の原文を共有します。開発時の正式ルールは[AGENTS.md](../../AGENTS.md)です。

PR #29/#30/#31はsquash済みです。日本語の独立品質とM5は未受入、M6は未着手です。

PR #29–#35はレビュー後squashでmainへ提供。中日情緒返答チェック／回復文は実装済みです。記憶は[M2](M2_MEMORY.md)、天気は[M3](WEATHER.md)、PR #34中日情緒申告／トリガーは[M4](EMOTION.md)へ。2026-11-13時点のmainへの提供記録です。旧失敗は[テスト](TEST_HISTORY.md)へ保持、独立品質受入とはしません。

本回の人物／記憶出所／場所返答の意味対応はPR #36レビュー後squashでmainへ提供。[M5](M5_EVALUATION.md)に設計、[テスト](TEST_HISTORY.md)に結果と失敗を集約します。

今回の日語口調／記憶v2・候補開発評価・母語盲評準備はPR #37レビュー後mainへ提供。実採点は評審待ち。[日本語対応](JAPANESE_LOCALIZATION.md)と[M2](M2_MEMORY.md)へ。

今回PR #38で提供する日語記憶四層回放は[M2](M2_MEMORY.md)、結果は[テスト](TEST_HISTORY.md)へ。脚本回放は母語独立人評の代わりでなく、実採点は引き続き未実施です。

PR #39レビューで日語回答v3／日中口調審査v2を提供。[日語対応](JAPANESE_LOCALIZATION.md)と[テスト](TEST_HISTORY.md)へ。母語独立盲評は未実施、言語横断未命中と歴史未検証を保持。

PR #40レビュー後squashで、日問日／中問中の記憶query・選択Prompt v3と別の同言語開発回放を提供。旧横断未命中は対象外観測として保存。[M2](M2_MEMORY.md)／[履歴](TEST_HISTORY.md)へ。Gemini実測と独立母語盲評は未完了。

PR #41レビュー提供で記憶共有予算を改善：短い独立v4と既定各6秒・合計12秒。実8呼出で選択は完了、返答漏判／503は保存。[M2](M2_MEMORY.md)と[履歴](TEST_HISTORY.md)へ。

PR #42レビュー後squash提供、未設定雑談の自由と明記記憶／正史の照合を区別し、旧犬句は現欠陥扱いにしません。[M2](M2_MEMORY.md)／[履歴](TEST_HISTORY.md)に方針変更・最初timeoutと後続2単例審査を保存。母語盲評／実品質の受入は増やしていません。
