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

| Nível | Tabuleiro | Memorização | Alimentos | Saúde do Solo |
|---|---|---:|---:|
| 1 — Monocultura familiar | 3×3 | Posições com o mesmo ingrediente escolhido | 1 | −10 |
| 2 — Monocultura latifúndio | 6×6 | Posições menores do mesmo ingrediente | 3 | −35 |
| 3 — Multicultura | 3×3 | Posição e ingrediente de cada célula | 4 diferentes | −20 |

Em 1 e 2, clicar marca/desmarca a célula com o ingrediente escolhido. No Extra, clicar repetidamente alterna entre vazio e os cinco ingredientes. A ordem dos cliques nunca importa.

O Farmer começa com três terrenos para manter lotes à venda; não há compra de
novos terrenos. O espaço volta a ficar livre quando **todos** os ingredientes
do lote são vendidos. Dados de parcelas adquiridas numa versão de teste anterior
são preservados.

**Saúde do Solo:** uma única barra de 0–100 por Farmer, inicializada em 100.
Plantar consome 10/35/20 pontos por nível, **apenas quando o desafio é validado
corretamente**. O nível 2 memoriza 6 posições mas produz 3 unidades, pois
quantidade de posições e quantidade de alimentos não precisam coincidir.
Multicultura é a mais exigente visualmente e gera **uma unidade de cada um dos
quatro ingredientes distintos exibidos no padrão**, com menor desgaste por
alimento.

- **Cuidar da Terra:** gratuito, restaura o solo **até 10**, apenas quando
  estiver abaixo de 10. Não adiciona 10 pontos quando já está acima disso.
- **Preparar o Solo:** custa **5 moedas**, recupera **até +40** pontos e nunca
  passa de 100. As moedas pagas desaparecem da economia (gasto recorrente).

O Farmer pode sair de zero moedas e zero saúde com o cuidado básico, realizar
uma produção de nível 1 e voltar ao mercado.

## Citizen

| Nível | Operação | Moedas |
|---|---|---:|
| 1 | Soma/subtração | 5 |
| 2 | Multiplicação/divisão inteira | 10 |
| 3 | Expressões com precedência e parênteses | 15 |

Cada trabalho correto gasta 10 de energia. O Citizen começa com 60/100 de
energia e zero moedas. **Descansar** é gratuito e recupera a Energia **até 10**
quando abaixo desse valor; não é +10 irrestrito. Uma compra desconta 5 moedas,
credita ao Farmer dono do alimento, remove um item do estoque e restaura até
30 de Energia (máximo 100). Erros nas contas não consomem energia.

São apenas cinco alimentos: milho, trigo, cenoura, alface e tomate. Não existem receitas, Dishes, preço dinâmico nem espera artificial.

## Arquitetura

- Nginx: páginas Vue 2 responsivas.
- Tornado: WebSockets `/publihser` e `/dashboard`.
- Redis: desafios com TTL de 180 segundos, estoques, lotes, terrenos, moedas e energia.
- `puzzles.py`: geração/validação das regras dos desafios.
- `economy.py`: regras econômicas centralizadas; Lua só para operações atômicas envolvendo múltiplas chaves (produção, compra, preparo pago).
- `websocket.py`: transporte e notificações.
- `player.js`: identidade casual separada por papel, permitindo jogar com Farmer e Citizen diferentes em duas abas do mesmo navegador.

Cada desafio válido pode conceder recompensa **uma única vez**, mesmo sob chamadas simultâneas. As respostas são verificadas pelo servidor; entretanto, os padrões enviados ao navegador podem ser lidos por bots, e o ID em `localStorage` pode ser falsificado. É um estudo de arquitetura para uso **exclusivamente local**.

**Princípio de desenvolvimento:** simplicidade no código e amor no coração.
SOLID pragmático e Zen of Python: funções pequenas e explícitas, código legível,
responsabilidades claras, sem hierarquias ou frameworks adicionais desnecessários.

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
5. Confira a barra de Saúde do Solo e os gastos de 10/35/20, conforme o nível.
6. No Extra, confirme que o mercado recebe **quatro tipos de ingredientes** e
   só libera o terreno após a venda de todos os itens.
7. Reduza o solo a menos de 10 e use Cuidar da Terra; com moedas, use Preparar o Solo.
8. Reduza a energia a menos de 10 e use Descansar; teste os limites de 100.
9. Tente enviar um mesmo desafio duas vezes e confirmar compras simultâneas.
10. Observe o estoque e os eventos em `/dashboard`.

Logs: `docker compose logs -f websocket`.
