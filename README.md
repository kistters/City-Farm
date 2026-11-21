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

## Identidade casual dos Farmers

No painel Farmer, escolha um apelido e clique em **Join** antes de produzir.
O perfil (ID aleatório de 128 bits e apelido) fica guardado no
`localStorage` do navegador; o WebSocket registra o perfil e associa
as provas e produtos a esse Farmer. O servidor valida formato e tamanho.
O Farmer pode mudar o apelido sem perder o ID no navegador.

**Não é autenticação:** o cliente controla o identificador e o apelido;
não use como prova de identidade, proteção contra trapaça ou base de
recompensas reais. A geração funciona também no HTTP da rede local,
mas usa `Math.random()`, impróprio para identificadores de segurança.

## Pedidos de consumo pendentes

A página principal mostra **Pending Eat requests** no lugar do painel de
estoque. Cada clique do Citizen registra um pedido individual no Redis.
Se houver estoque, o consumo ocorre imediatamente; caso contrário, o
pedido fica aguardando na fila por ingrediente, sem tarefas Celery
repetitivas. O contador é atualizado atomicamente após o atendimento.

Os ingredientes necessários a pratos também aparecem nos contadores.
O dashboard separado mantém estoque, histórico PoW, conexões e agora
métricas de pedidos pendentes e atendidos.

## Variedade, fontes de produção e pratos

A feira ganhou **18 ingredientes**: vegetais e grãos, arroz, feijão,
batata, frutas, leite, ovos, carnes e peixe. Os novos tipos são configurados
em `CityFarm/code/products.py`. Nesta fase a origem (`field`, `tree`,
`cow`, `pig`, `chicken` ou `pond`) é informativa: cada item ainda
é produzido por um PoW no navegador. Criar e alimentar animais, colher
árvores repetidamente e outras mecânicas de ciclo produtivo ficam para PRs
futuras.

Um Citizen pode pedir um prato de `dishes.py`, composto por quantidades
fixas de ingredientes:

- Rice, Beans & Beef: 1 rice + 1 beans + 1 beef
- Tomato Omelette: 2 eggs + 1 tomato
- Chicken & Potatoes: 1 chicken_meat + 2 potato
- Fruit Salad: 1 orange + 1 banana + 1 apple
- Fish & Rice: 1 fish + 1 rice

O pedido de um prato fica armazenado no Redis enquanto faltam
ingredientes. Quando a produção PoW termina, o backend reavalia
os pedidos e **consome todos os ingredientes de uma vez** com Lua
atômico. Se faltarem ingredientes, nenhum é consumido e a demanda
continua visível na seção `Pending Eat requests`. Não há peso,
qualidade, crescimento nem expiração nesta etapa. Pedidos de ingredientes
individuais agora são atendidos diretamente via Redis, sem retries
periódicos; veja a seção sobre a issue #12 abaixo.

Os pratos possuem fila limitada a 200 pedidos aguardando preparo;
não há cancelamento nem timeout automático ainda.

### Assets de imagens

Os 18 ingredientes e cinco pratos possuem ícones **SVG individuais
de 96 × 96**, com fundo transparente, traços e paleta consistentes,
no diretório `CityFarm/front/css/images/`. A interface usa esses
assets inclusive para os seis vegetais antigos, substituindo os PNGs
heterogêneos sem apagar os arquivos originais.

### Testes

```bash
docker compose exec worker python -m unittest test_pow test_players test_pending_eat test_dishes
```

Abra o jogo, peça uma omelete sem estoque de ovos, confira a demanda,
produza ovos e tomate por PoW e verifique o consumo do prato completo
e a baixa da demanda. O dashboard separado continua exibindo estoque,
conexões e histórico de validações.

**Limites:** o catálogo e as receitas ainda são demonstrativos;
não representam criação real de animais, árvores recorrentes ou nutrição.

## Pedidos eat sem retries infinitos (issue #12)

Pedidos individuais são registrados diretamente pelo Tornado no Redis e
armazenados em uma fila **FIFO por ingrediente** (`eat:queue:<produto>`).
Não são mais disparadas tarefas Celery para cada novo consumo. O pedido
fica visível na feira enquanto aguarda estoque, sem nenhum `sleep`,
`retry(countdown=3)` ou polling contínuo.

Tanto a criação de um pedido quanto a colheita por PoW usam scripts Lua
para consumir uma unidade disponível e atender atomicamente o primeiro
Citizen aguardando aquele ingrediente. Quando o estoque está zerado,
o pedido permanece na fila persistida no Redis. Um mesmo pedido não pode
consumir duas unidades; o backend usa um ID aleatório e marcador de
deduplicação. São permitidos até **200 pedidos individuais pendentes por
ingrediente** para evitar acúmulo ilimitado.

Os pratos continuam aguardando **a receita inteira**, pelo fluxo de
`dish_orders.py`. Na disputa por um ingrediente, pedidos individuais
pendentes têm prioridade no momento da colheita; a receita só usa o
estoque restante.

### Atualização a partir de versões anteriores

Na inicialização, o Tornado recupera marcadores `eat:pending:*` de versões
anteriores, insere os pedidos ainda pendentes na fila uma única vez e
tenta consumir estoque já disponível. Tarefas `eat` antigas que ainda
estejam no RabbitMQ são convertidas em pedidos persistentes quando
executadas pela primeira vez, **sem reenfileirar retries**. Pedidos já
concluídos são ignorados.

Os contadores de pedidos atendidos são expostos no payload do dashboard
(`pending_orders[].fulfilled`), junto com as pendências.

A fila não expira automaticamente nesta versão: isso evita perder demanda
enquanto não existe estoque, mas significa que o pedido continuará pendente
até ser atendido. Cancelamento e TTL podem ser evoluções futuras.
Os pedidos dependem da persistência configurada para Redis; o Compose
atual não promete durabilidade em caso de remoção do volume/dados do Redis.

### Teste da issue #12

```bash
docker compose up --build -d
docker compose exec worker python -m unittest test_pending_eat test_pow test_dishes
docker compose exec worker python -m unittest test_eat_redis
docker compose logs -f worker websocket
```

Em `/`, peça alguns alimentos com estoque zero e observe o painel de
pedidos pendentes: nenhum `tasks.eat ... Retry in 3s` novo deverá surgir.
Produza os alimentos via PoW e verifique que os contadores diminuem
sem estoque negativo, inclusive com dois Citizens conectados.
Repita após reiniciar os containers (sem `docker compose down -v`).

## Telas por papel e layout responsivo

As interfaces agora são independentes:

- `/`: escolha entre Farmer e Citizen.
- `/farmer`: nome do Farmer, demanda atual dos Citizens e produção PoW.
- `/citizen`: pedidos individuais de cinco ingredientes.
- `/dashboard`: monitoramento técnico, estoque, filas e histórico do PoW.

O Nginx mapeia `/farmer` para `farmer.html` e `/citizen` para
`citizen.html`. As páginas não carregam scripts Vue de papéis que
não utilizam. Estilos compartilhados em `css/dashboard.css` usam CSS Grid
com breakpoints a 850px e 600px, botões apropriados para toque e
navegação acessível também em telas pequenas.

**Separação de responsabilidades (SRP):** `farmer.js` cuida somente
da experiência de produzir; `citizen.js` cuida somente de pedidos;
`dashboard.js` mostra dados e demanda. O WebSocket do backend continua
sendo o mesmo, sem mudança no contrato nesta PR. Não é uma reescrita
completa em SOLID: o objetivo é um passo pequeno que podemos estudar,
testar e refatorar aos poucos.

### Teste de layout

```bash
python -m unittest discover -s tests -p 'test_role_pages.py'
docker compose up -d
```

Confira `/`, `/farmer`, `/citizen` e `/dashboard` em uma janela
desktop e no modo responsivo do navegador (larguras 375px e 768px).
Produza uma unidade por PoW e faça um pedido de prato ou ingrediente
para confirmar as conexões WebSocket. Use `Ctrl+Shift+R` se o navegador
mostrar uma versão anterior em cache.

Esta PR muda **somente a apresentação e roteamento**; não modifica
prioridades de fila, regras do Redis, receitas ou tasks Celery.
