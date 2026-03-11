# WebSocket Proxy Guide

DocReview360's collaborative editing, real-time notifications, and comment
streams all use WebSocket connections.  This guide covers how to configure
common reverse proxies to correctly forward WebSocket traffic.

---

## Connection architecture

```
Browser  ──WS──▶  Reverse proxy  ──WS──▶  uvicorn (port 8000)
                     (nginx / Caddy / ALB)
```

WebSocket endpoints served by DocReview360:

| Path prefix          | Purpose                            |
|----------------------|------------------------------------|
| `/ws/collab/{id}`    | Collaborative document editing     |
| `/ws/notifications`  | Server-sent event stream (SSE fallback) |
| `/ws/comments/{id}`  | Live comment feed                  |

---

## nginx

Add the following to your `server` block (see also `nginx/nginx.conf`):

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl http2;
    server_name docs.example.com;

    # ... TLS configuration ...

    location /ws/ {
        proxy_pass         http://docreview360:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_set_header   Host       $host;
        proxy_set_header   X-Real-IP  $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location / {
        proxy_pass http://docreview360:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Key parameters:**

| Parameter               | Why it matters                                     |
|-------------------------|----------------------------------------------------|
| `proxy_http_version 1.1`| HTTP/1.1 is required for WebSocket upgrades        |
| `Upgrade` header        | Signals the WebSocket handshake                    |
| `Connection` header     | Must be `upgrade` (not `close`)                    |
| `proxy_read_timeout`    | Must be large (≥ 3600s) to prevent idle drops      |

---

## Caddy

```caddy
docs.example.com {
    reverse_proxy /ws/* docreview360:8000 {
        header_up Connection {http.request.header.Connection}
        header_up Upgrade   {http.request.header.Upgrade}
        transport http {
            read_timeout  1h
            write_timeout 1h
        }
    }

    reverse_proxy * docreview360:8000
}
```

---

## AWS Application Load Balancer (ALB)

ALB supports WebSocket natively when the following conditions are met:

1. **Target protocol**: HTTP (not HTTPS — TLS terminates at the ALB).
2. **Idle timeout**: Set the ALB idle timeout to `3600` seconds
   (`aws elbv2 modify-load-balancer-attributes --attributes Key=idle_timeout.timeout_seconds,Value=3600`).
3. **Sticky sessions**: Enable for the target group to pin each browser
   session to a single backend instance when running multiple replicas.

No special listener rules are required for WebSocket — ALB automatically
handles the `Upgrade` header.

---

## Kubernetes Ingress (nginx-ingress)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: docreview360
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
spec:
  rules:
    - host: docs.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: docreview360
                port:
                  number: 8000
```

---

## Fallback behaviour

When WebSocket is unavailable (firewalls, certain corporate proxies), the
frontend falls back automatically:

- **Collaborative editing**: Periodic polling every 5 seconds via `GET /documents/{id}`.
- **Notifications**: Long-polling via `GET /notifications/poll?since=<ts>`.
- **Live comments**: Polling via `GET /comments/{project_id}?after=<ts>`.

Fallback mode is activated when the WebSocket `close` event fires with code
`1006` (abnormal closure) or the initial handshake times out after 10 s.
Set `NEXT_PUBLIC_DISABLE_WS=true` to force fallback mode in environments
where WebSocket traffic is known to be blocked.

---

## Testing WebSocket connectivity

```bash
# Requires wscat: npm install -g wscat
wscat -c "wss://docs.example.com/ws/notifications" \
      -H "Authorization: Bearer <token>"
```

Expected: connection opens, server sends a `{"type":"connected"}` frame.
