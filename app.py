from flask import Flask
import logging
import sys
import os # os.getenv用に追加

# Flaskアプリケーションの初期化
app = Flask(__name__)

# ロギング設定 (以前と同様)
app.logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

app.logger.info("--- Minimal App Start ---") # 最初にログが出るか確認

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key_minimal')

@app.route('/')
def index():
    app.logger.info("ルート / (minimal) が呼び出されました")
    return "Minimal App Root OK"

@app.route('/healthz')
def health_check():
    app.logger.info("ルート /healthz (minimal) が呼び出されました")
    return "Minimal App Health OK"

if __name__ == '__main__':
    # この部分は Render では使われないがローカルテスト用に残す
    app.run(debug=True)

app.logger.info("--- Minimal App End of File ---") # ファイルの最後まで到達するか確認 