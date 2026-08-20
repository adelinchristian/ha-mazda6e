"""Client for the Mazda 6e Changan cloud gateway."""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://cma-m.iov.changanauto.com.de/cma-app-gw"
PUB_KEY = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCRYk7lZkHwHCJo8sSoKs5UuD/Jh9j7Pv5Lnoc6wNpVcvGj1LG+a6Kyn+OoRSa0NP24MWoLd0WE+zRYJH2RFNdiXHDdHqZYcxtTsvwyMaBjI6jsizdXrbFc3oBZY4LMfr7nV66/nQB1TP7UO7fYMti3/wfHfbFG0BCgCgWeuGeRXQIDAQAB"
DEVICE_NAME = "iPhone 17 Pro Max"
HEADERS_BASE = {
    "content-type": "application/json",
    "devicetype": "iPhone",
    "apptype": "IOS",
    "appid": "cma",
    "accept": "*/*",
    "appversion": "V1.2.2",
    "accept-language": "en-US;q=1.0",
    "user-agent": "overseas/1.2.2 (com.mazda.mazda6e; build:6; iPhone 17 Pro Max; iOS 26.6) Alamofire/5.5.0",
    "language": "en_US",
}
TOKEN_EXPIRED_CODE = "APP_1_1_02_004"


class MazdaApiError(Exception):
    """Base Mazda cloud API error."""


class MazdaAuthError(MazdaApiError):
    """Mazda cloud credentials are invalid or expired."""


@dataclass(slots=True)
class MazdaTokens:
    """Token bundle returned by the Mazda login flow."""

    access_token: str
    refresh_token: str


class Mazda6eClient:
    """Mazda 6e API client for telemetry and device-login authentication."""

    commands_enabled = False

    def __init__(self, session: ClientSession, *, access_token: str, refresh_token: str, device_id: str) -> None:
        self._session = session
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.device_id = device_id

    @staticmethod
    def _now() -> str:
        return str(int(time.time()))

    def _headers(self, *, authenticated: bool = True) -> dict[str, str]:
        headers = {**HEADERS_BASE, "deviceid": self.device_id}
        if authenticated and self.access_token:
            headers["authorization"] = self.access_token
        return headers

    @staticmethod
    def encrypt_request_value(value: str) -> str:
        """Encrypt a Mazda login value with the app's embedded RSA key."""
        public_key = serialization.load_der_public_key(base64.b64decode(PUB_KEY))
        ciphertext = public_key.encrypt(value.encode(), padding.PKCS1v15())
        return base64.b64encode(ciphertext).decode()

    async def _post(self, path: str, body: dict[str, Any], *, retry: bool = True) -> dict[str, Any]:
        try:
            async with self._session.post(f"{BASE_URL}{path}", headers=self._headers(), json=body) as response:
                payload = await response.json(content_type=None)
        except (ClientError, ValueError) as err:
            raise MazdaApiError(f"Mazda cloud request failed: {err}") from err

        if payload.get("success") is True:
            return payload
        if payload.get("code") == TOKEN_EXPIRED_CODE:
            if not retry:
                raise MazdaAuthError("Mazda access token expired after refresh")
            await self.refresh_tokens()
            return await self._post(path, body, retry=False)
        message = payload.get("message") or payload.get("msg") or payload.get("code") or "unknown error"
        raise MazdaApiError(f"Mazda cloud request failed: {message}")

    async def login_email_password(self, *, email: str, password: str) -> MazdaTokens:
        """Log in with plain credentials encrypted as expected by the Mazda app."""
        body = {
            "loginTime": self._now(),
            "email": self.encrypt_request_value(email),
            "password": self.encrypt_request_value(password),
            "pubKey": PUB_KEY,
        }
        response = await self._post("/cma-app-auth/api/login/email-pass-in/v2", body, retry=False)
        data = response.get("data") or {}
        token = data.get("token")
        refresh_token = data.get("refreshToken")
        if not isinstance(token, str) or not isinstance(refresh_token, str):
            raise MazdaAuthError("Mazda login did not return usable tokens")
        self.access_token = token
        self.refresh_token = refresh_token
        return MazdaTokens(token, refresh_token)

    async def send_device_login(self, *, email: str) -> None:
        await self._post(
            "/cma-app-user/api/send-email/device-login/send",
            {"email": email, "deviceName": DEVICE_NAME, "loginTime": self._now(), "type": "1"},
        )

    async def verify_device_code(self, *, email: str, code: str) -> None:
        await self._post(
            "/cma-app-user/api/login-device/email-verify",
            {
                "authCode": code,
                "email": email,
                "deviceName": DEVICE_NAME,
                "lastLoginTime": self._now(),
                "type": "3",
                "deviceModel": DEVICE_NAME,
            },
        )

    async def refresh_tokens(self) -> MazdaTokens:
        response = await self._post(
            "/cma-app-auth/api/auth/refresh-token",
            {"refreshToken": self.refresh_token},
            retry=False,
        )
        data = response.get("data") or {}
        token = data.get("token")
        refresh_token = data.get("refreshToken")
        if not isinstance(token, str) or not isinstance(refresh_token, str):
            raise MazdaAuthError("Mazda token refresh failed")
        self.access_token = token
        self.refresh_token = refresh_token
        return MazdaTokens(token, refresh_token)

    async def vehicles(self) -> list[dict[str, Any]]:
        try:
            response = await self._post("/cma-app-user/api/vehicle/vehicles", {})
        except MazdaApiError:
            response = await self._post("/cma-app-user/api/car/vehicles", {})
        vehicles = response.get("data") or []
        if not isinstance(vehicles, list):
            raise MazdaApiError("Mazda vehicle response was not a list")
        return [{**vehicle, "carId": vehicle.get("carId") or vehicle.get("vehicleId")} for vehicle in vehicles]

    async def condition(self, vehicle_id: str) -> dict[str, Any]:
        response = await self._post(
            "/cma-app-car-condition/api/vehicle/condition/v2",
            {
                "vechileCriteria": {
                    "seat": "1", "tire": "1", "charge": "1", "vehicleStatus": "1", "hvac": "1",
                    "departurePlan": "0", "fuel": "0", "window": "1", "door": "1", "airConditionPlan": "0",
                    "lamp": "1", "warmCoolingBox": "0", "welcome": "0", "location": "1",
                },
                "vehicleId": int(vehicle_id),
            },
        )
        data = response.get("data")
        if not isinstance(data, dict):
            raise MazdaApiError("Mazda condition response was not an object")
        return data