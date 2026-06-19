
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select title
from "duckdb_local"."main"."gold_jobs"
where title is null



  
  
      
    ) dbt_internal_test