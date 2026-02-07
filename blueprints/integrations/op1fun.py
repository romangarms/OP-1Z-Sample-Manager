"""
At the moment, this contains all the op-1.fun integration code.
We may convert this to a package if we add more integrations later, or the code grows too large.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from flask import jsonify, request, current_app

from ..config import delete_config_setting, get_config_setting, set_config_setting
from ..constants import Config, OP1FUN
from . import integrations_bp


class Op1FunTokenError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _json_or_none(response: requests.Response) -> dict[str, Any] | None:
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
    except ValueError:
        return None
    return None


def build_op1fun_auth_header() -> dict[str, str] | None:
    """Build auth headers for op-1.fun authenticated requests.

    Per op-1.fun docs, all requests except API token lookup must include:
    - X-User-Token
    - X-User-Email

    Returns None if token/email are not configured.
    """
    token = get_config_setting(Config.Integrations.OP1FUN_USER_TOKEN, "")
    email = get_config_setting(Config.Integrations.OP1FUN_USER_EMAIL, "")
    if not token or not email:
        return None

    return {
        "accept": "application/json",
        "X-User-Token": token,
        "X-User-Email": email,
    }


@integrations_bp.route("/integrations/op1fun/api_token", methods=["POST"])
def op1fun_api_token_lookup():
    """Exchange email/password for an op-1.fun API token and store it.

    Request JSON:
      {"email": "user@example.com", "password": "..."}

    Response JSON:
      {"success": true, "api_token": "..."}

    Notes:
    - This endpoint does not persist the password.
    - The token + email are stored in app config for future op-1.fun requests.
    """

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Missing 'email' or 'password'"}), 400

    try:
        api_token = _attempt_op1fun_token_lookup_and_save(email, password)
    except Op1FunTokenError as exc:
        return jsonify({"success": False, "error": exc.message}), exc.status_code

    return jsonify({"success": True, "api_token": api_token})


def _attempt_op1fun_token_lookup_and_save(email: str, password: str) -> str:
    try:
        resp = requests.post(
            OP1FUN.OP1FUN_API_TOKEN_URL,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
            },
            json={
                "email": email,
                "password": password,
            },
            timeout=15,
        )
    except requests.exceptions.Timeout:
        current_app.logger.error("op-1.fun token lookup timed out")
        raise Op1FunTokenError("op-1.fun token lookup timed out", 504)
    except requests.exceptions.RequestException as e:
        current_app.logger.error("op-1.fun token lookup request failed: %s", e)
        raise Op1FunTokenError("op-1.fun token lookup request failed", 502)

    payload = _json_or_none(resp)

    if resp.status_code != 200:
        message = None
        if payload:
            message = payload.get("error") or payload.get("message")
        if not message:
            message = "Authentication failed"
        raise Op1FunTokenError(message, resp.status_code)

    if not payload or not payload.get("api_token"):
        current_app.logger.error(
            "op-1.fun token lookup succeeded but response JSON was unexpected (status=%s)",
            resp.status_code,
        )
        raise Op1FunTokenError("Unexpected response from op-1.fun", 502)

    api_token = payload["api_token"]

    # Store for future authenticated API requests
    set_config_setting(Config.Integrations.OP1FUN_USER_EMAIL, email)
    set_config_setting(Config.Integrations.OP1FUN_USER_TOKEN, api_token)
    set_config_setting(
        Config.Integrations.OP1FUN_TOKEN_OBTAINED_AT,
        datetime.now(timezone.utc).isoformat()
    )
    return api_token


def _clear_op1fun_auth():
    """Clear stored op-1.fun authentication token and email."""
    delete_config_setting(Config.Integrations.OP1FUN_USER_EMAIL)
    delete_config_setting(Config.Integrations.OP1FUN_USER_TOKEN)
    delete_config_setting(Config.Integrations.OP1FUN_TOKEN_OBTAINED_AT)


@integrations_bp.route("/integrations/op1fun/clear_auth", methods=["POST"])
def op1fun_clear_auth():
    """Clear stored op-1.fun authentication token and email.
    Response JSON:
      {"success": true}
    """
    _clear_op1fun_auth()
    return jsonify({"success": True})
