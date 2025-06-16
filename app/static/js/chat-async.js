/**
 * 非同期AIチャット処理
 * Server-Sent EventsとWeb Workersによる高速化
 */

class AsyncChatClient {
    constructor() {
        this.eventSource = null;
        this.isProcessing = false;
        this.currentDocumentId = null;
        this.responseBuffer = '';
        this.markdownWorker = null;
        
        this.initializeWorker();
        this.setupEventListeners();
    }
    
    /**
     * Web Worker初期化（マークダウン処理用）
     */
    initializeWorker() {
        if (typeof Worker !== 'undefined') {
            try {
                this.markdownWorker = new Worker('/static/js/markdown-worker.js');
                this.markdownWorker.onmessage = (e) => {
                    this.handleWorkerMessage(e.data);
                };
            } catch (error) {
                console.warn('Web Worker not available, falling back to sync processing');
            }
        }
    }
    
    /**
     * イベントリスナー設定
     */
    setupEventListeners() {
        // 送信ボタン
        const sendButton = document.getElementById('sendMessage');
        if (sendButton) {
            sendButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }
        
        // Enter キー送信
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // ページアンロード時のクリーンアップ
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }
    
    /**
     * メッセージ送信
     */
    async sendMessage() {
        if (this.isProcessing) {
            this.showMessage('処理中です。しばらくお待ちください。', 'warning');
            return;
        }
        
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) {
            this.showMessage('メッセージを入力してください。', 'warning');
            return;
        }
        
        // 現在のドキュメントIDを取得
        this.currentDocumentId = this.getCurrentDocumentId();
        if (!this.currentDocumentId) {
            this.showMessage('ドキュメントが選択されていません。', 'error');
            return;
        }
        
        // UI更新
        this.setProcessingState(true);
        messageInput.value = '';
        
        // ユーザーメッセージを表示
        this.addMessageToChat('user', message);
        
        // AI応答エリアを準備
        const assistantElement = this.prepareAssistantResponse();
        
        try {
            await this.streamChatResponse(message, assistantElement);
        } catch (error) {
            console.error('Chat error:', error);
            this.showMessage(`エラーが発生しました: ${error.message}`, 'error');
            this.setProcessingState(false);
        }
    }
    
    /**
     * ストリーミングチャット応答
     */
    async streamChatResponse(message, assistantElement) {
        const url = `/api/chat/async/stream/${this.currentDocumentId}`;
        
        const requestData = {
            message: message,
            aiModel: this.getSelectedAIModel(),
            searchEnabled: this.isSearchEnabled()
        };
        
        try {
            // EventSource接続
            this.eventSource = new EventSource(url);
            
            // POSTリクエストでメッセージ送信
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // EventSourceでストリーミング受信
            this.setupEventSourceListeners(assistantElement);
            
        } catch (error) {
            console.error('Stream setup error:', error);
            throw error;
        }
    }
    
    /**
     * EventSourceリスナー設定
     */
    setupEventSourceListeners(assistantElement) {
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleStreamMessage(data, assistantElement);
            } catch (error) {
                console.error('Message parse error:', error);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            this.showMessage('接続エラーが発生しました。', 'error');
            this.cleanup();
        };
        
        this.eventSource.onopen = () => {
            console.log('EventSource connection opened');
        };
    }
    
    /**
     * ストリームメッセージ処理
     */
    handleStreamMessage(data, assistantElement) {
        switch (data.type) {
            case 'status':
                this.updateStatusMessage(data.message);
                break;
                
            case 'user_message':
                // ユーザーメッセージは既に表示済み
                break;
                
            case 'chunk':
                this.appendToResponse(data.content, assistantElement);
                break;
                
            case 'complete':
                this.handleResponseComplete(assistantElement);
                break;
                
            case 'error':
                this.showMessage(data.message, 'error');
                this.setProcessingState(false);
                this.cleanup();
                break;
                
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    
    /**
     * 応答テキストを追加
     */
    appendToResponse(content, assistantElement) {
        this.responseBuffer += content;
        
        // Web Workerでマークダウン処理
        if (this.markdownWorker) {
            this.markdownWorker.postMessage({
                type: 'render',
                content: this.responseBuffer,
                elementId: assistantElement.id
            });
        } else {
            // フォールバック: 同期処理
            this.updateElementContent(assistantElement, this.responseBuffer);
        }
        
        // スクロール更新（throttled）
        this.throttledScrollToBottom();
    }
    
    /**
     * Worker メッセージ処理
     */
    handleWorkerMessage(data) {
        if (data.type === 'rendered') {
            const element = document.getElementById(data.elementId);
            if (element) {
                element.innerHTML = data.html;
                this.applySyntaxHighlighting(element);
            }
        }
    }
    
    /**
     * 応答完了処理
     */
    handleResponseComplete(assistantElement) {
        // 最終的なマークダウン処理
        if (this.markdownWorker) {
            this.markdownWorker.postMessage({
                type: 'finalize',
                content: this.responseBuffer,
                elementId: assistantElement.id
            });
        }
        
        this.setProcessingState(false);
        this.cleanup();
        this.responseBuffer = '';
        
        // 最終スクロール
        this.scrollChatToBottom();
        
        // 成功メッセージ
        this.updateStatusMessage('応答完了');
        setTimeout(() => this.clearStatusMessage(), 2000);
    }
    
    /**
     * AI応答エリア準備
     */
    prepareAssistantResponse() {
        const chatContainer = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = 'message assistant-message';
        messageElement.id = `msg-${Date.now()}`;
        
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content markdown-content';
        contentElement.innerHTML = '<div class="typing-indicator">AI応答中...</div>';
        
        messageElement.appendChild(contentElement);
        chatContainer.appendChild(messageElement);
        
        this.scrollChatToBottom();
        
        return contentElement;
    }
    
    /**
     * メッセージをチャットに追加
     */
    addMessageToChat(role, content) {
        const chatContainer = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}-message`;
        
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        
        if (role === 'user') {
            contentElement.textContent = content;
        } else {
            contentElement.innerHTML = content;
            this.applySyntaxHighlighting(contentElement);
        }
        
        messageElement.appendChild(contentElement);
        chatContainer.appendChild(messageElement);
        
        this.scrollChatToBottom();
    }
    
    /**
     * 要素コンテンツ更新
     */
    updateElementContent(element, content) {
        if (typeof marked !== 'undefined') {
            element.innerHTML = marked.parse(content);
        } else {
            element.innerHTML = content.replace(/\n/g, '<br>');
        }
        this.applySyntaxHighlighting(element);
    }
    
    /**
     * シンタックスハイライト適用
     */
    applySyntaxHighlighting(element) {
        if (typeof hljs !== 'undefined') {
            element.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
    }
    
    /**
     * スロットル付きスクロール
     */
    throttledScrollToBottom = this.throttle(() => {
        this.scrollChatToBottom();
    }, 100);
    
    /**
     * チャット最下部へスクロール
     */
    scrollChatToBottom() {
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    /**
     * 処理状態設定
     */
    setProcessingState(processing) {
        this.isProcessing = processing;
        
        const sendButton = document.getElementById('sendMessage');
        const messageInput = document.getElementById('messageInput');
        
        if (sendButton) {
            sendButton.disabled = processing;
            sendButton.textContent = processing ? '処理中...' : '送信';
        }
        
        if (messageInput) {
            messageInput.disabled = processing;
        }
    }
    
    /**
     * ステータスメッセージ更新
     */
    updateStatusMessage(message) {
        const statusElement = document.getElementById('chatStatus');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.style.display = 'block';
        }
    }
    
    /**
     * ステータスメッセージクリア
     */
    clearStatusMessage() {
        const statusElement = document.getElementById('chatStatus');
        if (statusElement) {
            statusElement.style.display = 'none';
        }
    }
    
    /**
     * メッセージ表示
     */
    showMessage(message, type = 'info') {
        // 既存のshowMessage関数を使用
        if (typeof showMessage === 'function') {
            showMessage(message, type);
        } else {
            alert(message);
        }
    }
    
    /**
     * 現在のドキュメントID取得
     */
    getCurrentDocumentId() {
        // 既存の実装を参照
        return window.currentDocumentId || null;
    }
    
    /**
     * 選択されたAIモデル取得
     */
    getSelectedAIModel() {
        const modelSelect = document.getElementById('aiModelSelect');
        return modelSelect ? modelSelect.value : 'openai';
    }
    
    /**
     * 検索機能有効状態取得
     */
    isSearchEnabled() {
        const searchCheckbox = document.getElementById('searchEnabled');
        return searchCheckbox ? searchCheckbox.checked : false;
    }
    
    /**
     * クリーンアップ
     */
    cleanup() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.setProcessingState(false);
    }
    
    /**
     * スロットル関数
     */
    throttle(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Web Worker用マークダウン処理スクリプト作成
const createMarkdownWorker = () => {
    const workerScript = `
        // markdown-worker.js
        self.onmessage = function(e) {
            const { type, content, elementId } = e.data;
            
            let html;
            if (typeof marked !== 'undefined') {
                html = marked.parse(content);
            } else {
                // フォールバック
                html = content.replace(/\\n/g, '<br>');
            }
            
            self.postMessage({
                type: type === 'finalize' ? 'rendered' : 'rendered',
                elementId: elementId,
                html: html
            });
        };
    `;
    
    const blob = new Blob([workerScript], { type: 'application/javascript' });
    return URL.createObjectURL(blob);
};

// グローバル初期化
let asyncChatClient;

document.addEventListener('DOMContentLoaded', () => {
    // Web Worker スクリプト作成
    if (typeof Worker !== 'undefined') {
        const workerURL = createMarkdownWorker();
        // グローバルに保存してAsyncChatClientで使用
        window.markdownWorkerURL = workerURL;
    }
    
    // 非同期チャットクライアント初期化
    asyncChatClient = new AsyncChatClient();
    
    // 既存のチャット機能を無効化して新しいものに置き換え
    const oldSendButton = document.getElementById('sendMessage');
    if (oldSendButton) {
        // イベントリスナーをクリア
        oldSendButton.replaceWith(oldSendButton.cloneNode(true));
    }
});

// エクスポート
window.AsyncChatClient = AsyncChatClient;
window.asyncChatClient = asyncChatClient;