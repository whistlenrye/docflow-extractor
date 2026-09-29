"""Block /fill from navigating the server browser at internal addresses."""
from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

_BLOCKED_HOSTS = {"metadata.google.internal", "metadata.internal"}


def assert_safe_target(url: str) -> str:
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not host:
        raise HTTPException(400, "target_url must be an absolute http(s) URL")
    if host in _BLOCKED_HOSTS:
        raise HTTPException(400, "target_url is not allowed")

    allow_local = os.getenv("ALLOW_LOCAL_FORM_TARGETS", "1") == "1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port)
    except socket.gaierror as exc:
        raise HTTPException(400, "target_url host did not resolve") from exc

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError as exc:
            raise HTTPException(400, "target_url host did not resolve") from exc
        if ip.is_loopback or ip.is_unspecified:
            if not allow_local:
                raise HTTPException(400, "local targets are disabled")
            continue
        if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(400, "target_url points at a non-public address")
    return url
