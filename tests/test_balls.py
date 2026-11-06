"""Tests for the balls CRUD endpoints."""

BALLS_URL = "/api/v1/balls"


def _create_ball(client, name="Lucky 7", color="gold", prize="Jackpot"):
    response = client.post(
        BALLS_URL, json={"name": name, "color": color, "prize": prize}
    )
    assert response.status_code == 201
    return response.json()


def test_create_ball(client):
    ball = _create_ball(client)
    assert ball["id"] == 1
    assert ball["name"] == "Lucky 7"
    assert ball["color"] == "gold"
    assert ball["prize"] == "Jackpot"


def test_create_ball_invalid_color(client):
    response = client.post(
        BALLS_URL, json={"name": "Nope", "color": "purple", "prize": "None"}
    )
    assert response.status_code == 422


def test_create_ball_missing_fields(client):
    response = client.post(BALLS_URL, json={"name": "Incomplete"})
    assert response.status_code == 422


def test_list_balls_empty(client):
    response = client.get(BALLS_URL)
    assert response.status_code == 200
    assert response.json() == []


def test_list_balls(client):
    _create_ball(client, name="A", color="red", prize="Prize A")
    _create_ball(client, name="B", color="blue", prize="Prize B")
    response = client.get(BALLS_URL)
    assert response.status_code == 200
    balls = response.json()
    assert len(balls) == 2
    assert {b["name"] for b in balls} == {"A", "B"}


def test_list_balls_filter_by_color(client):
    _create_ball(client, name="A", color="red", prize="Prize A")
    _create_ball(client, name="B", color="blue", prize="Prize B")
    _create_ball(client, name="C", color="red", prize="Prize C")
    response = client.get(BALLS_URL, params={"color": "red"})
    assert response.status_code == 200
    balls = response.json()
    assert len(balls) == 2
    assert all(b["color"] == "red" for b in balls)


def test_get_ball(client):
    created = _create_ball(client)
    response = client.get(f"{BALLS_URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_ball_not_found(client):
    response = client.get(f"{BALLS_URL}/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Ball 999 not found"


def test_update_ball(client):
    created = _create_ball(client)
    response = client.patch(
        f"{BALLS_URL}/{created['id']}", json={"prize": "Bigger Jackpot"}
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["prize"] == "Bigger Jackpot"
    assert updated["name"] == created["name"]
    assert updated["color"] == created["color"]


def test_update_ball_not_found(client):
    response = client.patch(f"{BALLS_URL}/999", json={"prize": "X"})
    assert response.status_code == 404


def test_delete_ball(client):
    created = _create_ball(client)
    response = client.delete(f"{BALLS_URL}/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"{BALLS_URL}/{created['id']}").status_code == 404


def test_delete_ball_not_found(client):
    response = client.delete(f"{BALLS_URL}/999")
    assert response.status_code == 404
