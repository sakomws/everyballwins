# everyballwins — You.com API service

A small, dependency-free Python service and typed client for the
[You.com](https://you.com) platform APIs (`https://api.you.com`).

## Features

* Typed client (`YouClient`) covering the You.com API surface:
  * Web search — `GET /v1/search`
  * News search — `GET /v1/news` (automatic fallback to the legacy `/v1/news-search`)
  * Content snippets — `GET /v1/content-snippets`
  * Research — `POST /v1/research`
  * Agents — `POST /v1/agents/runs`
* Small REST service (`you-api`) that proxies the endpoints above over HTTP
  with JSON error mapping.
* Structured exceptions for 401/403/404/429/5xx responses.
* Zero third-party dependencies — standard library only (Python ≥ 3.10).
* Pluggable HTTP transport for testing or for wiring in `requests`/`httpx`.

## Getting an API key

Create a key at [api.you.com](https://api.you.com) and export it:

```bash
export YOU_API_KEY="ydc-sk-..."
```

## Running the service

```bash
PYTHONPATH=src python3 -m you_api --host 127.0.0.1 --port 8000
```

or with the environment override for the upstream base URL:

```bash
YOU_API_BASE_URL=https://api.you.com PYTHONPATH=src python3 -m you_api.service
```

### Service endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET  | `/health` | Liveness probe |
| GET  | `/v1/search?q=...&count=&offset=&country=&language=&safesearch=&freshness=&include_domains=&exclude_domains=&livecrawl=` | Web search |
| GET  | `/v1/news?q=...` | News search |
| GET  | `/v1/snippets?urls=https://a.com,https://b.com` | Extracted snippets for up to 10 URLs |
| POST | `/v1/research` | Body: `{"question": "...", "instructions": "...", "model": "...", "stream": false}` |
| POST | `/v1/agents/runs` | Body: `{"agent": "...", "input": ..., "stream": false}` |

### Examples

```bash
curl "http://127.0.0.1:8000/v1/search?q=python%20news&count=3"

curl -X POST http://127.0.0.1:8000/v1/research \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is new in Python 3.14?"}'
```

## Using the client directly

```python
from you_api import YouClient

client = YouClient()  # reads YOU_API_KEY from the environment

results = client.search("python news", count=5, country="US")
news = client.news("artificial intelligence")
snippets = client.content_snippets(["https://docs.python.org"])
answer = client.research("Summarise the latest Python release")
```

### Error handling

```python
from you_api import YouClient, YouRateLimitError, YouAPIError

try:
    client = YouClient(api_key="...")
    client.search("hello")
except YouRateLimitError as exc:
    print("rate limited:", exc.status_code)
except YouAPIError as exc:
    print("request failed:", exc)
```

## Running the tests

The sandbox has no pip/pytest, so the suite uses `unittest` with a small
runner that puts `src/` on the path:

```bash
python3 run_tests.py
```

## Project layout

```
src/you_api/
├── __init__.py      # public API re-exports
├── __main__.py      # `python -m you_api` entry point
├── client.py        # YouClient — typed client for api.you.com
├── exceptions.py    # error hierarchy
├── http.py          # stdlib transport + Transport protocol
└── service.py       # REST service exposing the client over HTTP
tests/
├── test_client.py   # client unit tests (stub transport)
└── test_service.py  # service + live HTTP handler tests
run_tests.py         # dependency-free test runner
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
