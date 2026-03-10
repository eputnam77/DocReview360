# Dependency License Report

Generated from installed packages in the development environment.
DocReview360 core is MIT-licensed. Notes on non-MIT dependencies:

## Runtime dependency notes
- **psycopg** (LGPLv3) — optional extra (`[postgres]`); not installed for MIT-clean installs
- **pyphen** (GPLv2+/LGPLv2+/MPL) — transitive via `textstat`; LGPL dynamically linked, not modified
- **cmudict** (GPLv3+) — transitive via `textstat`; used as data resource only
- **semgrep** (LGPLv2) — dev/security tooling only, not a runtime dependency
- **govdocverify / FedStyleValidator** (GPL-3.0) — optional extra (`[fedstylevalidator]`); same author; not installed by default

## SPDX
All source files in `src/docreview360/` carry `# SPDX-License-Identifier: MIT`.

---

| Name                                     | Version     | License                                                                                                                                        |
|------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| protobuf                                 | 4.25.8      | 3-Clause BSD License                                                                                                                           |
| msgpack                                  | 1.1.1       | Apache 2.0                                                                                                                                     |
| cyclonedx-python-lib                     | 9.1.0       | Apache Software License                                                                                                                        |
| googleapis-common-protos                 | 1.70.0      | Apache Software License                                                                                                                        |
| id                                       | 1.6.1       | Apache Software License                                                                                                                        |
| importlib_metadata                       | 7.1.0       | Apache Software License                                                                                                                        |
| importlib_resources                      | 6.5.2       | Apache Software License                                                                                                                        |
| nltk                                     | 3.9.1       | Apache Software License                                                                                                                        |
| opentelemetry-api                        | 1.25.0      | Apache Software License                                                                                                                        |
| opentelemetry-exporter-otlp-proto-common | 1.25.0      | Apache Software License                                                                                                                        |
| opentelemetry-exporter-otlp-proto-http   | 1.25.0      | Apache Software License                                                                                                                        |
| opentelemetry-proto                      | 1.25.0      | Apache Software License                                                                                                                        |
| opentelemetry-sdk                        | 1.25.0      | Apache Software License                                                                                                                        |
| opentelemetry-semantic-conventions       | 0.46b0      | Apache Software License                                                                                                                        |
| pbr                                      | 6.1.1       | Apache Software License                                                                                                                        |
| pip-api                                  | 0.0.34      | Apache Software License                                                                                                                        |
| pip_audit                                | 2.9.0       | Apache Software License                                                                                                                        |
| py-serializable                          | 2.1.0       | Apache Software License                                                                                                                        |
| pytest-playwright                        | 0.7.0       | Apache Software License                                                                                                                        |
| readme_renderer                          | 44.0        | Apache Software License                                                                                                                        |
| requests                                 | 2.32.4      | Apache Software License                                                                                                                        |
| requests-toolbelt                        | 1.0.0       | Apache Software License                                                                                                                        |
| rfc3986                                  | 2.0.0       | Apache Software License                                                                                                                        |
| rsa                                      | 4.9.1       | Apache Software License                                                                                                                        |
| sortedcontainers                         | 2.4.0       | Apache Software License                                                                                                                        |
| stevedore                                | 5.4.1       | Apache Software License                                                                                                                        |
| tenacity                                 | 8.5.0       | Apache Software License                                                                                                                        |
| tzdata                                   | 2025.2      | Apache Software License                                                                                                                        |
| packaging                                | 25.0        | Apache Software License; BSD License                                                                                                           |
| python-dateutil                          | 2.9.0.post0 | Apache Software License; BSD License                                                                                                           |
| sniffio                                  | 1.3.1       | Apache Software License; MIT License                                                                                                           |
| CacheControl                             | 0.14.3      | Apache-2.0                                                                                                                                     |
| bandit                                   | 1.8.6       | Apache-2.0                                                                                                                                     |
| coverage                                 | 7.10.3      | Apache-2.0                                                                                                                                     |
| license-expression                       | 30.4.4      | Apache-2.0                                                                                                                                     |
| opentelemetry-instrumentation            | 0.46b0      | Apache-2.0                                                                                                                                     |
| opentelemetry-instrumentation-requests   | 0.46b0      | Apache-2.0                                                                                                                                     |
| opentelemetry-util-http                  | 0.46b0      | Apache-2.0                                                                                                                                     |
| playwright                               | 1.54.0      | Apache-2.0                                                                                                                                     |
| pytest-asyncio                           | 1.1.0       | Apache-2.0                                                                                                                                     |
| python-multipart                         | 0.0.20      | Apache-2.0                                                                                                                                     |
| twine                                    | 6.2.0       | Apache-2.0                                                                                                                                     |
| prometheus_client                        | 0.22.1      | Apache-2.0 AND BSD-2-Clause                                                                                                                    |
| regex                                    | 2025.7.34   | Apache-2.0 AND CNRI-Python                                                                                                                     |
| cryptography                             | 45.0.6      | Apache-2.0 OR BSD-3-Clause                                                                                                                     |
| text-unidecode                           | 1.3         | Artistic License; GNU General Public License (GPL); GNU General Public License v2 or later (GPLv2+)                                            |
| face                                     | 24.0.0      | BSD                                                                                                                                            |
| Jinja2                                   | 3.1.6       | BSD License                                                                                                                                    |
| MarkupSafe                               | 3.0.2       | BSD License                                                                                                                                    |
| Pygments                                 | 2.19.2      | BSD License                                                                                                                                    |
| amqp                                     | 5.3.1       | BSD License                                                                                                                                    |
| billiard                                 | 4.2.1       | BSD License                                                                                                                                    |
| boltons                                  | 21.0.0      | BSD License                                                                                                                                    |
| celery                                   | 5.5.3       | BSD License                                                                                                                                    |
| click                                    | 8.1.8       | BSD License                                                                                                                                    |
| click-plugins                            | 1.1.1.2     | BSD License                                                                                                                                    |
| colorama                                 | 0.4.6       | BSD License                                                                                                                                    |
| contourpy                                | 1.3.3       | BSD License                                                                                                                                    |
| cycler                                   | 0.12.1      | BSD License                                                                                                                                    |
| glom                                     | 22.1.0      | BSD License                                                                                                                                    |
| idna                                     | 3.10        | BSD License                                                                                                                                    |
| joblib                                   | 1.5.1       | BSD License                                                                                                                                    |
| kiwisolver                               | 1.4.9       | BSD License                                                                                                                                    |
| kombu                                    | 5.5.4       | BSD License                                                                                                                                    |
| lxml                                     | 6.0.0       | BSD License                                                                                                                                    |
| mutmut                                   | 3.3.1       | BSD License                                                                                                                                    |
| nodeenv                                  | 1.9.1       | BSD License                                                                                                                                    |
| numpy                                    | 2.3.2       | BSD License                                                                                                                                    |
| pandas                                   | 2.3.1       | BSD License                                                                                                                                    |
| prompt_toolkit                           | 3.0.51      | BSD License                                                                                                                                    |
| pyasn1                                   | 0.6.1       | BSD License                                                                                                                                    |
| pycparser                                | 2.22        | BSD License                                                                                                                                    |
| python-dotenv                            | 1.0.0       | BSD License                                                                                                                                    |
| reportlab                                | 4.4.3       | BSD License                                                                                                                                    |
| setproctitle                             | 1.3.6       | BSD License                                                                                                                                    |
| vine                                     | 5.1.0       | BSD License                                                                                                                                    |
| wrapt                                    | 1.17.3      | BSD License                                                                                                                                    |
| docutils                                 | 0.22.4      | BSD License; GNU General Public License (GPL); Public Domain                                                                                   |
| boolean.py                               | 5.0         | BSD-2-Clause                                                                                                                                   |
| SecretStorage                            | 3.5.0       | BSD-3-Clause                                                                                                                                   |
| click-option-group                       | 0.5.7       | BSD-3-Clause                                                                                                                                   |
| httpcore                                 | 1.0.9       | BSD-3-Clause                                                                                                                                   |
| httpx                                    | 0.27.2      | BSD-3-Clause                                                                                                                                   |
| starlette                                | 0.47.2      | BSD-3-Clause                                                                                                                                   |
| uvicorn                                  | 0.35.0      | BSD-3-Clause                                                                                                                                   |
| pyphen                                   | 0.17.2      | GNU General Public License v2 or later (GPLv2+); GNU Lesser General Public License v2 or later (LGPLv2+); Mozilla Public License 1.1 (MPL 1.1) |
| docreview360                             | 0.1.2       | GNU General Public License v3 (GPLv3)                                                                                                          |
| cmudict                                  | 1.1.1       | GNU General Public License v3 or later (GPLv3+)                                                                                                |
| semgrep                                  | 1.131.0     | GNU Lesser General Public License v2 (LGPLv2)                                                                                                  |
| psycopg                                  | 3.2.9       | GNU Lesser General Public License v3 (LGPLv3)                                                                                                  |
| psycopg-binary                           | 3.2.9       | GNU Lesser General Public License v3 (LGPLv3)                                                                                                  |
| docreview360                             | 0.1.2       | GPL-3.0-only                                                                                                                                   |
| govdocverify                             | 0.1.0       | GPL-3.0-only                                                                                                                                   |
| SQLAlchemy                               | 2.0.41      | MIT                                                                                                                                            |
| anyio                                    | 4.10.0      | MIT                                                                                                                                            |
| attrs                                    | 25.3.0      | MIT                                                                                                                                            |
| bracex                                   | 2.6         | MIT                                                                                                                                            |
| build                                    | 1.4.0       | MIT                                                                                                                                            |
| charset-normalizer                       | 3.4.3       | MIT                                                                                                                                            |
| click-repl                               | 0.3.0       | MIT                                                                                                                                            |
| ecdsa                                    | 0.19.1      | MIT                                                                                                                                            |
| fonttools                                | 4.58.5      | MIT                                                                                                                                            |
| graphene                                 | 3.4.3       | MIT                                                                                                                                            |
| identify                                 | 2.6.13      | MIT                                                                                                                                            |
| iniconfig                                | 2.1.0       | MIT                                                                                                                                            |
| jaraco.context                           | 6.1.1       | MIT                                                                                                                                            |
| jaraco.functools                         | 4.4.0       | MIT                                                                                                                                            |
| jeepney                                  | 0.9.0       | MIT                                                                                                                                            |
| jsonschema                               | 4.25.0      | MIT                                                                                                                                            |
| jsonschema-specifications                | 2025.4.1    | MIT                                                                                                                                            |
| keyring                                  | 25.7.0      | MIT                                                                                                                                            |
| more-itertools                           | 10.8.0      | MIT                                                                                                                                            |
| mypy_extensions                          | 1.1.0       | MIT                                                                                                                                            |
| nh3                                      | 0.3.3       | MIT                                                                                                                                            |
| pdfkit                                   | 1.0.0       | MIT                                                                                                                                            |
| pip-requirements-parser                  | 32.0.1      | MIT                                                                                                                                            |
| platformdirs                             | 4.3.8       | MIT                                                                                                                                            |
| pre_commit                               | 4.3.0       | MIT                                                                                                                                            |
| pydantic                                 | 2.11.7      | MIT                                                                                                                                            |
| pytest-cov                               | 6.2.1       | MIT                                                                                                                                            |
| redis                                    | 6.2.0       | MIT                                                                                                                                            |
| referencing                              | 0.36.2      | MIT                                                                                                                                            |
| rpds-py                                  | 0.27.0      | MIT                                                                                                                                            |
| soupsieve                                | 2.7         | MIT                                                                                                                                            |
| textstat                                 | 0.7.7       | MIT                                                                                                                                            |
| typing-inspection                        | 0.4.1       | MIT                                                                                                                                            |
| urllib3                                  | 2.5.0       | MIT                                                                                                                                            |
| virtualenv                               | 20.33.1     | MIT                                                                                                                                            |
| wcmatch                                  | 8.5.2       | MIT                                                                                                                                            |
| greenlet                                 | 3.2.4       | MIT AND Python-2.0                                                                                                                             |
| Deprecated                               | 1.2.18      | MIT License                                                                                                                                    |
| PyMySQL                                  | 1.1.1       | MIT License                                                                                                                                    |
| PyYAML                                   | 6.0.2       | MIT License                                                                                                                                    |
| aiosqlite                                | 0.21.0      | MIT License                                                                                                                                    |
| annotated-types                          | 0.7.0       | MIT License                                                                                                                                    |
| beautifulsoup4                           | 4.13.4      | MIT License                                                                                                                                    |
| cffi                                     | 1.17.1      | MIT License                                                                                                                                    |
| cfgv                                     | 3.4.0       | MIT License                                                                                                                                    |
| click-didyoumean                         | 0.3.1       | MIT License                                                                                                                                    |
| exceptiongroup                           | 1.2.2       | MIT License                                                                                                                                    |
| fastapi                                  | 0.116.1     | MIT License                                                                                                                                    |
| filetype                                 | 1.2.0       | MIT License                                                                                                                                    |
| graphql-core                             | 3.2.6       | MIT License                                                                                                                                    |
| graphql-relay                            | 3.2.0       | MIT License                                                                                                                                    |
| h11                                      | 0.16.0      | MIT License                                                                                                                                    |
| jaraco.classes                           | 3.4.0       | MIT License                                                                                                                                    |
| libcst                                   | 1.7.0       | MIT License                                                                                                                                    |
| linkify-it-py                            | 2.0.3       | MIT License                                                                                                                                    |
| markdown-it-py                           | 3.0.0       | MIT License                                                                                                                                    |
| mdit-py-plugins                          | 0.5.0       | MIT License                                                                                                                                    |
| mdurl                                    | 0.1.2       | MIT License                                                                                                                                    |
| mypy                                     | 1.17.1      | MIT License                                                                                                                                    |
| packageurl-python                        | 0.17.5      | MIT License                                                                                                                                    |
| peewee                                   | 3.18.2      | MIT License                                                                                                                                    |
| pluggy                                   | 1.6.0       | MIT License                                                                                                                                    |
| pydantic_core                            | 2.33.2      | MIT License                                                                                                                                    |
| pyee                                     | 13.0.0      | MIT License                                                                                                                                    |
| pyparsing                                | 3.2.3       | MIT License                                                                                                                                    |
| pyproject_hooks                          | 1.2.0       | MIT License                                                                                                                                    |
| pytest                                   | 8.4.1       | MIT License                                                                                                                                    |
| python-docx                              | 1.2.0       | MIT License                                                                                                                                    |
| python-jose                              | 3.5.0       | MIT License                                                                                                                                    |
| python-slugify                           | 8.0.4       | MIT License                                                                                                                                    |
| pytz                                     | 2025.2      | MIT License                                                                                                                                    |
| rich                                     | 13.5.3      | MIT License                                                                                                                                    |
| ruamel.yaml                              | 0.18.14     | MIT License                                                                                                                                    |
| ruamel.yaml.clib                         | 0.2.12      | MIT License                                                                                                                                    |
| ruff                                     | 0.12.8      | MIT License                                                                                                                                    |
| six                                      | 1.17.0      | MIT License                                                                                                                                    |
| textblob                                 | 0.19.0      | MIT License                                                                                                                                    |
| textual                                  | 5.3.0       | MIT License                                                                                                                                    |
| toml                                     | 0.10.2      | MIT License                                                                                                                                    |
| tomli                                    | 2.0.2       | MIT License                                                                                                                                    |
| uc-micro-py                              | 1.0.3       | MIT License                                                                                                                                    |
| wikipedia                                | 1.4.0       | MIT License                                                                                                                                    |
| y-py                                     | 0.6.2       | MIT License                                                                                                                                    |
| ypy-websocket                            | 0.12.4      | MIT License                                                                                                                                    |
| zipp                                     | 3.19.1      | MIT License                                                                                                                                    |
| tqdm                                     | 4.67.1      | MIT License; Mozilla Public License 2.0 (MPL 2.0)                                                                                              |
| pillow                                   | 11.3.0      | MIT-CMU                                                                                                                                        |
| hypothesis                               | 6.137.3     | MPL-2.0                                                                                                                                        |
| pytest-base-url                          | 2.1.0       | MPL-2.0                                                                                                                                        |
| certifi                                  | 2025.8.3    | Mozilla Public License 2.0 (MPL 2.0)                                                                                                           |
| pathspec                                 | 0.12.1      | Mozilla Public License 2.0 (MPL 2.0)                                                                                                           |
| typing_extensions                        | 4.14.1      | PSF-2.0                                                                                                                                        |
| defusedxml                               | 0.7.1       | Python Software Foundation License                                                                                                             |
| distlib                                  | 0.4.0       | Python Software Foundation License                                                                                                             |
| matplotlib                               | 3.10.3      | Python Software Foundation License                                                                                                             |
| filelock                                 | 3.18.0      | Unlicense                                                                                                                                      |
