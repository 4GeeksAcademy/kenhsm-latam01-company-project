"""Build PostgREST authentication headers for supported Supabase key types."""

from brasaland_api.core.config import Settings


def supabase_auth_headers(settings: Settings) -> dict[str, str] | None:
    if settings.supabase_secret_key is not None:
        secret_key = settings.supabase_secret_key.get_secret_value()
        if secret_key:
            return {"apikey": secret_key}

    if settings.supabase_service_role_key is not None:
        service_role_key = settings.supabase_service_role_key.get_secret_value()
        if service_role_key:
            return {
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
            }

    return None