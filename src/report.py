import json
import os
import argparse
from datetime import datetime

def carregar_dados(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def gerar_markdown(metrics, insights, health, img_path):
    data_relatorio = datetime.now().strftime("%d/%m/%Y")
    
    img_rel_path = os.path.basename(img_path)

    md = f"""# Relatório Semanal de Performance de Retalho
**Data de Emissão:** {data_relatorio}
**Modelo Analítico:** Llama 3.1:8b (Estratégia Few-Shot)

---

## Mapa de Fluxo e Topologia
A análise abaixo baseia-se na configuração física da loja. Os corredores de navegação (`Z_N`) servem como eixos centrais de tráfego, enquanto as secções de produtos (`Z_S`) funcionam como pontos de paragem.

![Topologia da Loja]({img_rel_path})

---

## 1. Resumo Executivo (AI Generated)
{chr(10).join([f"- {item}" for item in insights.get('resumo_executivo', [])]) if insights else "- Dados de insights não disponíveis."}

---

## Saúde dos Dados e Qualidade do Sistema
*Esta secção avalia a fiabilidade das métricas apresentadas com base no ruído capturado pelos sensores.*

| Indicador de Qualidade | Valor | Estado |
| :--- | :--- | :--- |
| **Trajetórias Reconstruídas** | {health.get('trajetorias_sucesso', 0) if health else 'N/A'} | OK |
| **Anomalias/Zombies Detetados** | {health.get('trajetorias_anomalas', 0) if health else 'N/A'} | Ruído |
| **Taxa de Integridade do Sinal** | {health.get('taxa_integridade', 0) if health else 'N/A'}% | { 'Alta' if health and health['taxa_integridade'] > 80 else 'Moderada' } |

> **Nota Técnica:** O volume de anomalias reflete eventos de "Ping-Pong" filtrados e trajetórias fragmentadas por oclusão visual. Uma taxa acima de 60% é considerada excelente para ambientes de visão computacional em tempo real.

---

## 2. Métricas Globais de Tráfego
| Métrica | Valor |
| :--- | :--- |
| **Total de Visitantes** | {metrics['funil']['total_visitantes_loja']} |
| **Total de Compradores** | {metrics['funil']['total_compradores']} |
| **Taxa de Conversão** | {metrics['funil']['taxa_conversao_percentagem']}% |
| **Tempo Médio de Visita** | {metrics['trafego']['tempo_medio_visita_minutos']} min |

### Afluência Diária
| Data | Visitantes |
| :--- | :--- |
"""
    for data, info in metrics['trafego']['afluencia_diaria'].items():
        md += f"| {data} | {info['total_dia']} |\n"

    md += f"""
---

## 3. Análise do Funil e Abandono
- **Perfil Dominante de Abandono:** {metrics['funil']['perfil_abandono'].get('genero_maioritario', 'N/A')} ({metrics['funil']['perfil_abandono'].get('idade_maioritaria', 'N/A')})
- **Total de Potenciais Clientes Perdidos:** {metrics['funil']['perfil_abandono'].get('total_perdidos', 0)}

---

## 4. Insights Estratégicos (Deep Analysis)
"""
    if insights:
        for ins in insights.get('insights', []):
            md += f"""
### {ins['titulo']}
- **ID:** `{ins['id']}` | **Urgência:** {ins['urgencia'].upper()}
- **Observação:** {ins['observacao']}
- **Implicação:** {ins['implicacao']}
- **Recomendação:** **{ins['recomendacao']}**
---
"""

    md += f"\n\n*Relatório gerado automaticamente pelo Sistema de Monitorização de Trajetórias TP1.*"
    return md

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", default=os.path.join(root_dir, "output", "metrics.json"))
    parser.add_argument("--insights", default=os.path.join(root_dir, "output", "insights.json"))
    parser.add_argument("--health", default=os.path.join(root_dir, "output", "stitching_stats.json"))
    parser.add_argument("--img", default=os.path.join(root_dir, "output", "topologia_loja.png"))
    parser.add_argument("--output", default=os.path.join(root_dir, "output", "weekly_report.md"))
    args = parser.parse_args()

    m = carregar_dados(args.metrics)
    i = carregar_dados(args.insights)
    h = carregar_dados(args.health)
    
    if m:
        conteudo = gerar_markdown(m, i, h, args.img)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(conteudo)