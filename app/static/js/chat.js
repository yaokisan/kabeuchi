/**
 * AIチャット機能を管理するスクリプト
 */

// グローバル変数
let currentChatModel = localStorage.getItem('lastSelectedAIModel') || 'gemini-2.0-flash'; // デフォルト値を設定し、ローカルストレージから取得
let thinkingEnabled = false;
let currentChatContext = null; // 追加されたコンテキストテキストを保持する変数
let attachedImageBase64 = null; // ★ 添付画像のBase64データを保持
let attachedImageMimeType = null; // ★ 添付画像のMIMEタイプを保持

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
    setupContextIndicatorEvents(); // インジケーターのイベント設定を追加
    
    // AIモデルの初期選択を復元
    restoreLastSelectedModel();
    
    setupChatInputAutoResize(); // ★ 新しい関数呼び出しを追加
    updateSearchToggleVisibility(); // ★ 初期表示時のチェックボックス表示更新を追加
    setupImageAttachment(); // ★ 画像添付関連のイベント設定を追加
});

/**
 * チャット関連のイベントを設定
 */
function setupChatEvents() {
    // チャット送信ボタン
    document.getElementById('send-chat-btn').addEventListener('click', sendChatMessage);
    
    // チャット履歴リセットボタン
    document.getElementById('reset-chat-btn').addEventListener('click', resetChatHistory);
    
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
        localStorage.setItem('lastSelectedAIModel', currentChatModel);
        
        // Claude用思考モードの表示切替
        const thinkingModeElement = document.getElementById('claude-thinking-mode');
        thinkingModeElement.style.display = currentChatModel.startsWith('claude') ? 'block' : 'none';

        // ★ 検索チェックボックスの表示切替
        updateSearchToggleVisibility();
    });
    
    // 思考モードトグルのイベント
    document.getElementById('thinking-toggle').addEventListener('change', function() {
        thinkingEnabled = this.checked;
    });
}

/**
 * コンテキストインジケーター関連のイベントを設定
 */
function setupContextIndicatorEvents() {
    document.getElementById('clear-chat-context-btn').addEventListener('click', clearContext);
}

/**
 * チャットメッセージを送信
 */
function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value.trim();
    
    // ★ メッセージも画像もない場合は送信しない
    if (!message && !attachedImageBase64) return;
    
    const documentId = window.editorAPI.getCurrentDocumentId();
    if (!documentId) {
        alert('ドキュメントが読み込まれていません。');
        return;
    }
    
    // ★ 送信するデータを保持（送信後にリセットするため）
    const messageToSend = message;
    const imageBase64ToSend = attachedImageBase64;
    const imageMimeTypeToSend = attachedImageMimeType;
    
    // UIをリセット
    chatInput.value = '';
    removeAttachedImage(); // 添付画像を削除してプレビューを消す
    
    // ★ ユーザーメッセージ（テキストのみ、または画像のみの場合もある）をUIに追加
    addMessageToChat('user', messageToSend, [], imageBase64ToSend); // 画像プレビューをユーザーメッセージに追加
    
    const loadingElement = createLoadingIndicator();
    document.getElementById('chat-messages').appendChild(loadingElement);
    
    const contextToSend = currentChatContext;
    const enableSearch = document.getElementById('enable-search-checkbox').checked;
    
    fetch(`/api/chat/send/${documentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: messageToSend,
            model: currentChatModel,
            thinking_enabled: thinkingEnabled,
            chat_context: contextToSend,
            enable_search: enableSearch,
            image_data: imageBase64ToSend, // ★ 画像データ (Base64)
            image_mime_type: imageMimeTypeToSend // ★ 画像MIMEタイプ
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('チャットメッセージの送信に失敗しました');
        }
        return response.json();
    })
    .then(data => {
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.parentNode.removeChild(loadingElement);
        }
        if (data.success) {
            addMessageToChat('assistant', data.message, data.sources);
        } else {
            addMessageToChat('assistant', data.message || 'エラーが発生しました。');
        }
        scrollChatToBottom();
        clearContext(); 
    })
    .catch(error => {
        console.error('チャットエラー:', error);
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.parentNode.removeChild(loadingElement);
        }
        addMessageToChat('assistant', 'エラーが発生しました。しばらく経ってからもう一度お試しください。');
        scrollChatToBottom();
        clearContext();
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
 * @param {Array<object>} [sources=[]] - (アシスタントの場合) 参照した情報源のリスト
 * @param {string|null} [imageBase64=null] - (ユーザーメッセージの場合) 添付画像のBase64データ
 */
function addMessageToChat(role, content, sources = [], imageBase64 = null) {
    const chatMessages = document.getElementById('chat-messages');
    
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${role}-message`;
    
    // ★ ユーザーメッセージで画像がある場合、プレビューを追加
    if (role === 'user' && imageBase64) {
        const userImagePreview = document.createElement('img');
        userImagePreview.src = imageBase64;
        userImagePreview.alt = "添付画像";
        userImagePreview.style.maxWidth = '50%'; // UI内で大きすぎないように
        userImagePreview.style.maxHeight = '150px';
        userImagePreview.style.borderRadius = '4px';
        userImagePreview.style.marginBottom = content ? '8px' : '0'; // テキストがあれば下にマージン
        userImagePreview.style.display = 'block';
        messageElement.appendChild(userImagePreview);
    }

    // メッセージ本文のコンテナ（テキストがある場合のみ追加）
    if (content) {
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';

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
                    contentElement.innerHTML = marked.parse(content, markedOptions);
                    
                    // リンクを新しいタブで開くように設定
                    const links = contentElement.querySelectorAll('a');
                    links.forEach(link => {
                        link.setAttribute('target', '_blank');
                        link.setAttribute('rel', 'noopener noreferrer');
                    });
                } else {
                    // marked.jsが読み込まれていない場合は通常のテキスト表示
                    console.warn('marked.js is not loaded, displaying plain text');
                    const escapedContent = escapeHtml(content).replace(/\n/g, '<br>');
                    contentElement.innerHTML = escapedContent;
                }
            } catch (error) {
                // エラーが発生した場合はプレーンテキストにフォールバック
                console.error('Markdown rendering failed:', error);
                const escapedContent = escapeHtml(content).replace(/\n/g, '<br>');
                contentElement.innerHTML = escapedContent;
            }
        } else {
            // ユーザーのメッセージはHTMLエスケープして改行を<br>に変換
            const escapedContent = escapeHtml(content).replace(/\n/g, '<br>');
            contentElement.innerHTML = escapedContent;
        }
        messageElement.appendChild(contentElement);
    } else if (role === 'user' && !imageBase64) {
        // テキストも画像もない場合は何も表示しない（または「空のメッセージ」などを表示）
        return; // 何も追加しない
    }
    
    // ★ アシスタントメッセージで、かつ情報源がある場合にリストを表示
    if (role === 'assistant' && sources && sources.length > 0) {
        const sourcesList = document.createElement('ul');
        sourcesList.className = 'message-sources';
        sourcesList.innerHTML = '<li class="sources-title">参照元:</li>'; // タイトル

        sources.forEach(source => {
            const sourceItem = document.createElement('li');
            const link = document.createElement('a');
            link.href = source.url;
            link.target = '_blank'; // 新しいタブで開く
            link.rel = 'noopener noreferrer';
            link.textContent = source.title || 'タイトル不明'; // タイトル表示
            
            const domainSpan = document.createElement('span');
            domainSpan.className = 'source-domain';
            domainSpan.textContent = ` (${source.domain || 'ドメイン不明'})`; // ドメイン表示

            sourceItem.appendChild(link);
            sourceItem.appendChild(domainSpan);
            sourcesList.appendChild(sourceItem);
        });
        messageElement.appendChild(sourcesList);
    }
    
    chatMessages.appendChild(messageElement);
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
            currentChatModel = lastModel; // ★ グローバル変数も先に更新
            // 変更イベントは updateSearchToggleVisibility 呼び出し後の方が良いかも
            // const event = new Event('change');
            // modelSelect.dispatchEvent(event); 
        }
    } else {
        // ローカルストレージにない場合、デフォルト値を設定
        const modelSelect = document.getElementById('ai-model');
        if (modelSelect) {
            currentChatModel = modelSelect.value; // ドロップダウンの初期値を取得
        }
    }
    // ここで思考モードなどの初期表示も更新（changeイベントを発火させない場合）
    const thinkingModeElement = document.getElementById('claude-thinking-mode');
    if(thinkingModeElement) thinkingModeElement.style.display = currentChatModel.startsWith('claude') ? 'block' : 'none';

    // updateSearchToggleVisibility(); // DOMContentLoaded 内で呼ばれるのでここでは不要かも
}

/**
 * AIチャットのコンテキストを設定し、インジケーターを表示する
 * @param {string} contextText - 設定するコンテキストテキスト
 */
function setContext(contextText) {
    currentChatContext = contextText;
    const indicator = document.getElementById('chat-context-indicator');
    indicator.style.display = 'flex'; // 表示 (flexを使うと中の要素が横並びになる)
    console.log('チャットコンテキストを設定:', currentChatContext);
}

/**
 * AIチャットのコンテキストをクリアし、インジケーターを非表示にする
 */
function clearContext() {
    currentChatContext = null;
    const indicator = document.getElementById('chat-context-indicator');
    indicator.style.display = 'none';
    console.log('チャットコンテキストをクリアしました');
}

/**
 * AIとのチャット履歴をリセットする
 */
function resetChatHistory() {
    const confirmed = confirm('AIとのチャット履歴をリセットしますか？\nこの操作は元に戻せません。');
    if (!confirmed) {
        return;
    }

    const documentId = window.editorAPI.getCurrentDocumentId();
    if (!documentId) {
        alert('ドキュメントが読み込まれていません。');
        return;
    }

    // サーバーにチャット履歴のリセットをリクエスト
    fetch(`/api/chat/reset/${documentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('チャット履歴のリセットに失敗しました。');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // UIのチャット履歴をクリア
            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML = '';
            console.log('チャット履歴がリセットされました。');
            // 必要であれば、ユーザーに通知などを表示
            // addMessageToChat('system', 'チャット履歴がリセットされました。');
        } else {
            alert('チャット履歴のリセットに失敗しました。');
        }
    })
    .catch(error => {
        console.error('チャットリセットエラー:', error);
        alert('チャット履歴のリセット中にエラーが発生しました。');
    });
}

// 他のJSファイルから呼び出せるようにAPIを公開
window.chatAPI = {
    setContext: setContext,
    clearContext: clearContext
};

// 既存の公開関数も chatAPI にまとめる方が整理されるかも
// window.restoreLastSelectedModel = restoreLastSelectedModel;
// window.loadChatHistory = loadChatHistory; 

const chatInput = document.getElementById('chat-input');
const sendChatBtn = document.getElementById('send-chat-btn');

// チャット入力欄の自動高さ調整を設定する関数
function setupChatInputAutoResize() {
    if (!chatInput) return;

    const adjustHeight = () => {
        chatInput.style.height = 'auto'; // 一旦高さをリセット
        chatInput.style.height = chatInput.scrollHeight + 'px'; // スクロール可能な高さに設定
    };

    chatInput.addEventListener('input', adjustHeight);
    adjustHeight(); // 初期表示時にも高さを調整
}

// メッセージ送信関数
function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // ... (既存のメッセージ送信ロジック) ...

    // 送信後に高さをリセット
    chatInput.value = '';
    chatInput.style.height = 'auto';
}

// イベントリスナー
sendChatBtn.addEventListener('click', sendMessage);

/* ★ ShiftなしEnterでの送信機能を無効化
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
*/

// 初期化関数の呼び出し
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChat);
} else {
    initChat();
}

// チャットメッセージを追加する関数 (例)
function addMessage(sender, message) {
    const messagesContainer = document.querySelector('.chat-messages');
    if (!messagesContainer) return;

    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', sender === 'user' ? 'user-message' : 'assistant-message');

    if (sender === 'assistant') {
        // MarkdownをHTMLに変換 (marked.jsなどを使用する場合)
        // messageElement.innerHTML = marked.parse(message);
        messageElement.textContent = message; // 仮実装
    } else {
        messageElement.textContent = message;
    }

    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ★ 新しい関数: 検索チェックボックスの表示を更新
function updateSearchToggleVisibility() {
    const searchToggleContainer = document.querySelector('.search-toggle-container');
    if (searchToggleContainer) {
        // 現在選択されているモデルが 'gemini' で始まるかチェック
        const isGeminiSelected = currentChatModel.startsWith('gemini');
        searchToggleContainer.style.display = isGeminiSelected ? 'flex' : 'none';
    }
}

// ★ 新しい関数: 画像添付関連のイベントを設定
function setupImageAttachment() {
    const attachBtn = document.getElementById('attach-image-btn');
    const imageInput = document.getElementById('chat-image-input');
    const previewContainer = document.getElementById('image-preview-container');
    const previewImage = document.getElementById('image-preview');
    const removeBtn = document.getElementById('remove-image-btn');

    if (!attachBtn || !imageInput || !previewContainer || !previewImage || !removeBtn) return;

    // 添付ボタンクリックでファイル入力をトリガー
    attachBtn.addEventListener('click', () => {
        imageInput.click();
    });

    // ファイルが選択されたときの処理
    imageInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        const MAX_FILE_SIZE_MB = 5;
        const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

        if (file && file.type.startsWith('image/')) {
            // ★ ファイルサイズチェック
            if (file.size > MAX_FILE_SIZE_BYTES) {
                alert(`画像ファイルサイズは ${MAX_FILE_SIZE_MB}MB を超えられません。`);
                removeAttachedImage(); // 添付をリセット
                imageInput.value = null; // ファイル選択もリセット
                return; // 処理中断
            }

            const reader = new FileReader();
            reader.onloadend = () => {
                attachedImageBase64 = reader.result;
                attachedImageMimeType = file.type;
                previewImage.src = attachedImageBase64;
                previewContainer.style.display = 'block';
            }
            reader.readAsDataURL(file);
        } else {
            // 画像以外、または選択キャンセル
            removeAttachedImage();
        }
        // 同じファイルを連続で選択できるように value をリセット
        imageInput.value = null;
    });

    // 画像削除ボタンの処理
    removeBtn.addEventListener('click', removeAttachedImage);
}

// ★ 新しい関数: 添付画像を削除し、プレビューを非表示にする
function removeAttachedImage() {
    attachedImageBase64 = null;
    attachedImageMimeType = null;
    const previewContainer = document.getElementById('image-preview-container');
    const previewImage = document.getElementById('image-preview');
    const imageInput = document.getElementById('chat-image-input');
    if (previewContainer) previewContainer.style.display = 'none';
    if (previewImage) previewImage.src = '#';
    if (imageInput) imageInput.value = null; // 念のためファイル選択もリセット
    console.log('添付画像を削除しました');
} 