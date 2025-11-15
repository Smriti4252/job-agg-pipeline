{{ config(materialized='table') }}

select
    JOB_ID,
    TITLE,
    COMPANY,
    LOCATION,
    REMOTE,
    URL,
    DESCRIPTION,
    POST_DATE,
    FETCHED_AT,
    SALARY,
    TAGS,
    SCORE,
    OUTREACH_MESSAGE,
    iff(SALARY is null, 0, 1) as HAS_SALARY_FLAG
from {{ ref('stg_gold_jobs') }}
