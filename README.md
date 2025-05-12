# KabeUchi - 思考の壁打ち×AI ワークベンチ

## 🚨 既知の不具合 / Bug Report

以下は 2025-05-08 時点で把握している主要な不具合です。

| ID | 内容 | 対応状況 |
| --- | --- | --- |
| `chat-504` | 本番環境で AI チャット要求がタイムアウト (504) しやすい | Gemini 呼び出しの負荷軽減パッチを適用修正中 |
| `mobile-ui` | スマホ表示でレイアウトが崩れる／最適化未実装 | 未着手（改善案を検討中） |
| `session-issue` | 一定時間経過後、ログイン状態に見えてもドキュメントが読み込めなくなる | 未着手 (原因調査中) |
| `doc-instability` | ドキュメントの保存や読み込みが不安定（エラー発生、リロード失敗など） | 未着手 (再現手順確認中) |
| `performance-slow` | アプリケーション全体の動作が非常に遅い | 未着手 (ボトルネック調査予定) |

> Issue 追加やプルリクエストは大歓迎です。📝  [Bug Tracker →](https://github.com/yaokisan/kabeuchi/issues)

KabeUchi は、リッチテキストエディタでのメモ書きと複数 AI モデルとの対話を 1 つの画面で完結させる **「思考の壁打ちアプリ」** です。Supabase をバックエンドに採用し、Google アカウントによる認証、ドキュメント管理、画像付きチャット、Web 検索付き AI 応答など、知的生産を支える多彩な機能を備えています。

> 🎙️ 音声入力には Chrome 拡張 **Voice In** の併用が便利です。後述の「Voice In 連携」を参照してください。

---

## 目次

1. [主な機能](#主な機能)
2. [スクリーンショット](#スクリーンショット)
3. [インストール](#インストール)
4. [環境変数と設定](#環境変数と設定)
5. [使い方](#使い方)
6. [Voice In 連携](#voice-in-連携)
7. [技術スタック](#技術スタック)
8. [デプロイ](#デプロイ)
9. [ライセンス](#ライセンス)

---

## 主な機能

### エディタ

- Quill.js 採用の **リッチテキストエディタ**。
  - 見出し・箇条書き・コードブロックほか一般的な装飾に対応
  - 自動保存 + 💾 手動保存ボタン
  - フォントサイズを 50–150 % の範囲で変更可能
- ドキュメントは Supabase の **`documents` テーブル** に保存され、どの端末からでも同期

### AI チャット

- 右ペインに **チャット欄**。現在編集中のドキュメント全文と過去の会話をコンテキストとして送信
- 対応モデル（2025-05 時点）
  - Google Gemini: `gemini-2.0-flash`, `gemini-2.5-pro-exp-03-25`, `gemini-2.5-pro-preview-05-06`
  - Anthropic Claude: `claude-3-7-sonnet-20250219`（思考モード On/Off 切替可）
  - OpenAI: `gpt-4o`, `gpt-4.5-preview`, `o3`
- **画像添付**: PNG/JPEG 画像をドラッグ or 📷 ボタンで添付し、Vision 対応モデルへ送信
- **Web 検索 (Gemini)**
  - 「Web検索を有効にする」チェックで、Gemini が DuckDuckGo 経由の検索を実行し最新情報を回答
  - 参照 URL をリストで表示
- チャット欄はドラッグで幅＆高さを可変、履歴リセットもワンクリック

### ドキュメント管理

- `/manage` ページで全ドキュメントを **カード UI** で一覧
- タイトル変更・複製・削除、検索、並び替え (更新順 / タイトル順)

### 認証 / 設定

- **Google アカウントでログイン**（Supabase OAuth Flow）
- 設定ページから OpenAI / Google / Anthropic の **API キーを安全に保存**
  - `.env` が書き込み不可のホスティング環境でもランタイム変数に退避

---

## スクリーンショット

<!-- 将来的に GIF や画像を追加 -->

---

## インストール

### 前提

- Python 3.9 以上
- `pip`, `virtualenv` もしくは `python -m venv`

### 手順

```bash
# 1. クローン
$ git clone https://github.com/yaokisan/kabeuchi.git && cd kabeuchi

# 2. 仮想環境 (推奨)
$ python -m venv venv
$ source venv/bin/activate  # Windows は venv\Scripts\activate

# 3. 依存関係
(venv)$ pip install -r requirements.txt

# 4. 環境変数 (.env) を準備
(venv)$ cp .env.example .env  # サンプルが無い場合は手動で作成
# 必須項目については後述

# 5. 起動
(venv)$ python app.py
# デフォルトで http://127.0.0.1:5001 が立ち上がります
```

---

## 環境変数と設定

下記は最小構成の例です。**いずれもダッシュボードで発行した値に置き換えてください。**

```dotenv
# Flask
SECRET_KEY=your_random_secret

# Supabase
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_JWT_SECRET=eyJhbGciOiJIUzI1NiIsInR5cCI6...
# 任意: OAuth コールバック URL を固定したい場合
# SUPABASE_REDIRECT=https://example.com/auth/callback

# AI ベンダー API キー（使用するものだけで可）
OPENAI_API_KEY=
GOOGLE_API_KEY=
ANTHROPIC_API_KEY=
```

API キーは **アプリ起動後に「設定 › API キー設定」から入力**→保存→サーバー再起動でも設定できます。

---

## 使い方

1. ブラウザで `http://127.0.0.1:5001` にアクセスし、Google でログイン
2. 左サイドバーの **「新規ドキュメント」** でメモ書きを開始
3. 右ペインの **AI チャット** へ質問・要約依頼などを送信（`Cmd/Ctrl + Enter`）
4. 必要に応じて **画像を添付**、または Gemini の **Web 検索** を ON
5. 出力された Markdown を中央エディタへコピペ→さらに肉付け…という「壁打ち」を繰り返します

---

## Voice In 連携

Chrome 拡張 [Voice In](https://chrome.google.com/webstore/detail/voice-in-voice-typing/pjnefijmagpdjfhhkpljicbbpicelgko) を使うと、KabeUchi のエディタ／チャット入力欄のどちらにも **リアルタイム音声入力** が可能です。

1. Chrome ウェブストアから **Voice In** をインストール
2. 拡張機能の設定で **"Allow voice typing on all text fields"** を有効化
3. KabeUchi の入力欄をクリックし、拡張アイコンをクリック (もしくは設定したショートカット)
4. マイクに向かって話すとテキストが入力 → AI チャットで文章構造化 → コピーしてエディタに貼り付け、というワークフローが快適に行えます

> ヒント: Voice In の **"Auto-punctuation"** 機能を ON にすると句読点が自動で挿入され、後工程の編集コストがさらに下がります。

---

## 技術スタック

| 層 | 使用技術 |
| --- | --- |
| フロントエンド | HTML5, CSS3, JavaScript, Quill.js, marked.js, Socket.IO |
| バックエンド | Python, Flask, Flask-SocketIO, python-dotenv |
| データベース | Supabase (PostgreSQL) + SQLAlchemy 互換モデル |
| AI API | Google Generative AI (Gemini), OpenAI, Anthropic |
| その他 | DuckDuckGo Search API, JWT (認証), Vercel Serverless |

---

## デプロイ

### Render

WebSocket を利用するため、下記の Gunicorn コマンドでデプロイしてください。

```bash
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app
```

- モジュール名 (`app`) と アプリインスタンス (`app`) が一致していることを確認

### Vercel (Serverless)

リポジトリ直下の `vercel.json` と `api/index.py` は Vercel Python Runtime 用の設定です。特別な手順は不要で、AI API キーと Supabase 関連の環境変数をダッシュボードに登録すればデプロイできます。

---

## ライセンス

本リポジトリは MIT License で公開されています。