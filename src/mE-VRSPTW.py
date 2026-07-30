from pydoc import cli
import gurobipy as gp
from gurobipy import GRB
import xml.etree.ElementTree as ET
from logging import root
import os
import math
from collections import defaultdict
import heapq
import networkx as nx

# Construcción del grafo de incompatibilidad considerando ventanas de tiempo
def grafo_incompatibilidad(clientes, ventanas, tiempos, indices):
    incompatibilidad = {i: set() for i in clientes}

    for i in clientes:
        for j in clientes:
            if i >= j:  # evita comparar el mismo par dos veces
                continue

            # ¿se puede ir de i a j respetando ventana de j?
            puede_ij = False
            if (i, j) in indices:
                for k in indices[(i, j)]:
                    if ventanas[i][0] + tiempos[i, j, k] <= ventanas[j][1]:
                        puede_ij = True
                        break  # con uno que cumpla es suficiente

            # ¿se puede ir de j a i respetando ventana de i?
            puede_ji = False
            if (j, i) in indices:
                for k in indices[(j, i)]:
                    if ventanas[j][0] + tiempos[j, i, k] <= ventanas[i][1]:
                        puede_ji = True
                        break

            # incompatibles si no se pueden visitar en ningún orden
            if not puede_ij and not puede_ji:
                incompatibilidad[i].add(j)
                incompatibilidad[j].add(i)

    return incompatibilidad

# Función para calcular la arborescencia de peso mínimo con raíz automática
def arborescencia_minima(aristas, nodos_reales, peso_ficticio=10**9):
    """
    Calcula la arborescencia de peso mínimo eligiendo
    automáticamente la raíz óptima mediante un nodo ficticio.

    Estrategia:
        - Se añade nodo ficticio -2 con aristas hacia todos los
          nodos reales con peso muy alto (peso_ficticio).
        - El algoritmo de Edmonds elige automáticamente qué nodo
          real usar como raíz (el que minimiza el costo total).
        - Se descarta la arista ficticia del resultado final.

    Parámetros:
        aristas        : lista de (u, v, peso)
        nodos_reales   : conjunto de nodos reales
        peso_ficticio  : peso de aristas del nodo ficticio

    Retorna:
        raiz           : nodo raíz elegido automáticamente
        peso_total     : suma de pesos de la arborescencia
        aristas_sol    : lista de (u, v, peso) de la arborescencia
    """
    NODO_FICTICIO = -2

    # Construir grafo dirigido
    G = nx.DiGraph()
    G.add_nodes_from(nodos_reales) 
    for u, v, w in aristas:
        # Conservar solo la arista de menor peso entre cada par
        if G.has_edge(u, v):
            if w < G[u][v]['weight']:
                G[u][v]['weight'] = w
        else:
            G.add_edge(u, v, weight=w)

    # Añadir aristas desde nodo ficticio hacia todos
    for v in nodos_reales:
        G.add_edge(NODO_FICTICIO, v, weight=peso_ficticio)

    # Ejecutar algoritmo de Edmonds
    T = nx.minimum_spanning_arborescence(G)

    # Separar arista ficticia (indica la raíz elegida)
    aristas_ficticias = [(u, v) for u, v in T.edges() if u == NODO_FICTICIO]
    aristas_reales    = [
        (u, v, T[u][v]['weight'])
        for u, v in T.edges()
        if u != NODO_FICTICIO
    ]

    raiz       = aristas_ficticias[0][1] if aristas_ficticias else None
    peso_total = sum(w for _, _, w in aristas_reales)

    return raiz, peso_total, aristas_reales

# Función de Bron-Kerbosch con pivote para encontrar cliques máximas
def bron_kerbosch_pivot(grafo, R, P, X, cliques):
    if not P and not X:
        cliques.append(R)
        return

    # elegir pivote: el nodo de P∪X con más vecinos en P
    u = max(P | X, key=lambda v: len(grafo[v] & P))

    # solo expandir nodos que NO son vecinos del pivote
    for v in list(P - grafo[u]):
        bron_kerbosch_pivot(
            grafo,
            R | {v},
            P & grafo[v],
            X & grafo[v],
            cliques
        )
        P.remove(v)
        X.add(v)

# Función para encontrar todas las cliques máximas en un grafo
def cliques_maximas(grafo):
    cliques = []
    bron_kerbosch_pivot(
        grafo,
        R=set(),
        P=set(grafo.keys()),
        X=set(),
        cliques=cliques
    )
    return cliques

# Función para calcular el ángulo polar de un cliente respecto al depósito
def angulo_polar(deposito, cliente):
    dx = cliente[0] - deposito[0]
    dy = cliente[1] - deposito[1]
    angulo = math.atan2(dy, dx)
    # convertir a [0, 2π]
    return angulo % (2 * math.pi)

# Función de barrido (sweep) para generar rutas violadoras de capacidad
def sweep(deposito, clientes, demandas, capacidad, alpha):
    orden = sorted(
        clientes.keys(),
        key=lambda c: angulo_polar(deposito, clientes[c])
    )

    rutas = []
    n = len(orden)

    for inicio in range(n):
        ruta_actual = []
        carga_actual = 0
        visitados = set()

        for i in range(n):
            cliente = orden[(inicio + i) % n]

            if cliente in visitados:
                break

            demanda = demandas[cliente]

            if carga_actual + demanda <= capacidad * alpha:
                # cliente entra normalmente
                ruta_actual.append(cliente)
                carga_actual += demanda
                visitados.add(cliente)

            else:
                # violador se agrega al final de la ruta actual
                ruta_actual.append(cliente)
                carga_actual += demanda
                visitados.add(cliente)

                rutas.append((ruta_actual,math.ceil(carga_actual / capacidad)))

                # nueva ruta empieza vacía
                # el siguiente cliente del for la inicializa
                ruta_actual = []
                carga_actual = 0

        # última ruta
        if ruta_actual:
            rutas.append((ruta_actual,math.ceil(carga_actual / capacidad)))

    return rutas

# Función de barrido (sweep) para generar rutas violadoras de incompatibilidad de ventanas de tiempo
def sweep_con_incompatibilidad_clique(deposito, clientes, cliques, m_tamanio_clique):
    orden = sorted(
        clientes.keys(),
        key=lambda c: angulo_polar(deposito, clientes[c])
    )

    rutas = []
    n = len(orden)

    for inicio in range(n):
        ruta_actual = set()
        visitados = set()

        for i in range(n):
            cliente = orden[(inicio + i) % n]

            if cliente in visitados:
                break

            ruta_actual.add(cliente)
            visitados.add(cliente)
            ruta_set = set(ruta_actual)

            # cuenta cuántos miembros de cada clique están en la ruta
            clique_disparador = next(
                (clique for clique in cliques
                 if len(clique & ruta_set) >= m_tamanio_clique),
                None
            )

            if clique_disparador:
                #agregar la intersección de la ruta con el clique disparador como una nueva ruta si no está ya en las rutas
                rutas.append((
                    list(ruta_set&clique_disparador),
                    len(ruta_actual & clique_disparador)
                    ))
                ruta_actual = set()

        if ruta_actual:
            rutas.append((
                list(ruta_actual),
                1
            ))
    
    #eliminar rutas repetidas
    rutas_unicas = []
    for r in rutas:
        if r not in rutas_unicas:
            rutas_unicas.append(r)

    return rutas_unicas

# Funciones auxiliares para leer datos del archivo XML
def get_int(parent, tag, default=0):
    if parent is None:
        return default
    value = parent.findtext(tag)
    return int(value) if value is not None else default

def get_float(parent, tag, default=0.0):
    if parent is None:
        return default
    value = parent.findtext(tag)
    return float(value) if value is not None else default

# Función para leer la instancia desde un archivo XML
def read_instance(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # =====================================================
    # INFO
    # =====================================================
    info_xml = root.find("info")

    info = {
    "num_chargers": get_int(info_xml, "num_chargers"),
    "num_arcs": get_int(info_xml, "num_arcs"),
    "two_alternative_pairs": get_int(info_xml, "two_alternative_pairs"),
    "avg_alternatives": get_float(info_xml, "avg_alternatives"),}

    # =====================================================
    # NODES
    # =====================================================
    nodes = {}
    for node in root.find("network/nodes").findall("node"):
        node_id = int(node.get("id"))
        nodes[node_id] = {
            "type": int(node.get("type")),   # 0 = depot, 1 = customer
            "x": float(node.findtext("cx")),
            "y": float(node.findtext("cy")),
            "load": int(node.findtext("load")),
            "tw_start": int(node.find("tw/start").text),
            "tw_end": int(node.find("tw/end").text),
        }

    # =====================================================
    # LINKS / ARCS
    # =====================================================
    arcs = {}
    for link in root.find("network/links").findall("link"):
        tail = int(link.get("tail"))
        head = int(link.get("head"))
        id = int(link.get("id"))
                 
        custom = link.find("custom")

        arcs[(tail, head,id)] = {
            "travel_cost": int(link.findtext("travel_cost")),
            "travel_time": int(link.findtext("travel_time")),
            "energy_consumption": int(custom.findtext("energy_consumption")),
            "min_cost": int(custom.findtext("min_cost")),
            "min_time": int(custom.findtext("min_time")),
            "min_energy": int(custom.findtext("min_energy")),
            "is_min_cost": custom.findtext("is_min_cost") == "true",
        }

    # =====================================================
    # FLEET
    # =====================================================
    vehicle = root.find("fleet/vehicle_profile")

    charging_function = []
    for bp in vehicle.find("custom/charging_function").findall("breakpoint"):
        charging_function.append({
            "energy_level": int(bp.findtext("energy_level")),
            "rate": float(bp.findtext("recharging_rate")),
        })

    inverse_charging = {}
    for item in vehicle.find("custom/inverse_recharging_function").findall("breakpoint"):
        inverse_charging[int(item.findtext("periods"))] = int(
            item.findtext("energy_level")
        )

    fleet = {
        "departure_node": int(vehicle.findtext("departure_node")),
        "arrival_node": int(vehicle.findtext("arrival_node")),
        "capacity": int(vehicle.findtext("capacity")),
        "energy_capacity": int(vehicle.find("custom/energy_capacity").text),
        "first_charging_period": int(vehicle.find("custom/first_charging_period").text),
        "last_charging_period": int(vehicle.find("custom/last_charging_period").text),
        "charging_function": charging_function,
        "inverse_recharging_function": inverse_charging,
    }

    # =====================================================
    # REQUESTS
    # =====================================================
    requests = {}
    for req in root.find("requests").findall("request"):
        req_id = int(req.get("id"))
        node_id = int(req.get("node"))
        requests[req_id] = node_id

    return info, nodes, arcs, fleet, requests

# =====================================================
# Construcción de la instancia y definición de conjuntos y parámetros
# =====================================================

if __name__ == "__main__":
    info, nodes, arcs, fleet, requests= read_instance("Dirección del archivo .xml")
    
# conjunto de clientes C
C = gp.tuplelist(i for i, data in nodes.items() if data["type"] == 1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
# número de clientes 
n = len(C)
# número de vehículos disponibles
numR = 15
#número de cargadores disponibles
numB=info["num_chargers"]
# número de periodos de carga por cargador
numT = fleet["last_charging_period"] - fleet["first_charging_period"] + 1
#numero de partes de la función de recarga
numF=len(fleet["charging_function"])
F= gp.tuplelist(f+1 for f in range(numF))
# capacidad de los vehículos
Q = fleet["capacity"]
# cantidad de energía maxima de las baterias
E = fleet["energy_capacity"]
#Tiempo mimno de salida del depósito
T_min=nodes[fleet["departure_node"]]["tw_start"]/10
#Tiempo máximo de llegada al depósito
T_max=nodes[fleet["arrival_node"]]["tw_end"]/10
# deposito fuente y sumidero como constantes
DEPOSITO_FUENTE_CARGA = -1
DEPOSITO_FUENTE = fleet["departure_node"]
DEPOSITO_SUMIDERO = fleet["arrival_node"]
# conjunto de nodos clientes C1 (incluye el depósito)
C1=gp.tuplelist(C+[DEPOSITO_FUENTE,DEPOSITO_SUMIDERO])
#Coordenadas de los nodos
coord = gp.tupledict({i: (data["x"], data["y"]) for i, data in nodes.items()})
# conjunto de vehículos R
R= gp.tuplelist(r+1 for r in range (numR))
# conjunto de periodos de carga T
T= gp.tuplelist(t+1 for t in range(numT))
# conjunto de cargadores 
B = gp.tuplelist(b+1 for b in range(numB))
# conjunto de nodos de recarga, y sus índices respectivos
CR = gp.tupledict({(t, b): n+2+(b-1)*numT+t-1 for t in T for b in B})
CR_inv= gp.tupledict({CR[k]: k for k in CR.keys()})
VT = gp.tuplelist(CR.values())
# conjunto de nodos V 
V = gp.tuplelist(C1 + VT + [DEPOSITO_FUENTE_CARGA])
# Periodos de recarga necesario para cargar el vehículo
P= gp.tuplelist(i for i in fleet["inverse_recharging_function"].keys())
# demandas de nodos clientes 
d = gp.tupledict()
for i, data in nodes.items():
    if data["type"] == 1:
        d[i] = data["load"]
# demandas del resto de nodos de recarga
for i in VT:
    d[i]=0
# demandas de los depósitos
d[DEPOSITO_FUENTE_CARGA]=0
d[DEPOSITO_FUENTE]=0
d[DEPOSITO_SUMIDERO]=0  
# ventanas de tiempo en cada cliente
ventana= gp.tupledict()
for i, data in nodes.items():
    ventana[i] = (data["tw_start"]/10, data["tw_end"]/10)
#ventanas de tiempo en nodos de periodo de carga
ventana[DEPOSITO_FUENTE_CARGA]=(0,T_max)
for i in VT:
    t=CR_inv[i][0]
    ventana[i]=(t-1,t-1)
#Cantidad de energía recargada en cada periodo
N= gp.tupledict()
N[0]=0
for t in range(len(P)-1):
    N[t+1]=fleet["inverse_recharging_function"][t+1]-fleet["inverse_recharging_function"][t]
#Nivel de energia en cada parte de la función de recarga
phi= gp.tupledict()
phi[0]=0
for p in range(len(fleet["charging_function"])):
    phi[p+1]=fleet["charging_function"][p]["energy_level"]
# tasa de recarga en cada parte de la función de recarga
tasa= gp.tupledict()
for p in range(len(fleet["charging_function"])):
    tasa[p+1]=fleet["charging_function"][p]["rate"]
# costos de los arcos
c = gp.tupledict()
# tiempos de los arcos
tiempo = gp.tupledict()
# energía consumida en los arcos
energia= gp.tupledict()

# costos, tiempos y energía entre clientes
for (i, j,l), arc_data in arcs.items():
    c[i, j, l] = arc_data['travel_cost']/10
    tiempo[i, j, l] = arc_data['travel_time']/10
    energia[i, j, l] = arc_data['energy_consumption']
# costos entre nodos de periodo de carga
for t in T:
    for b in B:
        i=CR[t,b]
        c[DEPOSITO_FUENTE_CARGA,i,1]=0
        c[i,DEPOSITO_FUENTE,1]=0
        if t<numT:
            c[i,i+1,1]=0
# tiempos entre nodos de periodo de carga
for t in T:
    for b in B:
        i=CR[t,b]
        tiempo[DEPOSITO_FUENTE_CARGA,i,1]=0
        tiempo[i,DEPOSITO_FUENTE,1]=0
        if t<numT:
            tiempo[i,i+1,1]=1
#Energía entre nodos de periodo de carga
for t in T:
    for b in B:
        i=CR[t,b]
        energia[DEPOSITO_FUENTE_CARGA,i,1]=0
        energia[i,DEPOSITO_FUENTE,1]=0
        if t<numT:
            energia[i,i+1,1]=0
    
A = list(c.keys())
#arcos de salida del depósito            
A0 = [(i, j, k) for (i, j, k) in A if j in VT or j == DEPOSITO_FUENTE]
A1= [(i,j,k) for(i,j,k) in A if i in C1 and j in C1]
# definir constante M 
M = 200*Q
#=========================================================================
        # NÚMERO MÍNIMO DE VEHÍCULOS CONSIDERANDO DEMANDA
#=========================================================================
#calcular numero minimo de vehículos necesarios
n_min_demanda=math.ceil(sum(d[i] for i in C)/Q)

#=========================================================================
        # NÚMERO MÍNIMO DE VEHÍCULOS CONSIDERANDO ENERGÍA
#=========================================================================
# Encontremos el conjunto de arcos con consumo de energía mínimo para cada par de nodos clientes (i,j)
min_energy_arcs = {}
for i in C:
    for j in C:
        min_arc = None
        min_energy = float('inf')
        for (ii, jj, k) in A1:
            if ii == i and jj == j:
                if energia[i, j, k] < min_energy:
                    min_energy = energia[i, j, k]
                    min_arc = (i, j, k)
                if min_arc is not None:
                    min_energy_arcs[(i, j)] = min_arc

aristas_min_energy = [(arc[0], arc[1], energia[min_energy_arcs[arc]]) for arc in min_energy_arcs.keys()]
    
# Encontramos el consumo minimo que sale del depósito
min_energy_depot_arcs = float('inf')
for (i, j, k) in A1:
    if i == DEPOSITO_FUENTE and energia[i, j, k] < min_energy_depot_arcs:
        min_energy_depot_arcs = energia[i, j, k]
# Encontremos el arco de minimo consumo que llega al depósito sumidero
min_energy_sink_arcs = float('inf')
for (i, j, k) in A1:
    if j == DEPOSITO_SUMIDERO and energia[i, j, k] < min_energy_sink_arcs:
        min_energy_sink_arcs = energia[i, j, k]

### Creamos una arborescencia de costo mínimo de energía para los arcos en min_energy_arcs, el arco de salida del depósito y el arco de llegada al depósito sumidero
nodos= C.copy()
raiz, peso_total, aristas_resultado = arborescencia_minima(aristas_min_energy , set(nodos))
#Encontramos el número mínimo de vehículos necesarios para cubrir el costo total de energía del árbol de costo mínimo, considerando la capacidad de energía de los vehículos
n_min_energy = math.ceil((peso_total+min_energy_depot_arcs+min_energy_sink_arcs) / E)
#=========================================================================
        # NÚMERO MÍNIMO DE VEHÍCULOS CONSIDERANDO VENTANAS DE TIEMPO
#=========================================================================
#Encontramos los indices de todos los arcos entre par de nodos clientes
indices = {}
for (i, j, k) in A1:
    if i!=DEPOSITO_FUENTE and j!=DEPOSITO_SUMIDERO:
        if (i, j) not in indices:
            indices[(i, j)] = []
        indices[(i, j)].append(k)
#Encontramos el grafo de incompatibilidad considerando las ventanas de tiempo
grafo_inc=grafo_incompatibilidad(C,ventana,tiempo,indices)
#Encontramos las cliques máximas del grafo de incompatibilidad
cliques=cliques_maximas(grafo_inc)


#Encontramos el tamaño de la clique maxima más grande
n_min_tiempo=max(len(c) for c in cliques)
#=========================================================================
        # NÚMERO MÍNIMO DE VEHÍCULOS 
#=========================================================================
#Escogemos el máximo entre el número mínimo de vehículos necesarios para cubrir la demanda y el número mínimo de vehículos necesarios para cubrir el costo total de energía del árbol de costo mínimo
n_min = max(n_min_demanda, n_min_energy, n_min_tiempo) 
#almacenamos el número mínimo de vehículos necesario para la instancia en el diccionario e identificamos si n_min es igual a n_min_demanda o a n_min_energy para cada instancia


#===================================================================================
#Generacion de conjuntos de clientes que violenten la restricción de demanda 
# atendida por vehículo
#===================================================================================
coord_dep=coord[0]
coord_clientes={i:coord[i] for i in coord.keys() if i!=DEPOSITO_FUENTE and i!=DEPOSITO_SUMIDERO}
conjuntos_capacidad=sweep(coord_dep, coord_clientes, d, Q, 1)+sweep(coord_dep, coord_clientes, d, Q, 2)

#=============================================================================
#Generacion de conjuntos de clientes con incompatibilidad de ventanas de tiempo
#=============================================================================
for m in range(2, n_min_tiempo):
    conjuntos_cliques += sweep_con_incompatibilidad_clique(coord_dep, coord_clientes, cliques, m)

#=============================================================================
#Generacion de conjuntos de clientes con todas las cliques
#=============================================================================
conjuntos_todas_cliques =[(clique, len(clique)) for clique in cliques if len(clique) > 1]


#=========================================================================
# CREACIÓN DEL MODELO
#=========================================================================
# crear el objeto modelo
m = gp.Model('mE-VRPTW')
### definir variables ###
# variables de selección de arcos
x = m.addVars(A,R, name="x", vtype=GRB.BINARY)
# variables de inicio de servicio en cada nodo
w=m.addVars(V,R, name="w", lb=0, ub=T_max, vtype=GRB.CONTINUOUS)
#variable con la cantidad de energía con la que sale el vehículo del depósito
e=m.addVars(R, name="e", lb=0, ub=E, vtype=GRB.CONTINUOUS)
#variable del número de periodos de carga utilizados por cada vehículo
u=m.addVars(R, name="u", lb=0, ub=len(P), vtype=GRB.INTEGER)
# variable de carga del vehículo en el periodo de carga p
y=m.addVars(R,P, name="y", vtype=GRB.BINARY)
# función objetivo 
m.setObjective(gp.quicksum(c[i,j,k]*x[i,j,k,r] for (i,j,k) in A for r in R) , GRB.MINIMIZE)
### restricciones ###
# restricciones de grado saliente clientes
m.addConstrs((x.sum(i,'*','*','*') == 1 for i in C), "g_entrante_cliente")
#restricciones de grado saliente periodos de carga
m.addConstrs((x.sum('*',i,'*','*')<=1 for i in VT), "g_entrante_carga")   
# restricción de grado saliente del nodo fuente ficticio
m.addConstrs((x.sum(DEPOSITO_FUENTE_CARGA,'*','*',r) <= 1 for r in R), "grado_saliente_fuente_carga")
# restricción de grado saliente del nodo depósito 
m.addConstrs((x.sum(DEPOSITO_FUENTE,'*','*',r) <= 1 for r in R), "grado_saliente_fuente")
# restricción de conservación de flujo
m.addConstrs((x.sum(i,'*','*',r)-x.sum('*',i,'*',r)  == 0 for i in V if i not in [DEPOSITO_FUENTE_CARGA,DEPOSITO_SUMIDERO] for r in R), "conservacion_flujo")
# restricción de servicio dentro de la ventana de tiempo
m.addConstrs((w[i,r]+tiempo[i,j,k]-M*(1-x[i,j,k,r]) <= w[j,r] for (i,j,k) in A for r in R ), "ventana_tiempo")
#restriccion que garantiza que se cargue por completo antes de salir del deposito
m.addConstrs((w[t,r] <= w[DEPOSITO_FUENTE,r] for t in VT for r in R))
# restricción de tiempo de servicio en cada nodo - lower bound
m.addConstrs((ventana[i][0]*x.sum(i,'*','*',r) <= w[i,r] 
            for i in C for r in R), "tiempo_servicio_lb")
# restricción de tiempo de servicio en cada nodo - upper bound
m.addConstrs((w[i,r] <= ventana[i][1]*x.sum(i,'*','*',r) 
            for i in C for r in R), "tiempo_servicio_ub")
# restricción de tiempo de servicio en cada nodo - lower bound
m.addConstrs((ventana[i][0]*x.sum(i,'*','*',r) <= w[i,r] 
            for i in VT for r in R), "tiempo_servicio_lb_t")
# restricción de tiempo de servicio en cada nodo - upper bound
m.addConstrs((w[i,r] <= ventana[i][1]*x.sum(i,'*','*',r) 
            for i in VT for r in R), "tiempo_servicio_ub_t")
# restricción de demanda atendida por vehículo
m.addConstrs((gp.quicksum(d[i] * x.sum(i, '*', '*', r) for i in C)<= Q for r in R), name="demanda_vehiculo")
#restricción de la energía con la que sale el vehículo del depósito
m.addConstrs((e[r]>=gp.quicksum(energia[i,j,k]*x[i,j,k,r] for (i,j,k) in A1) for r in R), name="energia_deposito")
#restriccion de igualdad entre el total de energía recargada y la energía con la que sale el depósito
m.addConstrs((e[r]<=gp.quicksum(y[r,p]*N[p+1] for p in P if p < len(N)-1) for r in R), name="energia_recargada_igual_salida_deposito")
#restricción de número de periodos de carga utilizados por cada vehículo
m.addConstrs((u[r]==gp.quicksum(x[i,j,k,r] for (i,j,k) in A0 if i in VT and j in VT) for r in R), name="numero_periodos_carga")
#restricción de número de periodos necesarios para cada vehículo
m.addConstrs((u[r]==gp.quicksum(y[r,p] for p in P) for r in R), name="periodos_necesarios")
#restriccion de monotonía de la variable y
m.addConstrs((y[r,p] <= y[r,p-1] for r in R for p in P if p>=1), name="monotonia_y")
# restricción de número mínimo de vehículos 
m.addConstr(x.sum(DEPOSITO_FUENTE,'*','*','*') >= n_min, name="num_vehiculos_minimos")

#Nota: Desigualdades de cotas locales, solo agregar una dependiendo del conjunto de cortes a evaluar

#restricciones de cortes de capacidad para cada ruta violadora encontrada por el método sweep
for idx, (ruta, num_vehiculos) in enumerate(conjuntos_capacidad):
     m.addConstr(gp.quicksum(x.sum(i,'*','*','*') for i in ruta) >= num_vehiculos, name=f"corte_capacidad_{idx}")
#restricciones de cortes de capacidad para cada ruta violadora encontrada por todas las cliques
for idx, (ruta, num_vehiculos) in enumerate(conjuntos_todas_cliques):
   m.addConstr(gp.quicksum(x.sum(i,'*','*','*') for i in ruta) >= num_vehiculos, name=f"corte_clique_{idx}")
##restricciones de cortes de capacidad para cada ruta violadora encontrada por incompatibilidad de ventanas de tiempo
for idx, (ruta, num_vehiculos) in enumerate(conjuntos_cliques):
   m.addConstr(gp.quicksum(x.sum(i,'*','*','*') for i in ruta) >= num_vehiculos, name=f"corte_clique_{idx}")

# fijar el tiempo límite de cálculo en 2 horas
m.Params.TimeLimit = 7200


# resolver el modelo 
m.optimize()


    

