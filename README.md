# drone-image-processing

Prova prática de Back-end João Victor Volpato.

---

## Parte 1: Objetivo de cada componente do diagrama

### 1. Camada externa

| Componente | Objetivo |
|---|---|
| **Drone** | Capturar as mídias (fotos e vídeos) e gera a telemetria de posição, bateria e status dos sensores. |
| **Controle Remoto** | Controlar as funcionalidades do drone remotamente. |
| **Usuário** | Operar o drone pelo controle remoto e acompanha o voo pelo aplicativo. |
| **Android APP** | Servir a interface que controla o drone e conversa com o back-end: publica a telemetria, recebe os comandos e envia as mídias capturadas. Usa **HTTP** para as requisições e **WebSocket** para receber os eventos em tempo real que vêm do servidor. |

### 2. Camada de entrada

| Componente | Objetivo |
|---|---|
| **Gateway — Kong** | Atuar como ponto único de entrada do sistema, responsável por rotear as requisições para os serviços internos e por concentrar a lógica da plataforma, como TLS, rate limiting e logging. Ele ainda é responsável pela autenticação e identificação do Usuário, o Dispositivo e o Cliente antes que a requisição chegue aos serviços.|

### 3. Camada de aplicação

| Componente | Objetivo |
|---|---|
| **API Java** | Centralizar as regras de negócio da aplicação. Para isso, persiste o estado em MySql, utiliza o Redis como cache e usa o EMQX como broker da mensageria. |
| **API REST** | Componente que abstrai o acesso ao S3. Por meio de uma interface HTTP.|

### 4. Camada de dados e mensageria

| Componente | Objetivo |
|---|---|
| **EMQX** | Servir como canal de comunicação com os dispositivos. Pelo broker passam a telemetria, os eventos e as respostas de comando, e é ele que desacopla o dispositivo do back-end. |
| **MySql** | Armazenar dados transacionais referente ao estado regras de negócio, como usuários, dispositivos, logs de voo e metadados das mídias. |
| **Redis** | Armazenar em memória para os dados que são acessados/alterados com frequência, antes de escrever ou ler do MySql|
| **Storage S3** | Guarda as mídias do drone, que são arquivos grandes e imutáveis, com durabilidade alta e custo baixo por GB.  |

### 5. Camada de observabilidade

| Componente | Objetivo |
|---|---|
| **Prometheus** | Coletar e armazenar as métricas dos serviços, como latência, taxa de erro, throughput e conexões no EMQX, e avalia as regras de alerta em cima delas. |
| **Grafana** | Montar e mostrar os dashboards sobre as métricas do Prometheus, dando visão da saúde da plataforma, dos drones conectados e do desempenho das APIs. |
| **Técnico** | Operar a plataforma. É quem acompanha o sistema pelo Grafana e pelo dashboard do EMQX para diagnosticar dispositivos e investigar incidentes. |


---

## Parte 2: API RESTful de missões

CRUD de missões em FastAPI, com persistência em SQLite. A emissão do token é
responsabilidade do serviço de autenticação; esta API apenas valida o JWT recebido.

### Como rodar

O projeto usa [uv](https://docs.astral.sh/uv/) e Python 3.13.

```bash
cp .env.example .env
uv sync
uv run uvicorn src.main:app --reload   # docs em http://localhost:8000/docs
uv run pytest                          # testes
```

Como não há login aqui, para testar basta um token assinado com o mesmo `JWT_SECRET`
que o serviço de autenticação usaria:

```bash
TOKEN=$(uv run python -c "
import jwt, datetime as dt
now = dt.datetime.now(dt.timezone.utc)
print(jwt.encode({'sub': 'user-123', 'username': 'piloto', 'iat': now,
                  'exp': now + dt.timedelta(hours=1)}, 'change-me-in-production'))")

curl -X POST localhost:8000/missions \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Talhão 12","drone_model":"DJI Mavic 3M","image_count":500,"area_hectares":12.5}'
```

### Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/auth/me` | Identidade extraída do token atual |
| `GET` | `/health` | Saúde da API e do banco (pública) |
| `POST` | `/missions` | Cria uma missão |
| `GET` | `/missions/{id}` | Busca uma missão pelo id |
| `PATCH` | `/missions/{id}` | Atualização parcial |
| `DELETE` | `/missions/{id}` | Remove uma missão |

### Organização do código

```
src/
├── domain/       entidades, erros e as portas de persistência
├── api/          rotas, schemas, middleware e injeção de dependência
├── service/      regras de negócio, atrás de interfaces
└── repository/   SQL, driver do banco e mapeamento para o domínio
```

O fluxo é `api -> service -> repository -> banco` e as dependências apontam para dentro:
o service depende da interface `IMissionRepository`, que fica no domínio, e é a
implementação SQL que depende do domínio. O `domain/` não importa nada das outras camadas.

### Decisões técnicas

- **Entidade que se valida.** `Mission` é imutável e carrega a máquina de estados do
  `status`: de `planned` só se vai para `in_progress` ou `canceled`, e missão encerrada
  não volta a rodar. A regra fica na entidade para não se perder quando outro caso de uso
  precisar alterar uma missão.
- **Interfaces nos services.** Os endpoints dependem de `IMissionService`, nunca da
  implementação, o que permite trocar a regra ou usar um dublê nos testes sem tocar na rota.
- **Injeção de dependência.** A cadeia `Database -> Repository -> Service` é montada em
  `api/dependencies.py` e entregue pronta ao endpoint via `Depends`, sempre tipada pela
  interface. Trocar implementação é mudança em um arquivo só.
- **Singleton do driver.** `Database` mantém uma conexão por processo, aberta no lifespan e
  fechada no shutdown. Só ele conhece o driver concreto; os repositories usam `execute`,
  `fetch_one` e `fetch_all`.
- **Repository abstrato.** `AbstractRepository` concentra o CRUD genérico; cada repository
  declara tabela, colunas e o mapeamento linha ↔ entidade. O mapeamento fica aqui para que
  o formato do banco (status em texto, `created_at` em ISO 8601) não vaze para o domínio.
- **JWT em middleware, sem login.** A autenticação acontece em outro microsserviço: aqui o
  middleware só valida assinatura, expiração e — quando configurados — `iss` e `aud`, e
  coloca a identidade no request. Como a validação roda antes das rotas, rota nova já nasce
  protegida: só o que está em `PUBLIC_PATHS` fica de fora, e a identidade chega ao endpoint
  pela dependência `get_current_user`. Assim esta API não guarda usuários nem senhas.
- **Erros traduzidos na borda.** As camadas internas levantam erros de domínio e
  `api/errors.py` faz o de-para para 404, 409 e 422 — nenhuma delas conhece HTTP.
- **Banco.** A Parte 2 pede SQLite e a Parte 4 pede PostgreSQL. Mantive SQLite aqui e isolei
  o driver no singleton `Database`, de forma que a migração fique restrita a ele e ao
  repository.
