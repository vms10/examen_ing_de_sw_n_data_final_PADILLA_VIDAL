"""Airflow DAG that orchestrates the medallion pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
# from airflow.providers.standard.operators.python import PythonOperator


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from include.transformations import clean_daily_transactions

RAW_DIR = BASE_DIR / "data/raw"
CLEAN_DIR = BASE_DIR / "data/clean"
QUALITY_DIR = BASE_DIR / "data/quality"
DBT_DIR = BASE_DIR / "dbt"
PROFILES_DIR = BASE_DIR / "profiles"
WAREHOUSE_PATH = BASE_DIR / "warehouse/medallion.duckdb"


def _build_env(ds_nodash: str) -> dict[str, str]:
    """Build environment variables needed by dbt commands."""
    env = os.environ.copy()
    env.update(
        {
            "DBT_PROFILES_DIR": str(PROFILES_DIR),
            "CLEAN_DIR": str(CLEAN_DIR),
            "DS_NODASH": ds_nodash,
            "DUCKDB_PATH": str(WAREHOUSE_PATH),
        }
    )
    return env


def _run_dbt_command(command: str, ds_nodash: str) -> subprocess.CompletedProcess:
    """Execute a dbt command and return the completed process."""
    env = _build_env(ds_nodash)
    return subprocess.run(
        [
            "dbt",
            command,
            "--project-dir",
            str(DBT_DIR),
        ],
        cwd=DBT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------
# BRONZE TASK — CLEAN RAW CSV
# ---------------------------------------------------------------------

# def bronze_task(ds_nodash: str):
#     """
#     Bronze step: read the raw CSV for the execution date, clean it
#     using clean_daily_transactions, and save parquet in CLEAN_DIR.
#     """
#     raw_file = RAW_DIR / f"transactions_{ds_nodash}.csv"
#     if not raw_file.exists():
#         raise AirflowException(f"Raw file not found: {raw_file}")

#     out_file = CLEAN_DIR / f"transactions_{ds_nodash}_clean.parquet"
#     CLEAN_DIR.mkdir(exist_ok=True, parents=True)

#     clean_daily_transactions(str(raw_file), str(out_file))

#     return f"Bronze OK → {out_file}"


def bronze_task(ds, ds_nodash, **context):
    execution_date = context["logical_date"].date()

    clean_daily_transactions(
        execution_date=execution_date,
        raw_dir=RAW_DIR,
        clean_dir=CLEAN_DIR,
    )



# ---------------------------------------------------------------------
# SILVER TASK — DBT RUN
# ---------------------------------------------------------------------

def silver_task(ds_nodash: str):
    """Silver step: run dbt run."""
    result = _run_dbt_command("run", ds_nodash)

    if result.returncode != 0:
        raise AirflowException(
            f"dbt run failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    return "dbt run completed"


# ---------------------------------------------------------------------
# GOLD TASK — DBT TEST + QUALITY FILE
# ---------------------------------------------------------------------

def gold_task(ds_nodash: str):
    """Gold step: dbt test + generate dq_results_<ds>.json."""
    result = _run_dbt_command("test", ds_nodash)

    QUALITY_DIR.mkdir(exist_ok=True, parents=True)
    out_file = QUALITY_DIR / f"dq_results_{ds_nodash}.json"

    passed = result.returncode == 0

    with open(out_file, "w") as f:
        json.dump(
            {
                "date": ds_nodash,
                "passed": passed,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            f,
            indent=2,
        )

    # Even if tests fail, file is written → but task should fail.
    if not passed:
        raise AirflowException("dbt test failed — see dq_results json")

    return "dbt tests passed"


# ---------------------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------------------

def build_dag() -> DAG:
    """Construct the medallion pipeline DAG with bronze/silver/gold tasks."""
    with DAG(
        description="Bronze/Silver/Gold medallion demo with pandas, dbt, and DuckDB",
        dag_id="medallion_pipeline",
        schedule="0 6 * * *",
        start_date=pendulum.datetime(2025, 12, 1, tz="UTC"),
        catchup=True,
        max_active_runs=1,
    ) as medallion_dag:
        
        # bronze = PythonOperator(
        #     task_id="bronze_clean",
        #     python_callable=bronze_task,
        #     op_kwargs={"ds_nodash": "{{ ds_nodash }}"},
        # )

        bronze = PythonOperator(
            task_id="bronze_clean",
            python_callable=bronze_task,
            op_kwargs={},
        )


        silver = PythonOperator(
            task_id="silver_dbt_run",
            python_callable=silver_task,
            op_kwargs={"ds_nodash": "{{ ds_nodash }}"},
        )

        gold = PythonOperator(
            task_id="gold_dbt_tests",
            python_callable=gold_task,
            op_kwargs={"ds_nodash": "{{ ds_nodash }}"},
        )

        bronze >> silver >> gold
    
    # pass
    return medallion_dag
    
dag = build_dag()
