
  
    
    

    create  table
      "duckdb_local"."main"."job_metrics__dbt_tmp"
  
    as (
      

select
  count(*) as total_jobs,
  count(distinct company) as company_count,
  sum(case when remote = 1 then 1 else 0 end) as remote_jobs_count,
  avg(score) as avg_score
from "duckdb_local"."main"."gold_jobs"
    );
  
  