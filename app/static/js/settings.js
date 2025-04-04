/**
 * 設定ページの機能を管理するスクリプト
 */

document.addEventListener('DOMContentLoaded', function() {
    loadApiKeyStatus();
    setupSettingsEventListeners();
});

/**
 * APIキーの設定状況を読み込んで表示（入力欄を埋めない）
 */
function loadApiKeyStatus() {
    fetch('/api/settings/keys')
        .then(response => response.json())
        .then(data => {
            // プレースホルダーで設定状況を示す（例）
            if (data.openai_key_set) {
                document.getElementById('openai-key').placeholder = '設定済み (変更する場合のみ入力)';
            }
            if (data.google_key_set) {
                document.getElementById('google-key').placeholder = '設定済み (変更する場合のみ入力)';
            }
            if (data.anthropic_key_set) {
                document.getElementById('anthropic-key').placeholder = '設定済み (変更する場合のみ入力)';
            }
        })
        .catch(error => {
            console.error('APIキー設定状況の取得に失敗しました:', error);
        });
}

/**
 * 設定ページのイベントリスナーを設定
 */
function setupSettingsEventListeners() {
    document.getElementById('save-api-keys-btn').addEventListener('click', saveApiKeys);
}

/**
 * 入力されたAPIキーをサーバーに送信して保存
 */
function saveApiKeys() {
    const openaiKey = document.getElementById('openai-key').value;
    const googleKey = document.getElementById('google-key').value;
    const anthropicKey = document.getElementById('anthropic-key').value;
    
    const statusElement = document.getElementById('api-save-status');
    statusElement.textContent = '保存中...';
    statusElement.style.color = 'var(--text-light)';
    
    fetch('/api/settings/keys', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            openai_key: openaiKey || null, // 空の場合はnullを送る
            google_key: googleKey || null,
            anthropic_key: anthropicKey || null
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.error || '不明なエラー'); });
        }
        return response.json();
    })
    .then(data => {
        statusElement.textContent = data.message || '保存しました！';
        statusElement.style.color = 'var(--success-color)';
        // 保存後に入力欄をクリア
        document.getElementById('openai-key').value = '';
        document.getElementById('google-key').value = '';
        document.getElementById('anthropic-key').value = '';
        // プレースホルダーを更新
        loadApiKeyStatus(); 
    })
    .catch(error => {
        console.error('APIキーの保存に失敗しました:', error);
        statusElement.textContent = `保存エラー: ${error.message}`;
        statusElement.style.color = 'var(--error-color)';
    });
} 