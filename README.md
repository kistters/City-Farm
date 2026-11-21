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

## Experimento: Proof of Work no navegador (tomate)

Ao clicar em **tomato**, o Tornado cria um desafio SHA-256 aleatório,
com validade de **180 segundos** e dificuldade inicial de **3 zeros hexadecimais**.
Um Web Worker calcula a prova no browser sem bloquear o jogo, incluindo
navegadores acessando o IP local por HTTP (sem depender de `crypto.subtle`).

A solução (nonce) é enviada por WebSocket e verificada pelo worker Celery.
O Redis verifica e consome o desafio **atomicamente** com a criação
de um produto individual e atualização do contador de estoque.
Um desafio não pode ser usado duas vezes. Produtos são registrados com
`id`, `name` e `farmer` (temporariamente o IP de origem; não é login).
O consumo de tomate também remove o registro individual correspondente
quando disponível.

Os demais produtos mantêm o fluxo original. A interface confirma o
**envio** da prova; a confirmação da produção aparece no dashboard após
o worker atualizar o estoque. Se o prazo acabar, clique novamente.
A prova não é assinatura digital e não autentica o jogador.

### Verificação manual

1. Execute `docker compose up --build -d`.
2. Clique no tomate como Farmer e observe a mineração.
3. Aguarde o estoque subir **uma unidade** após a validação.
4. Teste a mesma ação em duas abas e confirme o total no dashboard.
5. Verifique os logs com `docker compose logs -f worker websocket`.

Testes do backend: `docker compose exec worker python -m unittest test_pow`.

**Segurança:** esta é uma experiência para uma rede local confiável.
Não exponha as portas do jogo à internet; não há autenticação nem
limitação global de desafios por IP.

### Histórico de Proof of Work

O dashboard mostra as **últimas 50 validações** registradas em Redis, incluindo
hash SHA-256 (quando o desafio ainda existe), nonce, Farmer, horário e resultado
**✓ VALID** ou **✗ INVALID**, sempre determinado pelo worker do backend.
As rejeições exibem um motivo como `invalid_hash`, `expired_or_used`
ou `already_used`. Ao atualizar a página, o dashboard busca o histórico
novamente. Não armazena os desafios completos nem apresenta o IP como
autenticação. O histórico permanece enquanto os dados no Redis existirem.

## PoW para todos os produtos

A produção dos seis vegetais é calculada no navegador e validada pelo
Celery. Dificuldades por produto ficam em `CityFarm/code/products.py`.
Cada prova gera **uma unidade**; o histórico registra o produto correspondente.
O backend mantém dificuldade, produto e desafio no Redis e não aceita
valores de dificuldade enviados pelo cliente.

| Produto | Zeros SHA-256 |
| --- | ---: |
| Corn | 3 |
| Wheat | 4 |
| Celery | 3 |
| Carrot | 3 |
| Lettuce | 2 |
| Tomato | 3 |

Teste: `docker compose exec worker python -m unittest test_pow`.
Valores são ilustrativos e devem ser ajustados após medições.
