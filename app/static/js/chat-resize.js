/**
 * チャットエリアのリサイズ機能を管理するスクリプト
 */

// DOMが読み込まれた後に実行
document.addEventListener('DOMContentLoaded', function() {
    setupChatResize();
});

/**
 * チャットエリアのリサイズ機能を設定
 */
function setupChatResize() {
    const handle = document.querySelector('.chat-resize-handle');
    const chatArea = document.querySelector('.chat-area');
    
    if (!handle || !chatArea) {
        console.error('リサイズハンドルまたはチャットエリアが見つかりませんでした');
        return;
    }

    // 現在のチャット幅をローカルストレージから取得（存在しない場合はCSSの変数値を使用）
    const savedWidth = localStorage.getItem('chat-area-width');
    if (savedWidth) {
        chatArea.style.width = savedWidth + 'px';
    }
    
    let isResizing = false;
    let startX;
    let startWidth;
    
    // ドラッグ開始時の処理
    handle.addEventListener('mousedown', function(e) {
        isResizing = true;
        startX = e.clientX;
        startWidth = parseInt(document.defaultView.getComputedStyle(chatArea).width, 10);
        
        // マウスカーソルのスタイルを変更
        document.body.style.cursor = 'col-resize';
        handle.style.backgroundColor = 'rgba(74, 111, 165, 0.3)'; // ハンドルの色を変更（ドラッグ中表示）
        
        e.preventDefault();
    });
    
    // ドラッグ中の処理（ウィンドウ全体でイベントを捕捉）
    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        // 新しい幅を計算（左方向にドラッグするため、startX - e.clientXを引く）
        const newWidth = startWidth - (e.clientX - startX);
        
        // 最小幅と最大幅を設定
        const minWidth = 200;
        const maxWidth = window.innerWidth - 400; // 画面幅から最低限のメインコンテンツ幅を引いた値
        
        // 幅の制限内であれば適用
        if (newWidth > minWidth && newWidth < maxWidth) {
            chatArea.style.width = newWidth + 'px';
        }
        
        e.preventDefault();
    });
    
    // ドラッグ終了時の処理
    document.addEventListener('mouseup', function() {
        if (isResizing) {
            isResizing = false;
            
            // マウスカーソルとハンドルのスタイルを元に戻す
            document.body.style.cursor = '';
            handle.style.backgroundColor = 'transparent';
            
            // 現在のチャット幅をローカルストレージに保存
            const currentWidth = parseInt(document.defaultView.getComputedStyle(chatArea).width, 10);
            localStorage.setItem('chat-area-width', currentWidth);
        }
    });
    
    // ハンドルにホバー効果を追加
    handle.addEventListener('mouseenter', function() {
        if (!isResizing) {
            handle.style.backgroundColor = 'rgba(74, 111, 165, 0.1)';
        }
    });
    
    handle.addEventListener('mouseleave', function() {
        if (!isResizing) {
            handle.style.backgroundColor = 'transparent';
        }
    });
} 