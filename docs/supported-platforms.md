# Supported Platforms

This document defines the officially supported and tested platforms for DocReview360 v0.1.x.

## Backend (Python / FastAPI)

| Platform            | Status        | Notes                                                       |
|---------------------|---------------|-------------------------------------------------------------|
| Linux (x86-64)      | **Supported** | Primary CI target; Debian/Ubuntu/RHEL/Raspberry Pi OS       |
| Raspberry Pi OS     | **Supported** | ARM64; tested with `headless-loop.sh` automation runner     |
| macOS (x86-64/ARM)  | **Supported** | Developer workstation; M1/M2/M3 (arm64) via Rosetta or native |
| Windows 10/11       | **Supported** | PowerShell + CMD; `uv venv` + `pip install` verified        |
| Docker (any OS)     | **Supported** | Multi-stage image; non-root user; see `Dockerfile`          |

### Python Version

| Python Version | Status        |
|----------------|---------------|
| 3.12           | **Recommended** — fully tested, primary target |
| 3.11           | Supported — tested in CI                       |
| 3.13           | **Not supported** — PyTorch wheels not yet available |

## Frontend (Next.js / React)

| Platform         | Status        | Notes                                   |
|------------------|---------------|-----------------------------------------|
| Linux (x86-64)   | **Supported** | Primary CI target                       |
| macOS            | **Supported** | Developer workstation                   |
| Windows 10/11    | **Supported** | PowerShell; `npm run dev` verified      |

### Node.js Version

| Node.js Version | Status            |
|-----------------|-------------------|
| 20.x (LTS)      | **Recommended**   |
| >=22.12.0        | **Supported**     | Matches `vite@7.x` engine requirement |
| 20.19.x+ (LTS)  | **Supported**     | Minimum Node 20 release accepted by Vite |
| < 20.19.0       | **Not supported** | Frontend test/build toolchain will fail |

## Database

| Database        | Status           | Notes                                        |
|-----------------|------------------|----------------------------------------------|
| SQLite          | **Supported**    | Default; zero-config for development         |
| PostgreSQL 14+  | Supported        | Requires `[postgres]` optional extra         |
| MySQL / MariaDB | Experimental     | SQLAlchemy driver required; not CI-tested    |
| MSSQL / Oracle  | Experimental     | Requires `[mssql]`/`[oracle]` optional extra |

## Container / Orchestration

| Platform         | Status        | Notes                                          |
|------------------|---------------|------------------------------------------------|
| Docker Engine 24+ | **Supported** | `docker-compose.yml` and `docker-compose.prod.yml` |
| Kubernetes 1.28+ | Supported     | Helm chart in `helm/docreview360/`; manifests in `k8s/` |
| Podman 4+        | Untested      | May work; OCI-compliant image                  |

## Out-of-scope Platforms

The following are explicitly **not supported** for v0.1.x:

- Python 3.13+ (blocked on PyTorch/ONNX wheel availability)
- Node.js < 20.19.0
- 32-bit operating systems
- Windows Subsystem for Linux v1 (WSL1) — WSL2 works fine
- Alpine Linux with `musl` libc (ML/ONNX extensions require glibc)

## Raspberry Pi Headless Operation

DocReview360 is tested on Raspberry Pi 4 (ARM64, Raspberry Pi OS Bookworm) for:

- Backend API (`uvicorn --host 0.0.0.0 --port 8000`)
- Headless automation runner (`scripts/headless-loop.sh`)
- SQLite persistence (in-process, no external DB required)

Frontend must be served from a separate machine or built as static assets
(`npm run build && npm run export`) due to RAM constraints.

## CI Matrix

GitHub Actions runs tests on:

| Job        | OS             | Python | Node   |
|------------|----------------|--------|--------|
| `test`     | ubuntu-latest  | 3.12   | —      |
| `lint`     | ubuntu-latest  | 3.12   | —      |
| `frontend` | ubuntu-latest  | —      | 20.x   |

See `.github/workflows/ci.yml` for the authoritative definition.
