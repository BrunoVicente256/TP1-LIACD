import os
import argparse
import pandas as pd
import json

def calcular_metricas_trafego(df: pd.DataFrame) -> dict:
    """Calcula as métricas globais de tráfego da loja."""
    
    visitantes_dia_hora = df.groupby(['visit_date', 'hour_of_day'])['person_id'].nunique().reset_index()
    
    trafego_diario = {}
    for _, row in visitantes_dia_hora.iterrows():
        data = row['visit_date']
        hora = str(row['hour_of_day']) + "h"
        visitantes = int(row['person_id'])
        
        if data not in trafego_diario:
            trafego_diario[data] = {"total_dia": 0, "por_hora": {}}
            
        trafego_diario[data]["por_hora"][hora] = visitantes
        trafego_diario[data]["total_dia"] += visitantes

    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'].replace('', pd.NA)).fillna(df['entry_time'])
    
    tempo_por_pessoa = df.groupby('person_id').agg(
        primeira_entrada=('entry_time', 'min'),
        ultima_saida=('exit_time', 'max')
    )
    tempo_por_pessoa['duracao_total_s'] = (tempo_por_pessoa['ultima_saida'] - tempo_por_pessoa['primeira_entrada']).dt.total_seconds()
    tempo_medio_loja_s = round(tempo_por_pessoa['duracao_total_s'].mean(), 2)

    return {
        "tempo_medio_visita_segundos": tempo_medio_loja_s,
        "tempo_medio_visita_minutos": round(tempo_medio_loja_s / 60, 2),
        "afluencia_diaria": trafego_diario
    }

def calcular_funil_cliente(df: pd.DataFrame) -> dict:
    """Calcula as métricas de conversão e abandono."""
    
    total_visitantes = df['person_id'].nunique()
    
    trafego_por_zona = df.groupby('zone_id')['person_id'].nunique().to_dict()
    
    zonas_caixa = ['Z_C1', 'Z_C2', 'Z_C3', 'Z_CK']
    visitantes_checkout = df[df['zone_id'].isin(zonas_caixa)]['person_id'].nunique()
    taxa_conversao = round((visitantes_checkout / total_visitantes) * 100, 2) if total_visitantes > 0 else 0
    
    pessoas_checkout = set(df[df['zone_id'].isin(zonas_caixa)]['person_id'])
    pessoas_todas = set(df['person_id'])
    pessoas_perdidas = pessoas_todas - pessoas_checkout
    
    df_perdidos = df[df['person_id'].isin(pessoas_perdidas)].drop_duplicates(subset=['person_id'])
    
    perfil_abandono = {}
    if not df_perdidos.empty:
        perfil_abandono = {
            "total_perdidos": len(pessoas_perdidas),
            "genero_maioritario": df_perdidos['gender'].mode()[0],
            "idade_maioritaria": df_perdidos['age_range'].mode()[0]
        }

    return {
        "total_visitantes_loja": total_visitantes,
        "total_compradores": visitantes_checkout,
        "taxa_conversao_percentagem": taxa_conversao,
        "visitantes_por_zona": trafego_por_zona,
        "perfil_abandono": perfil_abandono
    }

def calcular_metricas_zonas(df: pd.DataFrame) -> dict:
    """Calcula estatísticas de permanência e navegação por zona."""
    
    df_sorted = df.sort_values(by=['person_id', 'entry_time'])

    zonas_stats = {}
    for zona in df['zone_id'].unique():
        df_zona = df[df['zone_id'] == zona]
        visitantes_totais = df_zona['person_id'].nunique()
        visitantes_pararam = df_zona[df_zona['dwell_s'] > 0]['person_id'].nunique()
        dwell_medio = df_zona[df_zona['dwell_s'] > 0]['dwell_s'].mean()

        zonas_stats[zona] = {
            "visitantes_totais": int(visitantes_totais),
            "dwell_time_medio_s": round(dwell_medio, 2) if pd.notna(dwell_medio) else 0,
            "taxa_paragem_percentagem": round((visitantes_pararam / visitantes_totais) * 100, 2) if visitantes_totais > 0 else 0
        }

    caminhos = df_sorted.groupby('person_id')['zone_id'].apply(lambda x: ' -> '.join(x))
    top_caminhos = caminhos.value_counts().head(10).to_dict()

    return {
        "estatisticas_por_zona": zonas_stats,
        "top_10_rotas_frequentes": top_caminhos
    }

def calcular_segmentacao(df: pd.DataFrame) -> dict:
    """Calcula a distribuição demográfica da loja conforme exigido no guião."""
    
    df_hora = df.drop_duplicates(subset=['person_id', 'hour_of_day'])
    dist_hora = df_hora.groupby(['hour_of_day', 'gender', 'age_range']).size().reset_index(name='count')
    
    distribuicao_por_hora = {}
    for _, row in dist_hora.iterrows():
        hora = f"{int(row['hour_of_day'])}h"
        segmento = f"{row['gender']}_{row['age_range']}"
        if hora not in distribuicao_por_hora:
            distribuicao_por_hora[hora] = {}
        distribuicao_por_hora[hora][segmento] = int(row['count'])

    df_dwell = df[df['dwell_s'] > 0]
    dwell_segmento_zona = df_dwell.groupby(['zone_id', 'gender', 'age_range'])['dwell_s'].mean().reset_index()
    
    dwell_por_zona = {}
    for _, row in dwell_segmento_zona.iterrows():
        zona = row['zone_id']
        segmento = f"{row['gender']}_{row['age_range']}"
        if zona not in dwell_por_zona:
            dwell_por_zona[zona] = {}
        dwell_por_zona[zona][segmento] = round(row['dwell_s'], 2)

    return {
        "distribuicao_por_hora": distribuicao_por_hora,
        "dwell_medio_por_segmento_e_zona": dwell_por_zona
    }

def calcular_anomalias(df: pd.DataFrame) -> list:
    """Deteta anomalias no Dia 7 usando a Regra dos 2 Sigmas sobre o histórico."""
    
    dias_ordenados = sorted(df['visit_date'].unique())
    if len(dias_ordenados) < 7:
        return [{"aviso": "Dataset com menos de 7 dias. Análise de anomalias ignorada."}]

    dia_7 = dias_ordenados[6]
    dias_historico = dias_ordenados[:6]

    df_hist = df[df['visit_date'].isin(dias_historico)]
    df_dia7 = df[df['visit_date'] == dia_7]

    trafego_hist = df_hist.groupby(['visit_date', 'hour_of_day', 'zone_id'])['person_id'].nunique().reset_index()
    stats_hist = trafego_hist.groupby(['hour_of_day', 'zone_id'])['person_id'].agg(['mean', 'std']).reset_index()
    stats_hist['std'] = stats_hist['std'].fillna(0)

    trafego_dia7 = df_dia7.groupby(['hour_of_day', 'zone_id'])['person_id'].nunique().reset_index()
    trafego_dia7.rename(columns={'person_id': 'visitantes_dia_7'}, inplace=True)

    analise = pd.merge(trafego_dia7, stats_hist, on=['hour_of_day', 'zone_id'], how='inner')
    anomalias = []
    
    for _, row in analise.iterrows():
        media = row['mean']
        desvio = row['std']
        valor_real = row['visitantes_dia_7']

        if desvio > 0 and abs(valor_real - media) > (2 * desvio):
            tipo = "Pico de Tráfego" if valor_real > media else "Queda de Tráfego"
            anomalias.append({
                "data": dia_7,
                "hora": f"{int(row['hour_of_day'])}h",
                "zona": row['zone_id'],
                "tipo_anomalia": tipo,
                "visitantes_reais": int(valor_real),
                "media_historica": round(media, 1),
                "desvio_padrao": round(desvio, 1)
            })

    return anomalias

if __name__ == "__main__":

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    caminho_input_default = os.path.join(root_dir, "output", "journeys.csv")
    caminho_output_default = os.path.join(root_dir, "output", "metrics.json")
    
    parser = argparse.ArgumentParser(description="Módulo 2: Retail Analytics (Pandas)")
    parser.add_argument("--input", type=str, default=caminho_input_default, help="Caminho para o journeys.csv")
    parser.add_argument("--output", type=str, default=caminho_output_default, help="Caminho para o metrics.json")
    args = parser.parse_args()

    print(f"A carregar trajetórias limpas de: {args.input}")
    
    try:
        df_journeys = pd.read_csv(args.input)
    except FileNotFoundError:
        print(f"[ERRO] Não encontrei o ficheiro {args.input}. Já executaste o stitcher.py?")
        exit(1)

    metrics_report = {}
    
    metrics_report["trafego"] = calcular_metricas_trafego(df_journeys)
    metrics_report["funil"] = calcular_funil_cliente(df_journeys)
    metrics_report["zonas"] = calcular_metricas_zonas(df_journeys)
    metrics_report["demografia"] = calcular_segmentacao(df_journeys)
    metrics_report["anomalias"] = calcular_anomalias(df_journeys)

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(metrics_report, f, indent=4, ensure_ascii=False)

    print(f"Todas as métricas foram calculadas e exportadas para {args.output}")