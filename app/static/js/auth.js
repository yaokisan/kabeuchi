// auth.js: token handling & fetch wrapper
(function(){
  const LOGIN_PATH = '/login';

  function saveTokenFromHash(){
    if(location.hash && location.hash.includes('access_token')){
      const params = new URLSearchParams(location.hash.substring(1));
      const token  = params.get('access_token');
      if(token){
        localStorage.setItem('access_token', token);
      }
      // hash 部分を消して画面を再読み込みしない
      history.replaceState({}, document.title, location.pathname + location.search);
    }
  }

  function ensureToken(){
    const token = localStorage.getItem('access_token');
    if(!token && location.pathname !== LOGIN_PATH){
      // login 画面以外で token が無ければリダイレクト
      location.href = LOGIN_PATH;
    }
  }

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
    window.fetch = function(input, init={}){
      const token = localStorage.getItem('access_token');
      if(token){
        if(!init) init = {};
        // headers が Headers インスタンスかプレーンオブジェクトかを判定
        if(init.headers instanceof Headers){
          if(!init.headers.has('Authorization')){
            init.headers.set('Authorization', `Bearer ${token}`);
          }
        } else {
          init.headers = Object.assign({ 'Authorization': `Bearer ${token}` }, init.headers || {});
        }
      }
      return originalFetch(input, init);
    };
  })();

  // ----------------- 追加: ログアウト処理 -----------------
  window.logout = function(){
    // ローカルストレージのトークンを削除
    localStorage.removeItem('access_token');
    // サーバ側のセッションを明示的に終了（失敗しても無視）
    fetch('/auth/signout', {method:'POST'}).finally(()=>{
      location.href = '/login';
    });
  };

  // ----------------- 追加: ユーザメール表示 -----------------
  function parseJwtPayload(token){
    try{
      const base64Url = token.split('.')[1];
      let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      // 末尾のパディングを調整
      while(base64.length % 4 !== 0){ base64 += '='; }
      return JSON.parse(atob(base64));
    }catch{ return null; }
  }

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