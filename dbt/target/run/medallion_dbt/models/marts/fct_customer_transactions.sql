
  
    
    

    create  table
      "medallion"."main"."fct_customer_transactions__dbt_tmp"
  
    as (
      -- depends_on: "medallion"."main"."stg_transactions"

with base as (
    select *
    from "medallion"."main"."stg_transactions"
),

agg as (
    select
        customer_id,
        count(*) as transaction_count,
        sum(case when status = 'completed' then amount else 0 end) as total_amount_completed,
        sum(amount) as total_amount_all
    from base
    group by customer_id
)

select *
from agg
    );
  
  