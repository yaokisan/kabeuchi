/**
 * Web Worker for Markdown Processing
 * マークダウン処理を非同期で実行してメインスレッドをブロックしない
 */

// マークダウンライブラリの簡易実装（Web Worker内で使用）
const simpleMarkdown = {
    parse: function(text) {
        // 基本的なマークダウン変換
        return text
            // ヘッダー
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            
            // 太字・斜体
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            
            // コードブロック
            .replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            
            // リスト
            .replace(/^\\* (.+)$/gm, '<li>$1</li>')
            .replace(/(<li>.*<\\/li>)/s, '<ul>$1</ul>')
            
            // 改行
            .replace(/\\n/g, '<br>')
            
            // リンク
            .replace(/\\[([^\\]]+)\\]\\(([^\\)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    }
};

// メッセージハンドラー
self.onmessage = function(e) {
    const { type, content, elementId } = e.data;
    
    try {
        let html;
        
        // マークダウン変換
        if (typeof marked !== 'undefined') {
            // marked.js が利用可能な場合
            html = marked.parse(content);
        } else {
            // フォールバック: 簡易マークダウン処理
            html = simpleMarkdown.parse(content);
        }
        
        // シンタックスハイライト対応
        html = addSyntaxHighlightingClasses(html);
        
        // 結果を返送
        self.postMessage({
            type: 'rendered',
            elementId: elementId,
            html: html,
            processingTime: Date.now()
        });
        
    } catch (error) {
        // エラー処理
        self.postMessage({
            type: 'error',
            elementId: elementId,
            error: error.message,
            content: content.replace(/\\n/g, '<br>') // フォールバック
        });
    }
};

/**
 * シンタックスハイライト用のクラスを追加
 */
function addSyntaxHighlightingClasses(html) {
    // pre code タグにハイライト用クラスを追加
    return html.replace(
        /<pre><code([^>]*)>/g, 
        '<pre><code$1 class="hljs">'
    );
}

/**
 * コードブロックの言語検出
 */
function detectCodeLanguage(code) {
    // 簡単な言語検出ロジック
    if (code.includes('function') && code.includes('{')) return 'javascript';
    if (code.includes('def ') && code.includes(':')) return 'python';
    if (code.includes('public class')) return 'java';
    if (code.includes('#include')) return 'cpp';
    if (code.includes('SELECT') || code.includes('INSERT')) return 'sql';
    if (code.includes('<html>') || code.includes('<div>')) return 'html';
    if (code.includes('{') && code.includes('color:')) return 'css';
    return 'plaintext';
}

/**
 * パフォーマンス最適化: 大きなテキストの分割処理
 */
function processLargeText(text, chunkSize = 5000) {
    if (text.length <= chunkSize) {
        return simpleMarkdown.parse(text);
    }
    
    // チャンク単位で処理
    const chunks = [];
    for (let i = 0; i < text.length; i += chunkSize) {
        const chunk = text.slice(i, i + chunkSize);
        chunks.push(simpleMarkdown.parse(chunk));
    }
    
    return chunks.join('');
}

// エラーハンドリング
self.onerror = function(error) {
    self.postMessage({
        type: 'worker_error',
        error: error.message,
        filename: error.filename,
        lineno: error.lineno
    });
};

// 初期化完了を通知
self.postMessage({
    type: 'worker_ready',
    timestamp: Date.now()
});