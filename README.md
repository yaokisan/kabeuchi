# KabeUchi - 思考の壁打ちアプリ

KabeUchiは、個人の思考深化とアイデア整理を支援するWebアプリケーションです。リッチテキストエディタで思考を記述し、複数のAIモデルとの対話やシームレスな音声入力を通じて、アイデアを効果的に発展させることができます。

## 機能

- **リッチテキストエディタ**: Googleドキュメントのような直感的な操作感でメモを作成・編集。自動保存機能付き。
- **マルチAIチャット機能**: 現在の文書を参照しながら複数のAIモデルと対話。
  - 対応モデル: Google Gemini, Anthropic Claude, OpenAI GPT
  - AIの応答はMarkdown形式で表示。
  - 過去のチャット履歴をすべて参照して応答。
  - チャット欄の幅はドラッグで調整可能。
  - 最後に選択したAIモデルを記憶。
- **音声入力機能**: マイクからの音声をリアルタイムでテキスト化し、エディタに挿入。
- **ドキュメント管理**: 作成したドキュメントの一覧表示、検索、並び替え、タイトル変更、複製、削除など。
- **手動保存**: 好きなタイミングでドキュメントを保存可能。
- **設定ページ**: 利用するAIモデルのAPIキーを設定・管理。

## スクリーンショット (例)

<!-- ![KabeUchi Screenshot](link/to/screenshot.png) -->
<!-- (将来的にスクリーンショットやGIFを追加) -->

## インストール方法

### 前提条件

- Python 3.8以上
- pip (Pythonパッケージマネージャー)

### セットアップ手順

1.  リポジトリをクローンまたはダウンロード:
    ```bash
    git clone <repository-url>
    cd KabeUchi
    ```

2.  仮想環境を作成して有効化:
    ```bash
    python -m venv venv
    # Linux/macOS
    source venv/bin/activate
    # Windows (Command Prompt/PowerShell)
    venv\Scripts\activate
    ```

3.  必要なパッケージをインストール:
    ```bash
    pip install -r requirements.txt
    ```

4.  APIキーの設定:
    以下のいずれかの方法でAPIキーを設定します。
    - **方法1: 設定ページから設定 (推奨)**
      1.  アプリケーションを起動後、サイドバーの「設定」メニューを開きます。
      2.  利用したいAIモデルのAPIキーを入力し、「APIキーを保存」ボタンをクリックします。
      3.  **重要:** 保存後、Flaskサーバーを再起動してください。
    - **方法2: `.env` ファイルを直接編集**
      プロジェクトルートに `.env` ファイルを作成し、以下のようにキーを記述します:
      ```dotenv
      SECRET_KEY=your_very_secret_random_string # Flaskのセッション管理用。必ず設定してください。
      OPENAI_API_KEY=your_openai_api_key
      GOOGLE_API_KEY=your_google_api_key
      ANTHROPIC_API_KEY=your_anthropic_api_key
      ```
      `SECRET_KEY` はランダムな文字列を設定してください。各APIキーは、利用するモデルのものだけで構いません。

## 使用方法

1.  アプリケーションを起動:
    ```bash
    python app.py
    ```

2.  Webブラウザで以下のURLにアクセス:
    ```
    http://127.0.0.1:5000
    ```

3.  UIを使用してドキュメントの作成、編集、AIとの対話、音声入力などを行います:
    -   初回アクセス時は、最後に編集していたドキュメント、または最新のドキュメントが開かれます。ドキュメントがない場合は新規作成されます。
    -   左側のサイドバーから新規ドキュメントを作成、最近のドキュメントを開く、AIモデルを選択、音声入力のオン/オフを切り替え、設定ページへ移動できます。
    -   中央のエディタでテキストを入力・編集します。内容は自動保存されますが、ヘッダーの手動保存ボタン💾でも保存できます。
    -   右側のチャットエリアでAIと対話します。送信は `Cmd+Enter` (Mac) または `Ctrl+Enter` (Windows) です。
    -   サイドバー下部の「ドキュメント管理」から、過去のドキュメントを管理できます。

## 主要機能の詳細

### リッチテキストエディタ

-   テキストの書式設定: 太字、イタリック、下線、取り消し線など
-   見出し、リスト、引用、コードブロック
-   自動保存機能 + 手動保存ボタン

### AIチャット機能

-   現在のドキュメント内容と過去のチャット履歴全体をコンテキストとして、選択したAIモデルと対話
-   サポートされているモデル (例):
    -   Google Gemini: `gemini-2.5-pro-exp-03-25`, `gemini-2.0-flash`
    -   Anthropic Claude: `claude-3.7-sonnet` (思考モードの有効/無効を選択可能)
    -   OpenAI ChatGPT: `gpt-4o`, `gpt-4.5-preview`
-   チャット欄はリサイズ可能
-   モデル選択は保持される

### 音声入力機能

-   マイク入力からリアルタイムで文字起こし
-   無音検出による自動発話終了
-   認識結果はエディタの現在のカーソル位置に挿入

### ドキュメント管理

-   最近更新したドキュメントの一覧表示 (サイドバー)
-   全ドキュメントのグリッド表示、検索、並び替え (管理ページ)
-   タイトル変更、複製、削除などの操作 (管理ページ)

### 設定

-   OpenAI, Google, Anthropic のAPIキーを設定・更新

## 技術スタック

-   **バックエンド**: Python, Flask, SQLAlchemy, Flask-SocketIO, python-dotenv
-   **フロントエンド**: HTML5, CSS3, JavaScript, Quill.js, marked.js, Socket.IO
-   **データベース**: SQLite
-   **外部API**: OpenAI API, Google Generative AI API, Anthropic API


## ライセンス

このプロジェクトは [MIT License](LICENSE) の下で提供されています。

## Renderでのデプロイについて

Renderでデプロイする際は、以下の点に注意してください：

1. `gunicorn`コマンドでは、`app:app`の形式で指定する必要があります。
2. `app.py`内にFlaskアプリケーションのインスタンスを`app`変数としてエクスポートする必要があります。

### トラブルシューティング

- `Failed to find attribute 'app' in 'app'`というエラーが発生した場合は、`app.py`内で`app`インスタンスがエクスポートされていることを確認してください。
- WebSocketを使用する場合は、Gunicornのワーカークラスとして`geventwebsocket.gunicorn.workers.GeventWebSocketWorker`を指定し、ワーカー数を1に設定する必要があります：
  ```
  gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app
  ```