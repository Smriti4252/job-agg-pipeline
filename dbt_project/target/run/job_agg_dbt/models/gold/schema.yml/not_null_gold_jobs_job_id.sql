
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select job_id
from "duckdb_local"."main"."gold_jobs"
where job_id is null



  
  
      
    ) dbt_internal_test