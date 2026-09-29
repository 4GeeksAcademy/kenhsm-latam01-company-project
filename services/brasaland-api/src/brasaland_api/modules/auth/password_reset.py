"""Password-reset token persistence and email delivery through Resend."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from html import escape
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tinydb import Query

from brasaland_api.core.config import get_settings
from brasaland_api.core.db import password_reset_tokens_table
from brasaland_api.core.security import create_password_reset_token, decode_password_reset_token, hash_password
from brasaland_api.modules.users import services as user_services

logger = logging.getLogger(__name__)
_consume_lock = Lock()


def _hash_token_id(token_id: str) -> str:
    return hashlib.sha256(token_id.encode("utf-8")).hexdigest()


def create_reset_token(user_id: str) -> tuple[str, datetime]:
    token, token_id, expires_at = create_password_reset_token(user_id)
    table = password_reset_tokens_table()
    now = datetime.now(timezone.utc)
    table.remove(lambda row: datetime.fromisoformat(row["expires_at"]) <= now)
    table.insert(
        {
            "token_id_hash": _hash_token_id(token_id),
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
        }
    )
    return token, expires_at


def consume_reset_token(token: str, new_password: str) -> None:
    payload = decode_password_reset_token(token)
    token_hash = _hash_token_id(payload["jti"])
    table = password_reset_tokens_table()

    with _consume_lock:
        query = Query().token_id_hash == token_hash
        record = table.get(query)
        if record is None or record["user_id"] != payload["sub"]:
            raise ValueError("El enlace de restablecimiento es inválido o ya fue utilizado.")

        if datetime.fromisoformat(record["expires_at"]) <= datetime.now(timezone.utc):
            table.remove(query)
            raise ValueError("El enlace de restablecimiento es inválido o ha expirado.")

        if not user_services.update_password(payload["sub"], hash_password(new_password)):
            table.remove(query)
            raise ValueError("El usuario ya no existe.")
        table.remove(query)


def send_password_reset_email(email: str, reset_url: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY no está configurada.")

    safe_url = escape(reset_url, quote=True)
    payload = {
        "from": settings.resend_from_email,
        "to": [email],
        "subject": "Restablece tu contraseña de Brasaland",
        "text": (
            "Solicitaste restablecer tu contraseña. Abre este enlace en los próximos "
            f"{settings.password_reset_token_expire_minutes} minutos: {reset_url}\n\n"
            "Si no solicitaste este cambio, ignora este correo."
        ),
        "html": (
            '<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px;color:#27272a">'
            '<h1 style="font-size:22px">Restablece tu contraseña</h1>'
            '<p>Recibimos una solicitud para cambiar la contraseña de tu cuenta de Brasaland.</p>'
            f'<p style="margin:28px 0"><a href="{safe_url}" style="background:#92400e;color:#fff;padding:12px 18px;text-decoration:none;border-radius:6px;display:inline-block">Crear nueva contraseña</a></p>'
            f'<p>Este enlace vence en {settings.password_reset_token_expire_minutes} minutos. Si no solicitaste el cambio, puedes ignorar este correo.</p>'
            '<p style="font-size:12px;color:#71717a;word-break:break-all">Si el botón no funciona, abre este enlace:<br>'
            f'<a href="{safe_url}">{safe_url}</a></p></div>'
        ),
    }
    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10):
            pass
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError("No se pudo enviar el correo de restablecimiento.") from error