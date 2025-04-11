from app.supabase_client import supabase
from flask import session
def login_user(email, password):
    user_session = supabase.auth.sign_in_with_password({"email": email, "password": password})
    if user_session.user:
        access_token = user_session.session.access_token
        refresh_token = user_session.session.refresh_token
        return [user_session.user, access_token, refresh_token]
    return [None, None, None]


def get_current_user():
    return supabase.auth.get_user().user