from flask import Flask, render_template, jsonify, request, redirect, url_for
# from flask_socketio import SocketIO # コメントアウト
from dotenv import load_dotenv
import os
from app.models.database import db, init_db
from app.controllers.document_controller import document_bp
from app.controllers.chat_controller import chat_bp
from app.controllers.speech_controller import speech_bp # handle_speech_recognition を削除
from app.controllers.settings_controller import settings_bp
import logging
import sys # logging用に追

# 環境変数の読み込み
load_dotenv()

# Flaskアプリケーションの初期化
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')

# デバッグログを有効化
app.logger.setLevel(logging.DEBUG)
# RenderのログにFlaskのログが出力されるようにハンドラを追加
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.info("デバッグログを有効化しました")

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wallbounce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# データベースの初期化
db.init_app(app)

# データベーステーブルの作成
# try:
#     with app.app_context():
#         app.logger.info("init_db() を呼び出します...")
#         init_db()
#         app.logger.info("init_db() が正常に完了しました。")
# except Exception as e:
#     app.logger.error(f"init_db() でエラーが発生しました: {e}", exc_info=True)

# SocketIOの初期化 - engineioのロギングを有効に
# socketio = SocketIO(app, 
#                    cors_allowed_origins="*", 
#                    logger=True, 
#                    engineio_logger=True,
#                    ping_timeout=60,
#                    ping_interval=25)
# 
# app.logger.info("SocketIOを初期化しました")

# 音声認識ハンドラの接続
# handle_speech_recognition(socketio)
# app.logger.info("音声認識ハンドラを登録しました")

# 各種ブループリントの登録
app.register_blueprint(document_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(speech_bp)
app.register_blueprint(settings_bp)

@app.route('/')
def index():
    """メインページを表示"""
    app.logger.info("ルート / が呼び出されました")
    try:
        result = render_template('index.html')
        app.logger.info("render_template('index.html') は成功しました")
        return result
    except Exception as e:
        app.logger.error(f"ルート / の render_template でエラー: {e}", exc_info=True)
        return "サーバー内部エラーが発生しました。", 500

@app.route('/healthz')
def health_check():
    """ヘルスチェック用エンドポイント"""
    app.logger.info("ルート /healthz が呼び出されました")
    return "OK", 200

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
    app.logger.info("アプリケーションを起動します...")
    # socketio.run(app, debug=True)
    app.run(debug=True) # 通常のFlask開発サーバー起動に変更 