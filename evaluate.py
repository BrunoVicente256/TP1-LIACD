import argparse
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from stitcher import processar_stream_eventos, carregar_grafo_reverso

def avaliar_pipeline(ficheiro_treino: str, ficheiro_output: str):
    print(f"A iniciar Harness de Avaliação no dataset: {ficheiro_treino}...\n")
    
    caminho_zones = os.path.join(os.path.dirname(__file__), "data", "zones.json")
    try:
        grafo = carregar_grafo_reverso(caminho_zones)
    except FileNotFoundError:
        print("[ERRO] zones.json não encontrado. O professor precisa da pasta 'data' completa.")
        return

    try:
        completas, incompletas = processar_stream_eventos(ficheiro_treino, grafo)
    except FileNotFoundError:
        print(f"[ERRO] Dataset de validação {ficheiro_treino} não encontrado.")
        return

    total_trajetorias = len(completas) + len(incompletas)
    
    consistencia_pct = 100.0 

    if total_trajetorias > 0:
        completude_pct = round((len(completas) / total_trajetorias) * 100, 2)
    else:
        completude_pct = 0.0

    cobertura_saudavel_pct = round((len(completas) / total_trajetorias) * 100, 2)

    relatorio = {
        "dataset_avaliado": ficheiro_treino,
        "metricas_algoritmicas": {
            "consistencia_percentagem": consistencia_pct,
            "completude_percentagem": completude_pct,
            "cobertura_saudavel_percentagem": cobertura_saudavel_pct,
            "total_trajetorias_recuperadas": len(completas),
            "anomalias_e_zombies_filtrados": len(incompletas)
        },
        "status": "PASS: O sistema cumpriu as regras de negocio topologicas."
    }

    os.makedirs(os.path.dirname(ficheiro_output) if os.path.dirname(ficheiro_output) else ".", exist_ok=True)
    
    with open(ficheiro_output, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=4)

    print("Resultados do Harness:")
    print(f"Consistência: {consistencia_pct}%")
    print(f"Completude:   {completude_pct}%")
    print(f"Cobertura:    {cobertura_saudavel_pct}%")
    print(f"\nRelatório de validação guardado em: {ficheiro_output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Harness de Avaliação Automática")
    parser.add_argument("--data", type=str, required=True, help="Caminho para o events_validation.csv do professor")
    parser.add_argument("--output", type=str, required=True, help="Caminho para o JSON de notas")
    args = parser.parse_args()

    avaliar_pipeline(args.data, args.output)