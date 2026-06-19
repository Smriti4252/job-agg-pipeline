{{ config(materialized='table') }}

select
  count(*) as total_jobs,
  count(distinct company) as company_count,
  sum(case when remote = 1 then 1 else 0 end) as remote_jobs_count,
  avg(score) as avg_score
from {{ ref('gold_jobs') }}
