
  
  create view "duckdb_local"."main"."stg_jobs__dbt_tmp" as (
    
-- staging model for DuckDB: read silver Parquet and normalize fields
select
  coalesce(cast(job_id as varchar), '') as job_id,
  lower(trim(coalesce(title, ''))) as title,
  lower(trim(coalesce(company, ''))) as company,
  trim(coalesce(location, '')) as location,
  cast(coalesce(remote, 0) as integer) as remote,
  trim(coalesce(url, '')) as url,
  coalesce(description, '') as description,
  case when length(trim(coalesce(post_date, ''))) = 0 then null else post_date end as post_date,
  case when length(trim(coalesce(fetched_at, ''))) = 0 then null else fetched_at end as fetched_at,
  trim(coalesce(salary, '')) as salary,
  trim(coalesce(tags, '')) as tags
from read_parquet('C:/Users/sharm/job-agg-pipeline/data/silver/silver.parquet')


  );
