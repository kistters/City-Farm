# City-Farm

Jogo multiplayer local de produção e consumo de alimentos, com atualizações em tempo real.

## Executar

Pré-requisitos: Docker com Compose v2.

```bash
docker compose up --build -d
```

- Jogo: http://localhost
- RabbitMQ (somente localhost): http://localhost:15672 (usuário `cityfarm`, senha `cityfarm_dev`)
- Logs: `docker compose logs -f websocket worker`
- Parar: `docker compose down`

### Jogar com amigos na mesma rede Wi-Fi

Abra `http://IP_LOCAL_DO_COMPUTADOR` em outro dispositivo na mesma rede. A interface abre uma conexão WebSocket na porta **8888**, que também precisa estar acessível pela rede local. Não exponha as portas 80 ou 8888 à internet: esta é uma aplicação de demonstração sem autenticação.

## Arquitetura

- Nginx serve a interface Vue 2 existente.
- Tornado fornece WebSocket e encaminha ações para Celery.
- RabbitMQ transporta as tarefas de produção e consumo.
- Redis armazena o estoque compartilhado.

## Escopo da modernização

Esta PR atualiza o ambiente Docker, Python e bibliotecas do backend, remove a API obsoleta `@web.asynchronous` e corrige uma condição de estoque vazio no script Lua. **Não altera as regras de produção/consumo nem moderniza a interface Vue 2.**

Os serviços utilizam credenciais fixas apenas para desenvolvimento local. Ainda é necessário validar a execução integral via Docker e o funcionamento multiplayer em dois dispositivos.
