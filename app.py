from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os
from app.models.database import db, init_db
from app.controllers.document_controller import document_bp
from app.controllers.chat_controller import chat_bp
from app.controllers.settings_controller import settings_bp
from app.controllers.auth_controller import auth_bp

# 環境変数の読み込み
load_dotenv()

# Flaskアプリケーションの初期化
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
            
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
# Supabase への直接接続 URI（例: postgres://...）が無い場合、
# SQLAlchemy を実際には使わないが拡張の初期化だけを行うために
# インメモリ SQLite をフォールバックとして設定する。

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SUPABASE_DB_URL', 'sqlite:///:memory:')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# データベースの初期化
db.init_app(app)

# データベーステーブルの作成
with app.app_context():
    init_db()

# SocketIOの初期化 - engineioのロギングを有効に
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   logger=True, 
                   engineio_logger=True,
                   ping_timeout=60,
                   ping_interval=25)

print("SocketIOを初期化しました")

# 各種ブループリントの登録
app.register_blueprint(document_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(auth_bp)

@app.route('/')
def index():
    """メインページを表示"""
    return render_template('index.html')

@app.route('/manage')
def manage_documents():
    """ドキュメント管理ページを表示"""
    return render_template('manage.html')

@app.route('/settings')
def settings():
    """設定ページを表示"""
    return render_template('settings.html')

# ---------- 認証関連 ---------- #
# ローカル HTML ログインページ（Google ボタンを表示）

@app.route('/login')
def login_page():
    """トークン未保持時に表示されるシンプルなログインページ"""
    return render_template('login.html')

if __name__ == '__main__':
    # デバッグモードでサーバー起動
    print("アプリケーションを起動します...")
    socketio.run(app, debug=True, port=5001) 