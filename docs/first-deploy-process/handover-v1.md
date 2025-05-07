# **思考の壁打ちアプリ (Flask版) 開発引継書**

## 1. プロジェクト概要

-   **目的:** 個人の思考深化とアイデア整理支援。Streamlit版のUI/UX課題（特に音声入力）を克服し、スムーズな操作感と高機能性を両立させる。
-   **主要機能:**
    -   リッチテキストエディタ (Quill.js) によるメモ作成・自動保存
    -   AIチャット (Gemini, Claude, GPT) 機能 (ドキュメント内容＋チャット履歴連携)
    -   リアルタイム音声入力・文字起こし機能
    -   ドキュメント管理機能 (一覧、作成、編集、削除など)

## 2. 技術スタック

-   **バックエンド:** Python, Flask, SQLAlchemy, Flask-SocketIO, pydub, python-dotenv, openai, google-generativeai, anthropic
-   **フロントエンド:** HTML5, CSS3, JavaScript (ES6+), Quill.js, Socket.IO Client, Web Audio API
-   **データベース:** SQLite (`wallbounce.db`)
-   **外部API:** OpenAI Whisper, Google Gemini API, Anthropic API, OpenAI Chat API

## 3. 現在の実装状況

-   **バックエンド:**
    -   Flaskアプリケーション (`app.py`) セットアップ済み (テンプレート/静的フォルダ指定含む)。
    -   データベースモデル (`app/models/database.py`) 定義済み (`Document`, `ChatMessage`)。
    -   SQLAlchemyによるDB初期化済み。
    -   Flask-SocketIOによるWebSocket通信基盤構築済み。
    -   ドキュメント操作用API (`app/controllers/document_controller.py`) 実装済み。
    -   AIチャット用API (`app/controllers/chat_controller.py`) 実装済み (各モデル連携含む)。
    -   音声認識用WebSocketエンドポイント (`app/controllers/speech_controller.py`) 実装済み。
        -   `pydub` を用いたサーバーサイドでの音声形式変換処理を導入。
-   **フロントエンド:**
    -   メインページ (`index.html`), 管理ページ (`manage.html`) の基本レイアウト作成済み。
    -   CSS (`style.css`) による基本的なスタイリング適用済み。
    -   リッチテキストエディタ (`editor.js`) 初期化、自動保存、タイトル編集機能実装済み。
    -   AIチャット (`chat.js`) UI、メッセージ送受信、履歴読み込み機能実装済み。
    -   ドキュメント管理 (`manage.js`) UI、CRUD操作、検索・ソート機能実装済み。
    -   音声入力 (`speech.js`) :
        -   Web Audio APIによるマイク音声取得。
        -   MediaRecorderによる音声録音 (ブラウザ互換性考慮のフォールバック処理含む)。
        -   WebSocket経由での音声データ (Base64) 送信。
        -   音量監視による発話検出ロジック (UIフィードバック用)。
        -   サーバーからの認識結果受信・エディタ挿入処理。
        -   **課題:** リアルタイム処理のためのチャンク送信方式で実装中。
-   **設定:** `.env` ファイルによるAPIキー管理。

## 4. 直面している課題 (音声認識のリアルタイム性)

-   **現状:** クライアント (JS) は1秒ごとに音声チャンクを区切り、WebSocketでサーバー (Python) に送信。サーバーは受信したチャンクを `pydub` で `wav` に変換し、Whisper API で文字起こしを試みる。
-   **問題:**
    1.  **サーバー側デコードエラー:** `pydub` (内部の`ffmpeg`) が、単独の音声チャンク (特に `webm`, `ogg`) を完全なファイルとしてデコードできず、ヘッダーパースエラー (`CouldntDecodeError: ffmpeg returned error code: 183`, `EBML header parsing failed`) を起こし、Whisper API呼び出しに至らない。
    2.  **結果:** サーバーから連続してエラー (`transcription_error`) が返却され、クライアント側で「音声認識に失敗しました」と表示される。UI（フローティングウィンドウ）も不安定になる。
-   **要件:** リアルタイムに近い形での文字起こし表示を実現する必要があるが、現在のチャンク処理方式ではサーバー側でのデコードがボトルネックとなっている。

## 5. 試したこと・却下されたアプローチ

-   **閾値調整:** 発話検出の音量閾値 (`SILENCE_THRESHOLD`) を調整したが、根本原因ではなかった。
-   **クライアント形式変更:** クライアント録音形式を `wav` に試みたが、ブラウザ互換性で問題発生。フォールバック処理中の変数代入エラーも修正済み。
-   **サーバー拡張子変更:** 一時ファイルの拡張子を固定 (`.webm`, `.wav`) したが、ファイル形式エラーは解決せず。
-   **サーバー形式変換:** `pydub` を導入したが、チャンク単位のデコードに失敗。
-   **一括送信:** マイクオフ時に全音声データをまとめて送信する方式を検討したが、リアルタイム性の要件と合わず却下。
