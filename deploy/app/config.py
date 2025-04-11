from app.supabase_client import supabase
from flask import session

def _set_supabase_session():
    access_token = session.get('access_token')
    refresh_token = session.get('refresh_token')
    if access_token and refresh_token:
        supabase.auth.set_session(access_token, refresh_token)
        
def get_user_config():
    _set_supabase_session()
    user = supabase.auth.get_user().user
    user_id = user.id
    result = supabase.table('user_config').select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None

def set_user_config(config_name):
    _set_supabase_session()
    user = supabase.auth.get_user().user
    user_id = user.id
    existing = get_user_config()
    if existing:
        supabase.table('user_config').update({"config_name": config_name}).eq("user_id", user_id).execute()
    else:
        supabase.table('user_config').insert({"user_id": user_id, "config_name": config_name}).execute()
