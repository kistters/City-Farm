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
| 1 — Monocultura familiar | 3×3 | Posições com o mesmo ingrediente escolhido | 1 / −10 Saúde do Solo |
| 2 — Monocultura de latifúndio | 6×6 | Posições menores com o mesmo ingrediente escolhido | 3 / −35 Saúde do Solo |
| 3 — Multicultura | 3×3 | Posição e ingrediente de cada célula | 4 misturados / −20 Saúde do Solo |

Em 1 e 2, clicar marca/desmarca a célula com o ingrediente escolhido. No Extra, clicar repetidamente alterna entre vazio e os cinco ingredientes. A ordem dos cliques nunca importa.

O Farmer tem **três terrenos fixos** e uma barra global de **Saúde do Solo (0–100)**, inicialmente em 100. Cada produção válida gasta Saúde do Solo, e cada terreno é liberado quando todo seu lote é vendido. Na multicultura o lote contém **exatamente os ingredientes do padrão**, não quatro cópias do produto inicialmente escolhido.

- **Cuidar da Terra:** grátis; disponível somente abaixo de 10 pontos e recupera até **10/100**.
- **Preparar o Solo:** custa **5 moedas**, recupera até **+40/100**, limitado a 100.
- Não existe mais a compra permanente de terrenos como destino para as moedas. A manutenção é o gasto recorrente.

## Citizen

| Nível | Operação | Moedas |
|---|---|---:|
| 1 | Soma/subtração | 5 |
| 2 | Multiplicação/divisão inteira | 10 |
| 3 | Expressões com precedência e parênteses | 15 |

Cada trabalho correto gasta 10 de energia. **Descansar** é gratuito apenas quando a energia está abaixo de 10 e recupera até **10/100**. O Citizen começa com 60/100 de energia e zero moedas. Uma compra desconta 5 moedas, credita ao Farmer dono do alimento, remove um item do estoque e restaura 30 de energia (máximo 100). Erros nas contas não consomem energia.

São apenas cinco alimentos: milho, trigo, cenoura, alface e tomate. Não existem receitas, Dishes, preço dinâmico nem espera artificial.

## Arquitetura

- Nginx: páginas Vue 2 responsivas.
- Tornado: WebSockets `/publihser` e `/dashboard`.
- Redis: desafios com TTL de 180 segundos, estoques, lotes, terrenos, moedas, energia e Saúde do Solo.
- `puzzles.py`: geração/validação das regras dos desafios.
- `economy.py`: conclusão atômica, produção, compra e transferência em scripts Lua.
- `websocket.py`: transporte e notificações.
- `player.js`: identidade casual separada por papel, permitindo jogar com Farmer e Citizen diferentes em duas abas do mesmo navegador.

Cada desafio válido pode conceder recompensa **uma única vez**, mesmo sob chamadas simultâneas. As respostas são verificadas pelo servidor; entretanto, os padrões enviados ao navegador podem ser lidos por bots, e o ID em `localStorage` pode ser falsificado. É um estudo de arquitetura para uso **exclusivamente local**.

O mercado novo usa chaves Redis `game:*`. Estoques antigos de PoW, filas `eat` e pedidos Dish não aparecem no novo mercado e não são consumidos. Não execute `FLUSHDB` no Redis do jogo sem backup.

## Simplicidade, SOLID e Zen of Python

**Simplicidade no código e amor no coração.** O projeto favorece responsabilidades claras, funções pequenas, código explícito e poucas abstrações. Desafios pertencem a `puzzles.py`, economia a `economy.py` e WebSocket apenas transporta ações e atualizações. As operações concorrentes que mudam saldo, produção e estoque são atômicas em Redis. Preferir legibilidade e testes de comportamento a hierarquias artificiais: *Simple is better than complex* e *Readability counts*.

As ações gratuitas são apenas emergenciais (até 10); estudar seu impacto na economia antes de adicionar novos sistemas.

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
5. Repita na monocultura de latifúndio (3 unidades, −35 de solo) e multicultura (4 ingredientes do padrão, −20 de solo).
6. Teste **Cuidar da Terra** com solo abaixo de 10, **Preparar o Solo** com 5 moedas, e **Descansar** com energia abaixo de 10. Verifique que cada recurso nunca passa de 100.
7. Tente enviar um mesmo desafio duas vezes.
8. Observe o estoque e os eventos em `/dashboard`.

Logs: `docker compose logs -f websocket`.
