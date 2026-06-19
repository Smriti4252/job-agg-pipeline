
  
    
    

    create  table
      "duckdb_local"."main"."gold_jobs__dbt_tmp"
  
    as (
      

with src as (
  select * from "duckdb_local"."main"."stg_jobs"
),
canonical as (
  select *,
    lower(regexp_replace(url, '\?.*', '')) as canon_url_raw
  from src
),
canon_trim as (
  select *,
    regexp_replace(rtrim(canon_url_raw, '/'), '/+$', '') as canon_url
  from canonical
),
ranked as (
  select *,
    row_number() over (partition by canon_url order by coalesce(fetched_at, '1970-01-01') desc) as rn
  from canon_trim
),
scored as (
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
    tags,
    -- scoring logic: preserve existing heuristics
    (case when title like '%junior%' or title like '%entry%' or title like '%fresher%' or title like '%intern%' or title like '%graduate%' then 2.0 else 0 end
     + case when remote = 1 then 1.0 else 0 end
     + (
         (case when title like '%etl%' or description like '%etl%' then 1 else 0 end)
       + (case when title like '%sql%' or description like '%sql%' then 1 else 0 end)
       + (case when title like '%python%' or description like '%python%' then 1 else 0 end)
       + (case when title like '%dbt%' or description like '%dbt%' then 1 else 0 end)
       + (case when title like '%snowflake%' or description like '%snowflake%' then 1 else 0 end)
       + (case when title like '%spark%' or description like '%spark%' then 1 else 0 end)
     ) * 0.5
    )::DOUBLE AS score,
    'Hi — I found your ' || coalesce(title, 'role') || ' role at ' || coalesce(company, 'your team') || '. I''m building data pipelines and have hands-on SQL & Python experience. Would love to connect — thanks!' as outreach_message
  from ranked
  where rn = 1
)
select * from scored
    );
  
  