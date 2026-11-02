import os
import datetime
import yaml
import jwt
import bcrypt
import streamlit as st
import streamlit.components.v1 as components

CONFIG_PATH = "login_config.yml"


def get_config():
    """Load configuration from login_config.yml."""
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def is_authenticated() -> bool:
    """
    Check if user is authenticated in session state.
    If not, inspect st.context.cookies to automatically restore session on page reload/refresh.
    """
    # 1. Already authenticated in current session memory
    if st.session_state.get("authentication_status") and st.session_state.get("user_info"):
        return True

    # 2. Check for persistent browser cookie
    config = get_config()
    if not config:
        return False

    cookie_cfg = config.get("cookie", {})
    cookie_name = cookie_cfg.get("name", "mpis_auth_cookie")
    cookie_key = cookie_cfg.get("key")

    token = None
    try:
        token = st.context.cookies.get(cookie_name)
    except Exception:
        token = None

    if token and cookie_key:
        try:
            payload = jwt.decode(token, cookie_key, algorithms=["HS256"])
            username = payload.get("username")
            exp_date = payload.get("exp_date", 0)
            now_ts = datetime.datetime.now().timestamp()

            usernames = config.get("credentials", {}).get("usernames", {})
            if username and exp_date > now_ts and username in usernames:
                user_record = usernames[username]
                role = user_record.get("role", "Officer")

                # Rehydrate full session state
                st.session_state["authentication_status"] = True
                st.session_state["login_status"] = True
                st.session_state["username"] = username
                st.session_state["name"] = user_record.get("name", username)
                st.session_state["user"] = username
                st.session_state["role"] = role
                st.session_state["user_info"] = user_record
                return True
        except Exception:
            pass

    return False


def require_auth() -> bool:
    """Helper for sub-pages: returns True if authenticated (or restored), False otherwise."""
    return is_authenticated()


def login_user(username: str, password: str) -> tuple[bool, str | None]:
    """
    Validate username and password, generate signed JWT token,
    and persist cookie to the user's browser via client-side script.
    """
    config = get_config()
    if not config:
        return False, "Configuration file not found."

    usernames = config.get("credentials", {}).get("usernames", {})
    if username not in usernames:
        return False, "Invalid username or password."

    user_record = usernames[username]
    pw_hash = user_record.get("password", "")

    try:
        matched = bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8"))
    except Exception:
        matched = False

    if not matched:
        return False, "Invalid username or password."

    # Successful login: generate token
    cookie_cfg = config.get("cookie", {})
    cookie_name = cookie_cfg.get("name", "mpis_auth_cookie")
    cookie_key = cookie_cfg.get("key")
    expiry_days = cookie_cfg.get("expiry_days", 7)

    exp_ts = (datetime.datetime.now() + datetime.timedelta(days=expiry_days)).timestamp()
    token = jwt.encode({"username": username, "exp_date": exp_ts}, cookie_key, algorithm="HS256")

    # Set session state
    role = user_record.get("role", "Officer")
    st.session_state["authentication_status"] = True
    st.session_state["login_status"] = True
    st.session_state["username"] = username
    st.session_state["name"] = user_record.get("name", username)
    st.session_state["user"] = username
    st.session_state["role"] = role
    st.session_state["user_info"] = user_record

    max_age_secs = int(expiry_days * 86400)

    # Inject client-side cookie write & trigger refresh to rehydrate
    js_set_cookie = f"""
    <script>
        const cookieVal = "{token}";
        const cookieName = "{cookie_name}";
        const maxAge = {max_age_secs};
        const cookieStr = cookieName + "=" + cookieVal + "; path=/; max-age=" + maxAge + "; SameSite=Lax";
        try {{
            window.parent.document.cookie = cookieStr;
        }} catch(e) {{
            document.cookie = cookieStr;
        }}
        setTimeout(() => {{
            window.parent.location.reload();
        }}, 80);
    </script>
    """
    components.html(js_set_cookie, height=0)
    return True, None


def logout_user():
    """Clear session state and purge browser cookie."""
    config = get_config()
    cookie_name = (
        config.get("cookie", {}).get("name", "mpis_auth_cookie")
        if config
        else "mpis_auth_cookie"
    )

    for k in [
        "authentication_status",
        "login_status",
        "username",
        "name",
        "user",
        "role",
        "roles",
        "user_info",
    ]:
        if k in st.session_state:
            st.session_state[k] = None

    js_clear_cookie = f"""
    <script>
        const cookieName = "{cookie_name}";
        const clearStr = cookieName + "=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        try {{
            window.parent.document.cookie = clearStr;
        }} catch(e) {{
            document.cookie = clearStr;
        }}
        setTimeout(() => {{
            window.parent.location.href = "/";
        }}, 80);
    </script>
    """
    components.html(js_clear_cookie, height=0)

