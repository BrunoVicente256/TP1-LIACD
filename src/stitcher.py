import csv
import json
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ==========================================
# 1. ESTRUTURAS DE DADOS E ESTADO
# ==========================================

@dataclass
class Trajetoria:
    traj_id: str
    gender: str
    age_range: str
    start_time: str
    end_time: Optional[str] = None
    status: str = "active"
    path: List[Dict] = field(default_factory=list)
    last_timestamp: Optional[datetime] = field(default=None, repr=False)

_id_counter = 0

def gerar_novo_id() -> str:
    global _id_counter
    _id_counter += 1
    return f"P_{_id_counter:06d}"

def entrada_na_loja(zone_id: str) -> bool:
    return zone_id in ["Z_E1", "Z_E2"]

def saida_da_loja(zone_id: str) -> bool:
    return zone_id in ["Z_E1", "Z_E2", "Z_CK", "Z_C1", "Z_C2", "Z_C3"]

def carregar_grafo_reverso(caminho_json: str) -> dict:
    grafo_reverso = {}
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    for source_zone, info_zona in dados.get('zones', {}).items():
        for dest_zone, walk_secs in info_zona.get('walk_seconds', {}).items():
            if dest_zone not in grafo_reverso:
                grafo_reverso[dest_zone] = {}
            grafo_reverso[dest_zone][source_zone] = walk_secs
    return grafo_reverso

def distancia_hamming(g1: str, a1: str, g2: str, a2: str) -> int:
    dist = 0
    if g1 != g2: dist += 1
    if a1 != a2: dist += 1
    return dist

# ==========================================
# 3. MOTOR PRINCIPAL (STREAM PROCESSING)
# ==========================================

def processar_stream_eventos(caminho_csv: str, zonas_grafo_reverso: dict, max_transit_time_s: int = 300):
    in_zone: Dict[tuple, deque] = {}
    in_transit: Dict[tuple, deque] = {}
    transit_timeout_queue = deque()  # Fila TTL (Time-To-Live) para garantir O(1) na limpeza
    
    trajetorias_completas: List[Trajetoria] = []
    trajetorias_incompletas: List[Trajetoria] = []

    with open(caminho_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            event_id, ts_str, zone_id, event_type, duration_s, gender, age_range = row
            current_time = datetime.fromisoformat(ts_str)
            duration_s = int(duration_s)

            # ---------------------------------------------------------
            # 1. GARBAGE COLLECTOR O(1) - Processar expirados no trânsito
            # ---------------------------------------------------------
            while transit_timeout_queue:
                tempo_zombie, zombie = transit_timeout_queue[0]
                if (current_time - tempo_zombie).total_seconds() > max_transit_time_s:
                    transit_timeout_queue.popleft()
                    # Só avaliamos se ele NÃO foi resgatado entretanto
                    if zombie.status == "in_transit":
                        zombie.end_time = zombie.last_timestamp.isoformat()
                        ultima_zona = zombie.path[-1]["zone_id"]
                        if saida_da_loja(ultima_zona):
                            zombie.status = "completed"
                            trajetorias_completas.append(zombie)
                        else:
                            zombie.status = "incomplete"
                            trajetorias_incompletas.append(zombie)
                else:
                    break

            # ---------------------------------------------------------
            # 2. PROCESSAR EVENTO ATUAL
            # ---------------------------------------------------------
            if event_type == 'entry':
                if entrada_na_loja(zone_id):
                    # Nasce da rua
                    nova_traj = Trajetoria(
                        traj_id=gerar_novo_id(), gender=gender, age_range=age_range, start_time=current_time.isoformat()
                    )
                    nova_traj.last_timestamp = current_time
                    nova_traj.path.append({"zone_id": zone_id, "entry_time": current_time.isoformat(), "total_linger_s": 0})

                    chave = (zone_id, gender, age_range)
                    if chave not in in_zone: in_zone[chave] = deque()
                    in_zone[chave].append(nova_traj)

                else:
                    candidato_encontrado = None
                    origens_possiveis = zonas_grafo_reverso.get(zone_id, {})
                    TOLERANCIA_S = 10

                    # --- FAST PATH ---
                    for source_zone, walk_seconds in origens_possiveis.items():
                        chave_transito = (source_zone, gender, age_range)
                        fila_transito = in_transit.get(chave_transito)

                        if fila_transito:
                            while fila_transito:
                                candidato = fila_transito[0]
                                if candidato.status != "in_transit":
                                    fila_transito.popleft()
                                    continue
                                
                                tempo_em_transito = (current_time - candidato.last_timestamp).total_seconds()
                                if tempo_em_transito >= (walk_seconds - TOLERANCIA_S):
                                    candidato_encontrado = fila_transito.popleft()
                                    break
                                else: break
                        if candidato_encontrado: break

                    # --- MEDIUM PATH ---
                    if not candidato_encontrado:
                        for source_zone, walk_seconds in origens_possiveis.items():
                            for chave_t, fila_t in list(in_transit.items()):
                                sz, g_t, a_t = chave_t
                                if sz == source_zone and distancia_hamming(gender, age_range, g_t, a_t) == 1:
                                    while fila_t:
                                        candidato = fila_t[0]
                                        if candidato.status != "in_transit":
                                            fila_t.popleft()
                                            continue
                                        
                                        tempo_em_transito = (current_time - candidato.last_timestamp).total_seconds()
                                        if (walk_seconds - TOLERANCIA_S) <= tempo_em_transito:
                                            candidato_encontrado = fila_t.popleft()
                                            candidato_encontrado.path.append({
                                                "demographic_alert": f"Câmara reportou {gender}/{age_range}, assumido como erro do sensor."
                                            })
                                            break
                                        else: break
                                    if candidato_encontrado: break
                            if candidato_encontrado: break

                    # --- SLOW PATH ---
                    if not candidato_encontrado:
                        for chave_transito, fila_transito in list(in_transit.items()):
                            sz, g, a = chave_transito
                            
                            # PROTEÇÃO ANTI-ROUBO: Não roubar quem já saiu pelas portas/caixas!
                            if saida_da_loja(sz): 
                                continue
                                
                            if g == gender and a == age_range:
                                while fila_transito:
                                    candidato = fila_transito[0]
                                    if candidato.status != "in_transit":
                                        fila_transito.popleft()
                                        continue
                                        
                                    tempo_em_transito = (current_time - candidato.last_timestamp).total_seconds()
                                    if tempo_em_transito >= 0:
                                        candidato_encontrado = fila_transito.popleft()
                                        candidato_encontrado.path.append({
                                            "topology_alert": f"Cortou caminho de {sz} para {zone_id}"
                                        })
                                        break
                                if candidato_encontrado: break

                    # --- ATUALIZAR ESTADO ---
                    if candidato_encontrado:
                        candidato_encontrado.status = "active" # Ressuscita!
                        candidato_encontrado.last_timestamp = current_time
                        candidato_encontrado.path.append({"zone_id": zone_id, "entry_time": current_time.isoformat(), "total_linger_s": 0})
                        chave = (zone_id, candidato_encontrado.gender, candidato_encontrado.age_range)
                        if chave not in in_zone: in_zone[chave] = deque()
                        in_zone[chave].append(candidato_encontrado)
                    else:
                        nova_traj = Trajetoria(
                            traj_id=f"{gerar_novo_id()}_anomaly", gender=gender, age_range=age_range, start_time=current_time.isoformat()
                        )
                        nova_traj.last_timestamp = current_time
                        nova_traj.path.append({"zone_id": zone_id, "entry_time": current_time.isoformat(), "total_linger_s": 0})
                        chave = (zone_id, gender, age_range)
                        if chave not in in_zone: in_zone[chave] = deque()
                        in_zone[chave].append(nova_traj)

            elif event_type == 'linger':
                chave_zona = (zone_id, gender, age_range)
                fila_zona = in_zone.get(chave_zona)
                if fila_zona and len(fila_zona) > 0:
                    candidato = fila_zona[0]
                    candidato.last_timestamp = current_time
                    candidato.path[-1]["total_linger_s"] += duration_s
                else:
                    candidato_fuzzy = None
                    for chave_z, fila_z in in_zone.items():
                        z, g_z, a_z = chave_z
                        if z == zone_id and distancia_hamming(gender, age_range, g_z, a_z) == 1 and fila_z:
                            candidato_fuzzy = fila_z[0]
                            break

                    if candidato_fuzzy:
                        candidato_fuzzy.last_timestamp = current_time
                        candidato_fuzzy.path[-1]["total_linger_s"] += duration_s
                    else:
                        nova_anomalia = Trajetoria(
                            traj_id=f"{gerar_novo_id()}_phantom", gender=gender, age_range=age_range,
                            start_time=current_time.isoformat(), status="incomplete"
                        )
                        nova_anomalia.path.append({
                            "zone_id": zone_id, "entry_time": "unknown", "total_linger_s": duration_s, "note": "Linger detected without Entry"
                        })
                        trajetorias_incompletas.append(nova_anomalia)

            elif event_type == 'exit':
                chave_zona = (zone_id, gender, age_range)
                fila_zona = in_zone.get(chave_zona)

                if not fila_zona or len(fila_zona) == 0:
                    for chave_z, fila_z in in_zone.items():
                        z, g_z, a_z = chave_z
                        if z == zone_id and distancia_hamming(gender, age_range, g_z, a_z) == 1 and fila_z:
                            fila_zona = fila_z
                            break

                if fila_zona and len(fila_zona) > 0:
                    cliente = fila_zona.popleft()
                    cliente.last_timestamp = current_time
                    cliente.path[-1]["exit_time"] = current_time.isoformat()

                    cliente.status = "in_transit"
                    chave_transito = (zone_id, cliente.gender, cliente.age_range)
                    if chave_transito not in in_transit: in_transit[chave_transito] = deque()
                    in_transit[chave_transito].append(cliente)
                    
                    # Adiciona à fila de TTL (Time-To-Live) para garantir que expira passados 300s
                    transit_timeout_queue.append((current_time, cliente))

    # ACTIVE SWEEP FINAL (Limpar quem ficou na loja na hora de fecho)
    for fila in in_zone.values():
        while fila:
            cliente = fila.popleft()
            if cliente.status == "active":
                cliente.end_time = cliente.last_timestamp.isoformat()
                ultima_zona = cliente.path[-1]["zone_id"]
                if saida_da_loja(ultima_zona):
                    cliente.status = "completed"
                    trajetorias_completas.append(cliente)
                else:
                    cliente.status = "incomplete"
                    trajetorias_incompletas.append(cliente)

    while transit_timeout_queue:
        _, cliente = transit_timeout_queue.popleft()
        if cliente.status == "in_transit":
            cliente.end_time = cliente.last_timestamp.isoformat()
            ultima_zona = cliente.path[-1]["zone_id"]
            if saida_da_loja(ultima_zona):
                cliente.status = "completed"
                trajetorias_completas.append(cliente)
            else:
                cliente.status = "incomplete"
                trajetorias_incompletas.append(cliente)

    return trajetorias_completas, trajetorias_incompletas

# ==========================================
# 4. PÓS-PROCESSAMENTO E EXPORTAÇÃO
# ==========================================

def sanitizar_trajetorias(trajetorias: List[Trajetoria]) -> List[Trajetoria]:
    for traj in trajetorias:
        traj.path = [block for block in traj.path if 'zone_id' in block]
        if not traj.path: continue

        path_debounced = []
        i = 0
        n = len(traj.path)
        while i < n:
            if i <= n - 3:
                zona_A1, zona_B, zona_A2 = traj.path[i], traj.path[i+1], traj.path[i+2]
                if zona_A1['zone_id'] == zona_A2['zone_id'] and zona_B.get('total_linger_s', 0) < 5:
                    bloco_fundido = {
                        "zone_id": zona_A1['zone_id'],
                        "entry_time": zona_A1['entry_time'],
                        "exit_time": zona_A2.get('exit_time', zona_A2.get('entry_time')),
                        "total_linger_s": zona_A1.get('total_linger_s', 0) + zona_B.get('total_linger_s', 0) + zona_A2.get('total_linger_s', 0)
                    }
                    path_debounced.append(bloco_fundido)
                    i += 3
                    continue
            path_debounced.append(traj.path[i])
            i += 1

        path_limpo = []
        for bloco in path_debounced:
            zona = bloco['zone_id']
            if entrada_na_loja(zona) or saida_da_loja(zona):
                path_limpo.append(bloco)
                continue

            tempo_total_s = 0
            if 'exit_time' in bloco and bloco['exit_time'] != 'unknown':
                try:
                    entry_dt = datetime.fromisoformat(bloco['entry_time'])
                    exit_dt = datetime.fromisoformat(bloco['exit_time'])
                    tempo_total_s = (exit_dt - entry_dt).total_seconds()
                except ValueError: pass
            else:
                tempo_total_s = bloco.get('total_linger_s', 0)

            if tempo_total_s >= 3 or len(path_debounced) == 1:
                path_limpo.append(bloco)

        traj.path = path_limpo
    return trajetorias

def exportar_journeys_csv(trajetorias: List[Trajetoria], filepath: str = "journeys.csv"):
    print(f"A exportar dados para {filepath} (Formato Longo)...")
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["person_id", "zone_id", "entry_time", "exit_time", "dwell_s", "gender", "age_range", "visit_date", "hour_of_day"])

        for traj in trajetorias:
            for bloco in traj.path:
                if "zone_id" not in bloco or "entry_time" not in bloco or bloco["entry_time"] == "unknown": continue

                try:
                    dt_entry = datetime.fromisoformat(bloco["entry_time"])
                    visit_date = dt_entry.strftime("%Y-%m-%d")
                    hour_of_day = dt_entry.hour
                except ValueError: continue

                writer.writerow([
                    traj.traj_id, bloco["zone_id"], bloco["entry_time"],
                    bloco.get("exit_time", ""), bloco.get("total_linger_s", 0),
                    traj.gender, traj.age_range, visit_date, hour_of_day
                ])

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    import time
    import argparse
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    caminho_events = os.path.join(root_dir, "data", "events.csv")
    caminho_zones = os.path.join(root_dir, "data", "zones.json")
    caminho_output = os.path.join(root_dir, "output", "journeys.csv")

    parser = argparse.ArgumentParser(description="Módulo 1: Reconstrução de Trajetórias (Stitching)")
    parser.add_argument("--input", type=str, default=caminho_events)
    parser.add_argument("--zones", type=str, default=caminho_zones)
    parser.add_argument("--output", type=str, default=caminho_output)
    args = parser.parse_args()
    start_time = time.time()

    try:
        grafo = carregar_grafo_reverso(args.zones)
    except FileNotFoundError:
        print(f"\n[ERRO] Não encontrei o ficheiro zones.json no caminho: {args.zones}")
        exit(1)

    try:
        completas, incompletas = processar_stream_eventos(args.input, grafo)
    except FileNotFoundError:
        print(f"\n[ERRO] Não encontrei o ficheiro events.csv no caminho: {args.input}")
        exit(1)

    completas = sanitizar_trajetorias(completas)
    incompletas = sanitizar_trajetorias(incompletas)

    exec_time = time.time() - start_time

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    exportar_journeys_csv(completas, args.output)

    print(f"\nRESULTADOS DA FASE 1 (STITCHING):")
    print(f"Tempo de processamento: {exec_time:.2f} segundos")
    print(f"Trajetórias Completas: {len(completas)}")
    print(f"Trajetórias Incompletas/Anomalias: {len(incompletas)}")

    # Guardar estatísticas de saúde para o relatório final
    stats_path = os.path.join(root_dir, "output", "stitching_stats.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump({
            "trajetorias_sucesso": len(completas),
            "trajetorias_anomalas": len(incompletas),
            "taxa_integridade": round((len(completas) / (len(completas) + len(incompletas))) * 100, 2)
        }, f, indent=4)