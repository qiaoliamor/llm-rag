# 心語 · Persona RAG

[中文](README.md) · [日本語](README.ja.md)

女性プレイヤー向けゲームを想定した、オリジナルキャラクターとの対話プロトタイプです。React + TypeScript／FastAPI、Gemini・OpenAI・mock、確認式の長期記憶、天気の気遣い、訂正できる気持ちの参考を備えています。

M1〜M4の機能フローは実装済み、M5は品質検証中、M6は未着手です。日本語UI・基本対話、中日記憶・天気・情緒自己申告／信号の意味入口を追加。権限・調度・データはコードで検査し、実理解品質は独立検証が必要です。情緒の残る返答チェック等は未完了。[天気](docs/ja/WEATHER.md)と[情緒設計](docs/ja/EMOTION.md)へ。

- [日本語ドキュメント](docs/ja/README.md)／[言語対応の設計と改善計画](docs/ja/JAPANESE_LOCALIZATION.md)
- [TODO](TODOLIST.ja.md)／[計画](docs/ja/PLAN.md)／[テストと失敗記録](docs/ja/TEST_HISTORY.md)
- 開発前に正式な[AGENTS.md](AGENTS.md)を読んでください。[日本語の貢献案内](CONTRIBUTING.ja.md)もあります。

## ローカル起動

Python 3.11+、uv、Node.js 22.12+、npmが必要です。PostgreSQL/pgvectorはDocker Desktopを推奨します。クローンしたディレクトリで実行します。

```sh
# 初回のPostgreSQL設定前にDocker Desktopを起動。設定済みなら省略
./scripts/setup-memory-db.sh
./scripts/start.sh
```

[http://127.0.0.1:8000/](http://127.0.0.1:8000/)を開き、上部の「语言 / 言語」で「日本語」を選びます。同じアプリを切り替えるため、別サーバーや別のユーザーDBは不要です。言語選択は保存されますが、履歴・記憶・プロフィールの元の文章は自動翻訳しません。停止はCtrl+C。初回依存インストールにはネット接続が必要です。

ローカル.envへGEMINI_API_KEYをエディターで設定し、変更後は再起動します。キーをチャットやGitへ出さないでください。既定のモデル名はgemini-3.5-flash-liteという設定値で、利用権限・無料枠・提供継続を保証しません。GEMINI_MODELで上書きできます。

完全オフラインならCHAT_PROVIDER=mockとWEATHER_PROVIDER=mockを選び、必要なら独立SQLiteを使います。デモは実モデル／実天気の評価ではありません。OpenAIを使う場合はCHAT_PROVIDER=openaiと専用のOPENAI_API_KEYをローカル設定します。

## 操作・データ

トップはキャラクター選択／アカウントのみ。沈硯と話せます。親密度30で記憶、60で天気、90で気持ちの機能資格を得ますが、利用には個別許可が必要です。未解放機能名はトップに表示せず、解放時だけ短い案内を出し、後から機能名を押して説明を読めます。基本会話は常に利用できます。

ギフトはデモコインで購入して贈ります。実際の支払い・円・請求はありません。正式ログインや端末間復旧は未実装です。記憶は本人確認後にだけ必要時検索し、修正・削除できます。文字特徴ベクトルは学習済み意味埋め込みではなく、自動抽出も保守的です。Cookieを消すとIDを自動復旧できません。

普通の光・音・仕草は物語として描写できますが、人物設定、本人の経験、現実の天気を作りません。気持ちは推定であり診断ではありません。モデル／天気提供者への必要データ送信は[プライバシー](docs/ja/DATA_PRIVACY.md)を確認してください。

## CLIでの検証

```sh
npm ci --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend -- --run
uv run --frozen pytest -q
uv run --frozen python scripts/check_sealed_evaluation.py --validate-content
```

PG専用テストはscripts/test_postgres.pyが新しい一時DBを作って削除します。実プレイヤーDBを消去してテストしないでください。実APIの--liveは通常の自動検証に付けません。今回の結果・初回失敗・未検証項目は[テスト記録](docs/ja/TEST_HISTORY.md)へ集約します。

MITライセンス。提出できるのはコード、文書、権利のある素材と合成データのみです。.env、キー、DB、ログ、実会話・記憶、評価原本、実行エクスポートは提出しません。正式公開、支払い、完全アカウント削除、バックアップ消去、多インスタンスは未実装です。

記憶の意味対応：既定MEMORY_UNDERSTANDING_MODE=semanticで中日共通の必要時計画、原文候補、日付関係、根拠選択を使います。許可後の各ターンは必要な短期原文を追加で現在モデルへ送り、必要時だけDBを検索します。手動追加／修正も解析し、失敗なら原文と日付不明を維持。個別確認と本人／削除保護は不変です。legacyは明示再現用で、実際の精度・遅延・費用は未受入です。[M2](docs/ja/M2_MEMORY.md)を参照してください。
