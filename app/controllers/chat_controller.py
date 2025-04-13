from flask import Blueprint, request, jsonify, g
from app import supabase # Import supabase client from app/__init__.py
# Removed: from app.models.database import db, Document, ChatMessage
import os
import json
import sys
import uuid # Import uuid

# APIクライアントのインポート
import openai
import google.generativeai as genai
from anthropic import Anthropic

# Import the decorator and helpers
from app.utils.auth_utils import token_required, get_tenant_id_for_user, get_current_user

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

# --- Routes ---

# Changed route parameter
@chat_bp.route('/reset/<string:doc_id>', methods=['POST'])
@token_required # Apply decorator
def reset_chat_history(doc_id):
    """指定ドキュメントのチャット履歴削除 (テナント所属確認込み)"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({'success': False, 'message': '所属するテナントが見つかりません。'}), 400

    # !!! TODO: Add tenant check based on user's access to doc_id !!!
    try:
        # 1. ドキュメントが存在し、かつユーザーのテナントに属するか確認
        doc_check = supabase.table('documents').select('id').eq('id', doc_id).eq('tenant_id', tenant_id).maybe_single().execute()
        if not doc_check.data:
            return jsonify({'success': False, 'message': 'アクセス権限がないか、ドキュメントが見つかりません。'}), 404

        # 2. 該当ドキュメントIDのチャットメッセージを全て削除
        delete_response = supabase.table('chat_messages').delete().eq('document_id', doc_id).execute()

        # delete()のレスポンス形式を確認する必要があるが、エラーがなければ成功とみなす
        # print(f"ドキュメントID {doc_id} のチャット履歴削除レスポンス: {delete_response.data}") # デバッグ用
        print(f"ドキュメントID {doc_id} のチャット履歴を削除しました。") # 件数はレスポンスから取得できない場合がある
        return jsonify({'success': True, 'message': 'チャット履歴がリセットされました。'}), 200
    except Exception as e:
        # db.session.rollback() は不要
        print(f"チャット履歴のリセット中にエラーが発生しました: {str(e)}", file=sys.stderr)
        return jsonify({'success': False, 'message': 'チャット履歴のリセットに失敗しました。'}), 500

# Changed route parameter
@chat_bp.route('/history/<string:doc_id>', methods=['GET'])
@token_required # Apply decorator
def get_chat_history(doc_id):
    """指定ドキュメントのチャット履歴取得 (テナント所属確認込み)"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400

    # !!! TODO: Add tenant check based on user's access to doc_id !!!
    try:
        # 1. ドキュメントが存在し、ユーザーのテナントに属するか確認
        doc_check = supabase.table('documents').select('id').eq('id', doc_id).eq('tenant_id', tenant_id).maybe_single().execute()
        if not doc_check.data:
            return jsonify({"error": "アクセス権限がないか、ドキュメントが見つかりません。"}), 404

        # 2. チャット履歴を取得 (document_id でフィルタされているので tenant_id 不要)
        response = supabase.table('chat_messages').select('*').eq('document_id', doc_id).order('timestamp', desc=False).execute()
        return jsonify(response.data)
    except Exception as e:
        print(f"Error getting chat history for doc {doc_id}: {e}")
        return jsonify({"error": "Failed to get chat history"}), 500


# Changed route parameter
@chat_bp.route('/send/<string:doc_id>', methods=['POST'])
@token_required # Apply decorator
def send_message(doc_id):
    """メッセージを送信/保存し、AI応答取得 (テナント所属確認込み)"""
    # !!! TODO: Add tenant check based on user's access to doc_id !!!
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400

    try:
        # 1. ドキュメントの内容を取得 (テナント確認込み)
        doc_response = supabase.table('documents').select('content').eq('id', doc_id).eq('tenant_id', tenant_id).maybe_single().execute()
        if not doc_response.data:
            return jsonify({"error": "アクセス権限がないか、ドキュメントが見つかりません。"}), 404
        context = doc_response.data.get('content', '')

        data = request.get_json()
        user_message_content = data.get('message', '')
        model_name = data.get('model', 'gemini-1.5-flash') # Default model updated
        thinking_enabled = data.get('thinking_enabled', False)
        chat_context = data.get('chat_context') # Additional context from frontend selection

        # 2. ユーザーメッセージをデータベースに保存
        user_message_data = {
            'document_id': doc_id,
            'role': 'user',
            'content': user_message_content,
            'model_used': model_name,       # Record model used for this exchange
            'thinking_enabled': thinking_enabled, # Record setting for this exchange
            'user_id': user.id               # Associate message with authenticated user
        }
        # Filter out None user_id if necessary, though RLS might handle auth.uid()=user_id check
        # No longer needed as user is guaranteed by decorator

        insert_user_msg_response = supabase.table('chat_messages').insert(user_message_data).execute()
        if not insert_user_msg_response.data:
             print(f"Failed to save user message: {insert_user_msg_response}")
             # Don't proceed if user message saving failed
             return jsonify({"error": "Failed to save user message"}), 500


        # 3. ドキュメントの最新チャット履歴を取得
        history_response = supabase.table('chat_messages').select('*').eq('document_id', doc_id).order('timestamp', desc=False).execute()
        chat_history = history_response.data if history_response.data else []

        # 4. モデルに応じてAI応答を取得
        ai_response_content = ""
        try:
            # Pass the fetched history (list of dicts) to the AI functions
            if model_name.startswith('gemini'):
                if not GOOGLE_API_KEY: raise ValueError("Google API Keyが設定されていません。")
                ai_response_content = get_gemini_response(model_name, context, chat_history, user_message_content, chat_context)
            elif model_name.startswith('claude'):
                if not ANTHROPIC_API_KEY: raise ValueError("Anthropic API Keyが設定されていません。")
                ai_response_content = get_claude_response(model_name, context, chat_history, user_message_content, thinking_enabled, chat_context)
            elif model_name.startswith('gpt'):
                if not OPENAI_API_KEY: raise ValueError("OpenAI API Keyが設定されていません。")
                ai_response_content = get_openai_response(model_name, context, chat_history, user_message_content, chat_context)
            else:
                ai_response_content = "エラー: サポートされていないモデルが指定されました。"
        except Exception as e:
            ai_response_content = f"エラー: AIモデルからの応答取得に失敗しました。{str(e)}"
            print(f"AI応答エラー: {str(e)}", file=sys.stderr)

        # 5. AI応答をデータベースに保存
        ai_message_data = {
            'document_id': doc_id,
            'role': 'assistant',
            'content': ai_response_content,
            'model_used': model_name,
            'thinking_enabled': thinking_enabled
            # user_id for assistant messages is typically NULL
        }
        insert_ai_msg_response = supabase.table('chat_messages').insert(ai_message_data).execute()
        if not insert_ai_msg_response.data:
             # Log failure but maybe still return the AI response to the user?
             print(f"Warning: Failed to save AI response: {insert_ai_msg_response}")


        # 6. AI応答をフロントエンドに返す
        return jsonify({
            'message': ai_response_content, # Actual response content
            'model': model_name,
            'thinking_enabled': thinking_enabled
            # Optionally include the saved AI message ID from insert_ai_msg_response.data[0]['id']
        })

    except Exception as e:
        print(f"Error sending message for doc {doc_id}: {e}", file=sys.stderr)
        return jsonify({"error": "Failed to process message"}), 500


# --- AI Model Functions (mostly unchanged, ensure chat_history format is compatible) ---

def get_gemini_response(model_name, context, chat_history, user_message, chat_context):
    """Google Geminiモデルを使用して応答を生成"""
    # chat_history is now a list of dicts from Supabase, already in a good format.
    chat_history_formatted = []
    for msg in chat_history: # Process the history obtained from Supabase
        role = "model" if msg.get('role') == 'assistant' else msg.get('role') # Map 'assistant' to 'model'
        if role in ['user', 'model']: # Ensure only valid roles are added
             chat_history_formatted.append({"role": role, "parts": [msg.get('content', '')]})

    model = genai.GenerativeModel(model_name)

    # System prompt assembly (unchanged logic)
    system_prompt_base = f"""あなたはユーザーのアシスタントとして、ユーザーがチャットで入力した内容に応じて適切な内容を出力します。

このチャットでは、あなたとユーザーの過去の会話履歴が自動的に提供されます。過去の会話のコンテキストを考慮して返答してください。ユーザーが過去の会話内容に言及した場合は、その履歴を参照して適切に応答してください。

また、以下のドキュメントはユーザーが現在作成している内容で、この内容についての会話がこのチャットでは実施されます。
--- ドキュメントここから ---
{context}
--- ドキュメントここまで ---
"""
    if chat_context:
        system_prompt = system_prompt_base + f"""\n\n重要: ユーザーは以下のテキストを現在の会話の最重要コンテキストとして指定しました。ユーザーの指示が曖昧な場合（例：「これについて教えて」）、直前の会話履歴よりもまず、この追加コンテキストについて言及・回答することを最優先してください。\n--- 追加コンテキストここから ---\n{chat_context}\n--- 追加コンテキストここまで ---"""
    else:
        system_prompt = system_prompt_base

    # Inject system prompt if needed (unchanged logic, but relies on chat_history_formatted)
    if not chat_history_formatted or chat_history_formatted[0].get('role') != 'user' or not chat_history_formatted[0].get('parts',[''])[0].startswith('あなたは'):
         chat_history_formatted.insert(0, {"role": "user", "parts": [system_prompt]})
         chat_history_formatted.insert(1, {"role": "model", "parts": ["承知しました。"]}) # Assuming Gemini needs this structure

    # Start chat and send message
    chat = model.start_chat(history=chat_history_formatted)
    response = chat.send_message(user_message) # Send only the latest user message content

    return response.text

def get_claude_response(model_name, context, chat_history, user_message, thinking_enabled, chat_context):
    """Anthropic Claudeモデルを使用して応答を生成"""
    # chat_history is already a list of dicts from Supabase
    messages = []

    # System prompt assembly (unchanged logic)
    system_prompt_base = f"""あなたはユーザーのアシスタントとして、ユーザーがチャットで入力した内容に応じて適切な内容を出力します。\n\nこのチャットでは、あなたとユーザーの過去の会話履歴が自動的に提供されます。過去の会話のコンテキストを考慮して返答してください。ユーザーが過去の会話内容に言及した場合は、その履歴を参照して適切に応答してください。\n\nまた、以下のドキュメントはユーザーが現在作成している内容で、この内容についての会話がこのチャットでは実施されます。\n--- ドキュメントここから ---\n{context}\n--- ドキュメントここまで ---"""
    if chat_context:
        system_prompt = system_prompt_base + f"""\n\n重要: ユーザーは以下のテキストを現在の会話の最重要コンテキストとして指定しました。ユーザーの指示が曖昧な場合（例：「これについて教えて」）、直前の会話履歴よりもまず、この追加コンテキストについて言及・回答することを最優先してください。\n--- 追加コンテキストここから ---\n{chat_context}\n--- 追加コンテキストここまで ---"""
    else:
        system_prompt = system_prompt_base

    # Format messages for Claude (system prompt goes in `system` parameter)
    for msg in chat_history:
         # Ensure role is 'user' or 'assistant'
        role = msg.get('role')
        if role in ['user', 'assistant']:
            messages.append({
                "role": role,
                "content": msg.get('content', '')
            })

    # Add the latest user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    # Generate response using Claude API
    if not anthropic_client: # Check if client is initialized
        raise ValueError("Anthropic client not initialized. Check API Key.")

    response = anthropic_client.messages.create(
        model=model_name,
        messages=messages,
        system=system_prompt,
        max_tokens=4096 # Example: Set max tokens if needed
        # thinking_enabled not directly applicable here
    )

    # Handle potential list response for content
    if response.content and isinstance(response.content, list):
        return response.content[0].text
    elif hasattr(response.content, 'text'): # If it's a single object with text
         return response.content.text
    else: # Fallback or error
        print(f"Unexpected Claude response format: {response}")
        return "Error: Could not parse Claude response."


def get_openai_response(model_name, context, chat_history, user_message, chat_context):
    """OpenAI GPTモデルを使用して応答を生成"""
    messages = []

    # System prompt assembly (unchanged logic)
    system_prompt_base = f"""あなたはユーザーのアシスタントとして、ユーザーがチャットで入力した内容に応じて適切な内容を出力します。\n\nこのチャットでは、あなたとユーザーの過去の会話履歴が自動的に提供されます。過去の会話のコンテキストを考慮して返答してください。ユーザーが過去の会話内容に言及した場合は、その履歴を参照して適切に応答してください。\n\nまた、以下のドキュメントはユーザーが現在作成している内容で、この内容についての会話がこのチャットでは実施されます。\n--- ドキュメントここから ---\n{context}\n--- ドキュメントここまで ---\n"""
    if chat_context:
        system_prompt = system_prompt_base + f"""\n\n重要: ユーザーは以下のテキストを現在の会話の最重要コンテキストとして指定しました。ユーザーの指示が曖昧な場合（例：「これについて教えて」）、直前の会話履歴よりもまず、この追加コンテキストについて言及・回答することを最優先してください。\n--- 追加コンテキストここから ---\n{chat_context}\n--- 追加コンテキストここまで ---"""
    else:
        system_prompt = system_prompt_base

    # Add system message
    messages.append({
        "role": "system",
        "content": system_prompt
    })

    # Add history messages
    for msg in chat_history:
        role = msg.get('role')
        if role in ['user', 'assistant']:
            messages.append({
                "role": role,
                "content": msg.get('content', '')
            })

    # Add latest user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    # Generate response using OpenAI API
    # Ensure you are using the correct client library call, might be openai.chat.completions.create for newer versions
    try:
        # Assuming older openai library version based on initial requirements
        response = openai.ChatCompletion.create(
             model=model_name,
             messages=messages
        )
        return response.choices[0].message['content'] # Accessing content might differ slightly based on version
    except AttributeError:
         # Try newer client library style if the old one fails
         from openai import OpenAI
         client = OpenAI(api_key=OPENAI_API_KEY) # Initialize client here if needed
         response = client.chat.completions.create(
             model=model_name,
             messages=messages
         )
         return response.choices[0].message.content 