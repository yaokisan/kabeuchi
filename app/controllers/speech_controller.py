from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room, leave_room
import os
import tempfile
import openai
import base64
import time
import sys
import io
from pydub import AudioSegment

speech_bp = Blueprint('speech', __name__, url_prefix='/api/speech')

# OpenAIキーの設定
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print(f"音声認識用 OpenAI API Key設定状況: {'設定済み' if OPENAI_API_KEY else '未設定'}")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# 接続ごとの音声バッファ
audio_buffers = {}
# 接続ごとのMIMEタイプを保持
mime_types = {}

# リアルタイム処理用の定数
SILENCE_DETECT_SECONDS = 2.0 # 無音とみなす秒数
SILENCE_DETECT_INTERVAL = 0.5 # 無音チェックの間隔

# 接続ごとの状態管理
last_chunk_times = {}           # 最後にチャンクを受信した時刻
silence_detection_running = {} # 無音検出タスクが実行中か
processing_flags = {}           # 音声処理が実行中か

def handle_combined_audio(combined_audio_bytes, mime_type):
    """結合された音声データを処理し、文字起こし結果を返す"""
    if not OPENAI_API_KEY:
        print("音声認識エラー: OpenAI API Keyが設定されていません", file=sys.stderr)
        return None

    if not combined_audio_bytes:
        print("警告: 結合された音声データが空です。スキップします。", file=sys.stderr)
        return None

    print(f"結合データサイズ: {len(combined_audio_bytes)} bytes, MIME Type: {mime_type}")

    # ファイルサイズチェック (小さすぎるデータはpydub/whisperでエラーになりやすい)
    if len(combined_audio_bytes) < 500:
        print(f"警告: 結合後のファイルサイズが小さすぎます ({len(combined_audio_bytes)} bytes)。認識をスキップします。", file=sys.stderr)
        return None # サイズが小さい場合は None を返す

    audio_segment = None
    temp_wav_file_path = None
    transcription_result = None

    try:
        # --- pydubによる形式変換 ---
        input_format = None # 初期化
        try:
            audio_io = io.BytesIO(combined_audio_bytes)
            # MIMEタイプからフォーマットを決定
            # 例: 'audio/webm;codecs=opus' -> 'webm' または 'opus' を試す
            simple_mime = mime_type.split(';')[0].strip() # 前後の空白除去も追加
            if '/' in simple_mime:
                input_format = simple_mime.split('/')[-1]
            else: # 不明な場合やMIMEタイプが 'audio/opus' のような場合
                 input_format = 'webm' # デフォルトはwebmとする
                 if 'opus' in mime_type: # 'opus' 文字列が含まれていれば opus を優先的に試す
                     input_format = 'opus'

            print(f"pydub試行1: format='{input_format}' (from MIME: {mime_type})")
            audio_segment = AudioSegment.from_file(audio_io, format=input_format)
            print("pydubでの音声読み込み成功 (試行1)")

        except Exception as pydub_error1:
            print(f"pydub試行1失敗 (MIME='{mime_type}', format='{input_format}'): {type(pydub_error1).__name__}: {pydub_error1}", file=sys.stderr)
            # フォーマット指定を変えて再試行 (例: webmでダメならopus, opusでダメならwebm)
            alternative_format = None
            if input_format == 'webm' and 'opus' in mime_type:
                alternative_format = 'opus'
            elif input_format == 'opus' and 'webm' in mime_type:
                 alternative_format = 'webm'
            # 必要なら他の形式も試す (例: 'ogg' など)
            # elif 'ogg' in mime_type:
            #    alternative_format = 'ogg'

            if alternative_format:
                 try:
                     print(f"pydub試行2: format='{alternative_format}'")
                     input_format = alternative_format # 実際に試したフォーマットを記録
                     audio_io.seek(0) # BytesIOを再利用するため先頭に戻す
                     audio_segment = AudioSegment.from_file(audio_io, format=input_format)
                     print(f"pydubでの音声読み込み成功 (試行2, format='{input_format}')")
                 except Exception as pydub_error2:
                      print(f"pydub試行2失敗 (format='{input_format}'): {type(pydub_error2).__name__}: {pydub_error2}", file=sys.stderr)
                      print(f"pydub処理エラー: サポートされていない形式か、データ破損の可能性があります。MIME={mime_type}", file=sys.stderr)
                      print(f"エラー発生時のバイト列（先頭100バイト）: {combined_audio_bytes[:100]}...", file=sys.stderr) # ログに...を追加
                      return None # 読み込み失敗ならここで終了
            else:
                 # 再試行するフォーマットがない場合
                 print(f"pydub処理エラー: 適切な読み込みフォーマットが見つかりません。MIME={mime_type}", file=sys.stderr)
                 print(f"エラー発生時のバイト列（先頭100バイト）: {combined_audio_bytes[:100]}...", file=sys.stderr) # ログに...を追加
                 return None # 読み込み失敗ならここで終了

        # --- wav形式でのエクスポート ---
        try:
            # delete=Falseにするとデバッグ時にファイルを確認できるが、実行完了時に削除する必要がある
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav_file:
                temp_wav_file_path = temp_wav_file.name
                print(f"wav形式で一時ファイルにエクスポート: {temp_wav_file_path}")
                # エクスポート実行
                audio_segment.export(temp_wav_file_path, format="wav")
                print("wavエクスポート完了")
        except Exception as export_error:
            print(f"pydub wavエクスポートエラー: {type(export_error).__name__}: {export_error}", file=sys.stderr)
            # エクスポート失敗時は一時ファイルが残らないように試みる
            if temp_wav_file_path and os.path.exists(temp_wav_file_path):
                 try: os.remove(temp_wav_file_path)
                 except OSError: pass
            return None # エクスポート失敗

        # --- Whisper API 処理 ---
        try:
            with open(temp_wav_file_path, 'rb') as audio_file:
                print(f"Whisper APIにwavファイルを送信中: {temp_wav_file_path}")
                # ファイルサイズチェック
                audio_file.seek(0, os.SEEK_END)
                file_size = audio_file.tell()
                audio_file.seek(0, os.SEEK_SET)
                print(f"wavファイルサイズ: {file_size} bytes")
                if file_size < 100:
                     print(f"警告: wav変換後のファイルサイズが小さすぎます ({file_size} bytes)。Whisper呼び出しをスキップします。", file=sys.stderr)
                     transcription_result = "" # 空の結果を返す
                else:
                     # Whisper API呼び出し
                     response = openai.Audio.transcribe(
                         model="whisper-1",
                         file=audio_file,
                         language="ja"
                     )
                     print("Whisper APIからの応答を受信")
                     transcription_result = response.text # 結果を格納

            if transcription_result is not None:
                print(f"音声認識結果: {transcription_result[:50]}...") # 少し長めに表示
            else:
                 # ファイルサイズ以外の理由で結果がNoneだった場合（通常は発生しにくい）
                 print("Whisper APIから有効な結果が得られませんでした。", file=sys.stderr)
                 # transcription_result は None のまま

        except openai.error.InvalidRequestError as whisper_ire:
             print(f"Whisper APIリクエストエラー: {whisper_ire}", file=sys.stderr)
             print("考えられる原因: 音声データが短すぎる、無音部分が長すぎる、サポートされていない形式（wavのはずだが破損？）、など。", file=sys.stderr)
             # transcription_result は None のまま
        except openai.error.AuthenticationError as whisper_ae:
             print(f"Whisper API認証エラー: {whisper_ae}", file=sys.stderr)
             # transcription_result は None のまま
        except Exception as whisper_error:
             # openaiライブラリの他のエラーや、ファイルI/Oエラーなど
             print(f"Whisper API処理中に予期せぬエラー: {type(whisper_error).__name__}: {whisper_error}", file=sys.stderr)
             # transcription_result は None のまま

        # --- Whisper API 処理 ここまで ---

        # ★重要★: 最終的に文字起こし結果(成功時は文字列、失敗時はNone)を返す
        return transcription_result

    # このトップレベルの except は、上記でキャッチされなかった予期せぬエラー用
    except Exception as e:
         print(f"handle_combined_audio内で予期せぬ致命的エラー: {type(e).__name__}: {e}", file=sys.stderr)
         import traceback
         traceback.print_exc(file=sys.stderr) # スタックトレースを出力
         return None # 予期せぬエラーでもNoneを返す

    finally:
        # --- 一時ファイルのクリーンアップ ---
        if temp_wav_file_path and os.path.exists(temp_wav_file_path):
            try:
                os.remove(temp_wav_file_path)
                print(f"一時ファイル {temp_wav_file_path} を削除しました")
            except OSError as remove_error:
                 print(f"一時ファイル {temp_wav_file_path} の削除に失敗しました: {remove_error}", file=sys.stderr)

# WebSocketイベントハンドラを登録する関数
def handle_speech_recognition(socketio):

    def process_audio_segment(sid, is_final=False):
        """音声セグメントを処理し、文字起こし結果を送信する"""
        if sid not in audio_buffers or sid not in mime_types or sid not in processing_flags:
            print(f"エラー: process_audio_segment - 接続 {sid} の情報が見つかりません。", file=sys.stderr)
            return

        if processing_flags.get(sid, False):
            print(f"情報: 接続 {sid} の音声処理は既に実行中です。スキップします。")
            return

        processing_flags[sid] = True
        print(f"音声セグメント処理開始: sid={sid}, is_final={is_final}")

        try:
            # 現在のバッファ内容を取得
            current_buffer = audio_buffers.get(sid)
            if not current_buffer or current_buffer.tell() == 0:
                print(f"情報: 接続 {sid} のバッファは空です。処理をスキップします。")
                processing_flags[sid] = False
                return # バッファが空なら何もしない

            combined_audio_bytes = current_buffer.getvalue()
            mime_type = mime_types.get(sid)

            if not mime_type:
                print(f"エラー: 接続 {sid} のMIMEタイプが不明です。処理できません。", file=sys.stderr)
                emit('transcription_error', {'error': '音声形式が不明です'}, room=sid) # 特定のsidに送信
                # バッファリセット (念のため)
                if sid in audio_buffers: audio_buffers[sid] = io.BytesIO()
                if sid in mime_types: mime_types[sid] = None
                processing_flags[sid] = False
                return

            print(f"処理対象データサイズ: {len(combined_audio_bytes)} bytes, MIME: {mime_type}, is_final: {is_final}")

            # 文字起こし実行
            transcription = handle_combined_audio(combined_audio_bytes, mime_type)

            if transcription is not None:
                if is_final:
                    emit('transcription_response', {'text': transcription}, room=sid)
                    print(f"最終結果を送信 ({sid}): {transcription[:30]}...")
                    # 最終処理後はバッファを完全にリセット
                    if sid in audio_buffers: audio_buffers[sid] = io.BytesIO()
                    if sid in mime_types: mime_types[sid] = None # 次の録音に備えてMIMEもリセット
                else:
                    emit('interim_transcription', {'text': transcription}, room=sid)
                    print(f"中間結果を送信 ({sid}): {transcription[:30]}...")
                    # 中間処理後は処理した部分をバッファから削除する代わりに、
                    # ここではシンプルにバッファ全体を処理し、結果送信後にリセットする
                    # (より洗練させるなら、処理したバイト数分だけバッファを再構築する)
                    if sid in audio_buffers: audio_buffers[sid] = io.BytesIO() # 送信後リセット
                    # mime_types[sid] は維持する
            else:
                # 文字起こし失敗
                error_message = '音声認識に失敗しました'
                if is_final:
                    emit('transcription_error', {'error': error_message}, room=sid)
                    print(f"最終結果送信エラー ({sid})")
                    # エラーでも最終ならリセット
                    if sid in audio_buffers: audio_buffers[sid] = io.BytesIO()
                    if sid in mime_types: mime_types[sid] = None
                else:
                    # 中間結果でのエラーはクライアントに通知しない方がUXが良いかもしれない
                    print(f"中間結果処理エラー ({sid}) - クライアント通知はスキップ")
                    # エラーでも中間処理ならリセット
                    if sid in audio_buffers: audio_buffers[sid] = io.BytesIO()


        except Exception as e:
            print(f"process_audio_segment内で予期せぬエラー ({sid}): {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            if is_final:
                emit('transcription_error', {'error': 'サーバー内部エラーが発生しました'}, room=sid)
                # エラーでも最終ならリセット
                if sid in audio_buffers: audio_buffers[sid] = io.BytesIO()
                if sid in mime_types: mime_types[sid] = None
            else:
                 # 中間処理中の内部エラーもクライアントには通知しない
                 print(f"中間処理中の内部エラー ({sid}) - クライアント通知はスキップ")
                 if sid in audio_buffers: audio_buffers[sid] = io.BytesIO()

        finally:
            # 処理完了フラグを下ろす
            # sid がまだ存在するか確認してからフラグを操作
            if sid in processing_flags:
                processing_flags[sid] = False
            print(f"音声セグメント処理完了: sid={sid}, is_final={is_final}")


    def silence_detection_task(sid):
        """無音状態を監視し、中間的な文字起こしを実行するバックグラウンドタスク"""
        print(f"無音検出タスク開始: sid={sid}")
        # タスク開始時にフラグを立てる
        if sid in silence_detection_running:
            silence_detection_running[sid] = True
        else:
            # 開始しようとしたsidが存在しない場合（disconnect直後など）はタスクを即時終了
            print(f"警告: 無音検出タスク開始時にsid={sid}が見つかりません。タスクを終了します。")
            return

        try:
            while sid in last_chunk_times and silence_detection_running.get(sid, False):
                # 無音状態のチェック
                current_time = time.time()
                last_time = last_chunk_times.get(sid, current_time) # sidが存在しないケースはループ条件で弾かれるはず
                silence_duration = current_time - last_time

                # バッファにデータがあるかどうかもチェックする
                buffer_has_data = False
                if sid in audio_buffers and audio_buffers[sid].tell() > 0:
                    buffer_has_data = True

                if silence_duration >= SILENCE_DETECT_SECONDS and buffer_has_data:
                    print(f"★★★ 無音検出 ★★★ sid={sid} (無音時間: {silence_duration:.2f}秒)")
                    # --- 中間処理の呼び出しをコメントアウト ---
                    # print("中間処理を実行します...") # ログ追加
                    # process_audio_segment(sid, is_final=False)
                    # ------------------------------------
                    # 代わりに、最終チャンク受信時刻のみ更新して無音検出のループを継続
                    # (これにより、マイクオン中は無音が続いてもタスクが動き続ける)
                    if sid in last_chunk_times:
                        last_chunk_times[sid] = time.time() # Reset silence timer
                        print(f"無音検出のためタイマーリセット: sid={sid}") # ログ追加
                    # 一度処理したら、次のチャンクが来るまで待つ（last_chunk_timesを更新）
                    # 無音検出による連続処理を防ぐため、処理後は last_chunk_times を現在時刻にリセット
                    # ただし、sid がまだ存在する場合のみ更新する
                    # if sid in last_chunk_times:
                    #     last_chunk_times[sid] = time.time()

                # 一定間隔待機
                socketio.sleep(SILENCE_DETECT_INTERVAL)

        except Exception as e:
             print(f"無音検出タスクでエラー発生 ({sid}): {type(e).__name__}: {e}", file=sys.stderr)
             import traceback
             traceback.print_exc(file=sys.stderr)
        finally:
             # タスク終了時にフラグを確実に下ろす (sidが存在する場合のみ)
             if sid in silence_detection_running:
                 silence_detection_running[sid] = False
             print(f"無音検出タスク終了: sid={sid}")

    @socketio.on('connect')
    def handle_connect():
        sid = request.sid
        print(f"クライアント接続: {sid}")
        # 接続時にバッファと状態を初期化
        audio_buffers[sid] = io.BytesIO()
        mime_types[sid] = None
        last_chunk_times[sid] = time.time() # 接続時刻を初期値に
        silence_detection_running[sid] = False
        processing_flags[sid] = False
        print(f"接続初期化完了: {sid}, States: {last_chunk_times.keys()}, {silence_detection_running.keys()}, {processing_flags.keys()}")


    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        print(f"クライアント切断: {sid}")
        # 切断時にバッファと状態を削除
        if sid in audio_buffers:
            audio_buffers[sid].close()
            del audio_buffers[sid]
        if sid in mime_types:
            del mime_types[sid]
        if sid in last_chunk_times:
            del last_chunk_times[sid]
        if sid in silence_detection_running:
            # 実行中のタスクがあれば停止させる（フラグを下ろす）
            silence_detection_running[sid] = False # ★重要: タスク内のループを止める
            # del silence_detection_running[sid] # del するのはタスク終了後の方が安全かも
        if sid in processing_flags:
            del processing_flags[sid]
        print(f"切断後クリーンアップ完了: {sid}, Remaining States: {last_chunk_times.keys()}, {silence_detection_running.keys()}, {processing_flags.keys()}")


    @socketio.on('audio_chunk')
    def process_audio_chunk(data):
        """クライアントから受信した音声チャンクをバッファに追記し、無音検出タスクを管理"""
        sid = request.sid
        # print(f"音声チャンク受信 from {sid}")
        audio_data_b64 = data.get('audio')
        mime_type = data.get('mime_type')

        if not audio_data_b64 or not mime_type:
            print(f"エラー: 不正な音声データまたはMIMEタイプなし from {sid}", file=sys.stderr)
            emit('transcription_error', {'error': '不正な音声データ形式です'}, room=sid)
            return

        # 接続情報が存在するか確認 (disconnect後に届く可能性も考慮)
        if sid not in audio_buffers or sid not in mime_types or sid not in last_chunk_times or sid not in silence_detection_running or sid not in processing_flags:
             print(f"警告: 切断処理中または不明な接続ID {sid} から音声チャンクを受信。無視します。", file=sys.stderr)
             return

        # 最初のチャンクでMIMEタイプを記録
        if mime_types[sid] is None:
            mime_types[sid] = mime_type
            print(f"接続 {sid} のMIMEタイプを設定: {mime_type}")

        try:
            # Base64デコード
            if ',' in audio_data_b64:
                _, encoded = audio_data_b64.split(',', 1)
                audio_bytes = base64.b64decode(encoded)
            else:
                audio_bytes = base64.b64decode(audio_data_b64)

            # バッファに追記
            audio_buffers[sid].write(audio_bytes)
            # print(f"チャンクをバッファに追加 from {sid}. 現在のサイズ: {audio_buffers[sid].tell()}")

            # 最終チャンク受信時刻を更新
            last_chunk_times[sid] = time.time()

            # 無音検出タスクが実行中でなければ開始
            if not silence_detection_running.get(sid, False):
                 # タスクが既に終了している可能性も考慮し、再度フラグを確認・設定
                 if sid in silence_detection_running: # まだsidが存在するなら
                     print(f"無音検出タスクを起動します: sid={sid}")
                     # フラグを先に True に設定してからタスクを開始する方が安全かもしれない
                     # silence_detection_running[sid] = True # タスク関数側で設定されるはずだが念のため
                     socketio.start_background_task(silence_detection_task, sid)
                 else:
                      print(f"警告: 無音検出タスク起動試行時に sid={sid} が見つかりません。")


        except base64.binascii.Error as b64_error:
            print(f"Base64デコードエラー from {sid}: {b64_error}. スキップします。", file=sys.stderr)
            emit('transcription_error', {'error': '音声データのデコードに失敗しました'}, room=sid)
        except Exception as e:
            print(f"チャンク処理中に予期せぬエラー from {sid}: {type(e).__name__}: {e}", file=sys.stderr)
            emit('transcription_error', {'error': 'サーバー内部エラーが発生しました'}, room=sid)


    @socketio.on('end_audio')
    def process_end_audio():
        """録音終了シグナルを受け取り、最終的な音声処理を実行"""
        sid = request.sid
        print(f"録音終了シグナル受信 from {sid}")

        # 接続情報が存在するか確認
        if sid not in audio_buffers or sid not in mime_types or sid not in processing_flags:
            print(f"エラー: process_end_audio - 接続 {sid} の情報が見つかりません。", file=sys.stderr)
            emit('transcription_error', {'error': 'サーバーエラー：セッション情報が見つかりません'}, room=sid)
            return

        # 無音検出タスクを停止させるフラグを立てる
        if sid in silence_detection_running:
             silence_detection_running[sid] = False
             print(f"録音終了により無音検出タスク停止指示: sid={sid}")

        # ★★★ 修正点 ★★★
        # タスク停止をより確実にするため、last_chunk_timesからも削除
        if sid in last_chunk_times:
            del last_chunk_times[sid]
            print(f"録音終了によりlast_chunk_timesから削除: sid={sid}")
        # ★★★ 修正ここまで ★★★

        # タスクが完全に終了するのを少し待つ (任意)
        # socketio.sleep(SILENCE_DETECT_INTERVAL * 1.1)

        # 最終処理を実行
        process_audio_segment(sid, is_final=True)


# REST API経由の音声認識リクエスト（バックアップとして実装）
@speech_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """音声ファイルを文字起こし"""
    if not OPENAI_API_KEY:
        return jsonify({'error': 'OpenAI API Keyが設定されていません。.envファイルを確認してください。'}), 400

    if 'audio' not in request.files:
        return jsonify({'error': '音声ファイルが見つかりません'}), 400

    audio_file = request.files['audio']

    try:
        # Whisper APIを使用して文字起こし
        response = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file,
            language="ja"
        )

        return jsonify({'text': response.text})

    except Exception as e:
        return jsonify({'error': f'音声認識エラー: {str(e)}'}), 500 