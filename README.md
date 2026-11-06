# everyballwins

A Python [FastAPI](https://fastapi.tiangolo.com/) service where every ball wins a prize.

## Features

- FastAPI application with automatic OpenAPI docs (`/docs`, `/redoc`)
- CRUD API for prize balls under `/api/v1/balls`
- Health check at `/health`
- In-memory, thread-safe repository (easy to swap for a real database)
- Full test suite with pytest

## Project layout

```
app/
├── __init__.py
├── main.py          # App factory + entrypoint
├── models.py        # Pydantic models
├── storage.py       # In-memory repository
└── routes/
    └── balls.py     # /api/v1/balls endpoints
tests/
├── conftest.py
├── test_main.py
└── test_balls.py
```

## Getting started

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run the development server
uvicorn app.main:app --reload
```

Then open:

- API: http://localhost:8000
- Interactive docs (Swagger UI): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API overview

| Method | Path               | Description            |
| ------ | ------------------ | ---------------------- |
| GET    | `/`                | Welcome message        |
| GET    | `/health`          | Health check           |
| GET    | `/api/v1/balls`    | List balls (filterable by `color`) |
| POST   | `/api/v1/balls`    | Create a ball          |
| GET    | `/api/v1/balls/{id}` | Get a ball           |
| PATCH  | `/api/v1/balls/{id}` | Update a ball        |
| DELETE | `/api/v1/balls/{id}` | Delete a ball        |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/balls \
  -H "Content-Type: application/json" \
  -d '{"name": "Lucky 7", "color": "gold", "prize": "Jackpot"}'
```

## Running tests

```bash
python -m pytest
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
