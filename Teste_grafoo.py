import math
import random
from copy import deepcopy
import itertools
import time
import networkx as nx
import matplotlib.pyplot as plt

# --- CLASSES ---

class Cliente:
    def __init__(self, id, x, y, demanda):
        self.id = id
        self.x = x
        self.y = y
        self.demanda = demanda


class Caminhao:
    def __init__(self, id, capacidade):
        self.id = id
        self.capacidade = capacidade
        self.rota = []
        self.distancia_percorrida = 0.0
        self.relatorio_entregas = []
        self.retornos_deposito = 0


# --- MAPA DE RUAS (GRID) ---

def construir_mapa_ruas(tamanho=100, passo=10):
    G = nx.Graph()
    
    # Criar nós do grid
    for x in range(0, tamanho + 1, passo):
        for y in range(0, tamanho + 1, passo):
            G.add_node((x, y), pos=(x, y))
    
    # Criar ruas horizontais e verticais
    for x in range(0, tamanho + 1, passo):
        for y in range(0, tamanho + 1, passo):

            if x + passo <= tamanho:
                G.add_edge((x, y), (x + passo, y), weight=passo)

            if y + passo <= tamanho:
                G.add_edge((x, y), (x, y + passo), weight=passo)

    return G


# --- UTILITÁRIOS PARA DISTÂNCIAS (CACHE) ---

def mapear_pontos_para_nos(G_ruas, pontos):
    """
    Retorna dicionário {id_cliente: nó_mais_próximo} para cada ponto em 'pontos'.
    Pontos deve incluir o depósito (id -1) e todos os clientes.
    """
    mapeamento = {}
    nos = list(G_ruas.nodes())
    for p in pontos:
        melhor = None
        melhor_d = float('inf')
        for n in nos:
            d = math.hypot(p.x - n[0], p.y - n[1])
            if d < melhor_d:
                melhor_d = d
                melhor = n
        mapeamento[p.id] = melhor
    return mapeamento


def construir_matriz_distancias(G_ruas, pontos, mapeamento):
    """
    Constrói matriz (dict de dicts) dist[id_a][id_b] com distâncias de rua
    entre os nós mapeados de cada ponto.
    """
    ids = [p.id for p in pontos]

    # Rodar dijkstra uma vez por nó de origem único
    dists_por_no = {}
    nos_origem = set(mapeamento.values())

    for no in nos_origem:
        dists_por_no[no] = nx.single_source_dijkstra_path_length(G_ruas, no, weight='weight')

    matriz = {i: {} for i in ids}
    for a, b in itertools.product(ids, ids):
        na = mapeamento[a]
        nb = mapeamento[b]
        matriz[a][b] = dists_por_no[na].get(nb, float('inf'))

    return matriz


# --- DISTÂNCIA (compatibilidade com código original) ---
# Nota: a função antiga distancia(a,b) usa G_RUAS global; aqui usaremos matriz quando possível.
G_RUAS = None
DIST_MATRIX = None
MAPEAMENTO = None


def distancia(a, b):
    """Compatibilidade: se DIST_MATRIX configurada, usa ela; senão, calcula via grafo."""
    global DIST_MATRIX, G_RUAS
    if DIST_MATRIX is not None:
        return DIST_MATRIX[a.id][b.id]
    else:
        # fallback lento: usar o método original
        na = no_mais_proximo(G_RUAS, a)
        nb = no_mais_proximo(G_RUAS, b)
        try:
            return nx.shortest_path_length(G_RUAS, na, nb, weight='weight')
        except:
            return float('inf')


def no_mais_proximo(G_ruas, cliente):
    cx, cy = cliente.x, cliente.y
    melhor = None
    dist = float("inf")

    for (x, y) in G_ruas.nodes():
        d = math.hypot(cx - x, cy - y)
        if d < dist:
            dist = d
            melhor = (x, y)

    return melhor


# --- INSTÂNCIAS ---

def gerar_instancia_manual():
    num_clientes = int(input("Quantos clientes? "))
    num_caminhoes = int(input("Quantos caminhões? "))

    deposito_x = float(input("Coordenada X do depósito: "))
    deposito_y = float(input("Coordenada Y do depósito: "))
    deposito = Cliente(-1, deposito_x, deposito_y, 0)

    clientes = []
    for i in range(num_clientes):
        x = float(input(f"Cliente {i} - X: "))
        y = float(input(f"Cliente {i} - Y: "))
        d = float(input(f"Cliente {i} - Demanda: "))
        clientes.append(Cliente(i, x, y, d))

    caminhoes = []
    for k in range(num_caminhoes):
        cap = float(input(f"Capacidade do caminhão {k}: "))
        caminhoes.append(Caminhao(k, cap))

    return deposito, clientes, caminhoes


def gerar_instancia_aleatoria(n=12, k=3, area=100, demanda_max=40, seed=None):
    rng = random.Random(seed)
    deposito = Cliente(-1, area/2, area/2, 0)
    clientes = [
        Cliente(i, rng.uniform(0, area), rng.uniform(0, area), rng.uniform(5, demanda_max))
        for i in range(n)
    ]
    caminhoes = [
        Caminhao(j, rng.choice([100.0, 120.0, 150.0])) for j in range(k)
    ]
    return deposito, clientes, caminhoes


# --- DISTRIBUIÇÃO INICIAL ---

def distribuir_clientes_balanceado(clientes, caminhoes):
    cargas = [0.0 for _ in caminhoes]
    listas = [[] for _ in caminhoes]

    clientes_sorted = sorted(clientes, key=lambda c: c.demanda, reverse=True)

    for c in clientes_sorted:
        idx = min(range(len(caminhoes)), key=lambda i: cargas[i])
        listas[idx].append(c)
        cargas[idx] += c.demanda

    for i, tr in enumerate(caminhoes):
        tr.rota = listas[i][:]

    return caminhoes


# --- SIMULAÇÃO POR CAMINHÃO (usa distancia function) ---

def simular_entregas_caminhao(cam, deposito):
    demandas = {c.id: c.demanda for c in cam.rota}
    pos = deposito
    carga = cam.capacidade

    distancia_total = 0
    eventos = []
    retornos = 0

    for cliente in cam.rota:

        while demandas[cliente.id] > 0:

            if carga <= 0:
                distancia_total += distancia(pos, deposito)
                pos = deposito
                carga = cam.capacidade
                retornos += 1
                eventos.append(("retorno_sem_carga", cliente.id))

            distancia_total += distancia(pos, cliente)
            pos = cliente

            if carga >= demandas[cliente.id]:
                entregue = demandas[cliente.id]
                carga -= entregue
                demandas[cliente.id] = 0
                eventos.append(("entrega_total", cliente.id, entregue))

            else:
                entregue = carga
                demandas[cliente.id] -= entregue
                carga = 0
                eventos.append(("entrega_parcial", cliente.id, entregue, demandas[cliente.id]))

    distancia_total += distancia(pos, deposito)

    cam.distancia_percorrida = distancia_total
    cam.relatorio_entregas = eventos
    cam.retornos_deposito = retornos

    return distancia_total


def avaliar_solucao(caminhoes, deposito):
    total = 0
    for tr in caminhoes:
        total += simular_entregas_caminhao(tr, deposito)
    return total


# --- VIZINHANÇA MELHORADA ---

def gerar_vizinho_amplo(caminhoes, rng):
    novo = deepcopy(caminhoes)

    ops = ['intraswap', 'interchange', 'relocate', 'twoopt']
    op = rng.choice(ops)

    non_empty = [i for i, t in enumerate(novo) if len(t.rota) >= 1]
    if not non_empty:
        return novo

    if op == 'intraswap':
        k = rng.choice(non_empty)
        rota = novo[k].rota
        if len(rota) >= 2:
            i, j = rng.sample(range(len(rota)), 2)
            rota[i], rota[j] = rota[j], rota[i]

    elif op == 'interchange':
        if len(novo) >= 2:
            a, b = rng.sample(range(len(novo)), 2)
            if novo[a].rota and novo[b].rota:
                i = rng.randrange(len(novo[a].rota))
                j = rng.randrange(len(novo[b].rota))
                novo[a].rota[i], novo[b].rota[j] = novo[b].rota[j], novo[a].rota[i]

    elif op == 'relocate':
        a = rng.choice(range(len(novo)))
        if novo[a].rota:
            i = rng.randrange(len(novo[a].rota))
            cliente = novo[a].rota.pop(i)
            b = rng.choice(range(len(novo)))
            insert_pos = rng.randrange(len(novo[b].rota)+1)
            novo[b].rota.insert(insert_pos, cliente)

    elif op == 'twoopt':
        idxs = [i for i,t in enumerate(novo) if len(t.rota) >= 3]
        if idxs:
            idx = rng.choice(idxs)
            rota = novo[idx].rota
            i = rng.randrange(0, len(rota)-2)
            j = rng.randrange(i+1, len(rota))
            rota[i:j+1] = list(reversed(rota[i:j+1]))

    return novo


# --- SIMULATED ANNEALING USANDO MATRIZ DE DISTÂNCIAS ---

def simulated_annealing_melhorado(caminhoes, deposito, dist_matrix, seed=None,
                                 temp0=100.0, alpha=0.995, n_iter=2000):
    rng = random.Random(seed)

    atual = deepcopy(caminhoes)
    melhor = deepcopy(caminhoes)

    def avaliar_local(sol):
        total = 0.0
        for tr in sol:
            demandas = {c.id: c.demanda for c in tr.rota}
            carga = tr.capacidade
            pos_id = deposito.id
            for cliente in tr.rota:
                while demandas[cliente.id] > 0:
                    if carga <= 0:
                        total += dist_matrix[pos_id][deposito.id]
                        pos_id = deposito.id
                        carga = tr.capacidade
                    total += dist_matrix[pos_id][cliente.id]
                    pos_id = cliente.id
                    if carga >= demandas[cliente.id]:
                        carga -= demandas[cliente.id]
                        demandas[cliente.id] = 0
                    else:
                        demandas[cliente.id] -= carga
                        carga = 0
            total += dist_matrix[pos_id][deposito.id]
        return total

    val_atual = avaliar_local(atual)
    val_melhor = val_atual

    temp = temp0
    start = time.time()
    for it in range(n_iter):
        viz = gerar_vizinho_amplo(atual, rng)
        val_viz = avaliar_local(viz)
        delta = val_viz - val_atual

        accept = False
        if delta < 0:
            accept = True
        else:
            p = math.exp(-delta / temp) if temp > 1e-12 else 0.0
            if rng.random() < p:
                accept = True

        if accept:
            atual = viz
            val_atual = val_viz
            if val_viz < val_melhor:
                melhor = deepcopy(viz)
                val_melhor = val_viz

        temp *= alpha

        # pequeno "reheating" ocasional
        if it % 500 == 0 and it > 0:
            temp = max(temp, temp0 * 0.1)

    duration = time.time() - start

    # atualizar metadata de distancia_percorrida para a solução final
    for tr in melhor:
        tr.distancia_percorrida = 0.0
        pos_id = deposito.id
        demandas = {c.id: c.demanda for c in tr.rota}
        carga = tr.capacidade
        for cliente in tr.rota:
            while demandas[cliente.id] > 0:
                if carga <= 0:
                    tr.distancia_percorrida += dist_matrix[pos_id][deposito.id]
                    pos_id = deposito.id
                    carga = tr.capacidade
                tr.distancia_percorrida += dist_matrix[pos_id][cliente.id]
                pos_id = cliente.id
                if carga >= demandas[cliente.id]:
                    carga -= demandas[cliente.id]
                    demandas[cliente.id] = 0
                else:
                    demandas[cliente.id] -= carga
                    carga = 0
        tr.distancia_percorrida += dist_matrix[pos_id][deposito.id]

    return melhor, val_melhor, duration


# --- PLOTAGEM: desenha rotas seguindo os nós do grafo ---

def plotar_grafo_rotas_melhor(G, caminhoes, deposito, MAPEAMENTO):
    plt.figure(figsize=(10, 10))

    # Usar o atributo correto dos nós
    pos = {n: G.nodes[n]['pos'] for n in G.nodes()}

    # Desenha o grid de ruas
    nx.draw(G, pos, node_size=20, node_color='lightgray', edge_color='gray', alpha=0.5)

    # Plota depósito
    plt.scatter(deposito.x, deposito.y, c='black', s=200, zorder=5)
    plt.text(deposito.x + 1, deposito.y + 1, "Depósito", fontsize=12)

    cores = ['red', 'green', 'orange', 'blue', 'purple']

    for tr in caminhoes:
        cor = cores[tr.id % len(cores)]

        atual = deposito
        for prox in tr.rota + [deposito]:

            n1 = MAPEAMENTO[atual.id]
            n2 = MAPEAMENTO[prox.id]

            # Caminho sobre o grafo REAL
            path = nx.shortest_path(G, n1, n2, weight='weight')

            # Extrai coordenadas corretas
            xs = [G.nodes[n]['pos'][0] for n in path]
            ys = [G.nodes[n]['pos'][1] for n in path]

            # Agora as linhas seguem as arestas EXATAMENTE
            plt.plot(xs, ys, color=cor, linewidth=3, zorder=4)

            atual = prox

        for c in tr.rota:
            plt.scatter(c.x, c.y, s=80, zorder=5)
            plt.text(c.x + 1, c.y + 1, str(c.id), fontsize=12)

    plt.show()


# --- MAIN ---

def main():
    global G_RUAS, DIST_MATRIX, MAPEAMENTO

    # Construir mapa
    G_RUAS = construir_mapa_ruas(tamanho=100, passo=10)

    modo = input("Modo manual (m) ou aleatório (a)? [a]: ").strip().lower() or 'a'

    if modo == 'm':
        deposito, clientes, caminhoes = gerar_instancia_manual()
    else:
        deposito, clientes, caminhoes = gerar_instancia_aleatoria(n=12, k=3, area=100, demanda_max=40)

    caminhoes = distribuir_clientes_balanceado(clientes, caminhoes)

    print("Distribuição inicial:")
    for tr in caminhoes:
        print(f"Caminhão {tr.id}: {[c.id for c in tr.rota]}")

    # Precomputar mapeamento e matriz de distâncias
    pontos = [deposito] + clientes
    MAPEAMENTO = mapear_pontos_para_nos(G_RUAS, pontos)
    DIST_MATRIX = construir_matriz_distancias(G_RUAS, pontos, MAPEAMENTO)

    # Executar Simulated Annealing
    melhor, custo, dur = simulated_annealing_melhorado(caminhoes, deposito, DIST_MATRIX,
                                                       seed=42, temp0=120.0, alpha=0.995, n_iter=3000)

    print(f"Melhor custo encontrado: {custo:.2f}  (tempo: {dur:.2f}s)")
    for tr in melhor:
        print(f"Caminhão {tr.id} - DistPercorrida (estimada): {tr.distancia_percorrida:.2f} - rota: {[c.id for c in tr.rota]}")

    # Plotar solução
    plotar_grafo_rotas_melhor(G_RUAS, melhor, deposito, MAPEAMENTO)


if __name__ == '__main__':
    main()
