# app/index.py
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os

# --- Flask App Initialization ---
# 'app' is the WSGI application instance Vercel/Gunicorn will look for
app = Flask(__name__,
            # template_folder and static_folder are relative to the app package ('app')
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_for_dev_replace_in_prod')
print("Flask App initialized in app/index.py")

# --- Load Environment Variables ---
load_dotenv()

# --- Initialize Supabase Client ---
# Use relative import from within the 'app' package
try:
    from .supabase_client import supabase
    print("Supabase client imported in app/index.py")
except ImportError as e:
    print(f"Error importing Supabase client in app/index.py: {e}")
    raise e

# --- Initialize SocketIO ---
socketio = SocketIO(app,
                   cors_allowed_origins="*",
                   logger=True,
                   engineio_logger=True,
                   ping_timeout=60,
                   ping_interval=25)
print("SocketIO initialized in app/index.py")

# --- Import and Register Blueprints ---
# Use relative imports for controllers within the same package
try:
    from .controllers.document_controller import document_bp
    from .controllers.chat_controller import chat_bp
    from .controllers.settings_controller import settings_bp

    blueprints_to_register = [document_bp, chat_bp, settings_bp]
    for bp in blueprints_to_register:
        if not app.blueprints.get(bp.name):
            app.register_blueprint(bp)
    print("ブループリントを登録しました (app/index.py)")

except ImportError as e:
    print(f"Error importing or registering blueprints in app/index.py: {e}")
    raise e

# --- Route Definitions ---
# These routes are now part of the 'app' package

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manage')
def manage_documents():
    return render_template('manage.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/config')
def get_config():
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_KEY environment variables not set.")
        return jsonify({"error": "Server configuration error"}), 500
    return jsonify({
        'supabaseUrl': supabase_url,
        'supabaseKey': supabase_key
    })

# --- Application Execution (for local development) ---
# This block might not be directly used by Vercel but is useful for local testing
if __name__ == '__main__':
    # To run this locally, you might need to execute: python -m app.index
    print("アプリケーションを起動します (app/index.py - local)...")
    socketio.run(app, debug=True, use_reloader=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
    print("アプリケーションを終了します。") 