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

