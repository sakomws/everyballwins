# everyballwins

A simple Python JSON API built only on the standard library — no dependencies required.

## Run

```bash
python3 api.py                 # serves on http://127.0.0.1:8000
python3 api.py --port 9000     # custom port
```

## Endpoints

| Method | Path              | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | `/`               | Service info                         |
| GET    | `/health`         | Health check                         |
| GET    | `/api/items`      | List all items                       |
| GET    | `/api/items/{id}` | Get a single item                    |
| POST   | `/api/items`      | Create an item: `{"name": "..."}`    |
| DELETE | `/api/items/{id}` | Delete an item                       |

## Example

```bash
curl -s -X POST http://127.0.0.1:8000/api/items \
  -H 'Content-Type: application/json' \
  -d '{"name": "ball"}'
# {"id": 1, "name": "ball"}

curl -s http://127.0.0.1:8000/api/items
# {"items": [{"id": 1, "name": "ball"}]}
```

## Tests

```bash
python3 -m unittest -v
```
