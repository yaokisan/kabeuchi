/**
 * アプリケーションのメイン処理を行うスクリプト
 * 他のモジュールを初期化し、共通の機能を提供します
 */

// デバッグモード
const DEBUG = true;

// カスタムロガー
const logger = {
    log: function(message, ...args) {
        if (DEBUG) console.log(`%c[WALL-BOUNCE] ${message}`, 'color: #4a6fa5', ...args);
    },
    warn: function(message, ...args) {
        if (DEBUG) console.warn(`%c[WALL-BOUNCE] ${message}`, 'color: #ff9800', ...args);
    },
    error: function(message, ...args) {
        if (DEBUG) console.error(`%c[WALL-BOUNCE] ${message}`, 'color: #f44336', ...args);
    }
};

// DOMが読み込まれた後に実行
document.addEventListener('DOMContentLoaded', function() {
    logger.log('アプリケーションを初期化中...');
    
    // アプリケーションの初期化
    initApp();
});

/**
 * アプリケーション全体の初期化
 */
function initApp() {
    logger.log('環境を確認中...');
    checkEnvironment();
    
    // キーボードショートカットの設定
    setupKeyboardShortcuts();
    
    // Enterキーでのフォーム送信を防止
    preventFormSubmit();
    
    // リサイズイベントのハンドリング
    handleResize();
    
    // 初期表示時にAIモデルの表示を制御
    const aiModelSelect = document.getElementById('ai-model');
    if (aiModelSelect) {
        const event = new Event('change');
        aiModelSelect.dispatchEvent(event);
        logger.log('AIモデル選択を初期化しました:', aiModelSelect.value);
    } else {
        logger.warn('AIモデル選択要素が見つかりません');
    }
}

/**
 * 環境の確認
 */
function checkEnvironment() {
    // ブラウザ環境のチェック
    logger.log('ブラウザ:', navigator.userAgent);
    
    // WebAudioサポートのチェック
    if (window.AudioContext || window.webkitAudioContext) {
        logger.log('WebAudio API: サポートされています');
    } else {
        logger.error('WebAudio API: サポートされていません');
    }
    
    // MediaRecorderサポートのチェック
    if (window.MediaRecorder) {
        logger.log('MediaRecorder API: サポートされています');
        
        // サポートされているMIMEタイプをチェック
        const mimeTypes = ['audio/webm', 'audio/ogg', 'audio/wav', 'audio/mp4'];
        const supportedTypes = mimeTypes.filter(type => {
            try {
                return MediaRecorder.isTypeSupported(type);
            } catch (e) {
                return false;
            }
        });
        logger.log('サポートされている音声形式:', supportedTypes.join(', ') || 'なし');
        
    } else {
        logger.error('MediaRecorder API: サポートされていません');
    }
    
    // WebSocket (Socket.IO) サポートのチェック
    if (window.io) {
        logger.log('Socket.IO: ライブラリが読み込まれています');
    } else {
        logger.error('Socket.IO: ライブラリが読み込まれていません');
    }
}

/**
 * キーボードショートカットの設定
 */
function setupKeyboardShortcuts() {
    logger.log('キーボードショートカットを設定中...');
    
    document.addEventListener('keydown', function(e) {
        // Ctrl+S または Cmd+S でドキュメント保存
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            logger.log('ショートカット検出: Ctrl/Cmd+S (保存)');
            
            if (typeof saveDocument === 'function') {
                saveDocument();
            }
        }
        
        // Esc キーでモーダルを閉じる
        if (e.key === 'Escape') {
            logger.log('ショートカット検出: Escape');
            
            const modal = document.getElementById('modal-container');
            if (modal && modal.style.display === 'flex') {
                e.preventDefault();
                logger.log('モーダルを閉じます');
                
                if (typeof hideModal === 'function') {
                    hideModal();
                } else {
                    modal.style.display = 'none';
                }
            }
            
            // 音声認識オーバーレイを閉じる
            const speechOverlay = document.getElementById('speech-overlay');
            if (speechOverlay && speechOverlay.style.display === 'flex') {
                e.preventDefault();
                logger.log('音声認識オーバーレイを閉じます');
                
                if (typeof showSpeechOverlay === 'function') {
                    showSpeechOverlay(false);
                } else {
                    speechOverlay.style.display = 'none';
                }
            }
        }
    });
}

/**
 * フォームのデフォルト送信を防止
 */
function preventFormSubmit() {
    document.addEventListener('submit', function(e) {
        // 明示的に送信するフォーム以外は送信を防止
        if (!e.target.hasAttribute('data-submit-form')) {
            e.preventDefault();
            logger.log('フォームのデフォルト送信を防止しました');
        }
    });
}

/**
 * リサイズイベントのハンドリング
 */
function handleResize() {
    // 初期リサイズ
    adjustLayoutForScreenSize();
    
    // ウィンドウサイズ変更時
    window.addEventListener('resize', function() {
        adjustLayoutForScreenSize();
    });
}

/**
 * 画面サイズに応じたレイアウト調整
 */
function adjustLayoutForScreenSize() {
    const width = window.innerWidth;
    
    // 小さい画面サイズの場合、レイアウトを調整
    if (width < 768) {
        // モバイル向けの調整
        document.body.classList.add('mobile-view');
        logger.log('モバイルビューに調整しました', width);
    } else {
        document.body.classList.remove('mobile-view');
        logger.log('デスクトップビューに調整しました', width);
    }
}

/**
 * 日付をフォーマット
 * @param {Date|string} date - フォーマットする日付（DateオブジェクトまたはISO形式の文字列）
 * @param {boolean} withTime - 時刻も含めるかどうか
 * @returns {string} フォーマット済みの日付文字列
 */
function formatDate(date, withTime = true) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    
    if (withTime) {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    } else {
        return `${year}-${month}-${day}`;
    }
}

/**
 * テキストを省略して表示
 * @param {string} text - 元のテキスト
 * @param {number} maxLength - 最大文字数
 * @returns {string} 省略されたテキスト
 */
function truncateText(text, maxLength = 50) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    
    return text.substring(0, maxLength) + '...';
}

/**
 * HTMLをエスケープ
 * @param {string} html - エスケープするHTML文字列
 * @returns {string} エスケープされた文字列
 */
function escapeHTML(html) {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}

/**
 * エラー通知を表示
 * @param {string} message - エラーメッセージ
 * @param {number} duration - 表示時間（ミリ秒）
 */
function showNotification(message, duration = 3000) {
    logger.log('通知を表示します:', message);
    
    // 既存の通知があれば削除
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 新しい通知を作成
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    
    // bodyに追加
    document.body.appendChild(notification);
    
    // 表示アニメーション
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // 指定時間後に非表示
    setTimeout(() => {
        notification.classList.remove('show');
        
        // 非表示アニメーション後に削除
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, duration);
}

// グローバルに公開
window.appUtils = {
    logger,
    formatDate,
    truncateText,
    escapeHTML,
    showNotification
}; 