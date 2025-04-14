from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO # Import SocketIO
from dotenv import load_dotenv
import os

# --- Flask App Initialization ---
# Define 'app' here for Vercel's entrypoint detection
app = Flask(__name__,
            template_folder='app/templates', # Adjust path relative to app.py
            static_folder='app/static')     # Adjust path relative to app.py
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_dev_replace_in_prod')
print("Flask App initialized in app.py")

# --- Load Environment Variables ---
load_dotenv()

# --- Initialize Supabase Client (Imported) ---
# Import the initialized Supabase client from its dedicated module
try:
    from app.supabase_client import supabase
    print("Supabase client imported in app.py")
except ImportError as e:
    print(f"Error importing Supabase client in app.py: {e}")
    # Handle error appropriately, maybe raise it to stop the app
    raise e

# --- Initialize SocketIO ---
# Initialize SocketIO *after* Flask app instance is created
socketio = SocketIO(app,
                   cors_allowed_origins="*",
                   logger=True,
                   engineio_logger=True,
                   ping_timeout=60,
                   ping_interval=25)
print("SocketIO initialized in app.py")

# --- Import and Register Blueprints ---
# Ensure blueprints are imported *after* app exists
# Also, update blueprint imports if they rely on 'app' or 'supabase' being passed differently
try:
    from app.controllers.document_controller import document_bp
    from app.controllers.chat_controller import chat_bp
    from app.controllers.settings_controller import settings_bp

    blueprints_to_register = [document_bp, chat_bp, settings_bp]
    for bp in blueprints_to_register:
        if not app.blueprints.get(bp.name):
            app.register_blueprint(bp)
    print("ブループリントを登録しました (app.py)")

except ImportError as e:
    print(f"Error importing or registering blueprints in app.py: {e}")
    # Handle blueprint import errors
    raise e


# --- Route Definitions ---
# Define routes directly on the 'app' instance

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
    print("アプリケーションを起動します (app.py - local)...")
    # use_reloader=False は SocketIO+デバッグモードでの二重実行や初期化問題を回避するため推奨
    # socketio インスタンスは __init__ からインポートしたものを使用
    socketio.run(app, debug=True, use_reloader=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
    print("アプリケーションを終了します。") 