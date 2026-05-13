import os
import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def mapa_loja(caminho_json, caminho_output_img):
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    G = nx.Graph()

    zonas = dados.get('zones', {})
    for zone_id, info in zonas.items():
        tipo = info.get('type', 'unknown')
        G.add_node(zone_id, tipo=tipo)

        for adj in info.get('adjacent', []):
            G.add_edge(zone_id, adj)
            
    cores_nos = []
    for node in G.nodes():
        tipo = G.nodes[node].get('tipo', '')
        if tipo == 'entrance': cores_nos.append('lightgreen')
        elif tipo == 'checkout': cores_nos.append('gold')
        elif tipo == 'checkout_exit': cores_nos.append('salmon')
        elif tipo == 'navigation': cores_nos.append('lightblue')
        elif tipo == 'product_section': cores_nos.append('mediumpurple')
        else: cores_nos.append('lightgray')

    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(G, k=0.5, seed=42)

    nx.draw(G, pos,
            with_labels=True,
            node_color=cores_nos,
            node_size=2500,
            font_size=10,
            font_weight='bold',
            edge_color='gray',
            linewidths=1,
            edgecolors='black')

    plt.title("Topologia da Loja (Baseada no zones.json)", fontsize=16)

    tipos_legenda = {
        'Entrada': 'lightgreen', 
        'Caixas (Checkout)': 'gold', 
        'Saída de Caixas': 'salmon',
        'Corredores de Navegação': 'lightblue',
        'Secções de Produtos': 'mediumpurple'
    }
    handles = [mpatches.Patch(color=cor, label=label) for label, cor in tipos_legenda.items()]
    plt.legend(handles=handles, loc='upper left', bbox_to_anchor=(1, 1), title="Tipos de Zona")
    
    plt.tight_layout()
    
    plt.savefig(caminho_output_img, dpi=300, bbox_inches='tight')
    
    plt.show()

if __name__ == "__main__":
    import argparse
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir) if os.path.basename(script_dir) == 'src' else script_dir
        
    caminho_zones_default = os.path.join(root_dir, "data", "zones.json")
    caminho_img_default = os.path.join(root_dir, "output", "topologia_loja.png")

    parser = argparse.ArgumentParser(description="Módulo Extra: Visualização da Topologia")
    parser.add_argument("--input", type=str, default=caminho_zones_default, help="Caminho para o zones.json")
    parser.add_argument("--output", type=str, default=caminho_img_default, help="Caminho de saída da imagem")
    args = parser.parse_args()
        
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
    mapa_loja(args.input, args.output)