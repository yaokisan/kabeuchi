/**
 * AIチャット機能を管理するスクリプト
 */

// グローバル変数
let currentChatModel = localStorage.getItem('lastSelectedAIModel') || 'gemini-2.0-flash'; // デフォルト値を設定し、ローカルストレージから取得
let thinkingEnabled = false;

// DOMが読み込まれた後に実行
document.addEventListener('DOMContentLoaded', function() {
    // Marked.jsの設定
    if (typeof marked === 'function') {
        // Markdownレンダリングの設定
        marked.setOptions({
            breaks: true,        // 改行を<br>に変換
            gfm: true,           // GitHub風のMarkdown
            headerIds: false,    // ヘッダーIDを生成しない
            mangle: false,       // リンクを難読化しない
            sanitize: false      // HTMLタグを許可
        });
    }
    
    setupChatEvents();
    
    // AIモデルの初期選択を復元
    restoreLastSelectedModel();
});

/**
 * チャット関連のイベントを設定
 */
function setupChatEvents() {
    // チャット送信ボタン
    document.getElementById('send-chat-btn').addEventListener('click', sendChatMessage);
    
    const chatInput = document.getElementById('chat-input');
    
    // 送信方法をプレースホルダーに表示（OS判定）
    const sendHint = navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘ + Enter で送信' : 'Ctrl + Enter で送信';
    chatInput.placeholder = `メッセージを入力... (${sendHint})`;
    
    // チャット入力欄でのキーダウンイベント
    chatInput.addEventListener('keydown', function(e) {
        // Command/Ctrl + Enter で送信
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            sendChatMessage();
        }
        // 通常のEnterキーでの送信を防ぎたい場合（Shift+Enterでの改行は許可）
        else if (e.key === 'Enter' && !e.shiftKey) {
            // 何もしない（デフォルトの改行を防ぐため、状況に応じて preventDefault() を追加）
            // e.preventDefault(); // 必要であればコメント解除
        }
    });
    
    // AIモデル選択変更時のイベント
    document.getElementById('ai-model').addEventListener('change', function() {
        currentChatModel = this.value;
        // ローカルストレージに選択を保存
        localStorage.setItem('lastSelectedAIModel', currentChatModel);
        
        // Claudeモデルが選択された場合のみ思考モードオプションを表示
        const thinkingModeElement = document.getElementById('claude-thinking-mode');
        if (currentChatModel.startsWith('claude')) {
            thinkingModeElement.style.display = 'block';
        } else {
            thinkingModeElement.style.display = 'none';
        }
    });
    
    // 思考モードトグルのイベント
    document.getElementById('thinking-toggle').addEventListener('change', function() {
        thinkingEnabled = this.checked;
    });
}

/**
 * チャットメッセージを送信
 */
function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    // 現在のドキュメントIDを取得
    const documentId = window.editorAPI.getCurrentDocumentId();
    if (!documentId) {
        alert('ドキュメントが読み込まれていません。');
        return;
    }
    
    // 送信前に入力欄をクリア
    chatInput.value = '';
    
    // ユーザーメッセージをUIに追加
    addMessageToChat('user', message);
    
    // 待機中インジケータを表示
    const loadingElement = createLoadingIndicator();
    document.getElementById('chat-messages').appendChild(loadingElement);
    
    // AIのレスポンスを取得
    fetch(`/api/chat/send/${documentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            model: currentChatModel,
            thinking_enabled: thinkingEnabled
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('チャットメッセージの送信に失敗しました');
        }
        return response.json();
    })
    .then(data => {
        // 待機中インジケータを削除
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.parentNode.removeChild(loadingElement);
        }
        
        // AIメッセージをUIに追加
        addMessageToChat('assistant', data.message);
        
        // チャットエリアを最下部にスクロール
        scrollChatToBottom();
    })
    .catch(error => {
        console.error('チャットエラー:', error);
        
        // 待機中インジケータを削除
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.parentNode.removeChild(loadingElement);
        }
        
        // エラーメッセージを表示
        addMessageToChat('assistant', 'エラーが発生しました。しばらく経ってからもう一度お試しください。');
        
        // チャットエリアを最下部にスクロール
        scrollChatToBottom();
    });
}

/**
 * チャット履歴を読み込む
 * @param {number} documentId - ドキュメントID
 */
function loadChatHistory(documentId) {
    fetch(`/api/chat/history/${documentId}`)
        .then(response => response.json())
        .then(messages => {
            // チャットエリアをクリア
            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML = '';
            
            // メッセージがない場合は何もしない
            if (messages.length === 0) return;
            
            // メッセージをUIに追加
            messages.forEach(msg => {
                addMessageToChat(msg.role, msg.content);
            });
            
            // チャットエリアを最下部にスクロール
            scrollChatToBottom();
        })
        .catch(error => {
            console.error('チャット履歴の読み込みに失敗しました:', error);
        });
}

/**
 * メッセージをチャットUIに追加
 * @param {string} role - メッセージの送信者のロール ('user' または 'assistant')
 * @param {string} content - メッセージの内容
 */
function addMessageToChat(role, content) {
    const chatMessages = document.getElementById('chat-messages');
    
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${role}-message`;
    
    if (role === 'assistant') {
        try {
            console.log('AIメッセージをマークダウンレンダリングします', content.substring(0, 50) + '...');
            
            // アシスタントのメッセージはMarkdownとしてレンダリング
            if (typeof marked !== 'undefined') {
                // markedオプション
                const markedOptions = {
                    breaks: true,       // 改行を<br>に変換
                    gfm: true,          // GitHub Flavored Markdown
                    headerIds: false,   // ヘッダーIDの自動生成を無効化
                    mangle: false,      // リンクの難読化を無効化
                    sanitize: false     // HTMLサニタイズを無効化（古いバージョンのmarkedで必要）
                };

                // マークダウンをHTMLに変換
                messageElement.innerHTML = marked.parse(content, markedOptions);
                
                // リンクを新しいタブで開くように設定
                const links = messageElement.querySelectorAll('a');
                links.forEach(link => {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                });
            } else {
                // marked.jsが読み込まれていない場合は通常のテキスト表示
                console.warn('marked.js is not loaded, displaying plain text');
                const escapedContent = escapeHtml(content).replace(/\n/g, '<br>');
                messageElement.innerHTML = escapedContent;
            }
        } catch (error) {
            // エラーが発生した場合はプレーンテキストにフォールバック
            console.error('Markdown rendering failed:', error);
            const escapedContent = escapeHtml(content).replace(/\n/g, '<br>');
            messageElement.innerHTML = escapedContent;
        }
    } else {
        // ユーザーのメッセージはHTMLエスケープして改行を<br>に変換
        const escapedContent = escapeHtml(content).replace(/\n/g, '<br>');
        messageElement.innerHTML = escapedContent;
    }
    
    chatMessages.appendChild(messageElement);
    
    // チャットエリアを最下部にスクロール
    scrollChatToBottom();
}

/**
 * 待機中インジケータを作成
 * @returns {HTMLElement} 作成されたローディングインジケータ要素
 */
function createLoadingIndicator() {
    const loadingElement = document.createElement('div');
    loadingElement.className = 'chat-message assistant-message loading';
    loadingElement.innerHTML = `
        <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    return loadingElement;
}

/**
 * チャットエリアを最下部にスクロール
 */
function scrollChatToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * HTMLエスケープ
 * @param {string} str - エスケープする文字列
 * @returns {string} エスケープされた文字列
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * 最後に選択されたAIモデルを復元し、UIに反映
 */
function restoreLastSelectedModel() {
    const lastModel = localStorage.getItem('lastSelectedAIModel');
    if (lastModel) {
        const modelSelect = document.getElementById('ai-model');
        if (modelSelect) {
            modelSelect.value = lastModel;
            // 変更イベントを手動でトリガーして、UI（思考モードなど）を更新
            const event = new Event('change');
            modelSelect.dispatchEvent(event);
        }
        currentChatModel = lastModel; // グローバル変数も更新
    }
}

// 他のJSファイルから呼び出せるようにグローバルに公開
window.restoreLastSelectedModel = restoreLastSelectedModel; 