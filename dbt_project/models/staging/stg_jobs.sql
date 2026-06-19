{% if target.type == 'duckdb' %}
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
from read_parquet('{{ var("silver_path") }}')

{% else %}
-- Fallback for non-duckdb targets: read from existing source if available
select
  job_id,
  title,
  company,
  location,
  remote,
  url,
  description,
  post_date,
  fetched_at,
  salary,
  tags
from {{ source('job_data', 'gold_jobs') }}
{% endif %}
