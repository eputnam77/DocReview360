# SPDX-License-Identifier: MIT
"""URL validation helpers for outbound callbacks."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


def validate_public_https_url(url: str) -> None:
    """Raise ``ValueError`` unless ``url`` is a public HTTPS URL."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("webhook_url must be a public https:// URL")
    if parsed.username or parsed.password:
        raise ValueError("webhook_url must not contain credentials")
    hostname = parsed.hostname.strip().lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise ValueError("webhook_url must not target a local host")
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise ValueError("webhook_url must not target a private network")
