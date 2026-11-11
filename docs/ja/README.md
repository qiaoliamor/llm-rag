# プロジェクト文書

[中文](../README.md) · [日本語](README.md)

2026-11-11。M1〜M4の機能フローは実装済み、M5は品質検証中、M6は未着手です。日本語UI／基本対話の実装は日本語の全機能品質の合格を意味しません。

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

PR #29の文書整理は5a62fcaへsquash済みです。PR #30の基本日本語対応を本回squashでmainへ提供します。日本語の独立品質とM5は未受入、M6は未着手です。
