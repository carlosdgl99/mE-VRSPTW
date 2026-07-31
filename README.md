# mE-VRSPTW
# mE-VRSPTW

Este repositorio contiene el código fuente, las instancias de prueba y los resultados computacionales desarrollados en el marco del proyecto de tesis sobre el **problema de enrutamiento de vehículos eléctricos con ventanas de tiempo y programación de recargas nocturnas (mE-VRSPTW)**.

El objetivo principal del proyecto es desarrollar, implementar y evaluar computacionalmente métodos de optimización y **heurísticas primales** para resolver el problema de enrutamiento de una flota de vehículos eléctricos, considerando simultáneamente restricciones de capacidad, autonomía de los vehículos, ventanas de tiempo de los clientes y programación de las recargas durante el período nocturno.

El repositorio contempla dos componentes principales. En primer lugar, se presenta la **formulación de un modelo matemático compacto de programación lineal entera mixta (MILP)** para representar el problema mE-VRSPTW y obtener soluciones mediante un enfoque exacto basado en optimización matemática. En segundo lugar, se implementan **tres heurísticas primales**, diseñadas para obtener soluciones factibles de buena calidad de manera eficiente, especialmente para instancias de mayor tamaño.

Además, se incluyen los resultados obtenidos mediante la experimentación computacional, permitiendo analizar y comparar el desempeño del modelo compacto y de las heurísticas propuestas en términos de calidad de las soluciones, tiempo computacional y capacidad para resolver las instancias de prueba.

## Estructura del repositorio

La estructura principal del repositorio se organiza de la siguiente manera:

* **`src/`**: contiene el código fuente correspondiente a la implementación del modelo compacto, las heurísticas primales y los procedimientos computacionales utilizados para la resolución del problema.
* **`data/`**: contiene las instancias y los datos utilizados en los experimentos computacionales.
* **`Resultados/`**: contiene los resultados obtenidos a partir de la ejecución del modelo compacto y de las heurísticas desarrolladas.
* **`README.md`**: contiene la documentación general del proyecto y las instrucciones necesarias para comprender y reproducir los experimentos.

## Metodología

El desarrollo computacional del proyecto se estructura en las siguientes etapas:

1. **Formulación del modelo compacto:** se desarrolla un modelo de programación lineal entera mixta para representar el problema mE-VRSPTW, integrando las decisiones de enrutamiento de los vehículos eléctricos y la programación de sus recargas nocturnas.

2. **Implementación computacional:** se implementa el modelo matemático utilizando Python y la interfaz GurobiPy, empleando **Gurobi Optimizer** como solucionador de problemas de optimización.

3. **Desarrollo de heurísticas primales:** se implementan tres heurísticas primales, denominadas **H1, H2 y H3**, orientadas a obtener soluciones factibles y de buena calidad en tiempos computacionales reducidos.

4. **Experimentación computacional:** se realizan experimentos sobre diferentes conjuntos de instancias para evaluar el comportamiento del modelo compacto y de las heurísticas propuestas.

5. **Análisis de resultados:** se comparan los métodos implementados considerando métricas como la calidad de las soluciones, el tiempo de ejecución y el número de instancias resueltas.

## Problema abordado

**Electric Vehicle Routing Problem with Scheduled Overnight Recharging and Time Windows (mE-VRSPTW)**.

El problema combina las decisiones de **enrutamiento de vehículos eléctricos** con la **programación de sus recargas durante el período nocturno**, considerando restricciones de capacidad de los vehículos, autonomía, ventanas de tiempo de los clientes y disponibilidad de períodos de recarga.

El objetivo consiste en determinar rutas factibles para los vehículos eléctricos y programar adecuadamente sus recargas, buscando optimizar el criterio definido en el modelo, mientras se satisfacen las restricciones operativas del problema.

## Contenido del repositorio

Este repositorio proporciona los recursos computacionales asociados al desarrollo de la tesis, incluyendo:

* Formulación e implementación de un **modelo compacto MILP** para el problema mE-VRSPTW.
* Código fuente de las metodologías y algoritmos implementados.
* Implementación de las **tres heurísticas primales H1, H2 y H3**.
* Instancias y datos utilizados en los experimentos.
* Resultados computacionales obtenidos mediante el modelo compacto.
* Resultados computacionales obtenidos mediante las heurísticas primales.
* Recursos necesarios para facilitar la **reproducibilidad y validación de los experimentos** presentados en el proyecto de tesis.

## Tecnologías utilizadas

* **Python**
* **Gurobi Optimizer**
* **GurobiPy**

## Propósito

El repositorio tiene como finalidad servir como soporte computacional para el proyecto de tesis y proporcionar una base reproducible para el estudio del problema mE-VRSPTW. Se busca facilitar la consulta de la formulación matemática, la implementación de los métodos de solución y el análisis de los resultados computacionales obtenidos.

