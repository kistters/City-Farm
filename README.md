# City-Farm

Jogo multiplayer local de produção, trabalho e consumo. O Farmer resolve desafios de memória espacial para produzir alimentos; o Citizen resolve operações matemáticas para ganhar moedas, comprar comida e recuperar energia.

**Issue #19:** atividade humana substitui Proof of Work. Alimentos e moedas são concedidos **imediatamente após a validação** no backend, sem Celery, RabbitMQ ou tempo de crescimento.

## Executar

Pré-requisito: Docker Compose v2.

~~~bash
docker compose up --build -d
~~~

- `http://localhost/`: escolha do papel.
- `http://localhost/farmer`: memória, Saúde do Solo e plantio.
- `http://localhost/citizen`: aritmética, moedas, energia e mercado.
- `http://localhost/dashboard`: estoque e atividades em tempo real.

No celular conectado à mesma rede Wi-Fi, acesse `http://IP_LOCAL_DO_PC`. As portas 80 e 8888 precisam estar acessíveis na rede local. **Não publique o jogo na internet**: não há login real.

## Economia: somente Food

O jogo possui **um único produto: Food**. O Farmer resolve memória e produz Food, independentemente do nível. O Citizen resolve contas para ganhar moedas, compra Food por **5 moedas** e recupera **até 30 de Energia** (máximo 100). A compra credita as 5 moedas ao Farmer dono da unidade.

Não existe escolha de ingrediente, preço por ingrediente, receita nem vários estoques na interface.

**Compatibilidade:** o estoque de versões anteriores (corn, wheat, carrot, lettuce, tomato) continua disponível dentro do **total de Food**. Ao comprar Food, o backend prioriza unidades novas e depois consome as antigas, preservando o proprietário e a transferência de moedas. Não há exclusão de dados nem migração destrutiva.

## Farmer

Escolha o nível, memorize o padrão temporário e reproduza as posições. Todos os acertos criam somente Food:

| Nível | Puzzle | Produção | Saúde do Solo |
|---|---|---:|---:|
| Monocultura familiar | 3×3, posições com o mesmo vegetal | +1 Food | −10 |
| Monocultura latifúndio | 4×4, seis posições com o mesmo vegetal | +3 Food | −35 |
| Multicultura | 4×4, quatro vegetais diferentes | +4 Food | −20 |

Os vegetais aparecem como imagens pixel art nos três puzzles. Nas monoculturas, um vegetal é sorteado para todas as posições; na multicultura, são quatro vegetais diferentes. Eles são **apenas símbolos visuais**: **não existem produtos diferentes nem escolha de ingredientes.** O jogador pode rever o padrão sem apagar sua resposta, ou cancelar o desafio sem gastar Saúde do Solo.

O Farmer pode produzir quantas vezes desejar, inclusive com estoque não vendido, desde que tenha Saúde do Solo. A barra vai de 0 a 100; **Cuidar da Terra** (grátis) recupera até 10 quando abaixo de 10, e **Preparar o Solo** custa 5 moedas para recuperar até 40 (máximo 100).

## Citizen

| Cargo | Trabalho | Recompensa |
|---|---|---:|
| Estagiário | Soma/subtração | 5 moedas |
| Efetivo | Multiplicação/divisão exata | 10 moedas |
| Consultor | Expressões com precedência | 15 moedas |

Cada trabalho correto gasta 10 de Energia. O Citizen começa com 60/100 e 0 moedas; **Descansar** recupera gratuitamente até 10 (somente quando abaixo de 10). Comprar **1 Food** por 5 moedas recupera até +30, com atualização atômica de estoque e saldos.


## Identidade visual — Pixel Art

Direção 4, **Escala e Ferramenta**. Sprites PNG 16-bit (com CSS `image-rendering: pixelated`) em `CityFarm/front/css/images/pixel-cityfarm.png`, reutilizados por todas as páginas: enxada, trator, hortinha familiar, plantação extensiva, horta diversificada, dormir, prato de Food e os cargos Estagiário/Efetivo/Consultor. Os cinco vegetais também são sprites do puzzle.

Farmer e Citizen usam os mesmos componentes CSS para ações e níveis. No Citizen, **Descansar** e **Comer Food** aparecem juntos ao lado da barra de Energia; a compra continua custando 5 moedas e recuperando até 30 de Energia. O estoque continua sendo um único Food.

## Arquitetura

- Nginx: páginas Vue 2 responsivas.
- Tornado: WebSockets `/publihser` e `/dashboard`.
- Redis: desafios com TTL de 180 segundos, estoque de Food e identificadores dos Farmers, moedas, Energia e Saúde do Solo; leitura compatível de estoques legados.
- `puzzles.py`: geração/validação das regras dos desafios.
- `economy.py`: regras econômicas centralizadas; Lua só para operações atômicas envolvendo múltiplas chaves (produção, compra, preparo pago).
- `websocket.py`: transporte e notificações.
- `player.js`: identidade casual separada por papel, permitindo jogar com Farmer e Citizen diferentes em duas abas do mesmo navegador.

Cada desafio válido pode conceder recompensa **uma única vez**, mesmo sob chamadas simultâneas. As respostas são verificadas pelo servidor; entretanto, os padrões enviados ao navegador podem ser lidos por bots, e o ID em `localStorage` pode ser falsificado. É um estudo de arquitetura para uso **exclusivamente local**.

**Princípio de desenvolvimento:** simplicidade no código e amor no coração.
SOLID pragmático e Zen of Python: funções pequenas e explícitas, código legível,
responsabilidades claras, sem hierarquias ou frameworks adicionais desnecessários.

O mercado usa chaves Redis `game:*`. Filas antigas de PoW e pedidos Dish não entram na economia atual. Os cinco estoques de ingredientes da implementação anterior entram no total Food e podem ser vendidos até acabar. Não execute `FLUSHDB` no Redis do jogo sem backup.

## Testar

~~~bash
docker compose exec websocket python -m unittest test_puzzles test_economy_redis test_players
python -m unittest discover -s tests -p 'test_role_pages.py'
~~~

Os testes de integração limpam somente o banco Redis **DB 15**; o jogo usa o **DB 0**. O workflow GitHub Actions executa testes com Redis e checagem de sintaxe JavaScript.

### Cenário manual

1. Abra Farmer e Citizen em duas abas, com IDs diferentes.
2. Farmer conclui Monocultura familiar: o mercado ganha 1 Food.
3. Repita antes de vender: o estoque Food acumula enquanto houver Saúde do Solo.
4. Citizen conclui uma conta, ganha moedas, compra 1 Food e recupera energia. O Farmer recebe 5 moedas.
5. Farmer conclui Multicultura: o puzzle usa quatro ícones diferentes, mas produz somente 4 Food.
6. Teste **Ver padrão novamente**, **Cancelar desafio**, cuidados do solo e descanso básico.
7. Confirme que itens dos estoques antigos aparecem no total Food e ainda pagam o Farmer original.
8. Tente completar o mesmo desafio e comprar a mesma unidade simultaneamente: sem recursos duplicados.

Logs: `docker compose logs -f websocket`.
