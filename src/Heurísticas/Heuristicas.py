import gurobipy as gp
from gurobipy import GRB
import xml.etree.ElementTree as ET
import math
import os
import random
import time


random.seed(7)
num=10

# Función para construir el grafo de incompatibilidad entre clientes según ventanas de tiempo 
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

# Función para calcular el ángulo polar de un cliente respecto al depósito
def angulo_polar(deposito, cliente):
    dx = cliente[0] - deposito[0]
    dy = cliente[1] - deposito[1]
    angulo = math.atan2(dy, dx)
    # convertir a [0, 2π]
    return angulo % (2 * math.pi)

# Función inversa para determinar el número de periodos necesarios según la energía acumulada
def funcion_inversa(e):
    energia_acumulada = 0
    for t in N.keys():
        energia_acumulada += N[t]
        if energia_acumulada >= e:
            return t+1
    return max(N.keys())

# Heurística 1: Construcción de rutas
def Heuristica_1(Clientes, iter, arcos_entrada, grafo_inc, energia, min_energy_to, min_cost_from, min_cost_to, c, tiempo, d, P, Q):
    
    solucion=[]

    for semilla in range(iter):       
        rutas = []
        Nvisitado = random.sample(Clientes,len(Clientes))

        while(len(Nvisitado)>0):
            inicio = Nvisitado.pop(0)
            
            # la ruta empieza en el sumidero 
            ruta_actual = [DEPOSITO_SUMIDERO, inicio]
            arcos_actuales = [min_cost_from[inicio][1]] #arco de menor costo desde el depósito sumidero al cliente inicio
            energia_ruta = E - energia[inicio, DEPOSITO_SUMIDERO, min_cost_from[inicio][1]]
            costo_ruta = min_cost_from[inicio][0]
            tiempo_ruta = min(ventana[DEPOSITO_SUMIDERO][1] - tiempo[inicio, DEPOSITO_SUMIDERO, min_cost_from[inicio][1]], ventana[inicio][1])
            capacidad_ruta = Q - d[inicio]
            nodo_actual = inicio
            
            while nodo_actual != DEPOSITO_FUENTE:
                vecinos_ordenados = sorted(
                    [(tail, k) for tail, k in arcos_entrada[nodo_actual] if tail in Nvisitado],
                    key=lambda x:  c[x[0], nodo_actual, x[1]]-min_cost_to[x[0]][0])
                
                mejor_vecino = None
                for vecino, arco in vecinos_ordenados:
                    if vecino not in Nvisitado:
                        continue

                    energia_necesaria = energia[vecino, nodo_actual, arco]
                    energia_p= energia_ruta - energia_necesaria - min_energy_to[vecino][0]
                    periodos_necesarios = funcion_inversa(energia_p)
                    tiempo_llegada = tiempo_ruta - tiempo[vecino, nodo_actual, arco]
                    tiempo_servicio = min(tiempo_llegada, ventana[vecino][1])
                    tiempo_regreso = tiempo[DEPOSITO_FUENTE, vecino, min_energy_to.get(vecino, (float('inf'),))[1]]

                    if (vecino not in grafo_inc.get(nodo_actual, set()) and energia_p > 0 and
                        tiempo_servicio - tiempo_regreso >= periodos_necesarios 
                        and tiempo_servicio >= ventana[vecino][0] and
                        capacidad_ruta - d.get(vecino, 0) >= 0 ):
                        mejor_vecino = (vecino, arco)
                        break

                if mejor_vecino:
                    vecino, arco = mejor_vecino
                    ruta_actual.append(vecino)
                    arcos_actuales.append(arco)
                    energia_ruta -= energia[vecino, nodo_actual, arco]
                    costo_ruta += c[vecino, nodo_actual, arco]
                    tiempo_llegada = tiempo_ruta - tiempo[vecino, nodo_actual, arco]
                    tiempo_ruta = min(tiempo_llegada, ventana[vecino][1])
                    capacidad_ruta -= d.get(vecino, 0)
                    Nvisitado.remove(vecino)
                    nodo_actual = vecino
                else:
                    if nodo_actual == DEPOSITO_SUMIDERO:
                        break  # no se pudo avanzar desde el sumidero, esta ruta no es válida
                    if(energia_ruta - energia[ DEPOSITO_FUENTE,nodo_actual, min_cost_to[nodo_actual][1]] > 0 and 
                    tiempo_ruta - tiempo[DEPOSITO_FUENTE, nodo_actual, min_cost_to[nodo_actual][1]] >= len(P)):
                        arco_retorno = min_cost_to[nodo_actual][1]
                    else:
                        arco_retorno = min_energy_to[nodo_actual][1]

                    ruta_actual.append(DEPOSITO_FUENTE)
                    arcos_actuales.append(arco_retorno)
                    energia_ruta -= energia[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                    costo_ruta += c[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                    tiempo_ruta -= tiempo[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                    nodo_actual = DEPOSITO_FUENTE
                    rutas.append((ruta_actual, arcos_actuales, costo_ruta,
                                    energia_ruta, tiempo_ruta, capacidad_ruta))
                    break

            else:
                rutas.append((ruta_actual, arcos_actuales, costo_ruta,
                              energia_ruta, tiempo_ruta, capacidad_ruta))

        #almacenar la solución
        solucion.append(rutas)
        
    return solucion

# Heurística 3: Construcción de rutas 
def Heuristica_3(Clientes, iter, ventana, arcos_entrada, grafo_inc,
                              energia, min_energy_to, min_cost_from, min_cost_to,
                              c, tiempo, d, P, Q, indices):

    solucion_final = []


    for i in range(iter):
    
        Nvisitado1 = random.sample(Clientes,len(Clientes))

        solucion = []

        while len(Nvisitado1) > 0:

            # ── Primera fase ──────────────────────────────
            Nvisitado2 = Nvisitado1.copy()
            rutas = {}
            arcos = {}
            recursos = {}

            while len(Nvisitado2) > 0:
                semilla = Nvisitado2.pop(0)
                Nvisitado1.remove(semilla)
                nodo_actual = semilla

                rutas[semilla] = [DEPOSITO_SUMIDERO, semilla]
                arcos[semilla] = [min_cost_from[semilla][1]]
                energia_ruta = E - energia[semilla, DEPOSITO_SUMIDERO, min_cost_from[semilla][1]]
                costo_ruta = min_cost_from[semilla][0] 
                tiempo_ruta = min(ventana[DEPOSITO_SUMIDERO][1] - tiempo[semilla, DEPOSITO_SUMIDERO, min_cost_from[semilla][1]],ventana[semilla][1])
                capacidad_ruta = Q - d[semilla]

                while True:
                    vecinos_ordenados = sorted(
                        [(tail, k) for tail, k in arcos_entrada[nodo_actual] if tail in Nvisitado2],
                        key=lambda x: c[x[0], nodo_actual, x[1]] + min_cost_from[x[0]][0])

                    mejor_vecino = None
                    for vecino, arco in vecinos_ordenados:
                        energia_necesaria = energia[vecino, nodo_actual, arco]
                        energia_p = energia_ruta - energia_necesaria - min_energy_to[vecino][0]
                        periodos_necesarios = funcion_inversa(energia_p)
                        tiempo_regreso = tiempo[DEPOSITO_FUENTE, vecino,min_energy_to[vecino][1]]
                        tiempo_llegada = tiempo_ruta - tiempo[vecino, nodo_actual, arco]
                        tiempo_servicio = min(tiempo_llegada, ventana[vecino][1])

                        if (vecino not in grafo_inc.get(nodo_actual, set()) and
                            energia_p > 0 and
                            tiempo_servicio - tiempo_regreso >= periodos_necesarios and
                            tiempo_servicio >= ventana[vecino][0] and
                            capacidad_ruta - d.get(vecino, 0) >= 0):
                            mejor_vecino = (vecino, arco)
                            break

                    if mejor_vecino:
                        vecino, arco = mejor_vecino
                        rutas[semilla].append(vecino)
                        arcos[semilla].append(arco)
                        energia_ruta -= energia[vecino, nodo_actual, arco]
                        costo_ruta += c[vecino, nodo_actual, arco]
                        tiempo_ruta = min(tiempo_ruta - tiempo[vecino, nodo_actual, arco],ventana[vecino][1])
                        capacidad_ruta -= d.get(vecino, 0)
                        Nvisitado2.remove(vecino)
                        nodo_actual = vecino
                    else:
                        if nodo_actual == DEPOSITO_SUMIDERO:
                            break

                        if (nodo_actual in min_cost_to and
                            energia_ruta - energia[DEPOSITO_FUENTE, nodo_actual,
                                                   min_cost_to[nodo_actual][1]] > 0 and
                            tiempo_ruta - tiempo[DEPOSITO_FUENTE, nodo_actual,
                                                 min_cost_to[nodo_actual][1]] >= len(P)):
                            arco_retorno = min_cost_to[nodo_actual][1]
                        else:
                            arco_retorno = min_energy_to[nodo_actual][1]

                        rutas[semilla].append(DEPOSITO_FUENTE)
                        arcos[semilla].append(arco_retorno)
                        energia_ruta -= energia[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                        costo_ruta += c[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                        tiempo_ruta -= tiempo[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                        break

                recursos[semilla] = (energia_ruta, costo_ruta, tiempo_ruta, capacidad_ruta)

            # ── Segunda fase: inserción por epsilon ────────────────────────
            J = list(rutas.keys())
            ruta_asociada = {j: [] for j in J}

            for i_cliente in Clientes:
                if i_cliente in J:
                    continue

                mejor_j = None
                mejor_epsilon = float('inf')

                for j in J:
                    costo_dep = min_cost_from[i_cliente][0] 
                    arcos_ji = indices.get((j, i_cliente), [])
                    if not arcos_ji:
                        continue
                    costo_ji = min(c[j, i_cliente, k] for k in arcos_ji)
                    epsilon = costo_dep + costo_ji
                    if epsilon < mejor_epsilon:
                        mejor_epsilon = epsilon
                        mejor_j = j

                if mejor_j is not None:
                    ruta_asociada[mejor_j].append(i_cliente)

            for j in J:
                Tau = {}

                for i_cliente in ruta_asociada[j]:
                    mejor_costo = float('inf')
                    mejor_k = None

                    for k in J:
                        if k == j:
                            continue
                        arcos_ki = indices.get((k, i_cliente), [])
                        if not arcos_ki:
                            continue
                        costo_ki = min(c[k, i_cliente, arc] for arc in arcos_ki)
                        costo_dep_i = min_cost_from[i_cliente][0] 
                        costo_ins = costo_ki + costo_dep_i
                        if costo_ins < mejor_costo:
                            mejor_costo = costo_ins
                            mejor_k = k

                    if mejor_k is None:
                        continue

                    arcos_ji = indices.get((j, i_cliente), [])
                    if not arcos_ji:
                        continue
                    costo_ji = min(c[j, i_cliente, arc] for arc in arcos_ji) + min_cost_from[i_cliente][0]
                    Tau[i_cliente] = mejor_costo - costo_ji

                if not Tau:
                    e, co, ti, ca = recursos[j]
                    solucion.append((rutas[j], arcos[j], co, e, ti, ca))
                    # ← j ya fue removido de Nvisitado1 en la primera fase
                    continue

                Nvisitado3 = [i_c for i_c in ruta_asociada[j] if i_c in Nvisitado1]

                nuevas_rutas_j = [DEPOSITO_SUMIDERO, j]
                nuevos_arcos_j = [min_cost_from[j][1]]
                energia_nueva = E - energia[j, DEPOSITO_SUMIDERO, min_cost_from[j][1]]
                costo_nuevo = min_cost_from[j][0] 
                tiempo_nuevo = min(
                    ventana[DEPOSITO_SUMIDERO][1] - tiempo[j, DEPOSITO_SUMIDERO, min_cost_from[j][1]],
                    ventana[j][1]
                )
                capacidad_nueva = Q - d[j]
                nodo_actual = j

                while len(Nvisitado3) > 0:
                    Tau_ordenado = sorted(
                        [(i_c, tau) for i_c, tau in Tau.items() if i_c in Nvisitado3],
                        key=lambda x: x[1],
                        reverse=True
                    )

                    mejor_vecino = None
                    for vecino, _ in Tau_ordenado:
                        arcos_disponibles = sorted(indices.get((vecino, nodo_actual), []),
                            key=lambda k: c[vecino, nodo_actual, k])
                        if not arcos_disponibles:
                            continue

                        arco = arcos_disponibles[0]
                        energia_necesaria = energia[vecino, nodo_actual, arco]
                        energia_p = energia_nueva - energia_necesaria - min_energy_to[vecino][0]
                        periodos_necesarios = funcion_inversa(energia_p)
                        tiempo_regreso = tiempo[DEPOSITO_FUENTE, vecino,
                                                min_energy_to.get(vecino, (float('inf'),))[1]]

                        if (vecino not in grafo_inc.get(nodo_actual, set()) and
                            energia_p > 0 and
                            tiempo_nuevo - tiempo[vecino, nodo_actual, arco] - tiempo_regreso >= periodos_necesarios and
                            capacidad_nueva - d.get(vecino, 0) >= 0):
                            mejor_vecino = (vecino, arco)
                            break

                    if mejor_vecino:
                        vecino, arco = mejor_vecino
                        nuevas_rutas_j.append(vecino)
                        nuevos_arcos_j.append(arco)
                        energia_nueva -= energia[vecino, nodo_actual, arco]
                        costo_nuevo += c[vecino, nodo_actual, arco]
                        tiempo_nuevo = min(
                            tiempo_nuevo - tiempo[vecino, nodo_actual, arco],
                            ventana[vecino][1]
                        )
                        capacidad_nueva -= d.get(vecino, 0)
                        Nvisitado3.remove(vecino)
                        if vecino in Nvisitado1:
                            Nvisitado1.remove(vecino)  # ← elimina de Nvisitado1
                        nodo_actual = vecino
                    else:
                        break

                if nodo_actual not in (DEPOSITO_FUENTE, DEPOSITO_SUMIDERO):
                    if (nodo_actual in min_cost_to and
                        energia_nueva - energia[DEPOSITO_FUENTE, nodo_actual,
                                               min_cost_to[nodo_actual][1]] > 0 and
                        tiempo_nuevo - tiempo[DEPOSITO_FUENTE, nodo_actual,
                                             min_cost_to[nodo_actual][1]] >= len(P)):
                        arco_retorno = min_cost_to[nodo_actual][1]
                    else:
                        arco_retorno = min_energy_to[nodo_actual][1]

                    nuevas_rutas_j.append(DEPOSITO_FUENTE)
                    nuevos_arcos_j.append(arco_retorno)
                    energia_nueva -= energia[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                    costo_nuevo += c[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                    tiempo_nuevo -= tiempo[DEPOSITO_FUENTE, nodo_actual, arco_retorno]

                    solucion.append((
                        nuevas_rutas_j, nuevos_arcos_j,
                        costo_nuevo, energia_nueva,
                        tiempo_nuevo, capacidad_nueva
                    ))

        solucion_final.append(solucion)

    return solucion_final

# Heurística 2: Construcción de rutas con barrido angular
def Heuristica_2(C, iter, coord_dep, coord_clientes, arcos_entrada, grafo_inc,
                    energia, min_energy_to, min_cost_from, c, tiempo, d, P, Q):
    posibles_soluciones=[]
    nodos_ordenados = sorted([j for j in C],key=lambda x: angulo_polar(coord_dep, coord_clientes[x]),
        reverse=True)

    n = len(nodos_ordenados)
    numero_inicios = min(iter, n)  # no más inicios que clientes
    inicios = random.sample(C, numero_inicios)  # prueba con hasta n inicios aleatorios

    for semilla in inicios:
        rutas = []
        visitado = set()

        for i in range(n):
            inicio = nodos_ordenados[(i + semilla) % n]
            if inicio in visitado:
                continue

            # mejor arco desde DEPOSITO_SUMIDERO a inicio
            arco_inicio= min_cost_from[inicio][1]

            ruta_actual = [DEPOSITO_SUMIDERO, inicio]
            arcos_actuales = [arco_inicio]
            energia_ruta = E - energia[inicio, DEPOSITO_SUMIDERO, arco_inicio]
            costo_ruta = c[inicio, DEPOSITO_SUMIDERO, arco_inicio]
            tiempo_ruta = min(
                ventana[DEPOSITO_SUMIDERO][1] - tiempo[inicio, DEPOSITO_SUMIDERO, arco_inicio],
                ventana[inicio][1]
            )
            capacidad_ruta = Q - d.get(inicio, 0)
            visitado.add(inicio)
            nodo_actual = inicio

            # orden de visita restante según el barrido
            # son los clientes aún no visitados en el orden angular a partir de inicio
            pos_actual = nodos_ordenados.index(inicio)
            orden_visita = [
                nodos_ordenados[(pos_actual + k) % n]
                for k in range(1, n)
                if nodos_ordenados[(pos_actual + k) % n] not in visitado
            ]

            for siguiente in orden_visita:
                if siguiente in visitado:
                    continue
                if siguiente == DEPOSITO_FUENTE or siguiente == DEPOSITO_SUMIDERO:
                    continue

                # paso 1: ¿hay arcos desde nodo_actual a siguiente?
                arcos_disponibles = sorted(
                    [k for k in indices.get((siguiente, nodo_actual), [])],
                    key=lambda x: c[siguiente, nodo_actual, x]  # paso 2: menor costo
                )

                mejor_arco = None
                for arco in arcos_disponibles:
                    energia_necesaria = energia[siguiente, nodo_actual, arco]
                    energia_restante = energia_ruta - energia_necesaria - min_energy_to.get(siguiente, (0,))[0] 
                    tiempo_llegada = tiempo_ruta - tiempo[siguiente, nodo_actual, arco]
                    periodos_necesarios = funcion_inversa(energia_restante)
                    tiempo_regreso = tiempo[DEPOSITO_FUENTE, siguiente, min_energy_to.get(siguiente, (float('inf'),))[1]]
                    tiempo_llegada = tiempo_ruta - tiempo[siguiente, nodo_actual, arco]
                    tiempo_servicio = min(tiempo_llegada, ventana[siguiente][1])

                    if (siguiente not in grafo_inc.get(nodo_actual, set()) and
                        energia_restante > 0 and
                        tiempo_servicio - tiempo_regreso >= periodos_necesarios 
                        and tiempo_servicio >= ventana[siguiente][0] and
                        capacidad_ruta - d.get(siguiente, 0) >= 0):
                        mejor_arco = arco
                        break

                if mejor_arco is not None:
                    # agrega siguiente a la ruta con el mejor arco
                    ruta_actual.append(siguiente)
                    arcos_actuales.append(mejor_arco)
                    energia_ruta -= energia[siguiente, nodo_actual, mejor_arco]
                    costo_ruta += c[siguiente, nodo_actual, mejor_arco]
                    tiempo_ruta = min(
                        tiempo_ruta - tiempo[siguiente, nodo_actual, mejor_arco],
                        ventana[siguiente][1]
                    )
                    capacidad_ruta -= d.get(siguiente, 0)
                    visitado.add(siguiente)
                    nodo_actual = siguiente
                # si no hay arco factible hacia siguiente, simplemente se salta
                # y continúa con el próximo en el orden angular

            # cierra la ruta regresando al fuente
            if nodo_actual != DEPOSITO_SUMIDERO and nodo_actual in min_energy_to:
                arco_retorno = min_energy_to[nodo_actual][1]
                ruta_actual.append(DEPOSITO_FUENTE)
                arcos_actuales.append(arco_retorno)
                energia_ruta -= min_energy_to[nodo_actual][0]
                costo_ruta += c[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                tiempo_ruta -= tiempo[DEPOSITO_FUENTE, nodo_actual, arco_retorno]
                rutas.append((ruta_actual, arcos_actuales, costo_ruta,
                              energia_ruta, tiempo_ruta, capacidad_ruta))
            
        posibles_soluciones.append(rutas)
       

    return posibles_soluciones

# Función para mejorar rutas combinando dos rutas existentes
def mejorar_rutas(funcion,ruta1, ruta2, arcos_entrada, grafo_inc, energia, min_energy_to, min_cost_from, min_cost_to, c, tiempo, d, P, Q):
    
    nodos = [i for i in set(ruta1[0] + ruta2[0]) if i in C]

    if funcion == "Heuristica_1":
        nuevas_rutas = Heuristica_1(nodos, 1, coord_dep, coord_clientes, arcos_entrada, grafo_inc,
                                        energia, min_energy_to, min_cost_from, min_cost_to,
                                        c, tiempo, d, P, Q)[0]
    elif funcion == "Heuristica_3":
        nuevas_rutas = Heuristica_3(nodos, 1, coord_dep, coord_clientes, arcos_entrada, grafo_inc,
                                        energia, min_energy_to, min_cost_from, min_cost_to,
                                        c, tiempo, d, P, Q, indices)[0]
    elif funcion == "Heuristica_2":
        nuevas_rutas = Heuristica_2(nodos, 1, coord_dep, coord_clientes, arcos_entrada, grafo_inc,
                                        energia, min_energy_to, min_cost_from, min_cost_to,
                                        c, tiempo, d, P, Q)[0]
    
    estado = False 

    costos=sum(r[2] for r in nuevas_rutas)
    if costos < ruta1[2] + ruta2[2]:
        estado = True
        return nuevas_rutas, estado
    else:
        return [ruta1, ruta2], estado

# Función para asignación greedy de cargadores a rutas generadas por la heurística
def asignacion_cargadores_GA(rutas, C, CR, n, c, energia, tiempo, ventana, E, B, numT):
    asignacion = True
    rutas_completas = []

    # construye disponibilidad de periodos por cargador
    cargadores_actuales = {b: [] for b in B}
    for (t, b), nodo in CR.items():
        cargadores_actuales[b].append(nodo)

    # ordena periodos de cada cargador
    for b in B:
        cargadores_actuales[b].sort()

    procesada = []

    # ordena rutas por tiempo de salida ascendente
    rutas_ordenadas = sorted(rutas, key=lambda r: r[4])  
    for cargador in B:
        hubo_asignacion = True

        while hubo_asignacion:
            hubo_asignacion = False

            for ruta in rutas_ordenadas:
                if ruta in procesada:
                    continue

                periodos_necesarios = funcion_inversa(E - ruta[3]) +1
                tiempo_ruta = ruta[4]
                periodos_disponibles = cargadores_actuales[cargador]

                if len(periodos_disponibles) < periodos_necesarios :
                    continue

                # convierte nodos de periodo a tiempos reales
                tiempos_periodos = [
                    nodo - n - 1 - (cargador - 1) * numT
                    for nodo in periodos_disponibles
                ]

                ultimo_tiempo = tiempos_periodos[periodos_necesarios-1] 
                primer_tiempo = tiempos_periodos[0] 

                if ultimo_tiempo <= tiempo_ruta:
                    procesada.append(ruta)
                    hubo_asignacion = True

                    # orden para rutas de atrás hacia adelante:
                    # ultimo_periodo → primer_periodo → -1
                    nuevos_nodos = (
                        list(ruta[0]) +
                        [tiempo + n + 1 + (cargador - 1) * numT          # ← nodo real
                        for tiempo in range(ultimo_tiempo, primer_tiempo - 1, -1)] +  # ← orden correcto
                        [DEPOSITO_FUENTE_CARGA]
                    )
                    nuevos_arcos = (
                        list(ruta[1]) +
                        [1 for _ in range(ultimo_tiempo, primer_tiempo - 1, -1)] +
                        [1]
                    )

                    # elimina los periodos usados del cargador
                    cargadores_actuales[cargador] = periodos_disponibles[periodos_necesarios:]

                    rutas_completas.append((
                        nuevos_nodos,
                        nuevos_arcos,
                        ruta[2],      # costo
                        ruta[3],      # energia restante
                        ruta[4],      # tiempo
                        ruta[5],      # capacidad
                        cargador,
                        ultimo_tiempo
                    ))

            # si no quedan periodos disponibles para este cargador, para
            if not cargadores_actuales[cargador]:
                break

    #rutas que no pudieron asignarse a ningún cargador
    no_asignadas = [r for r in rutas if r not in procesada]

    if  no_asignadas:
        asignacion=False
    else:
        asignacion=True

    costo_rutas = sum(r[2] for r in rutas_completas)
    return rutas_completas, costo_rutas, asignacion

# Función para asignación exacta de cargadores a rutas generadas por la heurística
def asignacion_cargadores_exacta(rutas, C, CR, n, c, energia, tiempo, ventana, E, B):
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
    #variable con la cantidad de enrgía con la que sale el vehículo del depósito
    e=m.addVars(R, name="e", lb=0, ub=E, vtype=GRB.CONTINUOUS)
    #variable del número de periodos de carga utilizados por cada vehículo
    u=m.addVars(R, name="u", lb=0, ub=len(P), vtype=GRB.INTEGER)
    # variable de carga del vehículo en el periodo de carga p
    y=m.addVars(R,P, name="y", vtype=GRB.BINARY)

    # función objetivo 
    m.setObjective(gp.quicksum(c[i,j,k]*x[i,j,k,r] for (i,j,k) in A for r in R) , GRB.MINIMIZE)

    ### restricciones ###
    rutas_usadas = set()

    # fijar arcos de las rutas generadas por la heurística
    for r, ruta in enumerate(rutas, start=1):
        nodos_ruta = ruta[0]
        arcos_ruta = ruta[1]

        # invertir porque la heurística construye de atrás hacia adelante
        nodos_ruta_inv = list(reversed(nodos_ruta))
        arcos_ruta_inv = list(reversed(arcos_ruta))

        for i in range(len(nodos_ruta_inv) - 1):
            nodo_i = nodos_ruta_inv[i]
            nodo_j = nodos_ruta_inv[i + 1]
            arco_ij = arcos_ruta_inv[i]

            if (nodo_i, nodo_j, arco_ij) in A:
                m.addConstr(
                    x[nodo_i, nodo_j, arco_ij, r] == 1,
                    name=f"fijar_arco_{nodo_i}_{nodo_j}_{arco_ij}_r{r}"
                )
        
        rutas_usadas.add(r)
    
    rutas_no_usadas = set(R) - rutas_usadas
    for r in rutas_no_usadas:
        # fija u=0 para rutas vacías
        m.addConstr(u[r] == 0, name=f"u_vacia_r{r}")
        # fija e=0 para rutas vacías  
        m.addConstr(e[r] == 0, name=f"e_vacia_r{r}")
        # fija w=0 para todos los nodos en rutas vacías
        for i in V:
            m.addConstr(w[i, r] == 0, name=f"w_vacia_{i}_r{r}")

    
    # restricciones de grado saliente clientes
    m.addConstrs((x.sum(i,'*','*','*') == 1 for i in C), "g_entrante_cliente")
    #restricciones de grado saliente periodos de carga
    m.addConstrs((x.sum('*',i,'*','*')<=1 for i in VT), "g_entrante_carga")   
    # restricción de grado saliente del nodo fuente ficticio
    m.addConstrs((x.sum(DEPOSITO_FUENTE_CARGA,'*','*',r) <= 1 for r in R), "grado_saliente_fuente_carga")
    # restricción de grado saliente del nodo depósito 
    m.addConstrs((x.sum(DEPOSITO_FUENTE,'*','*',r) <= 1 for r in R), "grado_saliente_fuente")
    # restricción de conservación de flujo
    m.addConstrs((x.sum(i,'*','*',r)-x.sum('*',i,'*',r)  == 0 for i in V if i not in [DEPOSITO_FUENTE_CARGA, DEPOSITO_SUMIDERO] for r in R), "conservacion_flujo")
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
    m.addConstrs((e[r]<=gp.quicksum(y[r,p]*N[p] for p in P ) for r in R), name="energia_recargada_igual_salida_deposito")
    #restricción de número de periodos de carga utilizados por cada vehículo
    m.addConstrs((u[r]==gp.quicksum(x[i,j,k,r] for (i,j,k) in A0 if i in VT and j in VT) for r in R), name="numero_periodos_carga")
    #restricción de número de periodos necesarios para cada vehículo
    m.addConstrs((u[r]==gp.quicksum(y[r,p] for p in P) for r in R), name="periodos_necesarios")
    #restriccion de monotonía de la variable y
    m.addConstrs((y[r,p] <= y[r,p-1] for r in R for p in P if p>=1), name="monotonia_y")

    # fijar el tiempo límite de cálculo en 2 horas
    m.Params.TimeLimit = 7200

    # log_dir = "src/Resultados/"+grupo
    # os.makedirs(log_dir, exist_ok=True)

    # log_path = os.path.join(log_dir, file + "_SR.log")
    # sol_path = os.path.join(log_dir, file + "_solucion_SR.sol")
    

    # m.setParam("LogFile", log_path)

    # resolver el modelo 
    m.setParam("OutputFlag", 0)
    m.Params.SolutionLimit = 1
    m.optimize()

    tiempo = m.Runtime

    if m.Status == GRB.OPTIMAL:
        print(f"Objetivo Gurobi: {m.ObjVal:.2f}")
        # print("\nArcos activos en la solución del modelo:")
        # costo_total = 0
        # for r in R:
        #     print(f"\n  Ruta {r}:")
        #     for (i, j, k) in A:
        #         if x[i, j, k, r].X > 0.5:
        #             costo_arco = c[i, j, k]
        #             costo_total += costo_arco
    #                 print(f"    {i}→{j} (arco {k}): costo={costo_arco:.2f}")
            
    #         for p in P:
    #             if y[r, p].X > 0.5:
    #                 print(f"    Periodo de carga {p} utilizado")
    #       print(f"\nCosto recalculado: {costo_total:.2f}")

    # if m.Status == GRB.INFEASIBLE:
    #     m.computeIIS()
    #     print("Restricciones en el IIS:")
    #     for constr in m.getConstrs():
    #         if constr.IISConstr:
    #             print(f"  {constr.ConstrName}")
        
        # # también imprime bounds de variables en el IIS
        # print("\nVariables con bounds en el IIS:")
        # for var in m.getVars():
        #     if var.IISLB or var.IISUB:
        #          print(f"  {var.VarName}: lb={var.LB}, ub={var.UB}, valor={var.X if m.Status == GRB.OPTIMAL else 'N/A'}")

    return m.Status, tiempo

# Funciones para leer instancias desde archivos XML
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

# Función para leer una instancia desde un archivo XML
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
    info, nodes, arcs, fleet, requests= read_instance("direccion_del_archivo.xml")

    
    # conjunto de clientes C
    C = gp.tuplelist(i for i, data in nodes.items() if data["type"] == 1)

    # número de clientes K
    n = len(C)

    # número de vehículos disponibles
    numR = 20

    #número de cargadores disponibles
    numB=info["num_chargers"]

    # número de periodos de carga por cargador
    numT = fleet["last_charging_period"] - fleet["first_charging_period"] + 1

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
    VT.sort()
    # conjunto de nodos V 
    V = gp.tuplelist(C1 + VT + [DEPOSITO_FUENTE_CARGA])

    # Periodos de recarga necesario para cargar el vehículo
    P= gp.tuplelist(fleet["inverse_recharging_function"].keys())

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

    #calcular numero minimo de vehículos necesarios
    n_min=math.ceil(sum(d[i] for i in C)/Q)

    # Calcular la energía minima e id de los arcos con menor consumo energético desde el depósito fuente y hacia el depósito sumidero
    min_energy_to = {}
    for (tail, head, id_), data in arcs.items():
        if tail == DEPOSITO_FUENTE:
            energy = data["energy_consumption"]
        
            if head not in min_energy_to or energy< min_energy_to[head][0]:
                min_energy_to[head] = (energy, id_)
        
    min_energy_from = {}
    for (tail, head, id_), data in arcs.items():
        if head == DEPOSITO_SUMIDERO:
            energy = data["energy_consumption"]

            if tail not in min_energy_from or energy < min_energy_from[tail][0]:
                min_energy_from[tail] = (energy, id_)

    min_cost_from={}
    for (tail, head, id_), data in arcs.items():
        if head == DEPOSITO_SUMIDERO:
            cost = data["travel_cost"]
        
            if tail not in min_cost_from or cost < min_cost_from[tail][0]:
                min_cost_from[tail] = (cost*0.1, id_)

    min_cost_to={}
    for (tail, head, id_), data in arcs.items():
        if tail == DEPOSITO_FUENTE:
            cost = data["travel_cost"]

            if head not in min_cost_to or cost < min_cost_to[head][0]:
                min_cost_to[head] = (cost*0.1, id_) 

    #Obtenemos el indice de todos los arcos que conectan un par de nodos
    indices = {}
    for (i, j, k) in A1:
        if i!=DEPOSITO_FUENTE and j!=DEPOSITO_SUMIDERO:
            if (i, j) not in indices:
                indices[(i, j)] = []
            indices[(i, j)].append(k)

    grafo_inc=grafo_incompatibilidad(C,ventana,tiempo,indices)
    grafo_inc[DEPOSITO_FUENTE]=set()  # El depósito fuente no es incompatible con ningún cliente

    arcos_entrada = {j: [] for j in C1+VT}
    for (tail, head, k) in A:
        if head in arcos_entrada:
            arcos_entrada[head].append((tail, k))
    
    arcos_salida = {i: [] for i in C1+VT}
    for (tail, head, k) in A:
        if tail in arcos_salida:
            arcos_salida[tail].append((head, k))

    coord_dep=coord[DEPOSITO_FUENTE]
    coord_clientes={i:coord[i] for i in C}


#================================================
#         FASE 1: CONSTRUCCIÓN DE RUTAS INICIALES 
#================================================
#Elegir entre la heurística 1, 2 o 3 para generar las rutas iniciales
heuristica="Heuristica_1" # "Heuristica_1", "Heuristica_2" o "Heuristica_3"
if heuristica == "Heuristica_1":    
    soluciones=Heuristica_1(C, num, arcos_entrada, grafo_inc, energia, min_energy_to, min_cost_from, min_cost_to, c, tiempo, d, P, Q)
elif heuristica == "Heuristica_2":
    soluciones=Heuristica_2(C, num, arcos_entrada, grafo_inc, energia, min_energy_to, min_cost_from, min_cost_to, c, tiempo, d, P, Q)
elif heuristica == "Heuristica_3":
    soluciones=Heuristica_3(C, num, arcos_entrada, grafo_inc, energia, min_energy_to, min_cost_from, min_cost_to, c, tiempo, d, P, Q, indices)
#==============================================
#         FASE 2: MEJORAMIENTO DE RUTAS INICIALES
#================================================
soluciones_finales = []
for solucion in soluciones:
    mejoro = True
    solucion_final = solucion # se inicia con la solución generada por la heurística
    while mejoro:
        mejoro = False  # resetea en cada iteración
        rutas_actuales = solucion_final[:]  # copia para iterar sin modificar
        rutas_fusionadas = set()            # índices de rutas ya fusionadas
        nuevas_rutas_iter = []
        for i in range(len(rutas_actuales)):
            if i in rutas_fusionadas:
                continue    
            for j in range(i + 1, len(rutas_actuales)):
                if j in rutas_fusionadas:
                    continue
                ruta1 = rutas_actuales[i]
                ruta2 = rutas_actuales[j]
                
                nuevas_rutas, estado = mejorar_rutas("Heuristica_1",
                    ruta1, ruta2, arcos_entrada, grafo_inc, energia, min_energy_to,
                    min_cost_from, min_cost_to,c, tiempo, d, P, Q)
                                
                if estado:
                    # marca ambas rutas como fusionadas
                    rutas_fusionadas.add(i)
                    rutas_fusionadas.add(j)
                    
                    nuevas_rutas_iter.extend(nuevas_rutas)
                    mejoro = True
                    # reinicia el loop exterior con las rutas actualizadas
                    break
            if i in rutas_fusionadas:
                break  # sale también del loop exterior para reiniciar
        # reconstruye solucion_final: quita fusionadas y agrega nuevas
        solucion_final = (
            [r for idx, r in enumerate(rutas_actuales) if idx not in rutas_fusionadas]
            + nuevas_rutas_iter) 
    soluciones_finales.append(solucion_final)
soluciones_finales_ordenadas=sorted(soluciones_finales, key=lambda s: sum(r[2] for r in s))

#================================================
#         FASE 3: ASIGNACIÓN DE CARGADORES
#================================================

#Elegir entre la asignación exacta y la asignación greedy 
asig="greedy" # "exacta" o "greedy"
costo_solucion = None
solucion_completa = None

if asig == "greedy":
    for solucion in soluciones_finales_ordenadas:
        solucion_completa, costo, asignacion = asignacion_cargadores_GA(
            solucion, C, CR, n, c, energia, tiempo, ventana, E, B, numT)

        if asignacion:
            # asignación exitosa en primera instancia
            costo_solucion = costo
            break
        else:
            # la aignación falló, sigue con la siguiente solución
            costo_solucion = None
            solucion_completa = None
            continue
elif asig == "exacta":
    for solucion in soluciones_finales_ordenadas:
        costo= sum(r[2] for r in solucion) #calcula el costo de la solución sin asignación de cargadores
        asignacion, tiempo_asignacion= asignacion_cargadores_exacta(solucion, C, CR, n, c, energia, tiempo, ventana, E, B)
        
        if asignacion != 2 and asignacion != 13:
            costo_solucion=None
            continue
        else:
            costo_solucion = costo
            break  # solo queremos la primera solución completa (la de menor costo)