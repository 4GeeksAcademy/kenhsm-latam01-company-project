from __future__ import annotations

import os
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from brasaland_api.core import config, db
from brasaland_api.core.db import password_reset_tokens_table
from brasaland_api.core.security import create_password_reset_token, verify_password
from brasaland_api.modules.auth import router
from brasaland_api.modules.auth.password_reset import _hash_token_id, create_reset_token
from brasaland_api.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from brasaland_api.modules.users import services as user_services


class PasswordResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.environment = patch.dict(
            os.environ,
            {
                "TINYDB_PATH": os.path.join(self.temp_dir.name, "db.json"),
                "SECRET_KEY": "test-secret-key",
                "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES": "30",
            },
        )
        self.environment.start()
        config.get_settings.cache_clear()
        db.get_db.cache_clear()
        self.user = user_services.create_user("user@example.com", "old-password")

    def tearDown(self) -> None:
        db.get_db().close()
        db.get_db.cache_clear()
        config.get_settings.cache_clear()
        self.environment.stop()
        self.temp_dir.cleanup()

    def test_forgot_password_uses_generic_confirmation_for_known_and_unknown_email(self) -> None:
        with patch.object(router, "send_password_reset_email") as send_email:
            known = router.forgot_password(ForgotPasswordRequest(email="user@example.com"))
            unknown = router.forgot_password(ForgotPasswordRequest(email="unknown@example.com"))

        self.assertEqual(known.message, unknown.message)
        self.assertEqual(send_email.call_count, 1)

    def test_forgot_password_keeps_generic_response_when_email_delivery_fails(self) -> None:
        with patch.object(router, "send_password_reset_email", side_effect=RuntimeError("provider unavailable")):
            with self.assertLogs(router.logger, level="ERROR"):
                response = router.forgot_password(ForgotPasswordRequest(email="user@example.com"))

        self.assertEqual(response.message, "Si esa dirección está registrada, recibirás un enlace en breve.")

    def test_reset_token_lifetime_is_limited_to_fifteen_through_sixty_minutes(self) -> None:
        for lifetime in (14, 61):
            with self.subTest(lifetime=lifetime), self.assertRaises(ValidationError):
                config.Settings(password_reset_token_expire_minutes=lifetime)

    def test_reset_changes_password_and_token_cannot_be_reused(self) -> None:
        token, _ = create_reset_token(self.user.id)

        router.reset_password(ResetPasswordRequest(token=token, new_password="new-password"))
        updated_user = user_services.get_user_by_id(self.user.id)
        self.assertIsNotNone(updated_user)
        self.assertTrue(verify_password("new-password", updated_user.hashed_password))

        with self.assertRaises(HTTPException) as error:
            router.reset_password(ResetPasswordRequest(token=token, new_password="another-password"))
        self.assertEqual(error.exception.status_code, 400)

    def test_expired_reset_token_is_rejected(self) -> None:
        token, token_id, expires_at = create_password_reset_token(self.user.id, expires_minutes=-1)
        password_reset_tokens_table().insert(
            {
                "token_id_hash": _hash_token_id(token_id),
                "user_id": self.user.id,
                "expires_at": expires_at.isoformat(),
            }
        )

        with self.assertRaises(HTTPException) as error:
            router.reset_password(ResetPasswordRequest(token=token, new_password="new-password"))
        self.assertEqual(error.exception.status_code, 400)

    def test_change_password_requires_correct_current_password(self) -> None:
        with self.assertRaises(HTTPException) as error:
            router.change_password(
                ChangePasswordRequest(current_password="incorrect", new_password="new-password"),
                self.user,
            )
        self.assertEqual(error.exception.status_code, 400)

        router.change_password(
            ChangePasswordRequest(current_password="old-password", new_password="new-password"),
            self.user,
        )
        updated_user = user_services.get_user_by_id(self.user.id)
        self.assertIsNotNone(updated_user)
        self.assertTrue(verify_password("new-password", updated_user.hashed_password))


if __name__ == "__main__":
    unittest.main()