from functools import wraps
from flask import request, g, jsonify
from app.supabase_client import supabase # Import from new location

# Decorator to protect routes that require authentication
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Expecting "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"message": "Invalid Authorization header format"}), 401

        if not token:
            return jsonify({"message": "Authentication Token is missing!"}), 401

        try:
            # Validate the token using Supabase
            # user_response = supabase.auth.get_user(token) # This requires the token itself
            # Let's use the client's built-in method which uses the stored session if possible,
            # or verifies the passed token if not.
            # However, Supabase client typically manages the session server-side, 
            # and expects the JS client to send the token.
            # We need to verify the token sent by the JS client.
            
            # Get user associated with the provided token
            user_response = supabase.auth.get_user(token)
            user = user_response.user
            
            if not user:
                 # Check if maybe the error holds more info (e.g., expired token)
                 if user_response.error:
                     print(f"Token validation error: {user_response.error}")
                     # Map Supabase error to HTTP status if possible
                     message = f"Token validation failed: {user_response.error.message}"
                     status_code = 401 # Default to Unauthorized
                     if 'expired' in message.lower():
                         status_code = 401 # Or maybe 403 Forbidden
                     return jsonify({"message": message}), status_code
                 else:
                     return jsonify({"message": "Token is invalid or user not found"}), 401

            # Store the user object in Flask's global context `g`
            g.user = user
            print(f"Authenticated user: {g.user.id} ({g.user.email})") # Log authenticated user

        except Exception as e:
            print(f"Token validation unexpected error: {e}")
            return jsonify({"message": "Token validation failed unexpectedly"}), 500

        # Proceed with the original route function
        return f(*args, **kwargs)

    return decorated_function

# Helper function to get tenant ID (placeholder, needs implementation)
def get_tenant_id_for_user(user_id):
    """Fetches the tenant ID associated with the user.
       Placeholder: Implement logic to query user_tenants table.
       Handles single vs multiple tenants per user based on your SaaS design.
    """
    if not user_id:
        return None
    try:
        # Example: Assuming a user belongs to one tenant for simplicity
        response = supabase.table('user_tenants').select('tenant_id').eq('user_id', user_id).limit(1).maybe_single().execute()
        if response and response.data:
            tenant_id = response.data['tenant_id']
            print(f"Found tenant_id {tenant_id} for user {user_id}")
            return tenant_id
        else:
            print(f"No tenant found for user {user_id} in user_tenants table.")
            # Handle cases where user might not have a tenant yet or error occurred
            return None # Or raise an error / handle tenant creation
    except Exception as e:
        print(f"Error fetching tenant ID for user {user_id}: {e}")
        return None

# Helper function to get current user from context
def get_current_user():
    return getattr(g, 'user', None) 