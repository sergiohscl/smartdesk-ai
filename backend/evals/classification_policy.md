# SmartDesk AI — Política de Classificação

## Objetivo

Definir critérios de referência para avaliar as classificações
de chamados realizadas pela inteligência artificial.

## Prioridades

### Low
- Impacto individual ou muito limitado.
- Sem interrupção relevante das atividades.
- Alternativa simples disponível.

### Medium
- Impacto operacional moderado.
- Um usuário ou pequeno grupo afetado.
- Atividades prejudicadas ou bloqueadas, sem impacto crítico.

### High
- Impacto significativo em processos importantes.
- Equipes ou vários usuários afetados.
- Ausência de alternativa operacional adequada.
- Necessidade de atendimento urgente.

### Critical
- Interrupção de operação essencial.
- Indisponibilidade generalizada com impacto severo.
- Incidente grave de segurança em andamento.
- Necessidade de resposta imediata.

## Categorias

- hardware: equipamentos e componentes físicos.
- software: aplicações e sistemas.
- network: conectividade, rede e VPN.
- access: autenticação, permissões e contas.
- other: solicitações gerais e casos não enquadrados.

## Regras de avaliação

1. Considerar título e descrição em conjunto.
2. Avaliar impacto e urgência, não apenas palavras-chave.
3. Não inventar informações ausentes no chamado.
4. Em casos ambíguos, registrar a necessidade de revisão.
5. Não considerar a classificação da IA como decisão definitiva.
6. Manter validação humana para aplicação de prioridades.
7. A prioridade deve considerar conjuntamente o alcance do impacto,
   a interrupção das atividades, as alternativas disponíveis e a urgência.

8. Problemas individuais sem interrupção relevante das atividades
   devem ser classificados como low, salvo evidência de maior criticidade.

9. O bloqueio das atividades de um único usuário, sem impacto
   crítico adicional, normalmente corresponde à prioridade medium,
   mesmo quando não existe alternativa disponível.

10. A ausência de alternativa, isoladamente, não determina
    prioridade high. É necessário considerar a importância
    do processo afetado e a urgência do atendimento.

11. Não elevar a prioridade apenas porque o chamado menciona
    falha de acesso, indisponibilidade ou lentidão.

## Critérios complementares de prioridade — Política v2

### Impacto operacional moderado — medium

12. Uma funcionalidade relevante degradada para vários usuários
    pode receber prioridade medium, mesmo quando existe uma
    alternativa operacional disponível.

13. A existência de uma alternativa não determina, isoladamente,
    prioridade low. Devem ser considerados a relevância da
    funcionalidade, o número de usuários afetados e o impacto
    nas atividades.

14. Quando uma falha afeta vários funcionários e compromete
    atividades necessárias no mesmo dia, a prioridade medium
    pode ser adequada, mesmo que exista uma solução temporária.

15. Problemas individuais ou de impacto reduzido, sem prejuízo
    operacional relevante, normalmente permanecem como low.

### Interrupção de operações essenciais — critical

16. A paralisação completa de uma operação essencial, sem
    alternativa operacional viável, deve receber prioridade
    critical quando o impacto operacional for grave.

17. Processos como faturamento e movimentação de estoque
    podem ser essenciais. A classificação deve considerar
    a interrupção efetiva das atividades, e não apenas
    o nome do sistema afetado.

18. Uma falha restrita a um setor pode ser critical quando
    interrompe integralmente uma operação essencial.

### Regras de equilíbrio

19. Não reduzir automaticamente a prioridade porque existe
    uma alternativa parcial ou temporária.

20. Não elevar automaticamente a prioridade apenas porque
    vários usuários foram afetados.

21. Em casos ambíguos, considerar conjuntamente abrangência,
    relevância da atividade, interrupção, alternativas e
    urgência, sem presumir consequências não informadas.
