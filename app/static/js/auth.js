// auth.js: token handling & fetch wrapper
(function(){
  const LOGIN_PATH = '/login';
  // ページ <head> 内に埋め込まれた Supabase URL
  const SUPABASE_URL = document.querySelector('meta[name="supabase-url"]')?.content || '';

  // ------------------------------------------------------------------
  // ①   ハッシュフラグメントに含まれるトークン情報の保存
  // ------------------------------------------------------------------
  function saveTokenFromHash(){
    if(!location.hash || !location.hash.includes('access_token')) return;

    const params = new URLSearchParams(location.hash.substring(1));

    const accessToken  = params.get('access_token');
    const refreshToken = params.get('refresh_token');
    const expiresIn    = params.get('expires_in'); // 秒数

    if(accessToken){
      localStorage.setItem('access_token', accessToken);
    }

    if(refreshToken){
      localStorage.setItem('refresh_token', refreshToken);
    }

    if(expiresIn){
      const expiresAt = Date.now() + parseInt(expiresIn, 10) * 1000;
      localStorage.setItem('access_expires_at', String(expiresAt));
    }

    // URL からハッシュ部分を除去（ページの再読込は行わない）
    history.replaceState({}, document.title, location.pathname + location.search);
  }

  // ------------------------------------------------------------------
  // ②   アクセストークンの有無を確認し、無ければログインへ遷移
  // ------------------------------------------------------------------
  function ensureToken(){
    const token = localStorage.getItem('access_token');
    if(!token && location.pathname !== LOGIN_PATH){
      location.href = LOGIN_PATH;
    }
  }

  // ------------------------------------------------------------------
  // ③   JWT 解析補助
  // ------------------------------------------------------------------
  function parseJwtPayload(token){
    try{
      const base64Url = token.split('.')[1];
      let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      while(base64.length % 4 !== 0){ base64 += '='; }
      return JSON.parse(atob(base64));
    }catch{ return null; }
  }

  // ------------------------------------------------------------------
  // ④   アクセストークンの期限切れ判定
  // ------------------------------------------------------------------
  function isTokenExpired(token){
    if(!token) return true;

    // 1) localStorage に保存した expires_at を優先
    const stored = localStorage.getItem('access_expires_at');
    if(stored && Number(stored) <= Date.now() + 60_000){ // 60秒前倒し
      return true;
    }

    // 2) JWT exp を参照
    const payload = parseJwtPayload(token);
    if(payload && payload.exp){
      return payload.exp * 1000 <= Date.now() + 60_000;
    }
    return false; // exp が無い場合は未検証とする
  }

  // ------------------------------------------------------------------
  // ⑤   リフレッシュトークンを使ってアクセストークンを再取得
  // ------------------------------------------------------------------
  async function refreshAccessToken(){
    const refreshToken = localStorage.getItem('refresh_token');
    if(!refreshToken || !SUPABASE_URL){
      return null;
    }

    try{
      const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      if(!res.ok) throw new Error(`Refresh failed: ${res.status}`);

      const data = await res.json();
      if(data.access_token){
        localStorage.setItem('access_token', data.access_token);
      }
      if(data.refresh_token){
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      if(data.expires_in){
        localStorage.setItem('access_expires_at', String(Date.now() + data.expires_in * 1000));
      }
      return data.access_token;
    }catch(e){
      console.warn('[AUTH] トークンリフレッシュに失敗しました', e);
      return null;
    }
  }

  // 初期処理
  saveTokenFromHash();
  ensureToken();

  // fetch ラッパー (明示的に呼ぶ場合)
  window.apiFetch = function(url, options={}){
    const token = localStorage.getItem('access_token');
    options.headers = Object.assign({ 'Authorization': `Bearer ${token}`}, options.headers||{});
    return fetch(url, options);
  };

  // ----------------- NEW: 全 fetch にトークンを付与するグローバルパッチ -----------------
  (function(){
    const originalFetch = window.fetch;
    window.fetch = async function(input, init={}){
      // トークンの有効性を確認し、必要であればリフレッシュ
      let token = localStorage.getItem('access_token');
      if(token && isTokenExpired(token)){
        token = await refreshAccessToken();
      }

      // まだトークンが無い / 取得失敗時はログアウト扱い
      if(!token && location.pathname !== LOGIN_PATH){
        logout();
        return Promise.reject(new Error('Authentication required'));
      }

      // Authorization ヘッダー付与
      if(token){
        if(!init) init = {};
        if(init.headers instanceof Headers){
          if(!init.headers.has('Authorization')){
            init.headers.set('Authorization', `Bearer ${token}`);
          }
        } else {
          init.headers = Object.assign({ 'Authorization': `Bearer ${token}` }, init.headers || {});
        }
      }

      // API呼び出し
      const response = await originalFetch(input, init);

      // もし 401 が返ってきたら再度リフレッシュ→リトライ
      if(response.status === 401){
        const newToken = await refreshAccessToken();
        if(newToken){
          if(init.headers instanceof Headers){
            init.headers.set('Authorization', `Bearer ${newToken}`);
          } else {
            init.headers = Object.assign({ 'Authorization': `Bearer ${newToken}` }, init.headers || {});
          }
          return originalFetch(input, init);
        } else {
          logout();
        }
      }

      return response;
    };
  })();

  // ----------------- 追加: ログアウト処理 -----------------
  window.logout = function(){
    // ローカルストレージのトークンを削除
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('access_expires_at');
    // サーバ側のセッションを明示的に終了（失敗しても無視）
    fetch('/auth/signout', {method:'POST'}).finally(()=>{
      location.href = '/login';
    });
  };

  // ----------------- 追加: ユーザメール表示 -----------------
  function currentEmail(){
    const t = localStorage.getItem('access_token');
    if(!t) return null;
    const payload = parseJwtPayload(t);
    if(!payload) return null;
    if(payload.email) return payload.email;
    if(payload.user_metadata && payload.user_metadata.email) return payload.user_metadata.email;
    return null;
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    const mail = currentEmail();
    if(!mail) return;
    document.querySelectorAll('.user-email').forEach(el=>{el.textContent = mail;});
  });
})(); 