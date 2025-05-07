# **思考の壁打ちアプリ (Flask版) 開発引継書 (改訂版 v2)**

## 1. プロジェクト概要 (変更なし)

-   **目的:** 個人の思考深化とアイデア整理支援。Streamlit版のUI/UX課題（特に音声入力）を克服し、スムーズな操作感と高機能性を両立させる。
-   **主要機能:**
    -   リッチテキストエディタ (Quill.js) によるメモ作成・自動保存
    -   AIチャット (Gemini, Claude, GPT) 機能 (ドキュメント内容＋チャット履歴連携)
    -   **リアルタイム音声入力・文字起こし機能 (Whisper API)**
    -   ドキュメント管理機能 (一覧、作成、編集、削除など)

## 2. 技術スタック (変更なし)

-   **バックエンド:** Python, Flask, SQLAlchemy, Flask-SocketIO, pydub, python-dotenv, openai, google-generativeai, anthropic
-   **フロントエンド:** HTML5, CSS3, JavaScript (ES6+), Quill.js, Socket.IO Client, Web Audio API, MediaRecorder API
-   **データベース:** SQLite (`wallbounce.db`)
-   **外部API:** OpenAI Whisper, Google Gemini API, Anthropic API, OpenAI Chat API

## 3. 実装状況 (2024/MM/DD 現在)

-   **バックエンド (`app.py`, `app/controllers/*`, `app/models/*`):**
    -   基本的なFlaskアプリケーション、DBモデル (`Document`, `ChatMessage`)、DB初期化は完了済み。
    -   ドキュメント操作API (`document_controller.py`)、AIチャットAPI (`chat_controller.py`) は実装済み。
    -   **音声認識 (`speech_controller.py`):**
        -   WebSocket (`Flask-SocketIO`) による音声データ送受信基盤を構築。
        -   クライアントから送信された音声チャンク (Base64エンコードされた `audio/webm;codecs=opus` 形式が主) を接続(`sid`)ごとにバッファリング (`audio_buffers`)。
        -   録音停止イベント (`'end_audio'`) 受信時に、結合した音声データを `pydub` で `wav` に変換し、Whisper API で文字起こしする処理 (`handle_combined_audio`) を実装済み。**この基本フローは正常に動作し、文字起こし結果 (`transcription_response` イベント) が返却されることを確認済み。**
        -   **リアルタイム処理の実装:**
            -   クライアントからのチャンク受信時刻を記録 (`silence_trackers`)。
            -   一定時間 (`SILENCE_DETECT_SECONDS`) チャンク受信が途切れた場合に中間結果を処理・送信 (`'interim_transcription'` イベント) するためのバックグラウンドタスク (`silence_detection_task`) を `socketio.start_background_task` と `socketio.sleep` を用いて実装。
            -   中間処理と最終処理の共通ロジックとして `process_audio_segment(sid, is_final)` を実装。
            -   処理の同時実行を防ぐためのフラグ (`processing_flags`) を導入。
-   **フロントエンド (`app/static/js/*`, `templates/*.html`):**
    -   メインページ (`index.html`), 管理ページ (`manage.html`) の基本レイアウト、CSS (`style.css`) は完了済み。
    -   リッチテキストエディタ (`editor.js`)、AIチャット (`chat.js`)、ドキュメント管理 (`manage.js`) の基本機能は実装済み。
    -   **音声入力 (`speech.js`):**
        -   マイク音声取得 (Web Audio API)、録音 (MediaRecorder API - `audio/wav` を試行し、非対応なら `audio/webm` などにフォールバックする処理込み)。
        -   音量監視による発話検出 (`isSpeaking` フラグ管理) を実装済み。
        -   発話中 (`isSpeaking === true`) の音声チャンクは `'audio_chunk'` イベントでサーバーに送信 (MIMEタイプも送信)。
        -   非発話中 (`isSpeaking === false`) の音声チャンクはローカル (`audioChunks`) に一時保存。
        -   録音停止 (`stopSpeechRecognition`) 時に、ローカルに溜めたチャンクを最後の `'audio_chunk'` として送信後、`'end_audio'` イベントを送信する処理を実装済み。
        -   サーバーからの中間結果イベント (`'interim_transcription'`) を受信し、フローティングウィンドウ (`#speech-text`) の内容を更新するリスナー (`socket.on('interim_transcription', ...)`）を実装済み。
        -   サーバーからの最終結果イベント (`'transcription_response'`) を受信し、エディタへの挿入とオーバーレイ非表示を行う処理を実装済み。
-   **設定:** `.env` ファイルによるAPIキー管理。

## 4. デバッグ履歴と現在の課題

-   **[解決済] サーバー側デコードエラー (`CouldntDecodeError`)**
    -   **原因:** 音声チャンクを個別に `pydub` で処理しようとしていた。
    -   **対策:** サーバー側で接続ごとにチャンクをバッファリングし、録音停止 (`'end_audio'`) 時に結合して処理する方式に変更。クライアント側も対応。
-   **[解決済] 文字起こし結果の重複**
    -   **原因:** クライアント側のチャンク送信ロジックにより、同じ音声データが複数回サーバーに送られていた。
    -   **対策:** クライアントのチャンク管理ロジックを修正 (発話中は送信のみ、非発話中はローカル保存のみ。停止時にローカル保存分のみを送信)。
-   **[現在進行中] リアルタイム表示が機能しない**
    -   **目標:** マイクオン中に話している内容が、無音区間などで区切られ、フローティングウィンドウに逐次表示されるようにしたい。
    -   **実装アプローチ:** サーバー側で無音時間を検出し、中間的な文字起こし結果 (`interim_transcription`) をクライアントに送信。クライアントはそれを受けてUIを更新。
    -   **試した実装:**
        1.  `threading.Timer` を使用した無音検出 → 失敗 (タイマーが発火せず)。
        2.  `socketio.start_background_task` と `socketio.sleep` を使用した無音検出タスク (`silence_detection_task`) → **現在この実装を採用中**。
    -   **現在の状況:**
        -   マイクオン中はフローティングウィンドウに「認識中...」と表示されたまま、テキストは更新されない。
        -   サーバー側のログを確認しても、期待される無音検出のログ (`★★★ 無音検出 ★★★`) や中間結果送信のログ (`interim_transcription を送信`) が **出力されていない**。
        -   マイクオフ時に最終結果 (`'transcription_response'`) が送信され、エディタに全文が挿入される動作は正常に機能している。
    -   **原因の推測:** サーバー側の `silence_detection_task` が期待通りに開始/実行されていない、またはタスク内の無音状態を検知するロジック (`time.time() - last_chunk_time >= SILENCE_DETECT_SECONDS`) が正しく評価されていない可能性が高い。
