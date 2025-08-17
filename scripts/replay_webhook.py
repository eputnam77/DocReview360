#!/usr/bin/env python3
"""Replay a webhook payload multiple times to test idempotency."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import time
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay webhook callbacks")
    parser.add_argument("payload", type=Path, help="Path to JSON payload")
    parser.add_argument("--url", default="http://localhost:8000/hooks", help="Webhook endpoint")
    parser.add_argument("--provider", required=True, help="Provider name")
    parser.add_argument("--secret", required=True, help="HMAC secret for the provider")
    parser.add_argument("-n", "--count", type=int, default=2, help="Number of times to replay")
    args = parser.parse_args()

    data = json.loads(args.payload.read_text())
    body = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(args.secret.encode(), body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Provider": args.provider,
        "X-Signature": signature,
    }
    for i in range(args.count):
        resp = requests.post(args.url, data=body, headers=headers, timeout=5)
        print(f"Replay {i + 1}: {resp.status_code}")
        time.sleep(0.1)


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
