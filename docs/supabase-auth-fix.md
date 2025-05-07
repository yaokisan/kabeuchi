● SQLite で動いていた Flask アプリを Supabase（Postgres＋Auth）に全面移行する作業を開始
　– Supabase クライアント (`supabase_client.py`) 追加
　– `app/models/database.py` を Supabase CRUD ヘルパ中心に書き換え
　– SQLAlchemy 依存箇所（DocumentController／ChatController）を Supabase API へ置換
　– requirements に `supabase`, `psycopg2-binary` 追加

● API 変更後に CRUD とチャット履歴を cURL で確認し動作 OK
　– 旧 SQLite データを `scripts/migrate_sqlite_to_supabase.py` で Supabase へ移行
　– PostgREST error 対応で `.single()` を外し、0 行なら None / [] を返す実装に修正
　– マイグレーションスクリプトは `postgrest.exceptions.APIError` で例外処理

● GitHub 運用：`feature/supabase-migration` ブランチを作成 → PR → `main` へマージ
　– 次の作業用に `feature/supabase-auth` ブランチを作成

● Supabase Auth（Google）組込み計画を策定
　– Google OAuth、RLS、シンプル UI の方針確認
　– `PyJWT` 追加、`auth_controller.py` 作成（/auth/login, /auth/callback, `require_auth` デコレータ）
　– `/login` ページと `auth.js`（トークン保存 + fetch ラッパ）を追加
　– Document / Chat API に `@require_auth` を付与し `user_id` を保存
　– `/login` ルートを `app.py` に追加

● Google 側設定不足で 400 → `redirect_uri_mismatch` を解決
　– Google OAuth redirect URI に `https://<project>.supabase.co/auth/v1/callback` を追加
　– `/auth/callback` で最小 HTML を返しトークン保存後 `/` へリダイレクト

● 動作確認
　– ブラウザの Local Storage に `access_token` が保存され、API 呼び出しでも Bearer 付与が確認できた
　– ログインページ表示 → Google 同意 → アプリ復帰まで動作し、再ログイン要求も出ないことをユーザが確認

● ChatController 改修（Gemini Function Calling & Web検索／レスポンス改善）
　– `duckduckgo-search` パッケージを導入し `DDGS` を使った Web 検索ツールを実装
　– Gemini の Function Calling で検索クエリを自動発行し、検索結果を整形して AI へ再入力
　– API レスポンスに `sources`（タイトル、URL、ドメイン）を含め、フロントに表示可能に
　– AI 応答先頭に意図せず付与される `ny` 文字列を検出し自動で除去

結果：Supabase DB 移行＋Google 認証導入に加え、ChatController の検索連携・レスポンス品質向上を完了。
