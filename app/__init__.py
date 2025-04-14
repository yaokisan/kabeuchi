# app/__init__.py
# This file can be empty or just contain package-level comments.
# Initializations are moved to app.py or specific modules.
print("app package loaded (__init__.py)") # Optional: add a print statement for debugging Vercel imports

# app パッケージの初期化ファイル 
# Flaskアプリケーションをパッケージからインポートできるようにする
from flask import Flask
from flask_socketio import SocketIO # Import SocketIO
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv() # .envファイルから環境変数を読み込む

# Initialize Flask App
app = Flask(__name__,
            template_folder='templates', # Relative to app package directory
            static_folder='static')     # Relative to app package directory
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_dev_replace_in_prod')
print("Flask App initialized in app/__init__.py")

# Initialize Supabase Client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be set in environment variables.")
supabase: Client = create_client(supabase_url, supabase_key)
print("Supabase Client initialized in app/__init__.py")

# Initialize SocketIO
# Make sure SocketIO uses the 'app' instance defined above
socketio = SocketIO(app,
                   cors_allowed_origins="*",
                   logger=True,
                   engineio_logger=True, # Consider disabling in production
                   ping_timeout=60,
                   ping_interval=25)
print("SocketIO initialized in app/__init__.py")

# Import routes and blueprints *after* app and extensions initialization
# to avoid circular dependencies.
# We import app.py here implicitly when Vercel runs app.py,
# or we can explicitly import the routes if defined elsewhere.
# For now, let app.py import the initialized instances. 