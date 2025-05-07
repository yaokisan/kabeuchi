from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os
from app.models.database import db, init_db
from app.controllers.document_controller import document_bp
from app.controllers.chat_controller import chat_bp
from app.controllers.speech_controller import speech_bp, handle_speech_recognition
from app.controllers.settings_controller import settings_bp

# 環境変数の読み込み
load_dotenv()

# Flaskアプリケーションの初期化
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
            
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wallbounce.db'
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

# 音声認識ハンドラの接続
handle_speech_recognition(socketio)
print("音声認識ハンドラを登録しました")

# 各種ブループリントの登録
app.register_blueprint(document_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(speech_bp)
app.register_blueprint(settings_bp)

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

if __name__ == '__main__':
    # デバッグモードでサーバー起動
    print("アプリケーションを起動します...")
    socketio.run(app, debug=True, port=5001) 