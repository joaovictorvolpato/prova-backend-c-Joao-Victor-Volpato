"""Processamento de imagens: inferência, erros, tempo, versão e histórico.

Estes testes rodam contra o modelo ONNX de verdade — é o que garante que a
implementação real satisfaz a porta de inferência.
"""

import pytest

from src.api.dependencies import get_model_registry_for


def test_predicao_registra_versao_e_tempo(client, auth_headers, image_key):
    response = client.post(
        "/predictions", json={"image_key": image_key}, headers=auth_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["model_version"] == "ssd-mobilenet-v1"
    assert body["inference_ms"] > 0
    # O tempo de inferência é uma fatia do tempo total, nunca o mesmo número.
    assert body["inference_ms"] <= body["total_ms"]
    assert isinstance(body["detections"], list)


def test_modelo_carregado_apenas_uma_vez():
    registry = get_model_registry_for("models/manifest.json")

    assert registry.get() is registry.get()
    assert registry.get("ssd-mobilenet-v1") is registry.get()


def test_imagem_inexistente_retorna_404(client, auth_headers):
    response = client.post(
        "/predictions", json={"image_key": "nao-existe.png"}, headers=auth_headers
    )

    assert response.status_code == 404


def test_versao_de_modelo_desconhecida_retorna_422(client, auth_headers, image_key):
    response = client.post(
        "/predictions",
        json={"image_key": image_key, "model_version": "v99"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_arquivo_que_nao_e_imagem_falha_e_fica_no_historico(
    client, auth_headers, images_root
):
    (images_root / "corrompida.png").write_bytes(b"isto nao e uma imagem")

    response = client.post(
        "/predictions", json={"image_key": "corrompida.png"}, headers=auth_headers
    )

    assert response.status_code == 422

    historico = client.get("/predictions", headers=auth_headers).json()["items"]
    assert historico[0]["status"] == "failed"
    assert historico[0]["error"]


def test_request_id_repetido_nao_reprocessa(client, auth_headers, image_key):
    payload = {"image_key": image_key, "request_id": "req-123"}

    primeira = client.post("/predictions", json=payload, headers=auth_headers).json()
    segunda = client.post("/predictions", json=payload, headers=auth_headers).json()

    assert primeira["id"] == segunda["id"]
    assert len(client.get("/predictions", headers=auth_headers).json()["items"]) == 1


def test_historico_por_missao(client, auth_headers, image_key, mission_payload):
    mission_id = client.post("/missions", json=mission_payload, headers=auth_headers).json()["id"]
    client.post(
        "/predictions",
        json={"image_key": image_key, "mission_id": mission_id},
        headers=auth_headers,
    )

    response = client.get(
        "/predictions", params={"mission_id": mission_id}, headers=auth_headers
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["mission_id"] == mission_id


def test_missao_inexistente_retorna_404(client, auth_headers, image_key):
    response = client.post(
        "/predictions",
        json={"image_key": image_key, "mission_id": "nao-existe"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_busca_predicao_pelo_id(client, auth_headers, image_key):
    created = client.post(
        "/predictions", json={"image_key": image_key}, headers=auth_headers
    ).json()

    response = client.get(f"/predictions/{created['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_predicao_inexistente_retorna_404(client, auth_headers):
    assert client.get("/predictions/nao-existe", headers=auth_headers).status_code == 404


def test_endpoint_de_modelos_lista_versoes(client, auth_headers):
    response = client.get("/models", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["active_version"] == "ssd-mobilenet-v1"


def test_predicao_exige_autenticacao(client, image_key):
    assert client.post("/predictions", json={"image_key": image_key}).status_code == 401


@pytest.mark.parametrize("campo,valor", [("confidence_threshold", 1.5), ("max_detections", 0)])
def test_parametros_fora_da_faixa_sao_recusados(client, auth_headers, image_key, campo, valor):
    response = client.post(
        "/predictions", json={"image_key": image_key, campo: valor}, headers=auth_headers
    )

    assert response.status_code == 422
