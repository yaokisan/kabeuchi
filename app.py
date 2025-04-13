from flask import render_template, jsonify, request, redirect, url_for
# Flask, SocketIO, Supabaseは __init__ からインポート
from app import app, socketio, supabase
from dotenv import load_dotenv
import os

# コントローラーのブループリントをインポート
from app.controllers.document_controller import document_bp
from app.controllers.chat_controller import chat_bp
from app.controllers.speech_controller import speech_bp, handle_speech_recognition
from app.controllers.settings_controller import settings_bp

# 環境変数の読み込み (念のため)
load_dotenv()

# --- 設定 ---
# SECRET_KEY は SocketIO や Flask セッションで必要
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_dev_replace_in_prod')

# --- SocketIO ハンドラ登録 ---
# SocketIOインスタンスは __init__ からインポートしたものを使用
handle_speech_recognition(socketio)
print("音声認識ハンドラを登録しました (app.py)")

# --- ブループリント登録 ---
# 重複登録を避けるチェック
blueprints_to_register = [document_bp, chat_bp, speech_bp, settings_bp]
for bp in blueprints_to_register:
    # appインスタンスは __init__ からインポートしたものを使用
    if not app.blueprints.get(bp.name):
        app.register_blueprint(bp)
print("ブループリントを登録しました (app.py)")

# --- ルート定義 ---

@app.route('/')
def index():
    """メインページを表示"""
    # TODO: 認証状態を確認し、未ログインならログインページへリダイレクト
    # 例: session = supabase.auth.get_session() / if not session or not session.user: return redirect('/login')
    return render_template('index.html')

@app.route('/manage')
def manage_documents():
    """ドキュメント管理ページを表示"""
    # TODO: 認証状態を確認
    # 例: session = supabase.auth.get_session() / if not session or not session.user: return redirect('/login')
    return render_template('manage.html')

@app.route('/settings')
def settings():
    """設定ページを表示"""
    # TODO: 認証状態を確認
    # 例: session = supabase.auth.get_session() / if not session or not session.user: return redirect('/login')
    return render_template('settings.html')

# --- 認証関連ページルート ---

@app.route('/login')
def login_page():
    """ログインページを表示"""
    # TODO: 既にログイン済みならメインページへリダイレクト
    # 例: session = supabase.auth.get_session() / if session and session.user: return redirect('/')
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    """新規登録ページを表示"""
    # TODO: 既にログイン済みならメインページへリダイレクト
    # 例: session = supabase.auth.get_session() / if session and session.user: return redirect('/')
    return render_template('signup.html')

# --- Configuration Endpoint ---

@app.route('/config')
def get_config():
    """Frontendに必要な設定情報（Supabaseキーなど）を返す"""
    # 環境変数から Supabase の情報を取得
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY') # Anon key is public

    if not supabase_url or not supabase_key:
        # サーバーログにはエラーを出力
        print("Error: SUPABASE_URL or SUPABASE_KEY environment variables not set.")
        # クライアントには設定が見つからない旨を返す (500 Internal Server Error)
        return jsonify({"error": "Server configuration error"}), 500

    return jsonify({
        'supabaseUrl': supabase_url,
        'supabaseKey': supabase_key
        # 他にフロントエンドで必要な公開設定があればここに追加
    })

# --- End Configuration Endpoint ---

# --- アプリケーション実行 ---

if __name__ == '__main__':
    print("アプリケーションを起動します (app.py)...")
    # use_reloader=False は SocketIO+デバッグモードでの二重実行や初期化問題を回避するため推奨
    # socketio インスタンスは __init__ からインポートしたものを使用
    socketio.run(app, debug=True, use_reloader=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
    print("アプリケーションを終了します。") 