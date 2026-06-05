import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from infra.telemetry import get_logger

from tools.base import Permission, Tool

logger = get_logger("tools.web")

MAX_RESPONSE_SIZE = 5 * 1024 * 1024
MAX_REQUEST_SIZE = 1024 * 1024


class WebTool(Tool):
    name = "web"
    permission = Permission.READ

    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout

    async def _run(
        self,
        *,
        method: str = "GET",
        url: str,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        self._check_url(url)
        if body is not None and len(body) > MAX_REQUEST_SIZE:
            raise ValueError(
                f"Request body exceeds {MAX_REQUEST_SIZE} byte limit"
            )
        logger.info("%s %s", method, url)

        async with httpx.AsyncClient(
            timeout=self._timeout, follow_redirects=False
        ) as client:
            resp = await client.request(
                method,
                url,
                content=body,
                headers=headers,
            )

        resp_body = resp.text[:MAX_RESPONSE_SIZE]
        return (
            f"status: {resp.status_code}\n"
            f"headers: {dict(resp.headers)}\n"
            f"body:\n{resp_body}"
        )

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Blocked scheme: {parsed.scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("No hostname in URL")

        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failed for {hostname}") from e

        for info in infos:
            ip_str = info[4][0]
            if self._is_private_ip(ip_str):
                raise ValueError(f"Blocked private/internal IP: {ip_str}")

    @staticmethod
    def _is_private_ip(ip: str) -> bool:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        )
