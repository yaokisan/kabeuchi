/**
 * 最適化されたチャット機能
 * 既存のchat.jsとの互換性を保ちながらパフォーマンスを大幅改善
 */

class OptimizedChatManager {
    constructor() {
        this.isStreaming = false;
        this.messageQueue = [];
        this.messagePool = null;
        this.virtualList = null;
        this.currentChatModel = localStorage.getItem('lastSelectedAIModel') || 'gemini-2.0-flash';
        this.attachedImageBase64 = null;
        this.attachedImageMimeType = null;
        this.currentChatContext = null;
        this.thinkingEnabled = false;
        
        this.init();
    }
    
    init() {
        this.setupPerformanceOptimizations();
        this.setupEventListeners();
        this.setupMessagePool();
        this.setupVirtualScrolling();
        this.restoreLastSelectedModel();
        this.setupMarkdown();
    }
    
    /**
     * パフォーマンス最適化設定
     */
    setupPerformanceOptimizations() {
        // メッセージ要素のオブジェクトプール
        this.messagePool = window.performanceOptimizer?.createObjectPool(
            () => this.createMessageElement(),
            (element) => this.resetMessageElement(element),
            10
        );
        
        // DOM操作のバッチ処理
        this.pendingDOMOperations = [];
        this.domUpdateScheduled = false;
    }
    
    /**
     * イベントリスナー設定（最適化版）
     */
    setupEventListeners() {
        // イベント委譲を使用
        const chatContainer = document.getElementById('chatContainer');
        if (chatContainer && window.performanceOptimizer) {
            // 送信ボタン
            window.performanceOptimizer.setupEventDelegation(
                chatContainer, 'click', '#send-chat-btn', 
                (e) => this.sendChatMessage()
            );
            
            // リセットボタン
            window.performanceOptimizer.setupEventDelegation(
                chatContainer, 'click', '#reset-chat-btn',
                (e) => this.resetChatHistory()
            );
        }
        
        // チャット入力フィールド
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            // デバウンス付きのキーイベント
            const debouncedKeyHandler = window.performanceOptimizer?.debounce(
                (e) => this.handleChatInput(e), 100
            ) || ((e) => this.handleChatInput(e));
            
            chatInput.addEventListener('keydown', debouncedKeyHandler);
            chatInput.addEventListener('input', () => this.autoResizeInput());
        }
        
        // AIモデル選択
        const modelSelect = document.getElementById('chat-ai-model');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => this.handleModelChange());
        }
    }
    
    /**
     * メッセージ要素プール設定
     */
    setupMessagePool() {
        if (!this.messagePool && window.performanceOptimizer) {
            this.messagePool = window.performanceOptimizer.createObjectPool(
                () => this.createMessageElement(),
                (element) => this.resetMessageElement(element),
                10
            );
        }
    }
    
    /**
     * 仮想スクロール設定
     */
    setupVirtualScrolling() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages && window.performanceOptimizer) {
            // 大量のメッセージがある場合のみ仮想スクロールを適用
            const messageCount = chatMessages.children.length;
            if (messageCount > 50) {
                this.enableVirtualScrolling(chatMessages);
            }
        }
    }
    
    /**
     * マークダウン設定
     */
    setupMarkdown() {
        if (typeof marked === 'function') {
            marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false,
                sanitize: false,
                highlight: function(code, lang) {
                    if (window.hljs && lang && window.hljs.getLanguage(lang)) {
                        try {
                            return window.hljs.highlight(code, { language: lang }).value;
                        } catch (err) {}
                    }
                    return code;
                }
            });
        }
    }
    
    /**
     * チャットメッセージ送信（最適化版）
     */
    async sendChatMessage() {
        if (this.isStreaming) {
            this.showMessage('処理中です。しばらくお待ちください。', 'warning');
            return;
        }
        
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();
        
        if (!message && !this.attachedImageBase64) {
            this.showMessage('メッセージまたは画像を入力してください。', 'warning');
            return;
        }
        
        // 現在のドキュメントIDを取得
        const currentDocumentId = window.currentDocumentId;
        if (!currentDocumentId) {
            this.showMessage('ドキュメントが選択されていません。', 'error');
            return;
        }
        
        try {
            // 非同期チャット機能を使用
            if (window.asyncChatClient) {
                await window.asyncChatClient.sendMessage();
            } else {
                // フォールバック: 既存の同期処理
                await this.sendChatMessageSync(message, currentDocumentId);
            }
        } catch (error) {
            console.error('Chat error:', error);
            this.showMessage(`エラーが発生しました: ${error.message}`, 'error');
        }
    }
    
    /**
     * 同期チャット送信（フォールバック）
     */
    async sendChatMessageSync(message, documentId) {
        this.isStreaming = true;
        this.updateSendButtonState(true);
        
        // ユーザーメッセージを即座に表示
        this.addMessageToChat('user', message);
        
        // 入力フィールドをクリア
        const chatInput = document.getElementById('chat-input');
        chatInput.value = '';
        this.autoResizeInput();
        
        try {
            const requestData = {
                message: message,
                aiModel: this.currentChatModel,
                searchEnabled: this.isSearchEnabled(),
                image: this.attachedImageBase64,
                imageMimeType: this.attachedImageMimeType,
                context: this.currentChatContext,
                thinkingEnabled: this.thinkingEnabled
            };
            
            const response = await fetch(`/api/chat/send/${documentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.addMessageToChat('assistant', data.response, data.sources || []);
            } else {
                throw new Error(data.error || '不明なエラーが発生しました');
            }
            
        } finally {
            this.isStreaming = false;
            this.updateSendButtonState(false);
            this.clearAttachedImage();
        }
    }
    
    /**
     * メッセージをチャットに追加（最適化版）
     */
    addMessageToChat(role, content, sources = []) {
        // DOM操作をバッチ処理に追加
        this.pendingDOMOperations.push({
            type: 'addMessage',
            role: role,
            content: content,
            sources: sources
        });
        
        this.scheduleDOMUpdate();
    }
    
    /**
     * DOM更新のスケジューリング
     */
    scheduleDOMUpdate() {
        if (this.domUpdateScheduled) return;
        
        this.domUpdateScheduled = true;
        requestAnimationFrame(() => {
            this.processPendingDOMOperations();
            this.domUpdateScheduled = false;
        });
    }
    
    /**
     * 保留中のDOM操作を処理
     */
    processPendingDOMOperations() {
        const operations = this.pendingDOMOperations.splice(0);
        const chatMessages = document.getElementById('chat-messages');
        
        if (!chatMessages) return;
        
        // DocumentFragmentを使用してバッチ処理
        const fragment = document.createDocumentFragment();
        
        operations.forEach(op => {
            if (op.type === 'addMessage') {
                const messageElement = this.createOptimizedMessageElement(
                    op.role, op.content, op.sources
                );
                fragment.appendChild(messageElement);
            }
        });
        
        // 一度にDOMに追加
        chatMessages.appendChild(fragment);
        
        // スクロール調整（throttled）
        this.throttledScrollToBottom();
    }
    
    /**
     * 最適化されたメッセージ要素作成
     */
    createOptimizedMessageElement(role, content, sources = []) {
        // オブジェクトプールから要素を取得
        let messageElement;
        if (this.messagePool) {
            messageElement = this.messagePool.acquire();
            this.setupMessageElement(messageElement, role, content, sources);
        } else {
            messageElement = this.createMessageElementDirect(role, content, sources);
        }
        
        return messageElement;
    }
    
    /**
     * メッセージ要素を直接作成
     */
    createMessageElementDirect(role, content, sources = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (role === 'assistant') {
            // Web Workerでマークダウン処理
            if (window.asyncChatClient && window.asyncChatClient.markdownWorker) {
                const elementId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                contentDiv.id = elementId;
                
                window.asyncChatClient.markdownWorker.postMessage({
                    type: 'render',
                    content: content,
                    elementId: elementId
                });
            } else {
                // フォールバック: 同期処理
                contentDiv.innerHTML = this.renderMarkdown(content);
            }
            
            // ソース情報を追加
            if (sources && sources.length > 0) {
                const sourcesDiv = this.createSourcesElement(sources);
                messageDiv.appendChild(sourcesDiv);
            }
        } else {
            contentDiv.textContent = content;
        }
        
        messageDiv.appendChild(contentDiv);
        return messageDiv;
    }
    
    /**
     * メッセージ要素のセットアップ
     */
    setupMessageElement(element, role, content, sources = []) {
        element.className = `message ${role}-message`;
        
        const contentDiv = element.querySelector('.message-content') || 
                          element.appendChild(document.createElement('div'));
        contentDiv.className = 'message-content';
        
        if (role === 'assistant') {
            contentDiv.innerHTML = this.renderMarkdown(content);
        } else {
            contentDiv.textContent = content;
        }
    }
    
    /**
     * メッセージ要素作成
     */
    createMessageElement() {
        const messageDiv = document.createElement('div');
        const contentDiv = document.createElement('div');
        messageDiv.appendChild(contentDiv);
        return messageDiv;
    }
    
    /**
     * メッセージ要素リセット
     */
    resetMessageElement(element) {
        element.className = '';
        element.innerHTML = '';
        const contentDiv = document.createElement('div');
        element.appendChild(contentDiv);
    }
    
    /**
     * マークダウンレンダリング
     */
    renderMarkdown(content) {
        if (typeof marked === 'function') {
            return marked.parse(content);
        }
        return content.replace(/\n/g, '<br>');
    }
    
    /**
     * ソース要素作成
     */
    createSourcesElement(sources) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';
        sourcesDiv.innerHTML = '<strong>参考ソース:</strong><ul>' +
            sources.map(source => `<li><a href="${source.url}" target="_blank">${source.title}</a></li>`).join('') +
            '</ul>';
        return sourcesDiv;
    }
    
    /**
     * スロットル付きスクロール
     */
    get throttledScrollToBottom() {
        if (!this._throttledScroll) {
            this._throttledScroll = window.performanceOptimizer?.throttle(
                () => this.scrollToBottom(), 100
            ) || (() => this.scrollToBottom());
        }
        return this._throttledScroll;
    }
    
    /**
     * チャット最下部へスクロール
     */
    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    
    /**
     * 送信ボタン状態更新
     */
    updateSendButtonState(processing) {
        const sendBtn = document.getElementById('send-chat-btn');
        const chatInput = document.getElementById('chat-input');
        
        if (sendBtn) {
            sendBtn.disabled = processing;
            sendBtn.textContent = processing ? '送信中...' : '送信';
        }
        
        if (chatInput) {
            chatInput.disabled = processing;
        }
    }
    
    /**
     * チャット入力ハンドラー
     */
    handleChatInput(e) {
        if (e.key === 'Enter') {
            const isCtrlOrCmd = e.ctrlKey || e.metaKey;
            
            if (isCtrlOrCmd) {
                e.preventDefault();
                this.sendChatMessage();
            }
        }
    }
    
    /**
     * 入力フィールド自動リサイズ
     */
    autoResizeInput() {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        }
    }
    
    /**
     * AIモデル変更ハンドラー
     */
    handleModelChange() {
        const modelSelect = document.getElementById('chat-ai-model');
        if (modelSelect) {
            this.currentChatModel = modelSelect.value;
            localStorage.setItem('lastSelectedAIModel', this.currentChatModel);
            this.updateSearchToggleVisibility();
        }
    }
    
    /**
     * 最後に選択したモデルの復元
     */
    restoreLastSelectedModel() {
        const modelSelect = document.getElementById('chat-ai-model');
        if (modelSelect) {
            modelSelect.value = this.currentChatModel;
            this.updateSearchToggleVisibility();
        }
    }
    
    /**
     * 検索機能有効状態取得
     */
    isSearchEnabled() {
        const searchCheckbox = document.getElementById('search-enabled');
        return searchCheckbox ? searchCheckbox.checked : false;
    }
    
    /**
     * 検索トグル表示更新
     */
    updateSearchToggleVisibility() {
        const searchToggle = document.getElementById('search-toggle');
        if (searchToggle) {
            // Geminiの場合のみ検索機能を表示
            searchToggle.style.display = this.currentChatModel.includes('gemini') ? 'block' : 'none';
        }
    }
    
    /**
     * 添付画像クリア
     */
    clearAttachedImage() {
        this.attachedImageBase64 = null;
        this.attachedImageMimeType = null;
        
        const preview = document.getElementById('image-preview');
        if (preview) {
            preview.style.display = 'none';
        }
    }
    
    /**
     * チャット履歴リセット
     */
    async resetChatHistory() {
        if (!confirm('チャット履歴をリセットしますか？')) {
            return;
        }
        
        const currentDocumentId = window.currentDocumentId;
        if (!currentDocumentId) {
            this.showMessage('ドキュメントが選択されていません。', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/chat/reset/${currentDocumentId}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                // チャット表示をクリア
                const chatMessages = document.getElementById('chat-messages');
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                }
                
                this.showMessage('チャット履歴をリセットしました。', 'success');
            } else {
                throw new Error('リセットに失敗しました');
            }
        } catch (error) {
            console.error('Reset error:', error);
            this.showMessage('リセット中にエラーが発生しました。', 'error');
        }
    }
    
    /**
     * 仮想スクロール有効化
     */
    enableVirtualScrolling(container) {
        if (!window.performanceOptimizer) return;
        
        const messages = Array.from(container.children);
        
        this.virtualList = window.performanceOptimizer.createVirtualList(
            container,
            messages,
            (messageData, index) => {
                // メッセージ要素を再作成
                return messageData.cloneNode(true);
            }
        );
    }
    
    /**
     * メッセージ表示
     */
    showMessage(message, type = 'info') {
        if (typeof showMessage === 'function') {
            showMessage(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
}

// 既存のグローバル関数との互換性を保持
let optimizedChatManager;

// 既存の関数をラップ
function sendChatMessage() {
    return optimizedChatManager?.sendChatMessage() || console.warn('OptimizedChatManager not initialized');
}

function resetChatHistory() {
    return optimizedChatManager?.resetChatHistory() || console.warn('OptimizedChatManager not initialized');
}

function addMessageToChat(role, content, sources = []) {
    return optimizedChatManager?.addMessageToChat(role, content, sources) || console.warn('OptimizedChatManager not initialized');
}

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    // パフォーマンス最適化が利用可能になるまで待機
    const initWhenReady = () => {
        if (window.performanceOptimizer) {
            optimizedChatManager = new OptimizedChatManager();
            window.optimizedChatManager = optimizedChatManager;
        } else {
            setTimeout(initWhenReady, 100);
        }
    };
    
    initWhenReady();
});

// エクスポート
window.OptimizedChatManager = OptimizedChatManager;