"""
Apple Push Notification Service (APNs) client.
Uses HTTP/2 to send push notifications to iOS devices.
"""
import asyncio
import base64
import time
import logging
from typing import Optional

import httpx
import jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds
RETRY_BACKOFF_MAX = 10  # seconds


class APNsService:
    """Service for sending push notifications via Apple Push Notification service."""

    def __init__(self):
        self.settings = get_settings()
        self._private_key: Optional[bytes] = None
        self._token_expires_at: float = 0
        self._cached_token: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        """Check if APNs is properly configured."""
        return bool(
            self.settings.apns_key_id
            and self.settings.apns_team_id
            and self.settings.apns_key_base64
        )

    def _load_private_key(self) -> bytes:
        """Load the private key from base64 encoded string."""
        if self._private_key is None:
            if not self.settings.apns_key_base64:
                raise ValueError("APNs key not configured")
            self._private_key = base64.b64decode(self.settings.apns_key_base64)
        return self._private_key

    def _generate_token(self) -> str:
        """Generate a JWT token for APNs authentication.

        Tokens are valid for 1 hour, so we cache them.
        """
        now = time.time()

        # Return cached token if still valid (with 5 min buffer)
        if self._cached_token and self._token_expires_at > now + 300:
            return self._cached_token

        private_key = self._load_private_key()

        headers = {
            "alg": "ES256",
            "kid": self.settings.apns_key_id,
        }
        payload = {
            "iss": self.settings.apns_team_id,
            "iat": int(now),
        }

        self._cached_token = jwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers=headers,
        )
        self._token_expires_at = now + 3600  # Token valid for 1 hour

        return self._cached_token

    def _get_apns_url(self, device_token: str) -> str:
        """Get the APNs URL for the given device token."""
        host = (
            "api.sandbox.push.apple.com"
            if self.settings.apns_use_sandbox
            else "api.push.apple.com"
        )
        return f"https://{host}/3/device/{device_token}"

    async def send_notification(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
        badge: Optional[int] = None,
    ) -> bool:
        """Send a push notification to a device with retry logic.

        Args:
            device_token: The APNs device token
            title: Notification title
            body: Notification body text
            data: Optional custom data payload
            badge: Optional badge number to display

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("APNs not configured, skipping notification")
            return False

        url = self._get_apns_url(device_token)

        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body,
                },
                "sound": "default",
            }
        }

        if badge is not None:
            payload["aps"]["badge"] = badge

        if data:
            payload["data"] = data

        headers = {
            "authorization": f"bearer {self._generate_token()}",
            "apns-topic": self.settings.apns_bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }

        # Retry with exponential backoff for transient errors
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
                    response = await client.post(url, json=payload, headers=headers)

                    if response.status_code == 200:
                        logger.info(f"Notification sent successfully to {device_token[:20]}...")
                        return True
                    elif response.status_code == 410:
                        # Device token is no longer valid - don't retry
                        logger.warning(f"Device token expired: {device_token[:20]}...")
                        return False
                    elif response.status_code >= 500:
                        # Server error - retry
                        last_error = f"APNs server error {response.status_code}"
                        logger.warning(f"{last_error}, attempt {attempt + 1}/{MAX_RETRIES}")
                    else:
                        # Client error - don't retry
                        logger.error(f"APNs error {response.status_code}: {response.text}")
                        return False

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # Network error - retry
                last_error = str(e)
                logger.warning(f"APNs network error: {e}, attempt {attempt + 1}/{MAX_RETRIES}")
            except Exception as e:
                # Unknown error - don't retry
                logger.error(f"Failed to send notification: {e}")
                return False

            # Exponential backoff before retry
            if attempt < MAX_RETRIES - 1:
                delay = min(RETRY_BACKOFF_BASE * (2 ** attempt), RETRY_BACKOFF_MAX)
                await asyncio.sleep(delay)

        logger.error(f"Failed to send notification after {MAX_RETRIES} attempts: {last_error}")
        return False

    async def send_to_multiple(
        self,
        device_tokens: list[str],
        title: str,
        body: str,
        data: Optional[dict] = None,
    ) -> int:
        """Send notification to multiple devices.

        Args:
            device_tokens: List of APNs device tokens
            title: Notification title
            body: Notification body text
            data: Optional custom data payload

        Returns:
            Number of notifications sent successfully
        """
        success_count = 0
        expired_tokens: list[str] = []

        for token in device_tokens:
            result = await self._send_notification_with_expiry_check(token, title, body, data)
            if result == "success":
                success_count += 1
            elif result == "expired":
                expired_tokens.append(token)

        # Mark expired tokens as inactive in the database
        if expired_tokens:
            await self._mark_tokens_inactive(expired_tokens)

        return success_count

    async def _send_notification_with_expiry_check(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
    ) -> str:
        """Send notification with retry and return status: 'success', 'expired', or 'failed'."""
        if not self.is_configured:
            logger.warning("APNs not configured, skipping notification")
            return "failed"

        url = self._get_apns_url(device_token)

        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body,
                },
                "sound": "default",
            }
        }

        if data:
            payload["data"] = data

        headers = {
            "authorization": f"bearer {self._generate_token()}",
            "apns-topic": self.settings.apns_bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }

        # Retry with exponential backoff for transient errors
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
                    response = await client.post(url, json=payload, headers=headers)

                    if response.status_code == 200:
                        return "success"
                    elif response.status_code == 410:
                        # Device token is no longer valid - don't retry
                        logger.warning(f"Device token expired: {device_token[:20]}...")
                        return "expired"
                    elif response.status_code >= 500:
                        # Server error - retry
                        last_error = f"APNs server error {response.status_code}"
                        logger.warning(f"{last_error}, attempt {attempt + 1}/{MAX_RETRIES}")
                    else:
                        # Client error - don't retry
                        logger.error(f"APNs error {response.status_code}: {response.text}")
                        return "failed"

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # Network error - retry
                last_error = str(e)
                logger.warning(f"APNs network error: {e}, attempt {attempt + 1}/{MAX_RETRIES}")
            except Exception as e:
                # Unknown error - don't retry
                logger.error(f"Failed to send notification: {e}")
                return "failed"

            # Exponential backoff before retry
            if attempt < MAX_RETRIES - 1:
                delay = min(RETRY_BACKOFF_BASE * (2 ** attempt), RETRY_BACKOFF_MAX)
                await asyncio.sleep(delay)

        logger.error(f"Failed to send notification after {MAX_RETRIES} attempts: {last_error}")
        return "failed"

    async def _mark_tokens_inactive(self, tokens: list[str]) -> None:
        """Mark expired device tokens as inactive in the database."""
        from sqlalchemy import update
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from app.models.notification import UserDeviceToken
        from app.core.config import get_settings

        try:
            settings = get_settings()
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with session_factory() as db:
                stmt = (
                    update(UserDeviceToken)
                    .where(UserDeviceToken.device_token.in_(tokens))
                    .values(is_active=False)
                )
                await db.execute(stmt)
                await db.commit()
                logger.info(f"Marked {len(tokens)} expired device tokens as inactive")

            await engine.dispose()
        except Exception as e:
            logger.error(f"Failed to mark tokens as inactive: {e}")


# Singleton instance
apns_service = APNsService()
