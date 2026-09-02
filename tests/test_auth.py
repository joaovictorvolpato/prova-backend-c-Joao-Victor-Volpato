"""Validação do token pelo middleware.

O token é emitido por outro serviço; aqui os testes o produzem com a mesma
chave, e verificam o que esta API aceita e o que recusa.
"""

from datetime import timedelta


def test_token_valido_libera_a_rota(client, auth_headers):
    # 404 (e não 401) prova que a requisição passou pelo middleware.
    assert client.get("/missions/inexistente", headers=auth_headers).status_code == 404


def test_identidade_vem_do_token(client, make_token):
    headers = {"Authorization": f"Bearer {make_token(subject='abc', username='piloto')}"}

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"id": "abc", "username": "piloto"}


def test_sem_token_retorna_401(client):
    assert client.get("/missions/inexistente").status_code == 401


def test_token_malformado_retorna_401(client):
    response = client.get("/missions/x", headers={"Authorization": "Bearer nao-e-um-jwt"})

    assert response.status_code == 401


def test_token_sem_prefixo_bearer_retorna_401(client, make_token):
    response = client.get("/missions/x", headers={"Authorization": make_token()})

    assert response.status_code == 401


def test_token_expirado_retorna_401(client, make_token):
    token = make_token(expires_in=timedelta(minutes=-1))

    response = client.get("/missions/x", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expirado"


def test_token_assinado_com_outra_chave_retorna_401(client, make_token):
    token = make_token(secret="chave-de-outro-emissor")

    response = client.get("/missions/x", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_healthcheck_e_publico(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}
