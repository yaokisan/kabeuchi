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

  // fetch ラッパー
  window.apiFetch = function(url, options={}){
    const token = localStorage.getItem('access_token');
    options.headers = Object.assign({ 'Authorization': `Bearer ${token}`}, options.headers||{});
    return fetch(url, options);
  };

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
  function currentEmail(){
    const t = localStorage.getItem('access_token');
    if(!t) return null;
    try{
      const payload = JSON.parse(atob(t.split('.')[1]));
      return payload.email || null;
    }catch{ return null; }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    const emailSpan = document.getElementById('user-email');
    if(emailSpan){
       const mail = currentEmail();
       if(mail) emailSpan.textContent = mail;
    }
  });
})(); 