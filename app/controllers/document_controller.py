from flask import Blueprint, request, jsonify, g # Import g
from app import supabase # Import supabase client from app/__init__.py
import uuid # Import uuid for potential ID conversion
# Import the decorator and helpers
from app.utils.auth_utils import token_required, get_tenant_id_for_user, get_current_user

document_bp = Blueprint('document', __name__, url_prefix='/api/document')

# --- Routes ---

@document_bp.route('/list', methods=['GET'])
@token_required # Apply decorator
def list_documents():
    """認証されたユーザーのテナントに属するドキュメントを返す"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    # !!! TODO: Filter by current_tenant_id after auth implementation !!!
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400
    try:
        # Filter by tenant_id
        response = supabase.table('documents').select('*').eq('tenant_id', tenant_id).order('updated_at', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        print(f"Error listing documents: {e}")
        return jsonify({"error": "Failed to list documents"}), 500

@document_bp.route('/recent', methods=['GET'])
@token_required # Apply decorator
def get_recent_documents():
    """認証されたユーザーのテナントに属する最近のドキュメント10件を返す"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400
    # !!! TODO: Filter by current_tenant_id after auth implementation !!!
    try:
        # Filter by tenant_id
        response = supabase.table('documents').select('*').eq('tenant_id', tenant_id).order('updated_at', desc=True).limit(10).execute()
        return jsonify(response.data)
    except Exception as e:
        print(f"Error getting recent documents: {e}")
        return jsonify({"error": "Failed to get recent documents"}), 500

# Changed route parameter from <int:doc_id> to <string:doc_id>
@document_bp.route('/<string:doc_id>', methods=['GET'])
@token_required # Apply decorator
def get_document(doc_id):
    """指定されたIDのドキュメントを取得 (テナント所属確認込み)"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400
    # !!! TODO: Filter by current_tenant_id after auth implementation !!!
    try:
        # Filter by id AND tenant_id (RLS should also enforce this)
        response = supabase.table('documents').select('*').eq('id', doc_id).eq('tenant_id', tenant_id).maybe_single().execute()
        if response.data:
            return jsonify(response.data)
        else:
            return jsonify({"error": "Document not found"}), 404
    except Exception as e:
        print(f"Error getting document {doc_id}: {e}")
        return jsonify({"error": "Failed to get document"}), 500

@document_bp.route('/create', methods=['POST'])
@token_required # Apply decorator
def create_document():
    """新規ドキュメントを作成"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    data = request.get_json()
    title = data.get('title', '無題のドキュメント')
    content = data.get('content', '')
    # creator_id = user.id # RLS/trigger might handle this based on auth.uid()

    if not tenant_id:
        # If user has no tenant, maybe create one or return error
        # For now, return error. Tenant creation logic could be separate.
        return jsonify({"error": "所属するテナントが見つかりません。ドキュメントを作成できません。"}), 400

    # Prepare document data
    doc_data = {
        'title': title,
        'content': content,
        'tenant_id': tenant_id,
        'creator_id': user.id # Explicitly set creator_id
        # creator_id will be set by RLS/trigger based on auth.uid() if user is logged in
        # However, explicitly setting it might be clearer if user_id is available here
        # 'creator_id': creator_id # Add this if creator_id is fetched reliably
    }
    # Removed creator_id check as user is guaranteed by decorator

    try:
        response = supabase.table('documents').insert(doc_data).execute()
        if response.data:
            # Fetch the newly created document to return its full representation?
            # Supabase insert might only return minimal info by default
            # Or just return the input data + generated ID if available in response
            # Assuming response.data[0] has the created doc including 'id'
            new_doc = response.data[0]
            return jsonify(new_doc), 201
        else:
            # Check for errors in the response if possible
            print(f"Failed to create document, response: {response}")
            return jsonify({"error": "Failed to create document"}), 500
    except Exception as e:
        print(f"Error creating document: {e}")
        # Consider checking for specific Supabase errors (e.g., duplicate key, RLS violation)
        return jsonify({"error": f"Failed to create document: {e}"}), 500


# Changed route parameter
@document_bp.route('/<string:doc_id>', methods=['PUT'])
@token_required # Apply decorator
def update_document(doc_id):
    """指定されたIDのドキュメントを更新 (テナント所属確認込み)"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400

    # !!! TODO: RLS should enforce tenant check, but explicit check might be good practice !!!
    data = request.get_json()
    update_data = {}
    if 'title' in data:
        update_data['title'] = data['title']
    if 'content' in data:
        update_data['content'] = data['content']

    # updated_at is handled by the database trigger now

    if not update_data:
        return jsonify({"error": "No update data provided"}), 400

    try:
        # Filter by id AND tenant_id for update
        response = supabase.table('documents').update(update_data).eq('id', doc_id).eq('tenant_id', tenant_id).execute()
        # Check if rows were affected (Supabase client might not directly return this)
        # We might need to fetch the document again to confirm the update
        # For now, assume success if no exception
        # A better check involves seeing if response.data is empty or contains the updated item
        if response.data:
             return jsonify(response.data[0]) # Return updated doc
        else:
            # Could be not found or update failed silently
            # Check if document exists first?
             check_res = supabase.table('documents').select('id').eq('id', doc_id).eq('tenant_id', tenant_id).maybe_single().execute()
             if check_res.data:
                 print(f"Document {doc_id} found, but update returned no data. RLS issue?")
                 return jsonify({"error": "Update failed or document unchanged"}), 500
             else:
                 return jsonify({"error": "Document not found"}), 404

    except Exception as e:
        print(f"Error updating document {doc_id}: {e}")
        return jsonify({"error": "Failed to update document"}), 500

# Changed route parameter
@document_bp.route('/<string:doc_id>/duplicate', methods=['POST'])
@token_required # Apply decorator
def duplicate_document(doc_id):
    """指定されたIDのドキュメントを複製 (テナント所属確認込み)"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    # !!! TODO: RLS should enforce tenant check !!!
    # creator_id = user.id

    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。複製できません。"}), 400

    try:
        # 1. Get the original document (ensure it belongs to the user's tenant)
        get_response = supabase.table('documents').select('title, content').eq('id', doc_id).eq('tenant_id', tenant_id).maybe_single().execute()
        if not get_response.data:
            return jsonify({"error": "Original document not found"}), 404

        original_doc = get_response.data

        # 2. Prepare the new document data
        new_doc_data = {
            'title': f"{original_doc['title']} (コピー)",
            'content': original_doc['content'],
            'tenant_id': tenant_id,
            'creator_id': user.id # Set creator for the new copy
        }
        # Removed creator_id check as user is guaranteed by decorator

        # 3. Insert the new document
        insert_response = supabase.table('documents').insert(new_doc_data).execute()
        if insert_response.data:
            return jsonify(insert_response.data[0]), 201
        else:
            print(f"Failed to duplicate document, response: {insert_response}")
            return jsonify({"error": "Failed to duplicate document"}), 500
    except Exception as e:
        print(f"Error duplicating document {doc_id}: {e}")
        return jsonify({"error": "Failed to duplicate document"}), 500

# Changed route parameter
@document_bp.route('/<string:doc_id>', methods=['DELETE'])
@token_required # Apply decorator
def delete_document(doc_id):
    """指定されたIDのドキュメントを削除 (テナント所属確認込み)"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400

    # !!! TODO: RLS should enforce tenant check !!!
    try:
        # Filter by id AND tenant_id for delete
        response = supabase.table('documents').delete().eq('id', doc_id).eq('tenant_id', tenant_id).execute()
        # Deletion might return the deleted item(s) or just status/count
        # Check if deletion happened. Maybe check response.data is not empty or status code
        # If response.data is empty after delete, it might mean it wasn't found or RLS prevented it.
        # Need to verify Supabase client behavior for delete.
        # Let's check if it existed first for a better message.
        check_res = supabase.table('documents').select('id').eq('id', doc_id).eq('tenant_id', tenant_id).maybe_single().execute()
        if not check_res.data and not response.data: # Already gone or never existed
             return jsonify({"error": "Document not found or already deleted"}), 404

        # If check_res had data but response.data is empty, RLS might have blocked delete
        if check_res.data and not response.data:
             print(f"Document {doc_id} found, but delete returned no data. RLS issue?")
             return jsonify({"error": "Failed to delete document (check permissions)"}), 500

        # Assuming successful deletion if we get here without error and it existed
        return jsonify({"message": "ドキュメントが削除されました", "id": doc_id})

    except Exception as e:
        print(f"Error deleting document {doc_id}: {e}")
        return jsonify({"error": "Failed to delete document"}), 500

@document_bp.route('/latest_id', methods=['GET'])
@token_required # Apply decorator
def get_latest_document_id():
    """認証されたユーザーのテナントに属する最新ドキュメントIDを返す"""
    user = get_current_user()
    tenant_id = get_tenant_id_for_user(user.id)
    if not tenant_id:
        return jsonify({"error": "所属するテナントが見つかりません。"}), 400

    # !!! TODO: Filter by current_tenant_id after auth implementation !!!
    try:
        # Filter by tenant_id
        response = supabase.table('documents').select('id').eq('tenant_id', tenant_id).order('updated_at', desc=True).limit(1).maybe_single().execute()
        if response.data:
            return jsonify({"latest_id": response.data['id']})
        else:
            return jsonify({"error": "No documents found"}), 404
    except Exception as e:
        print(f"Error getting latest document ID: {e}")
        return jsonify({"error": "Failed to get latest document ID"}), 500 