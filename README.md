# everyballwins

A simple REST API service built with [FastAPI](https://fastapi.tiangolo.com/).
It provides a small in-memory item store with CRUD endpoints, plus root and
health-check routes.

## Requirements

- Python 3.11+
- Dependencies: see `requirements.txt`

```bash
pip install -r requirements.txt
```

## Run the service

```bash
uvicorn app.main:app --reload
```

The API is then available at <http://127.0.0.1:8000>, with interactive
OpenAPI docs at <http://127.0.0.1:8000/docs>.

## Endpoints

| Method   | Path            | Description                                  |
|----------|-----------------|----------------------------------------------|
| `GET`    | `/`             | Service info                                 |
| `GET`    | `/health`       | Health check                                 |
| `GET`    | `/items`        | List items (`q`, `limit`, `offset` filters)  |
| `POST`   | `/items`        | Create an item                               |
| `GET`    | `/items/{id}`   | Get an item by id                            |
| `PUT`    | `/items/{id}`   | Partially update an item                     |
| `DELETE` | `/items/{id}`   | Delete an item                               |

### Example

```bash
# Create an item
curl -X POST http://127.0.0.1:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Basketball", "price": 19.99, "tags": ["sports"]}'

# List items, filtered by name
curl "http://127.0.0.1:8000/items?q=ball"
```

Note: items are stored in memory, so they are lost when the server restarts.

## Tests

```bash
# Unit tests (stdlib unittest, no pytest required)
python3 -m unittest discover -s tests -v

# Smoke test: boots the real uvicorn server and exercises it over HTTP
python3 tests/smoke_server.py
```
