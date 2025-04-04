/**
 * ドキュメント管理ページの機能を管理するスクリプト
 */

// DOMが読み込まれた後に実行
document.addEventListener('DOMContentLoaded', function() {
    loadDocuments();
    setupEventListeners();
});

/**
 * 全てのドキュメントを読み込んで表示
 */
function loadDocuments() {
    fetch('/api/document/list')
        .then(response => response.json())
        .then(documents => {
            renderDocuments(documents);
        })
        .catch(error => {
            console.error('ドキュメント一覧の取得に失敗しました:', error);
            showError('ドキュメント一覧の読み込みに失敗しました。ページを再読み込みしてください。');
        });
}

/**
 * ドキュメント一覧をグリッドに表示
 * @param {Array} documents - ドキュメントの配列
 */
function renderDocuments(documents) {
    const grid = document.getElementById('documents-grid');
    
    // スケルトンローディングを削除
    grid.innerHTML = '';
    
    if (documents.length === 0) {
        grid.innerHTML = '<div class="no-documents">ドキュメントがありません。新規ドキュメントを作成してください。</div>';
        return;
    }
    
    // ドキュメントをカードとして表示
    documents.forEach(doc => {
        const card = createDocumentCard(doc);
        grid.appendChild(card);
    });
}

/**
 * ドキュメントカードのHTML要素を作成
 * @param {Object} doc - ドキュメントオブジェクト
 * @returns {HTMLElement} ドキュメントカード要素
 */
function createDocumentCard(doc) {
    const card = document.createElement('div');
    card.className = 'document-card';
    card.dataset.id = doc.id;
    
    // 日付フォーマット（日本時間 JST で表示）
    const updatedDate = new Date(doc.updated_at);
    // JST = UTC+9時間
    const jpDate = new Date(updatedDate.getTime() + (9 * 60 * 60 * 1000));
    const formattedDate = `${jpDate.getFullYear()}-${(jpDate.getMonth()+1).toString().padStart(2, '0')}-${jpDate.getDate().toString().padStart(2, '0')} ${jpDate.getHours().toString().padStart(2, '0')}:${jpDate.getMinutes().toString().padStart(2, '0')}`;
    
    // ドキュメント内容のプレビューを作成（HTMLタグを除去）
    let contentPreview = '';
    try {
        if (doc.content) {
            const contentObj = JSON.parse(doc.content);
            if (contentObj.ops && contentObj.ops.length > 0) {
                contentPreview = contentObj.ops
                    .filter(op => typeof op.insert === 'string')
                    .map(op => op.insert)
                    .join('')
                    .substring(0, 150);
            }
        }
    } catch (e) {
        contentPreview = '内容を表示できません';
    }
    
    if (!contentPreview) {
        contentPreview = '内容がありません';
    }
    
    card.innerHTML = `
        <div class="document-card-header">
            <h3>${escapeHtml(doc.title)}</h3>
            <p>更新日時: ${formattedDate}</p>
        </div>
        <div class="document-card-content">${escapeHtml(contentPreview)}</div>
        <div class="document-card-actions">
            <button class="primary-btn open-btn" data-id="${doc.id}">開く</button>
            <button class="secondary-btn rename-btn" data-id="${doc.id}">タイトル変更</button>
            <button class="secondary-btn duplicate-btn" data-id="${doc.id}">複製</button>
            <button class="secondary-btn delete-btn" data-id="${doc.id}">削除</button>
        </div>
    `;
    
    return card;
}

/**
 * ドキュメント管理ページのイベントリスナーを設定
 */
function setupEventListeners() {
    const grid = document.getElementById('documents-grid');
    
    // 各種ボタンのクリックイベントをデリゲート
    grid.addEventListener('click', function(e) {
        const target = e.target;
        const docId = target.dataset.id;
        
        if (!docId) return;
        
        // ドキュメントを開く
        if (target.classList.contains('open-btn')) {
            // 新しいURLに完全に移動する
            e.preventDefault();
            console.log('ドキュメントを開きます:', docId);
            
            // リダイレクト
            window.location.replace(`/?id=${docId}`);
        }
        
        // タイトル変更
        if (target.classList.contains('rename-btn')) {
            showRenameModal(docId);
        }
        
        // ドキュメントを複製
        if (target.classList.contains('duplicate-btn')) {
            duplicateDocument(docId);
        }
        
        // ドキュメントを削除
        if (target.classList.contains('delete-btn')) {
            confirmDeleteDocument(docId);
        }
    });
    
    // 新規ドキュメント作成ボタン
    document.getElementById('new-doc-btn').addEventListener('click', function() {
        // 新規作成時は、最後にアクティブだったIDをクリアする
        localStorage.removeItem('lastActiveDocumentId');
        createNewDocument();
    });
    
    // 検索ボックス
    document.getElementById('doc-search').addEventListener('input', function() {
        filterDocuments(this.value);
    });
    
    // 並び替え
    document.getElementById('sort-select').addEventListener('change', function() {
        sortDocuments(this.value);
    });
    
    // モーダルの閉じるボタン
    document.getElementById('modal-close').addEventListener('click', function() {
        hideModal();
    });
    
    // モーダルのキャンセルボタン
    document.getElementById('modal-cancel').addEventListener('click', function() {
        hideModal();
    });
    
    // リネーム確定ボタン
    document.getElementById('modal-confirm').addEventListener('click', function() {
        const docId = document.getElementById('modal-input').dataset.docId;
        const newTitle = document.getElementById('modal-input').value;
        
        if (docId && newTitle) {
            renameDocument(docId, newTitle);
        }
        
        hideModal();
    });
}

/**
 * ドキュメントのタイトル変更モーダルを表示
 * @param {string} docId - ドキュメントID
 */
function showRenameModal(docId) {
    // 現在のタイトルを取得
    const docCard = document.querySelector(`.document-card[data-id="${docId}"]`);
    const currentTitle = docCard ? docCard.querySelector('h3').textContent : '';
    
    const modalInput = document.getElementById('modal-input');
    modalInput.value = currentTitle;
    modalInput.dataset.docId = docId;
    
    document.getElementById('modal-title').textContent = 'タイトル変更';
    document.getElementById('modal-confirm').textContent = '保存';
    
    document.getElementById('modal-container').style.display = 'flex';
    modalInput.focus();
    modalInput.select();
}

/**
 * モーダルを非表示にする
 */
function hideModal() {
    document.getElementById('modal-container').style.display = 'none';
}

/**
 * ドキュメントのタイトルを変更
 * @param {string} docId - ドキュメントID
 * @param {string} newTitle - 新しいタイトル
 */
function renameDocument(docId, newTitle) {
    // 空のタイトルの場合はデフォルト値を設定
    if (!newTitle.trim()) {
        newTitle = '無題のドキュメント';
    }
    
    fetch(`/api/document/${docId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: newTitle
        })
    })
    .then(response => response.json())
    .then(updatedDoc => {
        // 成功したら、UIを更新
        const docCard = document.querySelector(`.document-card[data-id="${docId}"]`);
        if (docCard) {
            docCard.querySelector('h3').textContent = updatedDoc.title;
        }
    })
    .catch(error => {
        console.error('タイトル変更に失敗しました:', error);
        showError('タイトルの変更に失敗しました。もう一度お試しください。');
    });
}

/**
 * ドキュメントを複製
 * @param {string} docId - ドキュメントID
 */
function duplicateDocument(docId) {
    fetch(`/api/document/${docId}/duplicate`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(newDoc => {
        // 新しいドキュメントカードを作成
        const card = createDocumentCard(newDoc);
        
        // グリッドの先頭に追加
        const grid = document.getElementById('documents-grid');
        grid.insertBefore(card, grid.firstChild);
    })
    .catch(error => {
        console.error('ドキュメントの複製に失敗しました:', error);
        showError('ドキュメントの複製に失敗しました。もう一度お試しください。');
    });
}

/**
 * ドキュメント削除の確認ダイアログを表示
 * @param {string} docId - ドキュメントID
 */
function confirmDeleteDocument(docId) {
    const docCard = document.querySelector(`.document-card[data-id="${docId}"]`);
    const title = docCard ? docCard.querySelector('h3').textContent : 'このドキュメント';
    
    if (confirm(`「${title}」を削除してもよろしいですか？この操作は取り消せません。`)) {
        deleteDocument(docId);
    }
}

/**
 * ドキュメントを削除
 * @param {string} docId - ドキュメントID
 */
function deleteDocument(docId) {
    fetch(`/api/document/${docId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(() => {
        // 成功したら、UIから削除
        const docCard = document.querySelector(`.document-card[data-id="${docId}"]`);
        if (docCard) {
            docCard.remove();
        }
        
        // ドキュメントがなくなった場合のメッセージ表示
        const grid = document.getElementById('documents-grid');
        if (grid.children.length === 0) {
            grid.innerHTML = '<div class="no-documents">ドキュメントがありません。新規ドキュメントを作成してください。</div>';
        }
    })
    .catch(error => {
        console.error('ドキュメントの削除に失敗しました:', error);
        showError('ドキュメントの削除に失敗しました。もう一度お試しください。');
    });
}

/**
 * 新規ドキュメントを作成
 */
function createNewDocument() {
    fetch('/api/document/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: '無題のドキュメント',
            content: ''
        })
    })
    .then(response => response.json())
    .then(newDoc => {
        // 作成したドキュメントのページに移動
        window.location.href = `/?id=${newDoc.id}`;
    })
    .catch(error => {
        console.error('新規ドキュメントの作成に失敗しました:', error);
        showError('新規ドキュメントの作成に失敗しました。もう一度お試しください。');
    });
}

/**
 * ドキュメントをタイトルでフィルタリング
 * @param {string} query - 検索クエリ
 */
function filterDocuments(query) {
    // 全てのドキュメントカードを取得
    const cards = document.querySelectorAll('.document-card');
    
    query = query.toLowerCase();
    
    cards.forEach(card => {
        const title = card.querySelector('h3').textContent.toLowerCase();
        const content = card.querySelector('.document-card-content').textContent.toLowerCase();
        
        // タイトルまたは内容に検索クエリが含まれている場合は表示、それ以外は非表示
        if (title.includes(query) || content.includes(query)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * ドキュメントを並び替え
 * @param {string} sortBy - 並び替え基準
 */
function sortDocuments(sortBy) {
    const grid = document.getElementById('documents-grid');
    const cards = Array.from(grid.querySelectorAll('.document-card'));
    
    if (cards.length === 0) return;
    
    // カードを一旦削除
    grid.innerHTML = '';
    
    // 並び替え
    cards.sort((a, b) => {
        const titleA = a.querySelector('h3').textContent;
        const titleB = b.querySelector('h3').textContent;
        const dateA = new Date(a.querySelector('p').textContent.replace('更新日時: ', ''));
        const dateB = new Date(b.querySelector('p').textContent.replace('更新日時: ', ''));
        
        switch (sortBy) {
            case 'title_asc':
                return titleA.localeCompare(titleB);
            case 'title_desc':
                return titleB.localeCompare(titleA);
            case 'updated_asc':
                return dateA - dateB;
            case 'updated_desc':
            default:
                return dateB - dateA;
        }
    });
    
    // 並び替えたカードを再挿入
    cards.forEach(card => {
        grid.appendChild(card);
    });
}

/**
 * エラーメッセージを表示
 * @param {string} message - エラーメッセージ
 */
function showError(message) {
    alert(message);
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