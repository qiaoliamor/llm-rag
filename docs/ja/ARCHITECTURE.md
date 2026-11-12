# システム構成

[中文](../ARCHITECTURE.md) · [日本語](ARCHITECTURE.md)

既定天気semanticはweather_presentation.pyで生成Prompt追加→版付きWeatherAnalysisProvider審査→構造／証拠ID検査→純天気片段の数字検査→共通1回書き直し／locale回復へ進みます。中文単語は要求せず事実／表現を意味で分離。judgeなし／審査オフはweather_safe_fallback、非okも審査するため実呼出／遅延は別途検証が必要です。旧weather.py／companion／semantic_reviewと明示legacyは歴史再現用です。

天気はweather_understanding.pyで60点＋許可→本輪原文の構造化計画→原文／型検査→一意都市検索または本人選択都市→目的地時区の7日範囲→既存forecastと必要項目投影へ進みます。モデルは天気値・座標・IDを生成せず、理解／ツール境界でepochを確認します。旧weather.pyのデータ・数値／キャッシュ保護は維持し、言語legacyは明示再現のみ。[天気](WEATHER.md)を参照。

## 実装の分担

| 層 | 実装と入口 |
| --- | --- |
| UI | React + TypeScript + Vite、frontend/src/App.tsxとcomponents/ |
| 言語 | frontend/src/i18n.tsとlocales/ja.json、app/localization.py |
| API | FastAPI／Pydantic、app/main.py。Cookie所属、CSRF、同一会話の送信ロック |
| 返答 | dialogue.py／companion.py／reply_pipeline.py／semantic_review.py |
| 記憶 | SQLAlchemy、PostgreSQL + pgvector／ローカルSQLite。memory.py／memory_query.py／memory_routing.py |
| ツール | weather.pyのOpen-Meteo/mock、emotion.pyの構造化モデル推定 |
| 成長 | progression.pyのプロフィール・親密度・デモウォレット・冪等履歴 |
| 評価 | scripts/、evaluations/、app/*evaluation.pyとannotation_scoring.py |

省略したPython入口はapp/配下です。正史と場面はcharacters/shen_yan.json、shen_yan_scene.jsonです。

## 1ターンの流れ

ID／CSRF／ロック→親密度と個別許可→必要なら記憶検索・天気・気持ち→必要データだけを生成コンテキストへ→選択的な事実・口調チェック→最大1回書き直し→epoch再確認→候補記憶とポイントを同一トランザクションで確定→短期履歴を保存して返答。

通常の挨拶は第2モデルに依存させません。companionが既定、auditは過去の比較用です。日本語は列挙値localeと固定の言語指示で追加し、正史や過去の原文は変えません。個別の許可取り消しは処理中の古い応答を無効化します。

`./scripts/start.sh`で8000番へ起動し、生成物app/staticは直接編集しません。設定元はapp/config.py、秘密値はローカル.envのみです。モデル名は設定値であり利用可能性や無料枠の保証ではありません。

短期会話と天気キャッシュは単一プロセスのメモリです。端末間の復旧・複数インスタンス・実決済・正式公開は未実装です。日本語の追加範囲と未検証項目は[言語対応](JAPANESE_LOCALIZATION.md)、検証値は[テスト](TEST_HISTORY.md)を参照してください。

PR #29の文書整理は5a62fcaへsquash済みです。PR #30の基本日本語対応を本回squashでmainへ提供します。日本語の独立品質とM5は未受入、M6は未着手です。

## 多言語記憶理解

memory_understanding.pyが資格／許可後、DBを読む前に中日共通の構造化計画を作ります。必要な場合だけ最大20件を数値検索し、意味選択した5件／1200文字を生成へ渡します。共有4秒・分析最大2回で再試行しません。手動追加／修正も原文のメタデータをモデル解析し、失敗なら原文と日付不明を維持します。表／ベクトル版を変えず、既存の候補／ポイント取引へExactMemoryを渡します。[M2](M2_MEMORY.md)が仕様入口です。
