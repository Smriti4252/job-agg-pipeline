with source_data as (
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
        score,
        outreach_message
    from "JOB_AGG_DB"."GOLD"."gold_jobs"
)

select
    job_id,
    trim(title) as title,
    company,
    location,
    remote,
    url,
    description,
    post_date,
    fetched_at,
    salary,
    tags,
    score,
    outreach_message
from source_data
where trim(title) is not null
  and trim(title) <> ''