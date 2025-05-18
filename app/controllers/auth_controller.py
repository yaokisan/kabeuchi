from flask import Blueprint, redirect, request, jsonify, url_for, g
import os, jwt
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

SUPA_URL = os.getenv('SUPABASE_URL')
JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')

# ---------- Google OAuth flow via Supabase ---------- #

# Supabase へ渡す Google OAuth コールバック先
# 1) 環境変数 SUPABASE_REDIRECT があればそれを優先
# 2) なければリクエスト URL から動的に生成 (ポートやホストを自動追従)

def _build_redirect_url():
    env_url = os.getenv('SUPABASE_REDIRECT')
    if env_url:
        return env_url
    # request.host_url は trailing slash を含む
    from flask import request as _req  # 循環防止のため関数内 import
    return _req.host_url.rstrip('/') + '/auth/callback'

@auth_bp.route('/login')
def login():
    """Supabase の authorize エンドポイントへリダイレクト"""
    url = (
        f"{SUPA_URL}/auth/v1/authorize?provider=google"
        f"&redirect_to={_build_redirect_url()}"
        f"&access_type=offline"
        f"&prompt=consent%20select_account"
    )
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

        // Supabase は access_token / refresh_token / expires_in が返る想定
        const access    = params.get('access_token');
        const refresh   = params.get('refresh_token');
        const expiresIn = params.get('expires_in');

        if (access)  localStorage.setItem('access_token',  access);
        if (refresh) localStorage.setItem('refresh_token', refresh);
        if (expiresIn){
          const expiresAt = Date.now() + parseInt(expiresIn,10)*1000;
          localStorage.setItem('access_expires_at', String(expiresAt));
        }
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
        # デバッグ: 先頭数文字だけ表示して漏洩防止
        if os.getenv('DEBUG_AUTH', 'false').lower() == 'true':
            print('[AUTH] Header token (trunc):', token[:20] + '...')
            print('[AUTH] JWT_SECRET (trunc):', (JWT_SECRET or '')[:8] + '...')
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'], audience='authenticated')
            g.current_user = payload['sub']  # Supabase UID
            g.jwt_token = token
        except jwt.PyJWTError as e:
            if os.getenv('DEBUG_AUTH', 'false').lower() == 'true':
                print('[AUTH] Decode error:', e)
            return jsonify({'success': False, 'message': 'Token invalid'}), 401
        return fn(*args, **kwargs)
    return wrapper

# ------------ 明示的サインアウト ------------ #

@auth_bp.route('/signout', methods=['POST'])
def signout():
    """フロントがトークンを破棄したあと呼ばれる。現在は何もせず204"""
    return '', 204 