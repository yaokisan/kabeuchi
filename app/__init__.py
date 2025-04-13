# app パッケージの初期化ファイル 
# Flaskアプリケーションをパッケージからインポートできるようにする
from flask import Flask
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv() # .envファイルから環境変数を読み込む

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static') 

# Supabaseクライアントの初期化
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables.")

supabase: Client = create_client(supabase_url, supabase_key) 