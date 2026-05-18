# Relatório Semanal da Performance da Loja
**Data de Emissão:** 15/05/2026
**Modelo Analítico:** Llama 3.1:8b (Estratégia Few-Shot)

---

## Mapa de Fluxo e Topologia
A análise abaixo é uma projeção da configuração física da loja, feita com os dados fornecidos para o desenvolviemento do sistema de monitorização. Os corredores de navegação (`Z_N`) servem como eixos centrais de tráfego, enquanto as secções de produtos (`Z_S`) funcionam como pontos de paragem.

![Topologia da Loja](topologia_loja.png)

---

## Resumo Executivo
- A loja registrou uma taxa de conversão de 99,1%, indicando que a maioria dos clientes está realizando compras.
- As zonas Z_S3 e Z_N5 apresentaram anomalias de afluência, com números significativamente acima da média.
- É recomendável reforçar a reposição entre as 17h e as 19h nas zonas afetadas.

---

## Saúde dos Dados e Qualidade do Sistema
*Nesta secção temos uma avaliação da fiabilidade das métricas apresentadas com base no ruído capturado pelos sensores.*

| Indicador de Qualidade | Valor | Estado |
| :--- | :--- | :--- |
| **Trajetórias Reconstruídas** | 10583 | OK |
| **Anomalias** | 5849 | Ruído |
| **Taxa de Integridade do Sinal** | 64.4% | Moderada |

> **Nota Técnica:** Este número de anomalias reflete eventos onde as trajetórias são fragmentadas por oclusão visual. A taxa de 60% para cima é considerada excelente para ambientes deste tipo.

---

## Métricas Globais de Tráfego
| Métrica | Valor |
| :--- | :--- |
| **Total de Visitantes** | 10583 |
| **Total de Compradores** | 10488 |
| **Taxa de Conversão** | 99.1% |
| **Tempo Médio de Visita** | 49.46 min |

### Afluência Diária
| Data | Visitantes |
| :--- | :--- |
| 2025-03-10 | 1746 |
| 2025-03-11 | 1570 |
| 2025-03-12 | 1859 |
| 2025-03-13 | 1928 |
| 2025-03-14 | 1903 |
| 2025-03-15 | 2392 |
| 2025-03-16 | 2178 |

---

## Análise de Abandonos e Perdas
- **Perfil Dominante de Abandono:** F (adult)
- **Total de Potenciais Clientes Perdidos:** 95

---

## Insights Estratégicos

### Anomalia de Afluência em Z_S3
- **ID:** `INS_EX_01` | **Urgência:** ESTA_SEMANA
- **Observação:** A zona Z_S3 teve 8 visitantes, 53% acima da média.
- **Implicação:** Risco de congestionamento e rutura de stock.
- **Recomendação:** **Reforçar a reposição entre as 17h e as 19h.**
---

### Anomalia de Afluência em Z_N5
- **ID:** `INS_EX_02` | **Urgência:** ESTA_SEMANA
- **Observação:** A zona Z_N5 teve 9 visitantes, 115% acima da média.
- **Implicação:** Risco de congestionamento e rutura de stock.
- **Recomendação:** **Reforçar a reposição entre as 17h e as 19h.**
---

### Anomalia de Afluência em Z_S2
- **ID:** `INS_EX_03` | **Urgência:** ESTA_SEMANA
- **Observação:** A zona Z_S2 teve 5 visitantes, 417% acima da média.
- **Implicação:** Risco de congestionamento e rutura de stock.
- **Recomendação:** **Reforçar a reposição entre as 17h e as 19h.**
---

### Anomalia de Afluência em Z_N6
- **ID:** `INS_EX_04` | **Urgência:** ESTA_SEMANA
- **Observação:** A zona Z_N6 teve 2 visitantes, 67% abaixo da média.
- **Implicação:** Risco de queda de tráfego e perda de faturação.
- **Recomendação:** **Reforçar a promoção em redes sociais.**
---

### Anomalia de Afluência em Z_C2
- **ID:** `INS_EX_05` | **Urgência:** ESTA_SEMANA
- **Observação:** A zona Z_C2 teve 40 visitantes, 133% acima da média.
- **Implicação:** Risco de congestionamento e rutura de stock.
- **Recomendação:** **Reforçar a reposição entre as 17h e as 19h.**
---


*Relatório gerado automaticamente pelo Sistema de Monitorização de Trajetórias.*