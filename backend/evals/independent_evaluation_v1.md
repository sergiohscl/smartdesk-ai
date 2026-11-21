
# SmartDesk AI — Avaliação Independente v1

## 1. Objetivo

Avaliar a qualidade da classificação automática de chamados
realizada pelo serviço de IA do SmartDesk AI.

A avaliação mede a capacidade do modelo de sugerir:

- Categoria técnica do chamado.
- Prioridade operacional do chamado.
- Justificativa para a classificação.

## 2. Configuração

- Modelo: gpt-6-luna
- Prompt: v3
- Dataset: independent-v1
- Quantidade de chamados: 20
- Modo de execução: real
- Chamadas bem-sucedidas: 20
- Falhas de serviço: 0

O dataset independente não foi utilizado para desenvolver
o prompt v3.

## 3. Integridade e rastreabilidade

SHA-256 do dataset:

cdd4c612cd820e7c477c74b2f3faa0525b93e67052de773a86888835fad4992e

SHA-256 do prompt:

400e2d6b289a95f6561353c86628d46be8a173ce1c6d65a9d2ea0abc162ab0b0

SHA-256 da política:

1b88ecfa478b06a3ae572e210777f8eacc2e01e028d4dceebfd8d32ef7ae1807

Os cinco relatórios originais foram consolidados após
verificação de IDs únicos e consistência dos metadados.

## 4. Métricas gerais

| Métrica | Resultado |
|---|---:|
| Total de casos | 20 |
| Classificações bem-sucedidas | 20 |
| Acurácia de categoria | 90% |
| Acurácia de prioridade | 100% |
| Acurácia completa | 90% |
| Divergências | 2 |

Acurácia completa significa que categoria e prioridade
foram classificadas corretamente no mesmo chamado.

## 5. Resultados por prioridade

| Prioridade | Casos | Acurácia completa |
|---|---:|---:|
| low | 5 | 80% |
| medium | 5 | 100% |
| high | 5 | 100% |
| critical | 5 | 80% |

Todas as prioridades previstas corresponderam aos
rótulos esperados.

## 6. Divergências

### AI-IND-002

- Categoria esperada: hardware
- Categoria prevista: software
- Prioridade esperada: low
- Prioridade prevista: low

A divergência ocorreu na categoria técnica.

### AI-IND-020

- Categoria esperada: software
- Categoria prevista: access
- Prioridade esperada: critical
- Prioridade prevista: critical

A divergência ocorreu na categoria técnica.

Os dois casos devem ser revisados para verificar possíveis
ambiguidades entre sintomas, causas e sistemas afetados.

## 7. Interpretação

O modelo apresentou bom desempenho nesta amostra
independente de 20 chamados.

A classificação de prioridade atingiu 100% de acerto,
enquanto a classificação de categoria atingiu 90%.

Os resultados não garantem o mesmo desempenho em produção,
pois a amostra é pequena e não representa necessariamente
todas as situações operacionais.

## 8. Limitações

- Apenas 20 chamados avaliados.
- Uma única execução por chamado.
- Ausência de avaliação de variabilidade entre execuções.
- Justificativas não avaliadas por uma métrica específica.
- Distribuição de categorias não uniforme.
- Ausência de validação com chamados reais de produção.

## 9. Recomendações

1. Preservar o prompt v3 como baseline.
2. Preservar o dataset independent-v1 sem alterações.
3. Revisar qualitativamente as duas divergências.
4. Criar novos casos para avaliar ambiguidades técnicas.
5. Avaliar a qualidade das justificativas.
6. Ampliar a avaliação com novos chamados independentes.
7. Comparar futuras versões do prompt com o baseline v3.

## 10. Artefatos

- evals/classification_policy.md
- evals/independent_dataset_v1.json
- evals/metrics.py
- evals/runner.py
- evals/consolidate_reports.py
- evals/reports/independent_consolidated_v1.json

## 11. Conclusão

O SmartDesk AI possui uma integração funcional com um
modelo de linguagem para classificação de chamados.

A avaliação independente v1 apresentou:

- 100% de acerto de prioridade.
- 90% de acerto de categoria.
- 90% de acerto completo.

O prompt v3 será mantido como referência para futuras
comparações, sem alterar os rótulos do dataset independente.
