# Padilla - Vidal: ver branch main para corrección

# Medallion Architecture Demo (Airflow + dbt + DuckDB)

Este proyecto implementa un pipeline de datos siguiendo el patrón Medallion Architecture (Bronze / Silver / Gold) utilizando Airflow para la orquestación, Pandas para la limpieza inicial, dbt para el modelado y DuckDB como data warehouse local.

El objetivo es demostrar un flujo completo de ingestión, transformación, validación y observabilidad de calidad de datos.

🧱 Arquitectura Medallion

El pipeline consta de tres capas bien definidas:

🟤 Bronze

- Airflow lee un archivo CSV crudo correspondiente a la fecha de ejecución del DAG.

- Se aplica una limpieza básica con Pandas:

    - Normalización de columnas

    - Conversión de tipos

    - Eliminación de duplicados

    - Validación de campos obligatorios

- El resultado se guarda como Parquet limpio.

⚪ Silver

- Se ejecuta dbt run.

- dbt consume los archivos Parquet limpios.

- Se generan modelos staging y fact tables en DuckDB.

🟡 Gold

- Se ejecuta dbt test.

- Se validan reglas de calidad sobre los modelos finales.

- Se genera un archivo JSON con el resultado de los data quality checks para auditoría.


## 📁 Estructura del proyecto

```
├── dags/
│   └── medallion_medallion_dag.py
├── data/
│   ├── raw/
│   │   └── transactions_20251201.csv
│   ├── clean/
│   └── quality/
├── dbt/
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   └── marts/
│   └── tests/generic/
├── include/
│   └── transformations.py
├── profiles/
│   └── profiles.yml
├── warehouse/
│   └── medallion.duckdb (se genera en tiempo de ejecución)
└── requirements.txt
```

## ⚙️Requisitos 

- Python 3.10+
- DuckDB CLI opcional para inspeccionar la base.

📦 Instala dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 🌱 Configuración de variables de entorno
Correr esto en la terminal cada vez que se levante Airflow 
```bash
export AIRFLOW_HOME=$(pwd)/airflow_home
export DBT_PROFILES_DIR=$(pwd)/profiles
export DUCKDB_PATH=$(pwd)/warehouse/medallion.duckdb
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
```

## 🚀 Inicializar Airflow

```bash
airflow standalone
```

En el output de `airflow standalone` buscar la contraseña para loguearse. Ej:
```
standalone | Airflow is ready
standalone | Login with username: admin  password: pPr9XXxFzgrgGd6U
```
De no encontrarlo lo podes ver en `cat airflow_home/simple_auth_manager_passwords.json.generated`

La UI queda disponible en:

👉 http://localhost:8080 

## ▶️ Ejecutar el DAG - Trigger manual con Advanced options 

1. Vamos a usar como data el archivo `data/raw/transactions_20251201.csv`.

2. Desde la UI disparamos el DAG usando la fecha deseada, en este caso "2025-12-01".

Para eso usamos la opcion de "Advanced Options" para elegir la fecha para la cual tenemos el csv. De nuestra experiencia ademas del dia, es importante tambien la hora. Aconsejamos ejecutarlo con hora 9AM (nos fallaba con horas como 21hs). A continuación se muestra en un print de cómo hicimos eso

<img width="1112" height="495" alt="image" src="https://github.com/user-attachments/assets/d2532476-439f-41d0-a770-8cfcd70f1fc8" />

El DAG ejecutará secuencialmente:

- `bronze_clean`: llama a `clean_daily_transactions` para crear `data/clean/transactions_<ds>_clean.parquet`.
- `silver_dbt_run`: ejecuta `dbt run` apuntando al proyecto `dbt/` y carga la data en DuckDB.
- `gold_dbt_tests`: corre `dbt test` y escribe `data/quality/dq_results_<ds>.json` con el status (`passed`/`failed`).

Luego de haber:
- Implementado tareas de Airflow (dags/medallion_medallion_dag.py).
- Implementado modelos de dbt según cada archivo schema.yml (dbt/models completamos los schemas.yml tanto de /staging y /marts)

Logramos ejecutar con éxito las 3 tareas. A continuación mostramos los logs de un run en airflow donde podemos ver que terminaron en success.

### Bronze
<img width="1822" height="552" alt="image" src="https://github.com/user-attachments/assets/aec5d609-4606-489e-b10f-de2b90264a2c" />

### Silver
<img width="1825" height="592" alt="image" src="https://github.com/user-attachments/assets/dedf38a2-5197-4663-8496-936176edd06d" />

### Gold
<img width="1823" height="537" alt="image" src="https://github.com/user-attachments/assets/4e2f762c-76ae-40eb-b37a-f404c298b7b5" />
 

## 🔍 Verificación de resultados por capa

### Bronze
1. Revisa que exista el parquet más reciente:
    ```bash
    find data/clean/ | grep transactions_*
    data/clean/transactions_20251201_clean.parquet
    ```
Mostramos resultados exitosos:
<img width="1271" height="60" alt="image" src="https://github.com/user-attachments/assets/19af37ad-86e5-4a17-9d70-845ecf56ddc1" />


2. Inspecciona las primeras filas para confirmar la limpieza aplicada:
    ```bash
    duckdb -c "
      SELECT *
      FROM read_parquet('data/clean/transactions_20251201_clean.parquet')
      LIMIT 5;
    "
    ```
Mostramos resultados exitosos:
<img width="1110" height="337" alt="image" src="https://github.com/user-attachments/assets/cf934623-f018-4f12-b413-3ada37b02920" />

### Silver
1. Abre el warehouse y lista las tablas creadas por dbt:
    ```bash
    duckdb warehouse/medallion.duckdb -c ".tables"
    ```
  Mostramos resultados exitosos:
<img width="1370" height="57" alt="image" src="https://github.com/user-attachments/assets/b7bb2d0f-57a2-46ee-8b78-cc92edf280a9" />


2. Ejecuta consultas puntuales para validar cálculos intermedios:
    ```bash
    duckdb warehouse/medallion.duckdb -c "
      SELECT *
      FROM fct_customer_transactions
      LIMIT 10;
    "
    ```
Mostramos resultados exitosos:
<img width="1296" height="313" alt="image" src="https://github.com/user-attachments/assets/f7b5c54c-f493-4c79-8782-b4fc9c560528" />


### Gold
1. Revisa que exista el parquet más reciente:
    ```bash
    $ find data/quality/*.json
    data/quality/dq_results_20251201.json
    ```
El resultado: 
<img width="1167" height="60" alt="image" src="https://github.com/user-attachments/assets/0dcfa875-b8d4-48f4-9d5c-ea50e58b0b18" />

2. Confirma la generación del archivo de data quality:

    ```bash
    cat data/quality/dq_results_20251201.json | jq
    ```
El resultado donde vemos que todo corrio ok: 

<img width="1313" height="912" alt="image" src="https://github.com/user-attachments/assets/3ab63ff4-ec0d-4696-a15f-480758180ff0" />

## 🧪 Tests
 Implementamos los tests non_future.sql y non_greater_than.sql ubicados en:

```
├── dbt/
│   ├── tests/generic/
│   │   ├──  non_negative.sql
│   │   └──  non_future.sql
│   │   └──   non_greater_than.sql
```
✔️ non_future.sql se fija que todas las fechas de transacciones (`transaction_ts`) sean menores o iguales al momento de ejecución del test

✔️  non_greater_than.sql se fija que `total_amount_completed` no sea mayor que `total_amount_all`

## 🎨 Formato y calidad de código

Usamos las herramientas incluidas en `requirements.txt` para mantener un estilo consistente y detectar problemas antes de ejecutar el DAG.

### Black (formateo)

Aplicamos Black sobre los módulos de Python del proyecto. Añade rutas extra si incorporas nuevos paquetes.

```bash
black dags include
```

### isort (orden de imports)

Ordenamos automáticamente los imports para evitar diffs innecesarios y mantener un estilo coherente.

```bash
isort dags include
```

### Pylint (estático)

Ejecuta Pylint sobre las mismas carpetas para detectar errores comunes y mejorar la calidad del código.

```bash
pylint dags/*.py include/*.py
```

Mostramos la ejecucion del formateo 
<img width="1277" height="417" alt="image" src="https://github.com/user-attachments/assets/d0c99a5c-cd94-4263-8610-0d4ea8041bad" />


## Posibles mejoras al proyecto
- Manejar explícitamente el caso donde no exista archivo raw para una fecha determinada.
- Parametrizar múltiples fuentes o múltiples archivos diarios.
- Persistir históricos en Silver/Gold en lugar de sobrescritura.
- Incorporar particionado por fecha en DuckDB.
- Integrar alertas automáticas ante fallos de data quality.
- Versionar esquemas y snapshots en dbt.
- Externalizar configuración de paths y parámetros del DAG.
















