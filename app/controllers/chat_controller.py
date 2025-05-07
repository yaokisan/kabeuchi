from flask import Blueprint, request, jsonify
from app.models.database import (
    get_document as supa_get_document,
    get_chat_messages as supa_get_chat_messages,
    create_chat_message as supa_create_chat_message,
    delete_chat_messages as supa_delete_chat_messages,
)
import os
import json
import sys

# APIクライアントのインポート
import openai
import google.generativeai as genai
from anthropic import Anthropic
from duckduckgo_search import DDGS # ★ duckduckgo-search をインポート
from google.generativeai.types import GenerationConfig, FunctionDeclaration, Tool
from urllib.parse import urlparse # URLパース用に追記
from io import BytesIO # Base64デコード用
import base64
from openai import OpenAI

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# APIキーの取得と設定
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# APIキーが設定されているか確認
print(f"OpenAI API Key設定状況: {'設定済み' if OPENAI_API_KEY else '未設定'}")
print(f"Google API Key設定状況: {'設定済み' if GOOGLE_API_KEY else '未設定'}")
print(f"Anthropic API Key設定状況: {'設定済み' if ANTHROPIC_API_KEY else '未設定'}")

# APIクライアントの設定
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
if ANTHROPIC_API_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    anthropic_client = None

# --- Gemini用 Web検索ツールの定義 --- START ---
web_search_func = FunctionDeclaration(
    name="web_search",
    description="ユーザーの質問に答えるために、Webで情報を検索します。最新情報、不明確な用語、事実確認が必要な場合に加え、ユーザーが『検索して』と明示的に指示した場合は、他の判断基準よりも優先して必ずこのツールを呼び出してください。",
    parameters={
        "type": "object",
        "properties": {
            "search_query": {
                "type": "string",
                "description": "Webで検索する具体的なキーワードや質問。ユーザーの指示内容を正確に反映させてください。"
            }
        },
        "required": ["search_query"]
    }
)
search_tool = Tool(function_declarations=[web_search_func])
# --- Gemini用 Web検索ツールの定義 --- END ---

@chat_bp.route('/reset/<int:doc_id>', methods=['POST'])
def reset_chat_history(doc_id):
    """指定されたドキュメントIDに関連するチャット履歴を削除"""
    try:
        # ドキュメント存在チェック
        document = supa_get_document(doc_id)
        if not document:
            return jsonify({'success': False, 'message': 'Document not found'}), 404

        # Supabaseでチャットメッセージを削除
        num_deleted = supa_delete_chat_messages(doc_id)
        
        print(f"ドキュメントID {doc_id} のチャット履歴を {num_deleted} 件削除しました。")
        return jsonify({'success': True, 'message': 'チャット履歴がリセットされました。'}), 200
    except Exception as e:
        print(f"チャット履歴のリセット中にエラーが発生しました: {str(e)}", file=sys.stderr)
        return jsonify({'success': False, 'message': 'チャット履歴のリセットに失敗しました。'}), 500

@chat_bp.route('/history/<int:doc_id>', methods=['GET'])
def get_chat_history(doc_id):
    """指定されたドキュメントIDに関連するチャット履歴を取得"""
    document = supa_get_document(doc_id)
    if not document:
        return jsonify({'success': False, 'message': 'Document not found'}), 404

    chat_messages = supa_get_chat_messages(doc_id) or []
    return jsonify(chat_messages)

@chat_bp.route('/send/<int:doc_id>', methods=['POST'])
def send_message(doc_id):
    """ユーザーメッセージを保存し、AIからの応答を取得して保存"""
    document = supa_get_document(doc_id)
    if not document:
        return jsonify({'success': False, 'message': 'Document not found'}), 404

    data = request.get_json()
    
    user_message = data.get('message', '')
    model_name = data.get('model', 'gemini-2.0-flash')
    thinking_enabled = data.get('thinking_enabled', False)
    chat_context = data.get('chat_context')
    enable_search = data.get('enable_search', False)
    image_data_base64 = data.get('image_data') 
    image_mime_type = data.get('image_mime_type')

    # 画像データからヘッダー除去 (再確認)
    if image_data_base64 and ',' in image_data_base64:
        image_data_base64 = image_data_base64.split(',', 1)[1]

    # Supabaseにユーザーメッセージを保存
    supa_create_chat_message(
        document_id=doc_id,
        role='user',
        content=user_message,
        model_used=model_name,
        thinking_enabled=thinking_enabled,
    )

    # チャット履歴を取得 (画像情報は含まれない)
    chat_history = supa_get_chat_messages(doc_id) or []
    context = document.get('content', '')

    ai_response_data = {}
    try:
        if model_name.startswith('gemini'):
            if not GOOGLE_API_KEY:
                raise ValueError("Google API Keyが設定されていません。")
            ai_response_data = get_gemini_response(
                model_name, context, chat_history, user_message, chat_context, enable_search,
                image_data_base64, image_mime_type
            )
        elif model_name.startswith('claude'):
            if not ANTHROPIC_API_KEY:
                raise ValueError("Anthropic API Keyが設定されていません。")
            claude_response = get_claude_response(model_name, context, chat_history, user_message, thinking_enabled, chat_context)
            ai_response_data = {"message": claude_response, "sources": []} # sources は空
        elif model_name.startswith('o3'):
            if not OPENAI_API_KEY:
                raise ValueError("OpenAI API Keyが設定されていません。")
            o3_result = get_openai_o3_response(
                model_name, context, chat_history, user_message, chat_context
            )

            # get_openai_o3_response は dict 形式で返す
            if not o3_result.get("success", False):
                status_code = o3_result.get("status", 500)
                return jsonify({
                    'success': False,
                    'message': o3_result.get("message", "OpenAI APIエラー"),
                }), status_code

            ai_response_data = {
                "message": o3_result.get("message", ""),
                "sources": []
            }
        elif model_name.startswith('gpt'):
             if not OPENAI_API_KEY:
                raise ValueError("OpenAI API Keyが設定されていません。")
             gpt_response = get_openai_response(model_name, context, chat_history, user_message, chat_context)
             ai_response_data = {"message": gpt_response, "sources": []} # sources は空
        else:
            ai_response_data = {"message": "エラー: サポートされていないモデル...", "sources": []}

    except Exception as e:
        print(f"AI応答エラー: {str(e)}", file=sys.stderr)
        # エラーレスポンスを返す前に処理を終了
        return jsonify({'success': False, 'message': f"AI応答取得エラー: {str(e)}"}), 500

    # SupabaseにAI応答を保存
    supa_create_chat_message(
        document_id=doc_id,
        role='assistant',
        content=ai_response_data.get("message", ""),
        model_used=model_name,
        thinking_enabled=thinking_enabled,
    )

    ai_message = ai_response_data.get("message", "")
    # ★ 応答の先頭が "ny" であれば削除する処理を追加
    if ai_message.startswith("ny"):
        print(f"--- AI応答の先頭から 'ny' を削除しました: {ai_message[:10]}... ---") # デバッグ用ログ
        ai_message = ai_message[2:] # 先頭の2文字を削除

    # ★ フロントエンドに返すJSONに sources を含める
    return jsonify({
        'success': True, # 成功フラグを追加
        'message': ai_message, # ★ 修正後のメッセージを返す
        'sources': ai_response_data.get("sources", []), # 情報源リストを追加
        'model': model_name,
        'thinking_enabled': thinking_enabled
    })

def execute_web_search(search_query: str) -> dict: # ★ 返り値を dict に変更
    """Web検索を実行し、結果テキストと情報源リストを含む辞書を返す"""
    print(f"--- 実行する検索クエリ (AI提案): {search_query} ---")
    search_results_text = ""
    sources = [] # ★ 情報源リスト
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(search_query, region='jp-jp', max_results=3)]
            if results:
                search_results_text = "\n--- Web検索結果 ---\n" # AIに渡すテキスト用
                for i, result in enumerate(results):
                    title = result.get('title')
                    body = result.get('body')
                    url = result.get('href') # ★ URLを取得

                    # AIに渡すテキストの整形
                    if title and body:
                         search_results_text += f"{i+1}. {title}\n   {body}\n"
                    elif title:
                         search_results_text += f"{i+1}. {title}\n"
                    elif body:
                         search_results_text += f"{i+1}. {body}\n"

                    # ★ 情報源リストに追加 (タイトルとURLがあれば)
                    if title and url:
                        try:
                            # ドメイン名を抽出。失敗したらURLそのまま
                            parsed_url = urlparse(url)
                            domain = parsed_url.netloc if parsed_url.netloc else url
                        except Exception:
                            domain = url
                        sources.append({"title": title, "url": url, "domain": domain})

                search_results_text += "--- Web検索結果ここまで ---\n"
                print(f"検索結果 (Sources): {sources}") # デバッグ用
            else:
                print("Web検索結果が見つかりませんでした。")
                search_results_text = "Web検索結果は見つかりませんでした。"
    except Exception as e:
        print(f"Web検索中にエラーが発生しました: {e}", file=sys.stderr)
        search_results_text = "Web検索中にエラーが発生しました。"

    # ★ 結果テキストと情報源リストを辞書で返す
    return {"result_text": search_results_text, "sources": sources}

def get_gemini_response(model_name, context, chat_history, user_message, chat_context, enable_search,
                        image_data_base64=None, image_mime_type=None): 
    """Google Geminiモデルを使用して応答を生成 (Function Calling & 今回の画像入力対応)"""

    if not GOOGLE_API_KEY:
        raise ValueError("Google API Keyが設定されていません。")

    # ★ 画像入力がある場合、マルチモーダル対応モデルか確認/促す
    #    例: gemini-1.5-flash-latest などを使う
    if image_data_base64:
        # マルチモーダル非対応モデルが選択されていた場合の警告/変更（必要に応じて）
        if not ('flash' in model_name or 'pro' in model_name): # 簡単なチェック
             print(f"警告: 画像入力は Gemini Flash/Pro モデルでのみサポートされます。現在のモデル: {model_name}")
             # ここでエラーを返すか、モデル名を強制変更するかの選択肢あり
             # return {"message": f"エラー: 画像入力は Gemini Flash/Pro モデルを選択してください。", "sources": []}
             # model_name = 'gemini-1.5-flash-latest' # 強制変更例

        # マルチモーダル対応モデルでも古いバージョンの可能性もあるため注意喚起
        if not ('1.5' in model_name or 'latest' in model_name):
             print(f"情報: より新しいモデル(gemini-1.5-flash-latestなど)の方が画像認識性能が高い可能性があります。現在のモデル: {model_name}")

    generation_config = GenerationConfig()
    model_kwargs = {"generation_config": generation_config}
    tool_config = None
    if enable_search:
        print("--- Web検索ツールを有効にしてGeminiを初期化 ---")
        model_kwargs["tools"] = [search_tool]
        tool_config = {"function_calling_config": {"mode": "ANY"}}
        print(f"--- Tool config mode set to: {tool_config['function_calling_config']['mode']} ---")

    model = genai.GenerativeModel(model_name, **model_kwargs)

    # チャット履歴の作成 (★ 過去の画像は考慮しない)
    gemini_history = []
    system_instruction_content = f"""あなたは親切で知識豊富なアシスタントです。
ユーザーの質問に答えるために、提供された情報（ドキュメント内容、チャット履歴、必要に応じてWeb検索ツール、添付画像）を活用してください。
Web検索ツールが利用可能な場合は、最新情報や外部情報が必要だと判断した場合に使用できます。

--- ドキュメント ---
{context}
--- ドキュメントここまで ---
"""
    if chat_context:
         system_instruction_content += f"""
--- ユーザー指定の重要コンテキスト ---
{chat_context}
--- コンテキストここまで ---
"""
    gemini_history.append({"role": "user", "parts": [system_instruction_content]})
    gemini_history.append({"role": "model", "parts": ["承知しました。"]})

    # 既存履歴を追加 (テキストのみ)
    for msg in chat_history:
        role = "model" if msg['role'] == 'assistant' else msg['role']
        if msg['content'] == system_instruction_content or msg['content'] == "承知しました。":
            continue
        # テキストのみのパーツを作成
        msg_parts = []
        if msg['content']:
            msg_parts.append(msg['content'])
        
        if msg_parts:
            gemini_history.append({"role": role, "parts": msg_parts})
    
    # 最新のユーザー入力（テキスト＋今回の添付画像）を履歴に追加
    latest_user_parts = []
    if user_message:
        latest_user_parts.append(user_message)
    if image_data_base64 and image_mime_type:
        try:
            image_bytes = base64.b64decode(image_data_base64)
            image_part = {"mime_type": image_mime_type, "data": image_bytes}
            latest_user_parts.append(image_part)
            print(f"--- 今回の添付画像 ({image_mime_type}) をリクエストに追加 ---")
        except Exception as img_e:
            print(f"今回の添付画像処理エラー: {img_e}", file=sys.stderr)
            latest_user_parts.append(f"(添付画像処理エラー: {img_e})")
    if latest_user_parts:
        gemini_history.append({"role": "user", "parts": latest_user_parts})

    # --- Gemini API呼び出し --- 
    print(f"--- Geminiへ送信 (検索有効: {enable_search}, Tool Mode: {tool_config['function_calling_config']['mode'] if tool_config else 'AUTO'}) ---")

    final_response_text = ""
    sources = []

    try:
        # ★ Function Call後の再呼び出し時の履歴からは画像が除外される
        response = model.generate_content(
            gemini_history, 
            stream=False,
            tool_config=tool_config 
        )
        print("--- Geminiからの最初の応答受信 ---")

        # response.candidates が存在するか、空でないか確認
        if not response.candidates:
            print("--- 応答候補が存在しません --- ")
            # finish_reason など詳細があれば取得
            finish_reason = getattr(response, 'prompt_feedback', {}).get('block_reason', '不明')
            final_response_text = f"応答がブロックされたか、空でした。理由: {finish_reason}"
            return {"message": final_response_text, "sources": sources}
            
        candidate = response.candidates[0]

        # 安全性などで応答がない場合も考慮
        if not candidate.content or not candidate.content.parts:
             print("--- 応答候補にコンテンツまたはパーツがありません --- ")
             finish_reason = getattr(candidate, 'finish_reason', '不明')
             safety_ratings = getattr(candidate, 'safety_ratings', [])
             final_response_text = f"応答がブロックされたか、空でした。理由: {finish_reason}, Safety: {safety_ratings}"
             return {"message": final_response_text, "sources": sources}

        part = candidate.content.parts[0]

        # Function Call 処理
        if hasattr(part, 'function_call') and part.function_call.name == "web_search":
            print(f"--- Function Call検出: {part.function_call.name} ---")
            function_call = part.function_call
            args = function_call.args
            search_query = args.get("search_query")

            if search_query:
                search_result_data = execute_web_search(search_query)
                search_results_text_for_ai = search_result_data["result_text"]
                sources = search_result_data["sources"] # ★ sources に代入

                function_response_part = {
                    "function_response": {
                        "name": "web_search",
                        "response": {"result": search_results_text_for_ai}
                    }
                }
                # ★ Function Call後の再呼び出し履歴 (テキストのみで再構築)
                history_for_final_call = []
                for item in gemini_history:
                     # 簡単な実装: role='function' 以外で、parts が文字列のみのものを抽出
                     if item['role'] != 'function' and all(isinstance(p, str) for p in item['parts']):
                         history_for_final_call.append(item)
                history_for_final_call.append(candidate.content) # AIのFunctionCall要求
                history_for_final_call.append({"role": "function", "parts": [function_response_part]}) # Function Response
                
                response = model.generate_content(history_for_final_call, stream=False)
                print("--- Geminiからの最終応答受信 ---")

                # 最終応答の候補とパーツを再取得、存在チェック
                if not response.candidates:
                    print("--- 最終応答に候補が存在しません --- ")
                    finish_reason = getattr(response, 'prompt_feedback', {}).get('block_reason', '不明')
                    final_response_text = f"検索後の応答がブロックされたか、空でした。理由: {finish_reason}"
                    # sources は保持されているので返す
                    return {"message": final_response_text, "sources": sources}
                    
                final_candidate = response.candidates[0]
                if not final_candidate.content or not final_candidate.content.parts:
                    print("--- 最終応答にコンテンツまたはパーツがありません --- ")
                    finish_reason = getattr(final_candidate, 'finish_reason', '不明')
                    safety_ratings = getattr(final_candidate, 'safety_ratings', [])
                    final_response_text = f"検索後の応答がブロックされたか、空でした。理由: {finish_reason}, Safety: {safety_ratings}"
                    # sources は保持されているので返す
                    return {"message": final_response_text, "sources": sources}
                
                final_part = final_candidate.content.parts[0]
                if hasattr(final_part, 'text'):
                    final_response_text = final_part.text
                else:
                    final_response_text = "検索結果を踏まえた応答を生成できませんでした。"
            else:
                print("--- Function Callに検索クエリが含まれていません ---")
                if hasattr(part, 'text'): final_response_text = part.text
                else: final_response_text = "検索クエリがAIから指定されませんでした。"
        
        # Function Call がなかった場合
        else:
            print("--- Function Callなし ---")
            if hasattr(part, 'text'):
                final_response_text = part.text
            else:
                 print("--- 通常応答にテキストが含まれていません ---")
                 finish_reason = getattr(candidate, 'finish_reason', '不明')
                 safety_ratings = getattr(candidate, 'safety_ratings', [])
                 final_response_text = f"応答がブロックされたか、空でした。理由: {finish_reason}, Safety: {safety_ratings}"

    except Exception as e:
         print(f"--- 応答処理中に例外 ({type(e).__name__}): {e} ---")
         try:
             if 'response' in locals() and response and response.candidates and response.candidates[0].content.parts[0].text:
                 print("--- 例外発生、最初の応答テキストを返します ---")
                 final_response_text = response.candidates[0].content.parts[0].text
             else:
                 final_response_text = f"AIからの応答処理中にエラーが発生しました: {type(e).__name__}"
         except Exception as inner_e:
             print(f"--- エラー時のフォールバック処理でも例外: {inner_e} ---")
             final_response_text = f"AIからの応答処理中に深刻なエラーが発生しました: {type(e).__name__}"

    # ★ 最終的なテキスト応答と情報源リストを辞書で返す
    return {"message": final_response_text, "sources": sources}

def get_claude_response(model_name, context, chat_history, user_message, thinking_enabled, chat_context):
    """
    Anthropic Claude 3 / 3.5 / 3.7 系 (Messages API) で応答を生成します。
    Claude‑2 はサポート対象外とし、Completions API は使用しません。
    """
    if not ANTHROPIC_API_KEY or not anthropic_client:
        raise ValueError("Anthropic API Keyまたはクライアントが設定されていません。")

    # --- Claude Messages 配列の構築 ---
    messages = []

    # 既存履歴を追加
    for msg in chat_history:
        role = "assistant" if msg['role'] == "assistant" else "user"
        messages.append({"role": role, "content": msg['content']})

    # 最新のユーザーメッセージ
    messages.append({"role": "user", "content": user_message})

    # Claude Messages API では system プロンプトはトップレベル `system` 引数で渡す
    system_prompt = (
        "You are a helpful, knowledgeable assistant. "
        "Use the provided document, conversation history and any additional context to answer the user."
    )
    if chat_context:
        system_prompt += f"\n\n[追加コンテキスト]\n{chat_context}"

    # --- Claude Messages API 呼び出し ---
    try:
        result = anthropic_client.messages.create(
            model=model_name,        # 例: claude-3-7-sonnet-20250219
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )

        # result.content は list[ContentBlock]. Text を取り出して連結
        output_chunks = []
        for blk in result.content:
            if isinstance(blk, str):
                output_chunks.append(blk)
            elif hasattr(blk, "text"):
                output_chunks.append(blk.text)
        return "".join(output_chunks).strip()

    except Exception as e:
        print(f"Claude Messages API エラー: {e}", file=sys.stderr)
        raise RuntimeError(f"Claude API呼び出し中にエラーが発生しました: {type(e).__name__}")

def get_openai_response(model_name, context, chat_history, user_message, chat_context):
    """OpenAI GPTモデルを使用して応答を生成"""
    messages = []
    
    # システムプロンプトの組み立て
    system_prompt_base = f"""あなたはユーザーのアシスタントとして、ユーザーがチャットで入力した内容に応じて適切な内容を出力します。

このチャットでは、あなたとユーザーの過去の会話履歴が自動的に提供されます。過去の会話のコンテキストを考慮して返答してください。ユーザーが過去の会話内容に言及した場合は、その履歴を参照して適切に応答してください。

また、以下のドキュメントはユーザーが現在作成している内容で、この内容についての会話がこのチャットでは実施されます。
--- ドキュメントここから ---
{context}
--- ドキュメントここまで ---
"""
    
    # 選択テキスト -> チャットコンテキスト がある場合の追加指示
    if chat_context:
        system_prompt = system_prompt_base + f"""\n\n重要: ユーザーは以下のテキストを現在の会話の最重要コンテキストとして指定しました。ユーザーの指示が曖昧な場合（例：「これについて教えて」）、直前の会話履歴よりもまず、この追加コンテキストについて言及・回答することを最優先してください。
--- 追加コンテキストここから ---
{chat_context}
--- 追加コンテキストここまで ---
"""
    else:
        system_prompt = system_prompt_base
    
    messages.append({
        "role": "system",
        "content": system_prompt
    })
    
    # すべての会話履歴を追加
    for msg in chat_history:  # すべてのメッセージを使用（制限なし）
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    # 新しいユーザーメッセージを追加
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # --- OpenAI 新SDK (>=1.14) での呼び出し ---
    from openai import OpenAI   # 関数内 import（循環回避）
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model_name,         # 例: gpt-4o, gpt-4o-mini, gpt-4.5-turbo 等
        messages=messages
    )
    return response.choices[0].message.content


def get_openai_o3_response(model_name, context, chat_history, user_message, chat_context):
    """OpenAI o3 系モデル (Responses API) で応答を生成し、成功/失敗を dict で返す"""

    from openai import APIStatusError, APIConnectionError

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("環境変数 OPENAI_API_KEY が設定されていません。")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # --- 会話履歴を1本の文字列にまとめる ---
    history_text = ""
    for m in chat_history:
        role = "ユーザー" if m['role'] == "user" else "AI"
        history_text += f"{role}: {m['content']}\n"

    # --- system プロンプト ---
    system_prompt = (
        "あなたはユーザーの壁打ち相手です。\n"
        "--- ドキュメント ---\n"
        f"{context}\n"
        "--- ドキュメントここまで ---\n"
    )
    if chat_context:
        system_prompt += f"\n--- 追加コンテキスト ---\n{chat_context}\n--- ここまで ---"

    # --- input ---
    input_text = history_text + f"ユーザー: {user_message}"

    try:
        # o3 の Responses API 呼び出し
        rsp = client.responses.create(
            model=model_name,
            instructions=system_prompt,
            input=input_text
        )
        return {"success": True, "message": rsp.output_text}
    except (APIStatusError, APIConnectionError) as e:
        # OpenAI 側エラーを呼び出し元に伝える
        return {
            "success": False,
            "status": getattr(e, "status_code", 500),
            "message": f"OpenAI APIエラー: {getattr(e, 'message', str(e))}",
        }