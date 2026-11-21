# City-Farm

Jogo multiplayer local de produção, trabalho e consumo. O Farmer resolve desafios de memória espacial para produzir alimentos; o Citizen resolve operações matemáticas para ganhar moedas, comprar comida e recuperar energia.

**Issue #19:** atividade humana substitui Proof of Work. Alimentos e moedas são concedidos **imediatamente após a validação** no backend, sem Celery, RabbitMQ ou tempo de crescimento.

## Executar

Pré-requisito: Docker Compose v2.

~~~bash
docker compose up --build -d
~~~

- `http://localhost/`: escolha do papel.
- `http://localhost/farmer`: memória, terrenos e plantio.
- `http://localhost/citizen`: aritmética, moedas, energia e mercado.
- `http://localhost/dashboard`: estoque e atividades em tempo real.

No celular conectado à mesma rede Wi-Fi, acesse `http://IP_LOCAL_DO_PC`. As portas 80 e 8888 precisam estar acessíveis na rede local. **Não publique o jogo na internet**: não há login real.

## Farmer

Escolha apelido, terreno, ingrediente e nível. O backend mostra o padrão por 5 segundos (6 no Extra), esconde completamente e exige reproduzir as células corretas. Após acerto, o alimento está à venda **imediatamente**. O terreno fica livre novamente quando seu lote é vendido.

| Nível | Tabuleiro | Memorização | Alimentos |
|---|---|---|---:|
| 1 | 3×3 | Posições com o mesmo ingrediente escolhido | 1 |
| 2 | 6×6 | Posições menores com o mesmo ingrediente escolhido | 2 |
| Extra | 3×3 | Posição e ingrediente de cada célula | 3 |

Em 1 e 2, clicar marca/desmarca a célula com o ingrediente escolhido. No Extra, clicar repetidamente alterna entre vazio e os cinco ingredientes. A ordem dos cliques nunca importa.

O Farmer começa com três terrenos, pode comprar outros por 20 moedas (máximo seis) e só reutiliza um terreno quando o lote for totalmente vendido.

## Citizen

| Nível | Operação | Moedas |
|---|---|---:|
| 1 | Soma/subtração | 5 |
| 2 | Multiplicação/divisão inteira | 10 |
| 3 | Expressões com precedência e parênteses | 15 |

Cada trabalho correto gasta 10 de energia. O Citizen começa com 60/100 de energia e zero moedas. Uma compra desconta 5 moedas, credita ao Farmer dono do alimento, remove um item do estoque e restaura 30 de energia (máximo 100). Erros nas contas não consomem energia.

São apenas cinco alimentos: milho, trigo, cenoura, alface e tomate. Não existem receitas, Dishes, preço dinâmico nem espera artificial.

## Arquitetura

- Nginx: páginas Vue 2 responsivas.
- Tornado: WebSockets `/publihser` e `/dashboard`.
- Redis: desafios com TTL de 180 segundos, estoques, lotes, terrenos, moedas e energia.
- `puzzles.py`: geração/validação das regras dos desafios.
- `economy.py`: conclusão atômica, produção, compra e transferência em scripts Lua.
- `websocket.py`: transporte e notificações.
- `player.js`: identidade casual separada por papel, permitindo jogar com Farmer e Citizen diferentes em duas abas do mesmo navegador.

Cada desafio válido pode conceder recompensa **uma única vez**, mesmo sob chamadas simultâneas. As respostas são verificadas pelo servidor; entretanto, os padrões enviados ao navegador podem ser lidos por bots, e o ID em `localStorage` pode ser falsificado. É um estudo de arquitetura para uso **exclusivamente local**.

O mercado novo usa chaves Redis `game:*`. Estoques antigos de PoW, filas `eat` e pedidos Dish não aparecem no novo mercado e não são consumidos. Não execute `FLUSHDB` no Redis do jogo sem backup.

## Testar

~~~bash
docker compose exec websocket python -m unittest test_puzzles test_economy_redis test_players
python -m unittest discover -s tests -p 'test_role_pages.py'
~~~

Os testes de integração limpam somente o banco Redis **DB 15**; o jogo usa o **DB 0**. O workflow GitHub Actions executa testes com Redis e checagem de sintaxe JavaScript.

### Cenário manual

1. Abra Farmer e Citizen em duas abas; cada papel tem ID casual próprio mesmo no mesmo navegador.
2. Farmer produz um tomate no nível 1 e o vê no mercado.
3. Citizen conclui uma soma, recebe 5 moedas e compra o tomate.
4. Citizen recupera energia, o Farmer recebe moedas e o terreno é liberado.
5. Repita com grade 6×6 e Extra; tente enviar um mesmo desafio duas vezes.
6. Observe o estoque e os eventos em `/dashboard`.

Logs: `docker compose logs -f websocket`.
