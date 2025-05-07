from flask import Blueprint, redirect, request, jsonify, url_for, g
import os, jwt
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

SUPA_URL = os.getenv('SUPABASE_URL')
JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')

# ---------- Google OAuth flow via Supabase ---------- #
REDIRECT_URL = os.getenv('SUPABASE_REDIRECT', 'http://localhost:5001/auth/callback')

@auth_bp.route('/login')
def login():
    """Supabase の authorize エンドポイントへリダイレクト"""
    url = f"{SUPA_URL}/auth/v1/authorize?provider=google&redirect_to={REDIRECT_URL}"
    return redirect(url)

@auth_bp.route('/callback')
def callback():
    """
    Supabase から #access_token=... が付与されて戻って来る。
    サーバー側でリダイレクトするとフラグメントが欠落するので、
    ここでは最小ページを返し、JS で保存→ルートへ遷移させる。
    """
    return """
    <!doctype html><html><head><meta charset='utf-8'></head>
    <body>
    <script>
      // location.hash からアクセストークンを抽出して保存
      (function(){
        const hash = location.hash.substring(1);   // 先頭の # を除去
        const params = new URLSearchParams(hash);
        const token  = params.get('access_token');
        if (token) localStorage.setItem('access_token', token);
        // 認証後はトップページへ遷移
        window.location.replace('/');
      })();
    </script>
    </body></html>
    """

# ---------- JWT decorator ---------- #

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        token = auth_header.split()[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'], audience='authenticated')
            g.current_user = payload['sub']  # Supabase UID
        except jwt.PyJWTError:
            return jsonify({'success': False, 'message': 'Token invalid'}), 401
        return fn(*args, **kwargs)
    return wrapper

# ------------ 明示的サインアウト ------------ #

@auth_bp.route('/signout', methods=['POST'])
def signout():
    """フロントがトークンを破棄したあと呼ばれる。現在は何もせず204"""
    return '', 204 