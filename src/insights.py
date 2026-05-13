import json
import requests
import os
import argparse

# ==========================================
# 1. CONFIGURAÇÃO E PROMPTS DE SISTEMA
# ==========================================

SYSTEM_PROMPT = """
És um Analista Sénior de Retalho com especialização em Business Intelligence. 
O teu objetivo é transformar métricas frias em decisões de gestão estratégicas.
Deves analisar o ficheiro JSON fornecido e extrair insights que ajudem o gestor da loja.

REGRAS CRÍTICAS:
1. O teu output deve ser ESTRITAMENTE um objeto JSON e nada mais. Não incluas introduções nem texto fora do JSON.
2. Cada insight deve ser específico, citando números reais do dataset.
3. A recomendação deve ser uma ação concreta (ex: 'mudar o layout', 'reforçar staff').
4. Não inventes dados que não estejam no JSON fornecido.
"""

FEW_SHOT_EXAMPLES = [
    {
        "mau_exemplo": "A zona de frescos teve bastante tráfego.",
        "bom_exemplo": {
            "id": "INS_EX_01",
            "categoria": "trafego_zona",
            "titulo": "Anomalia de Afluência em Z_S3",
            "observacao": "A zona Z_S3 teve 847 visitantes, 31% acima da média.",
            "implicacao": "Risco de congestionamento e rutura de stock.",
            "recomendacao": "Reforçar a reposição entre as 17h e as 19h.",
            "urgencia": "esta_semana",
            "confianca": 0.95
        }
    },
    {
        "mau_exemplo": "Muitas pessoas desistem de comprar.",
        "bom_exemplo": {
            "id": "INS_EX_02",
            "categoria": "funil",
            "titulo": "Abandono Crítico no Segmento Masculino",
            "observacao": "72% dos visitantes masculinos adultos abandonam a loja sem passar pela caixa.",
            "implicacao": "Perda de faturação potencial em categorias específicas.",
            "recomendacao": "Rever o posicionamento de produtos de impulso perto da zona Z_N5.",
            "urgencia": "imediata",
            "confianca": 0.90
        }
    }
]

# ==========================================
# 2. FUNÇÕES DE COMUNICAÇÃO E PARSING
# ==========================================

def call_ollama(prompt, model="llama3.1:8b"):
    """Envia a prompt para o Ollama local e extrai a resposta JSON."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        # "format": "json",  <-- Mantido comentado para evitar Erro 500
        "options": {
            "temperature": 0,  # Garante reprodutibilidade (Guião Secção 7)
            "seed": 42,
            "num_gpu": 0       # Força o uso de CPU para evitar falhas CUDA
        }
    }
    
    try:
        # timeout=None diz ao Python para ter "Paciência Infinita"
        response = requests.post(url, json=payload, timeout=None)
        response.raise_for_status()
        return response.json()['response']
    except Exception as e:
        return json.dumps({"error": f"Erro ao contactar Ollama: {str(e)}"})

def limpar_json(texto_bruto):
    """Limpa formatações Markdown que o LLM possa adicionar à volta do JSON."""
    texto = texto_bruto.strip()
    if texto.startswith("```json"):
        texto = texto[7:]
    if texto.startswith("```"):
        texto = texto[3:]
    if texto.endswith("```"):
        texto = texto[:-3]
    return texto.strip()

def montar_prompt(metrics_data):
    """Constrói a prompt final usando a estratégia Few-Shot."""
    
    # Extrair destaques para não sobrecarregar a janela de contexto
    taxa_conv = metrics_data['funil']['taxa_conversao_percentagem']
    anomalias = metrics_data['anomalias']
    perfil_churn = metrics_data['funil']['perfil_abandono']

    prompt = f"""
{SYSTEM_PROMPT}

### EXEMPLOS DE QUALIDADE ESPERADA (FEW-SHOT) ###
Segue este padrão de raciocínio de qualidade:
1. MAU: "{FEW_SHOT_EXAMPLES[0]['mau_exemplo']}"
   BOM: {json.dumps(FEW_SHOT_EXAMPLES[0]['bom_exemplo'])}

2. MAU: "{FEW_SHOT_EXAMPLES[1]['mau_exemplo']}"
   BOM: {json.dumps(FEW_SHOT_EXAMPLES[1]['bom_exemplo'])}

### DADOS REAIS DO DATASET (metrics.json) ###
- Taxa de Conversão: {taxa_conv}%
- Perfil de Abandono (Maioria que não compra): {json.dumps(perfil_churn)}
- Lista de Anomalias Detetadas: {json.dumps(anomalias)} 

### TAREFA ###
Gera um objeto JSON válido com duas chaves principais: 
1. "insights": uma lista com 5 objetos contendo os teus melhores insights (usa o formato exato dos exemplos BOM). Foca-te nas anomalias.
2. "resumo_executivo": uma lista de 3 frases com o resumo estratégico.
A resposta deve começar com {{ e acabar com }}.
"""
    return prompt

# ==========================================
# 3. EXECUÇÃO PRINCIPAL
# ==========================================

if __name__ == "__main__":
    # Caminhos seguros
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    caminho_input_default = os.path.join(root_dir, "output", "metrics.json")
    caminho_output_default = os.path.join(root_dir, "output", "insights.json")
    
    parser = argparse.ArgumentParser(description="Módulo 3: Retail Insights (LLM)")
    parser.add_argument("--input", type=str, default=caminho_input_default, help="Caminho para o metrics.json")
    parser.add_argument("--output", type=str, default=caminho_output_default, help="Caminho para o insights.json")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERRO] Ficheiro {args.input} não encontrado. Corre o analytics.py primeiro!")
        exit(1)
        
    with open(args.input, 'r', encoding='utf-8') as f:
        metrics = json.load(f)

    print("\nA invocar o Ollama (Llama 3.1:8b) em modo CPU...")
    print("Aviso: Como estamos a usar o CPU, isto pode demorar entre 5 a 15 minutos.")
    print("Aguarde, por favor...\n")
    
    final_prompt = montar_prompt(metrics)
    raw_response = call_ollama(final_prompt)
    texto_limpo = limpar_json(raw_response)

    try:
        # Validar se o LLM gerou um JSON perfeito
        json_response = json.loads(texto_limpo)
        
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(json_response, f, indent=4, ensure_ascii=False)
            
        print(f"Sucesso Total! Insights gerados e guardados em: {args.output}")
        
    except json.JSONDecodeError:
        print("[ERRO] O modelo não devolveu um JSON válido. A guardar a resposta bruta para análise.")
        with open("error_log_llm.txt", "w", encoding='utf-8') as f:
            f.write(raw_response)
        print("Podes ver o que o modelo tentou responder no ficheiro 'error_log_llm.txt'")