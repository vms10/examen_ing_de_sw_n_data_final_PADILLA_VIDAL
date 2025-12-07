
  
  create view "medallion"."main"."stg_transactions__dbt_tmp" as (
    


with source as (
    select *
    from read_parquet(
        '/home/msol/examen_vidal_padilla/examen_ing_de_sw_n_data_final_PADILLA_VIDAL/data/clean/transactions_20251201_clean.parquet'
    )
)

-- TODO: Completar el modelo para que cree la tabla staging con los tipos adecuados segun el schema.yml.
select
    cast(transaction_id as varchar)      as transaction_id,
    cast(customer_id as varchar)         as customer_id,
    cast(amount as double)               as amount,
    cast(status as varchar)              as status,
    cast(transaction_ts as timestamp)    as transaction_ts,
    cast(transaction_date as date)       as transaction_date
from source
  );
