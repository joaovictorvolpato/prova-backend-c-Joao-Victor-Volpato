"""CRUD de missões."""


def test_ciclo_completo_de_crud(client, auth_headers, mission_payload):
    created = client.post("/missions", json=mission_payload, headers=auth_headers)
    assert created.status_code == 201
    mission = created.json()
    assert mission["status"] == "planned"
    assert mission["id"]

    fetched = client.get(f"/missions/{mission['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == mission_payload["name"]

    updated = client.patch(
        f"/missions/{mission['id']}",
        json={"status": "in_progress", "image_count": 200},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["image_count"] == 200

    assert client.delete(f"/missions/{mission['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/missions/{mission['id']}", headers=auth_headers).status_code == 404


def test_nome_duplicado_retorna_409(client, auth_headers, mission_payload):
    assert client.post("/missions", json=mission_payload, headers=auth_headers).status_code == 201

    duplicated = client.post("/missions", json=mission_payload, headers=auth_headers)

    assert duplicated.status_code == 409


def test_transicao_de_status_invalida_retorna_422(client, auth_headers, mission_payload):
    mission_id = client.post("/missions", json=mission_payload, headers=auth_headers).json()["id"]

    # planned -> completed não é permitido: a missão precisa passar por in_progress.
    response = client.patch(
        f"/missions/{mission_id}", json={"status": "completed"}, headers=auth_headers
    )

    assert response.status_code == 422


def test_payload_invalido_retorna_422(client, auth_headers):
    response = client.post(
        "/missions",
        json={"name": "", "drone_model": "DJI Mavic 3M"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_status_em_texto_e_convertido_para_o_enum():
    from src.domain.mission import Mission, MissionStatus

    mission = Mission.create(name="Talhão 12", drone_model="DJI Mavic 3M")

    updated = mission.with_changes(status="in_progress")

    assert updated.status is MissionStatus.IN_PROGRESS


def test_status_desconhecido_e_rejeitado_pelo_dominio():
    import pytest

    from src.domain.exceptions import InvalidMissionError
    from src.domain.mission import Mission

    mission = Mission.create(name="Talhão 12", drone_model="DJI Mavic 3M")

    with pytest.raises(InvalidMissionError):
        mission.with_changes(status="voando")
