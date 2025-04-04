# **思考の壁打ちアプリ (Flask版) 開発引継書 (v3)**

## 1. プロジェクト概要

-   **目的:** 個人の思考深化とアイデア整理支援。リアルタイムでの音声入力によるスムーズなテキスト化を実現する。
-   **最重要要件:** **マイクで話している内容が、ほぼリアルタイムで画面に文字表示されること。**
-   **主要機能 (実装済/目標):**
    -   リッチテキストエディタ (Quill.js) によるメモ作成・自動保存 (実装済)
    -   AIチャット (Gemini, Claude, GPT) 機能 (実装済)
    -   **[要改善]** リアルタイム音声入力・文字起こし機能
    -   ドキュメント管理機能 (実装済)

## 2. 技術スタック (現状)

-   **バックエンド:** Python, Flask, SQLAlchemy, Flask-SocketIO, pydub, python-dotenv, openai, google-generativeai, anthropic
-   **フロントエンド:** HTML5, CSS3, JavaScript (ES6+), Quill.js, Socket.IO Client, Web Audio API, MediaRecorder API
-   **データベース:** SQLite (`wallbounce.db`)
-   **外部API:** OpenAI Whisper, Google Gemini API, Anthropic API, OpenAI Chat API

## 3. v2 -> v3での主な変更点と経緯

-   **目標:** v2引継書記載の「リアルタイム表示が機能しない」問題を解決する。
-   **実装試行:**
    1.  **無音検出タスクの実装:**
        -   サーバー側 (`app/controllers/speech_controller.py`) で、`Flask-SocketIO` のバックグラウンドタスク (`socketio.start_background_task`, `socketio.sleep`) を使用し、接続ごとに無音状態を監視する `silence_detection_task` を実装。
        -   無音状態 (例: 2秒間音声チャンクの受信がない) を検出すること自体は成功した。ログ (`★★★ 無音検出 ★★★`) の出力を確認。
    2.  **中間音声データの文字起こし:**
        -   無音検出時に、それまでにバッファリングされた音声チャンク (`audio_buffers`) を結合し、`handle_combined_audio` 関数 (内部で `pydub` と Whisper API を使用) で文字起こしを試みた (`process_audio_segment(sid, is_final=False)` の呼び出し)。
        -   **問題発生:** フロントエンドから送られてくる中間的な音声チャンク (例: `audio/webm;codecs=opus`) を結合したデータは、**完全なファイル形式 (ヘッダー等) を持たない**ため、`pydub` (FFmpeg) がファイルを正しく解析できず、`Invalid data found when processing input` や `Unknown input format` といったエラーが頻発。中間的な文字起こしに失敗した。
        -   **原因:** `pydub` および Whisper API は、基本的に**完全な音声ファイル**を入力として想定しているため、ストリーミングされる断片的なチャンクの処理には適していない。
    3.  **エラー回避策:**
        -   `pydub` エラーを避けるため、`silence_detection_task` 内での中間的な文字起こし処理 (`process_audio_segment(is_final=False)`) の呼び出しをコメントアウト。
        -   これにより、マイクオン中は無音検出ログは出るものの、文字起こしは実行されなくなった。
    4.  **タスク停止処理の改善:**
        -   マイクオフ (`end_audio`) 後も無音検出タスクが不要に動作し続ける問題があったため、`end_audio` イベントハンドラ内でタスク停止フラグ (`silence_detection_running[sid] = False`) に加え、タスクのループ条件に関わる `last_chunk_times` 辞書からも該当 `sid` を削除するように修正。これにより、録音終了後にタスクが停止することを確認。

## 4. 現在の実装状況 (v3開始時点)

-   **バックエンド (`app/controllers/speech_controller.py`):**
    -   SocketIO 接続ごとに音声チャンクをバッファリング。
    -   `audio_chunk` 受信時に最終受信時刻 (`last_chunk_times`) を更新。
    -   `silence_detection_task` がバックグラウンドで動作し、無音を検出するが、**中間的な文字起こし処理は実行しない**。
    -   `end_audio` 受信時に、バッファ内の**全音声データ**を `handle_combined_audio` で処理し、Whisper API で文字起こしを実行。この処理は**成功**する。
    -   文字起こし結果 (`transcription_response`) をクライアントに送信。
-   **フロントエンド (`app/static/js/speech.js`):**
    -   マイクオン中は `audio_chunk` をサーバーに送信。
    -   `'interim_transcription'` イベントリスナーは存在するが、サーバーからこのイベントが発行されることはない。
    -   `'transcription_response'` イベントを受信し、エディタに最終的な全文を挿入する。
-   **ユーザー体験:**
    -   マイクオン中はフローティングウィンドウに「認識中...」と表示されたまま変化しない。
    -   マイクオフ時に、録音されていた全ての音声が一括で文字起こしされ、エディタに挿入される。

## 5. 最大の課題と次期開発への推奨事項

-   **最大の課題:** **リアルタイム性の欠如。** 現在のアーキテクチャ (ファイルベースの Whisper API + pydub) では、ストリーミングされる音声チャンクを逐次処理してリアルタイムで文字表示することが原理的に困難。
-   **推奨事項:** **リアルタイム音声認識に対応した専用APIサービスへの移行を強く推奨する。**
    -   **候補:**
        -   **Google Cloud Speech-to-Text (StreamingRecognizeRequest):** 高精度でリアルタイム性に優れる。WebSocket や gRPC でのストリーミングに対応。
        -   **AssemblyAI (Real-Time Transcription):** WebSocket ベースでリアルタイム認識機能を提供。話者分離などの付加機能も。
        -   その他、AWS Transcribe Streaming, Azure Speech to Text (Real-time) など。
    -   **必要な変更:**
        -   選択したAPIサービスのアカウント作成、APIキー設定。
        -   **バックエンド (`app/controllers/speech_controller.py`):**
            -   `pydub` と `openai` (Whisper) への依存を削除 (またはAPI併用構成にする)。
            -   選択したAPIの Python SDK を導入。
            -   SocketIO でクライアントから音声チャンクを受信したら、そのままリアルタイムAPIにストリーミング送信するロジックを実装。
            -   APIから返される中間結果・最終結果を SocketIO でクライアントに送信 (`'interim_transcription'`, `'transcription_response'` イベントを活用)。
        -   **フロントエンド (`app/static/js/speech.js`):**
            -   `MediaRecorder` の設定 (タイムスライス間隔など) をAPIの要件に合わせて調整する必要があるかもしれない。
            -   サーバーからの中間結果 (`'interim_transcription'`) を受け取り、フローティングウィンドウの表示を更新する処理を確実に動作させる。

この移行により、当初の目標であったリアルタイムでの文字起こし表示が実現可能になると考えられる。 