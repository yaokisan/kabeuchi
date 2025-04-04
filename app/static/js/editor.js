/**
 * エディタの初期化と管理を行うスクリプト
 */

// グローバル変数
let editor;
let currentDocumentId = null;
let saveTimeout = null;
const AUTO_SAVE_DELAY = 2000; // 自動保存の遅延時間（ミリ秒）

// DOMが読み込まれた後に実行
document.addEventListener('DOMContentLoaded', function() {
    console.log('ページが読み込まれました');
    
    try {
        // エディタ初期化
        initEditor();
        setupDocumentEvents();
        
        // 最近のドキュメント一覧を読み込む
        loadRecentDocuments();
        
        // URLからドキュメントIDを取得
        const urlParams = new URLSearchParams(window.location.search);
        const docIdFromUrl = urlParams.get('id');
        
        console.log('URL パラメータからドキュメントID:', docIdFromUrl);
        
        if (docIdFromUrl) {
            // URLにIDがあればそれを読み込む
            loadDocument(docIdFromUrl);
        } else {
            // URLにIDがない場合、ローカルストレージから最後のIDを取得
            const lastActiveDocId = localStorage.getItem('lastActiveDocumentId');
            console.log('ローカルストレージから最後のドキュメントID:', lastActiveDocId);
            
            if (lastActiveDocId) {
                // 最後にアクティブだったドキュメントを読み込む（リダイレクト）
                // loadDocument を直接呼ぶのではなくリダイレクトすることで、ページ状態を確実に更新
                window.location.replace(`/?id=${lastActiveDocId}`);
            } else {
                // URLにもローカルストレージにもIDがない場合、最新ドキュメントを読み込むか新規作成
                loadLatestDocumentOrShowEmpty();
            }
        }
    } catch (error) {
        console.error('ページ初期化中にエラーが発生しました:', error);
        // 重大なエラーの場合、ユーザーに通知
        alert('アプリケーションの初期化中にエラーが発生しました。ページをリロードしてください。');
    }
});

/**
 * Quillエディタを初期化
 */
function initEditor() {
    // Quillエディタのツールバーオプション
    const toolbarOptions = [
        ['bold', 'italic', 'underline', 'strike'],
        ['blockquote', 'code-block'],
        [{ 'header': 1 }, { 'header': 2 }],
        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
        [{ 'script': 'sub'}, { 'script': 'super' }],
        [{ 'indent': '-1'}, { 'indent': '+1' }],
        [{ 'size': ['small', false, 'large', 'huge'] }],
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
        [{ 'color': [] }, { 'background': [] }],
        [{ 'font': [] }],
        [{ 'align': [] }],
        ['clean']
    ];
    
    // Quillエディタの初期化
    editor = new Quill('#editor-container', {
        modules: {
            toolbar: toolbarOptions,
            clipboard: { /* 前回の clipboard 設定は一旦削除 or コメントアウト */ }
        },
        placeholder: 'ここに内容を入力してください...',
        theme: 'snow'
    });
    
    // --- ここから「AIチャットに追加」ボタンの動的生成 --- 
    let addToChatBtn = null; // ボタン要素の参照を保持する変数
    try {
        addToChatBtn = document.createElement('button');
        addToChatBtn.id = 'add-to-chat-btn';
        addToChatBtn.textContent = 'AIチャットに追加';
        addToChatBtn.className = 'secondary-btn'; // 既存のCSSクラスを適用
        // 初期スタイル (非表示、右上配置)
        addToChatBtn.style.display = 'none';
        addToChatBtn.style.position = 'absolute'; // エディタコンテナ基準
        addToChatBtn.style.top = '5px'; 
        addToChatBtn.style.right = '5px';
        addToChatBtn.style.zIndex = '10'; 
        addToChatBtn.style.padding = '3px 8px'; // 少し小さく
        addToChatBtn.style.fontSize = '11px'; // 少し小さく

        // クリックイベントリスナーを設定 (ボタン生成直後に設定)
        addToChatBtn.addEventListener('click', function() {
            const selection = editor.getSelection();
            if (selection && selection.length > 0) {
                const selectedText = editor.getText(selection.index, selection.length);
                console.log("追加するテキスト:", selectedText);
                if (typeof window.chatAPI !== 'undefined' && typeof window.chatAPI.setContext === 'function') {
                    window.chatAPI.setContext(selectedText);
                    this.style.display = 'none'; // ボタンを非表示
                    editor.setSelection(null); // 選択解除
                } else {
                    console.error('window.chatAPI または window.chatAPI.setContext 関数が見つかりません。');
                    alert('チャット機能との連携中にエラーが発生しました。');
                }
            }
        });

        // 作成したボタンをエディタコンテナに追加
        if (editor.container) {
             editor.container.appendChild(addToChatBtn);
             console.log("動的に生成したボタンをエディタコンテナに追加しました。");
        } else {
             console.error("editor.container が見つからず、ボタンを追加できませんでした。");
        }

    } catch (e) {
        console.error("ボタンの動的生成または追加中にエラー:", e);
    }
    // --- ボタンの動的生成 ここまで ---

    // エディタの変更を検知して自動保存
    editor.on('text-change', function() {
        updateSaveStatus('保存中...');
        
        // エディタの内容が変更されたら、新規作成済みフラグをクリア
        sessionStorage.removeItem('emptyDocumentCreated');
        
        // 一定時間後に保存処理を実行（タイピング中の頻繁な保存を防ぐ）
        if (saveTimeout) {
            clearTimeout(saveTimeout);
        }
        
        saveTimeout = setTimeout(function() {
            if (currentDocumentId) {
                saveDocument();
            }
        }, AUTO_SAVE_DELAY);
    });
    
    // イベントリスナー設定を少し遅延させる
    setTimeout(() => {
        console.log("遅延後にリスナー設定を開始します。");

        // 選択範囲の変更を検知して「AIチャットに追加」ボタンの表示/非表示
        editor.on('selection-change', function(range, oldRange, source) {
            console.log("selection-change 発火: ", { range: range, source: source });
            
            // 動的に生成されたボタン要素の参照を使用 (addToChatBtn 変数)
            if (addToChatBtn) { // ボタン要素の参照が存在するか確認
                if (range && range.length > 0) {
                    console.log("テキスト選択検知、ボタン表示試行");
                    // ボタンは右上固定なので位置計算は不要
                    addToChatBtn.style.display = 'block'; 
                } else {
                    console.log("選択解除または空、ボタン非表示");
                    addToChatBtn.style.display = 'none';
                }
            } else {
                 console.warn("動的に生成されたボタンの参照が見つかりません (selection-change)");
            }
        });
        
        // 「AIチャットに追加」ボタンのクリックイベントリスナーは既に上で設定済み
        // const buttonElementForListener = editor.container.querySelector('#add-to-chat-btn'); // 不要
        // if (buttonElementForListener) { ... } // 不要

    }, 100); // 100ミリ秒後に実行
}

/**
 * ドキュメント関連のイベントを設定
 */
function setupDocumentEvents() {
    // 新規ドキュメント作成ボタン
    document.getElementById('new-document-btn').addEventListener('click', function() {
        if (confirm('新しいドキュメントを作成しますか？現在の内容は保存されます。')) {
            saveDocument(); // 現在の内容を保存
            createNewDocument();
        }
    });
    
    // 手動保存ボタン
    document.getElementById('save-document-btn').addEventListener('click', function() {
        if (currentDocumentId) {
            saveDocument();
            updateSaveStatus('手動保存中...');
        } else {
            // ドキュメントIDがない場合は新規作成してから保存
            createNewDocument();
        }
    });
    
    // ドキュメントタイトル変更イベント
    document.getElementById('document-title').addEventListener('blur', function() {
        if (currentDocumentId) {
            updateDocumentTitle(this.value);
        }
    });
    
    // Enterキーでタイトル入力を確定
    document.getElementById('document-title').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this.blur();
        }
    });
}

/**
 * 最近更新されたドキュメントをサイドバーに読み込む
 */
function loadRecentDocuments() {
    fetch('/api/document/recent')
        .then(response => response.json())
        .then(documents => {
            const recentDocsList = document.getElementById('recent-docs-list');
            recentDocsList.innerHTML = '';
            
            if (documents.length === 0) {
                recentDocsList.innerHTML = '<li>最近のドキュメントはありません</li>';
                return;
            }
            
            documents.forEach(doc => {
                const li = document.createElement('li');
                li.dataset.id = doc.id;
                
                // 日付フォーマット（日本時間 JST で表示）
                const date = new Date(doc.updated_at);
                // JST = UTC+9時間
                const jpDate = new Date(date.getTime() + (9 * 60 * 60 * 1000));
                const formattedDate = `${jpDate.getFullYear()}-${(jpDate.getMonth()+1).toString().padStart(2, '0')}-${jpDate.getDate().toString().padStart(2, '0')} ${jpDate.getHours().toString().padStart(2, '0')}:${jpDate.getMinutes().toString().padStart(2, '0')}`;
                
                li.innerHTML = `
                    <div class="doc-title">${doc.title}</div>
                    <div class="doc-date">${formattedDate}</div>
                `;
                
                li.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('サイドバーからドキュメントを開きます:', doc.id);
                    
                    // 確実にセッションストレージをクリア
                    sessionStorage.removeItem('emptyDocumentCreated'); 
                    
                    // より確実なリダイレクト方法を使用
                    window.location.replace(`/?id=${doc.id}`);
                });
                
                recentDocsList.appendChild(li);
            });
        })
        .catch(error => {
            console.error('ドキュメント一覧の取得に失敗しました:', error);
        });
}

/**
 * 指定されたIDのドキュメントを読み込む
 * @param {number} docId - ドキュメントID
 */
function loadDocument(docId) {
    // docIdが空や無効な値の場合は処理しない
    if (!docId || isNaN(parseInt(docId))) {
        console.error('無効なドキュメントIDです:', docId);
        return;
    }

    // セッションストレージの新規作成フラグをクリア
    sessionStorage.removeItem('emptyDocumentCreated');
    // 最後にアクティブだったIDをローカルストレージに保存
    localStorage.setItem('lastActiveDocumentId', docId);

    fetch(`/api/document/${docId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('ドキュメントが見つかりません');
            }
            return response.json();
        })
        .then(docData => {
            // レスポンスが空の場合またはIDが一致しない場合はエラー
            if (!docData || docData.id != docId) {
                throw new Error('不正なドキュメントデータです');
            }

            currentDocumentId = docData.id;
            
            // タイトルを設定
            document.getElementById('document-title').value = docData.title;
            
            // エディタの内容を設定
            try {
                if (docData.content) {
                    editor.setContents(JSON.parse(docData.content));
                } else {
                    editor.setContents([]);
                }
            } catch (err) {
                console.error('ドキュメント内容の解析に失敗しました:', err);
                editor.setContents([]);
            }
            
            // URLを更新（既に正しいURLのはずだが念のため）
            window.history.pushState({}, '', `/?id=${docData.id}`);
            
            // チャット履歴を読み込む
            if (typeof loadChatHistory === 'function') {
                loadChatHistory(docId);
            }
            
            // 最後に選択されたAIモデルを復元（存在する場合）
            if (typeof restoreLastSelectedModel === 'function') {
                restoreLastSelectedModel();
            }
            
            updateSaveStatus('保存済み');
        })
        .catch(error => {
            console.error('ドキュメントの読み込みに失敗しました:', error);
            updateSaveStatus('エラー: ' + error.message);
            
            // エラー時にエディタを空にし、ローカルストレージのIDも削除
            editor.setContents([]);
            document.getElementById('document-title').value = '';
            currentDocumentId = null;
            localStorage.removeItem('lastActiveDocumentId');
        });
}

/**
 * 新規ドキュメントを作成
 */
function createNewDocument() {
    console.log('新規ドキュメントを作成します');
    
    // 新規ドキュメントのデフォルト値
    const defaultTitle = '無題のドキュメント';
    
    fetch('/api/document/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: defaultTitle,
            content: ''
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('新規ドキュメントの作成に失敗しました');
        }
        return response.json();
    })
    .then(docData => {
        console.log('新規ドキュメントが作成されました:', docData.id);
        
        // セッションストレージをクリア
        sessionStorage.removeItem('emptyDocumentCreated');
        // 最後にアクティブだったIDとしてローカルストレージに保存
        localStorage.setItem('lastActiveDocumentId', docData.id);
        
        currentDocumentId = docData.id;
        
        // タイトルとエディタの内容を設定
        document.getElementById('document-title').value = docData.title;
        editor.setContents([]);
        
        // URLを更新
        window.history.pushState({}, '', `/?id=${docData.id}`);
        
        // 最近のドキュメント一覧を更新
        loadRecentDocuments();
        
        // チャット履歴をクリア（または新しいドキュメント用に読み込み）
        if (typeof loadChatHistory === 'function') {
            loadChatHistory(docData.id);
        } else {
            // loadChatHistory関数がない場合、手動でチャットUIをクリア
            const chatMessages = document.getElementById('chat-messages');
            if (chatMessages) chatMessages.innerHTML = '';
        }
        
        updateSaveStatus('保存済み');
    })
    .catch(error => {
        console.error('新規ドキュメントの作成に失敗しました:', error);
        updateSaveStatus('エラー: ' + error.message);
        
        // エラー時にエディタを空にする
        editor.setContents([]);
        document.getElementById('document-title').value = '';
        currentDocumentId = null;
    });
}

/**
 * 現在のドキュメントを保存
 */
function saveDocument() {
    if (!currentDocumentId) {
        console.error('ドキュメントIDがありません。保存できません。');
        updateSaveStatus('保存エラー: ドキュメントIDがありません');
        return;
    }
    
    console.log('ドキュメントを保存します:', currentDocumentId);
    
    const content = JSON.stringify(editor.getContents());
    
    fetch(`/api/document/${currentDocumentId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            content: content
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('ドキュメントの保存に失敗しました');
        }
        return response.json();
    })
    .then(result => {
        console.log('ドキュメントが保存されました:', currentDocumentId);
        updateSaveStatus('保存済み');
    })
    .catch(error => {
        console.error('ドキュメントの保存に失敗しました:', error);
        updateSaveStatus('保存エラー: ' + error.message);
    });
}

/**
 * ドキュメントのタイトルを更新
 * @param {string} newTitle - 新しいタイトル
 */
function updateDocumentTitle(newTitle) {
    if (!currentDocumentId) return;
    
    // タイトルが変更されたら、新規作成済みフラグをクリア
    sessionStorage.removeItem('emptyDocumentCreated');
    
    // 空のタイトルの場合はデフォルト値を設定
    if (!newTitle.trim()) {
        newTitle = '無題のドキュメント';
        // タイトル入力欄の値を直接更新しない（二重更新の防止）
        // document.getElementById('document-title').value = newTitle;
    }
    
    updateSaveStatus('保存中...');
    
    fetch(`/api/document/${currentDocumentId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: newTitle
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('タイトルの更新に失敗しました');
        }
        return response.json();
    })
    .then(docData => {
        updateSaveStatus('保存済み');
        
        // サーバーから返されたタイトルを使用して入力欄を更新
        if (docData && docData.title) {
            document.getElementById('document-title').value = docData.title;
        }
        
        // 最近のドキュメント一覧を更新
        loadRecentDocuments();
    })
    .catch(error => {
        console.error('タイトルの更新に失敗しました:', error);
        updateSaveStatus('保存エラー: ' + error.message);
    });
}

/**
 * 保存ステータスを更新
 * @param {string} status - 表示するステータスメッセージ
 */
function updateSaveStatus(status) {
    const saveStatus = document.getElementById('save-status');
    saveStatus.textContent = status;
    
    if (status === '保存済み') {
        saveStatus.style.color = 'var(--success-color)';
    } else if (status.includes('エラー')) {
        saveStatus.style.color = 'var(--error-color)';
    } else {
        saveStatus.style.color = 'var(--text-light)';
    }
}

/**
 * テキストをエディタの現在のカーソル位置に挿入
 * @param {string} text - 挿入するテキスト
 */
function insertTextAtCursor(text) {
    if (!editor) return;
    
    const selection = editor.getSelection();
    if (selection) {
        editor.insertText(selection.index, text);
    } else {
        // 選択がない場合は最後に挿入
        editor.insertText(editor.getLength() - 1, text);
    }
}

/**
 * 最新のドキュメントを読み込むか、存在しない場合は新規作成フローを開始
 */
function loadLatestDocumentOrShowEmpty() {
    console.log('最新のドキュメントIDを取得します...');
    fetch('/api/document/latest_id')
        .then(response => {
            if (!response.ok) {
                // 404 Not Found などはドキュメントがないケースとして扱う
                if (response.status === 404) {
                    return null; // ドキュメントなし
                }
                throw new Error('最新ドキュメントIDの取得に失敗しました');
            }
            return response.json();
        })
        .then(data => {
            if (data && data.latest_id) {
                console.log('最新ドキュメントIDが見つかりました:', data.latest_id);
                // 最新ドキュメントにリダイレクト
                window.location.replace(`/?id=${data.latest_id}`);
            } else {
                console.log('利用可能なドキュメントがありません。新規作成フローを開始します。');
                // ドキュメントが存在しない場合、新規作成フローへ
                // セッションストレージに新規作成済みフラグがある場合はスキップ
                if (sessionStorage.getItem('emptyDocumentCreated')) {
                    console.log('新規未編集ドキュメントが既に存在します - 作成をスキップ');
                    editor.setContents([]);
                    document.getElementById('document-title').value = '';
                    currentDocumentId = null;
                    updateSaveStatus('新規作成をスキップしました');
                } else {
                    // 新規ドキュメントを作成し、フラグをセット
                    createNewDocument();
                    sessionStorage.setItem('emptyDocumentCreated', 'true');
                }
            }
        })
        .catch(error => {
            console.error('最新ドキュメントの処理中にエラー:', error);
            // エラーが発生した場合も新規作成フローへ（フォールバック）
            if (!sessionStorage.getItem('emptyDocumentCreated')) {
                createNewDocument();
                sessionStorage.setItem('emptyDocumentCreated', 'true');
            }
        });
}

// 他のJSファイルから使用できるようにグローバルに公開
window.editorAPI = {
    getCurrentDocumentId: function() {
        return currentDocumentId;
    },
    insertTextAtCursor: insertTextAtCursor,
    getEditorContents: function() {
        return editor ? editor.getContents() : null;
    }
}; 