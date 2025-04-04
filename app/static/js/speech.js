/**
 * 音声認識機能を管理するスクリプト
 */

// グローバル変数
let socket;
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let silenceTimeout = null;
let silenceStartTime = null;
let SILENCE_THRESHOLD = 0.01; // 無音判定の閾値
let SILENCE_DURATION = 1000; // 無音と判断する時間（ミリ秒）
let analyserNode;
let audioContext;
let isSpeaking = false; // 発話中かどうかのフラグ
let blobType = 'audio/wav'; // letに変更済み
let accumulatedInterimText = '';

// 無音検出関連の情報を格納する辞書 (最終チャンク受信時刻, タイマータスク実行中フラグ)
silence_trackers = {};
SILENCE_DETECT_SECONDS = 1.5;

// DOMが読み込まれた後に実行
document.addEventListener('DOMContentLoaded', function() {
    console.log('音声認識モジュールを初期化中...');
    setupSocketConnection();
    setupSpeechEvents();
});

/**
 * WebSocket接続の設定
 */
function setupSocketConnection() {
    console.log('WebSocket接続を設定中...');
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocketに接続しました - ID:', socket.id);
        accumulatedInterimText = '';
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket接続が切断されました');
        accumulatedInterimText = '';
    });
    
    socket.on('interim_transcription', function(data) {
        const interimText = data.text;
        console.log('中間結果を受信しました:', interimText);
        if (interimText) {
            accumulatedInterimText = interimText;
            updateSpeechText(accumulatedInterimText + '...');
        }
    });
    
    socket.on('transcription_response', function(data) {
        console.log('認識結果を受信しました:', data);
        const recognizedText = data.text;
        
        accumulatedInterimText = '';
        
        insertRecognizedText(recognizedText);
    });
    
    socket.on('transcription_error', function(data) {
        console.error('音声認識エラー:', data.error);
        showSpeechOverlay(false);
        accumulatedInterimText = '';
    });
}

/**
 * 音声認識関連のイベントを設定
 */
function setupSpeechEvents() {
    console.log('音声認識イベントを設定中...');
    // マイクトグルスイッチの変更イベント
    const micToggle = document.getElementById('mic-toggle-switch');
    if (micToggle) {
        micToggle.addEventListener('change', function() {
            console.log('マイクトグル状態:', this.checked ? 'オン' : 'オフ');
            if (this.checked) {
                startSpeechRecognition();
            } else {
                stopSpeechRecognition();
            }
        });
    } else {
        console.error('マイクトグル要素が見つかりません');
    }
}

/**
 * 音声認識開始
 */
async function startSpeechRecognition() {
    console.log('音声認識を開始しています...');
    try {
        // マイクの使用権限を取得
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('マイクアクセス権限を取得しました');
        
        // WebAudioのセットアップ
        setupAudioProcessing(stream);
        
        // MediaRecorderの設定
        const options = { mimeType: 'audio/wav' }; 
        
        try {
            mediaRecorder = new MediaRecorder(stream, options);
            console.log('MediaRecorderを初期化しました：', options);
        } catch (e) {
            console.warn(`audio/wav is not supported: ${e}. Falling back to default type.`);
            // フォールバック (デフォルト形式、多くはwebmかogg)
            mediaRecorder = new MediaRecorder(stream);
            // ★フォールバック時にblobTypeを確実に設定★
            blobType = mediaRecorder.mimeType || 'audio/webm'; // mimeTypeが取得できなければwebmを仮定
            console.log(`MediaRecorderをデフォルト設定(${blobType})で初期化しました`);
        }
        
        // データが利用可能になったときの処理
        mediaRecorder.ondataavailable = function(event) {
            if (event.data.size > 0) {
                // isSpeaking フラグに基づいて処理を分岐
                if (isSpeaking) {
                    // 発話中はチャンクを直接送信
                    const currentMimeType = mediaRecorder?.mimeType || blobType || 'audio/webm';
                    const audioBlob = new Blob([event.data], { type: currentMimeType });
                    console.log(`[発話中] 音声チャンクデータを送信します: サイズ=${audioBlob.size}バイト, タイプ=${currentMimeType}`);

                    const reader = new FileReader();
                    reader.readAsDataURL(audioBlob);
                    reader.onloadend = function() {
                        const base64data = reader.result;
                        if (socket && socket.connected) {
                            socket.emit('audio_chunk', {
                                audio: base64data,
                                mime_type: currentMimeType
                            });
                            console.log(`[発話中] 音声チャンクデータをサーバーに送信しました (MIME: ${currentMimeType})`);
                        } else {
                            console.warn('[発話中] WebSocket未接続のため、音声データを送信できませんでした');
                        }
                    };
                    // ★ 発話中に送信したデータは audioChunks には追加しない ★

                } else {
                    // 非発話中は audioChunks に溜める
                    audioChunks.push(event.data);
                    console.log(`[非発話中] 音声データをバッファに追加します。 現在のチャンク数: ${audioChunks.length}`);
                }
            }
        };
        
        // 録音開始
        mediaRecorder.start(1000); 
        console.log('MediaRecorderを開始しました - 1秒間隔');
        
        // 発話状態の初期化
        isSpeaking = false;
        isRecording = true;
        
        // UI更新
        updateMicStatus(true);
        
    } catch (error) {
        console.error('マイクの使用権限が取得できません:', error);
        
        // トグルスイッチをオフに戻す
        document.getElementById('mic-toggle-switch').checked = false;
        
        alert('マイクへのアクセスが拒否されました。ブラウザの設定でマイクへのアクセスを許可してください。');
    }
}

/**
 * WebAudioのセットアップと音量解析
 */
function setupAudioProcessing(stream) {
    console.log('WebAudioの処理をセットアップ中...');
    // AudioContextを作成
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    console.log('AudioContextを作成しました:', audioContext.sampleRate + 'Hz');
    
    // 音声ストリームからオーディオノードを作成
    const sourceNode = audioContext.createMediaStreamSource(stream);
    
    // アナライザーノードを作成
    analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 256; // fftSizeは2のべき乗
    analyserNode.smoothingTimeConstant = 0.8; // スムージング係数
    
    // ソースノードをアナライザーに接続
    sourceNode.connect(analyserNode);
    
    // 音量の監視を開始 (requestAnimationFrameからsetIntervalに変更)
    // monitorVolume(); // requestAnimationFrameでの呼び出しを削除
    setInterval(monitorVolume, 100); // 100ミリ秒ごとに音量をチェック
    console.log('音量監視を開始しました (100ms間隔)');
}

/**
 * 音量をリアルタイムで監視
 */
function monitorVolume() {
    // isRecordingフラグをチェック
    if (!isRecording || !analyserNode) return;
    
    // FFTデータを保存する配列を作成
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    // FFTデータを取得
    analyserNode.getByteFrequencyData(dataArray);
    
    // 平均音量を計算
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
    }
    const average = sum / bufferLength / 128.0; // 0-2の範囲になるように調整 (dBではない)
    
    // デバッグログ（毎回出力）
    // console.log(`現在の音量: ${average.toFixed(4)}, 閾値: ${SILENCE_THRESHOLD}, 発話中: ${isSpeaking}`); // ログ削減のためコメントアウト
    
    // 現在の音量が閾値を超えているか判定
    if (average > SILENCE_THRESHOLD) {
        // 発話開始
        if (!isSpeaking) {
            isSpeaking = true;
            console.log('発話を検出しました - オーバーレイを表示');
            showSpeechOverlay(true);
            updateSpeechText('認識中...'); // 認識中であることを示す
        }
        
        // 無音タイマーをリセット
        if (silenceTimeout) {
            clearTimeout(silenceTimeout);
            silenceTimeout = null;
        }
        silenceStartTime = null;
        
    } else {
        // 無音状態の開始を記録
        if (isSpeaking && !silenceStartTime) {
            silenceStartTime = Date.now();
            console.log('無音状態を検出しました - タイマー開始');
        }
        
        // 無音状態が続いているか確認
        if (isSpeaking && silenceStartTime && !silenceTimeout) {
            const silenceDuration = Date.now() - silenceStartTime;
            
            if (silenceDuration >= SILENCE_DURATION) {
                console.log(`無音状態が${SILENCE_DURATION}ミリ秒続いたため、発話終了とみなします`);
                
                // ★無音検出による発話終了でも end_audio を送るか検討★
                // 現状では手動停止のみで end_audio を送ることにする。
                // 理由：無音で一旦区切っても、続けて話す可能性があるため。
                // もし無音区間で自動的に文字起こししたい場合は、ここで end_audio を送り、
                // 再度発話が始まったら新しい録音セッションとして扱う必要がある。

                /* ★以下のチャンク送信ロジックは不要になる可能性あり。end_audioでサーバー側処理を待つため★
                silenceTimeout = setTimeout(() => {
                    // ... (既存の最終チャンク送信ロジックはコメントアウトまたは削除) ...
                    // if (isRecording && audioChunks.length > 0) {
                    //     const currentMimeType = mediaRecorder?.mimeType || blobType || 'audio/webm';
                    //     const audioBlob = new Blob(audioChunks, { type: currentMimeType });
                    //     console.log(`発話終了 - 最終音声データを送信: サイズ=${audioBlob.size}バイト, タイプ=${currentMimeType}`);
                    //     const reader = new FileReader();
                    //     reader.readAsDataURL(audioBlob);
                    //     reader.onloadend = function() {
                    //         const base64data = reader.result;
                    //         if (socket && socket.connected) {
                    //             // ★ mime_type を追加 ★
                    //             socket.emit('audio_chunk', { audio: base64data, mime_type: currentMimeType });
                    //             console.log('最終音声データをサーバーに送信しました');
                    //             // ★ end_audio は手動停止時に送る ★
                    //             // socket.emit('end_audio');
                    //         } else {
                    //             console.warn('WebSocket未接続のため、最終音声データを送信できませんでした');
                    //         }
                    //         audioChunks = []; // サーバー側で処理するのでクリア
                    //     };
                    // } else {
                    //    console.log('最終音声チャンクが空か、録音中でないため送信しませんでした。');
                    //}

                    isSpeaking = false;
                    silenceStartTime = null;
                    // updateSpeechText('処理中...'); // サーバーからの応答を待つのでここでは更新しない
                    silenceTimeout = null; // タイマーをクリア

                }, 500); // わずかな遅延は不要になる可能性
                */
               // 発話フラグだけをリセットし、UI更新（オーバーレイはまだ表示しておく）
               isSpeaking = false;
               silenceStartTime = null;
               console.log("無音検出。発話フラグをfalseに。end_audio は送信しません。");
               // updateSpeechText('...'); // 無音検出時にテキストをクリアするかどうかは検討事項

            }
        }
    }
}

/**
 * 音声認識停止
 */
function stopSpeechRecognition() {
    console.log('音声認識を停止しています...');
    if (mediaRecorder && isRecording) {
        // isRecordingフラグはすぐにfalseにする
        // これにより、stop()呼び出し後に発生する可能性のある ondataavailable で
        // isSpeaking が true でもチャンクが送信されなくなる（代わりにバッファに溜まる）
        isRecording = false;
        console.log("isRecording フラグを false に設定");

        mediaRecorder.onstop = () => {
            console.log("mediaRecorder.onstop イベント発火");

            // ★ audioChunksに溜まったデータのみを最後のチャンクとして送信 ★
            if (audioChunks.length > 0) {
                 const currentMimeType = mediaRecorder?.mimeType || blobType || 'audio/webm';
                 // ★溜めていたチャンクを結合してBlobを作成★
                 const finalBlob = new Blob(audioChunks, { type: currentMimeType });
                 console.log(`停止時 - 溜まっていたチャンク(${audioChunks.length}個)をBlobにまとめました: サイズ=${finalBlob.size}, タイプ=${currentMimeType}`);

                 const reader = new FileReader();
                 reader.readAsDataURL(finalBlob);
                 reader.onloadend = () => {
                     const base64data = reader.result;
                     if (socket && socket.connected) {
                         // 最後のチャンクデータを送信
                         socket.emit('audio_chunk', { audio: base64data, mime_type: currentMimeType });
                         console.log('停止時 - 溜まっていた最後の音声データをサーバーに送信しました');

                         // ★ 最後のチャンク送信「後」に end_audio を送信 ★
                         socket.emit('end_audio');
                         console.log("'end_audio' イベントを送信しました");

                     } else {
                        console.warn("WebSocket未接続のため、停止時の最後の音声データまたは 'end_audio' を送信できませんでした");
                     }
                     audioChunks = []; // 送信後にクリア
                 }
            } else {
                 // 溜まっていたチャンクがない場合でも end_audio を送信
                 console.log("停止時 - 溜まっていたチャンクはありませんでした。");
                 if (socket && socket.connected) {
                     socket.emit('end_audio');
                     console.log("溜まっていたチャンクなし。'end_audio' イベントを送信しました");
                 } else {
                      console.warn("WebSocket未接続のため、'end_audio' を送信できませんでした");
                 }
                 // audioChunks は既に空なのでクリア不要
            }
            // リソース解放（onstop の最後に移動）
             cleanupAudioResources();
        };

        // 録音停止を試みる
        try {
             // stop() を呼ぶと、キューに残っているデータで最後の ondataavailable が発生し、
             // その後に onstop が発生する。
             mediaRecorder.stop();
             console.log('MediaRecorder.stop() を呼び出しました');
        } catch (e) {
            console.error("mediaRecorder.stop() でエラー:", e);
            // エラーが発生してもリソース解放とend_audio送信は試みる
            // (onstopが呼ばれない可能性があるので、ここでも呼ぶ)
             cleanupAudioResources(); // ★エラー時の解放
             if (socket && socket.connected) {
                 // 念のため end_audio を送る（バッファにデータが残っているかは不明）
                socket.emit('end_audio');
                console.log("stopエラー後ですが 'end_audio' イベントを送信しました");
             }
        }

        // UI更新は即座に行う
        updateMicStatus(false);
        showSpeechOverlay(false); // 停止したらすぐにオーバーレイを消す

    } else {
         console.log("録音中でないか、MediaRecorderがありません。停止処理をスキップします。");
         cleanupAudioResources(); // 念のため
    }
}

/**
* オーディオ関連のリソースをクリーンアップする関数
*/
function cleanupAudioResources() {
    console.log("オーディオリソースのクリーンアップを開始");
    // トラックを停止
    if (mediaRecorder && mediaRecorder.stream) {
        mediaRecorder.stream.getTracks().forEach(track => {
            track.stop();
            console.log('音声トラックを停止しました:', track.id);
        });
    } else {
        console.log("mediaRecorder または stream が存在しません。トラック停止をスキップ。");
    }

    // AudioContextを閉じる
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close().then(() => {
            console.log("AudioContextを閉じました");
        }).catch(e => {
            console.error("AudioContextを閉じる際にエラー:", e);
        });
        audioContext = null; // 参照を削除
        analyserNode = null; // アナライザーも参照削除
    } else {
         console.log("AudioContext が存在しないか、既に閉じています。");
    }

    // タイマーをクリア
    if (silenceTimeout) {
        clearTimeout(silenceTimeout);
        silenceTimeout = null;
        console.log("無音タイマーをクリアしました");
    }

    // 状態をリセット
    silenceStartTime = null;
    isSpeaking = false; // 発話状態もリセット
    audioChunks = []; // チャンクリストもクリア
    mediaRecorder = null; // MediaRecorderの参照もクリア

    console.log("オーディオリソースのクリーンアップ完了");
}

/**
 * 音声認識オーバーレイの表示/非表示を切り替え
 * @param {boolean} show - 表示するかどうか
 */
function showSpeechOverlay(show) {
    const overlay = document.getElementById('speech-overlay');
    
    if (!overlay) {
        console.error('音声認識オーバーレイ要素が見つかりません');
        return;
    }
    
    if (show) {
        overlay.style.display = 'flex';
        console.log('音声認識オーバーレイを表示しました');
    } else {
        overlay.style.display = 'none';
        console.log('音声認識オーバーレイを非表示にしました');
    }
}

/**
 * 音声認識テキストを更新
 * @param {string} text - 表示するテキスト
 */
function updateSpeechText(text) {
    const speechText = document.getElementById('speech-text');
    
    if (!speechText) {
        console.error('音声認識テキスト要素が見つかりません');
        return;
    }
    
    speechText.textContent = text;
    // console.log('音声認識テキストを更新しました:', text.substring(0, 30) + (text.length > 30 ? '...' : '')); // ログはinterim/finalで出力済みなので削減
}

/**
 * 認識されたテキストをエディタに挿入
 * @param {string} text - 挿入するテキスト
 */
function insertRecognizedText(text) {
    if (text && text.trim() !== '') {
        console.log('[最終結果] エディタに認識テキストを挿入します:', text.substring(0, 50) + (text.length > 50 ? '...' : ''));
        
        if (window.editorAPI && typeof window.editorAPI.insertTextAtCursor === 'function') {
            window.editorAPI.insertTextAtCursor(text + ' ');
            console.log('[最終結果] エディタにテキストを挿入しました');
        } else {
            console.error('エディタAPIが見つからないか、insertTextAtCursor関数が定義されていません');
        }
        
        // ★最終結果を挿入したらオーバーレイを非表示★
        showSpeechOverlay(false);
        // ★念のため中間テキストもクリア★
        updateSpeechText('');
        accumulatedInterimText = '';

    } else {
        console.warn('[最終結果] 挿入するテキストが空のため、何も挿入しませんでした');
        // テキストが空でもオーバーレイは非表示にする
        showSpeechOverlay(false);
        updateSpeechText('');
        accumulatedInterimText = '';
    }
}

/**
 * マイク状態表示の更新
 * @param {boolean} isActive - マイクがアクティブかどうか
 */
function updateMicStatus(isActive) {
    const micStatus = document.getElementById('mic-status');
    
    if (!micStatus) {
        console.error('マイク状態表示要素が見つかりません');
        return;
    }
    
    if (isActive) {
        micStatus.textContent = 'オン';
        micStatus.style.color = 'var(--success-color)';
        console.log('マイク状態を「オン」に更新しました');
    } else {
        micStatus.textContent = 'オフ';
        micStatus.style.color = 'var(--text-light)';
        console.log('マイク状態を「オフ」に更新しました');
    }
}