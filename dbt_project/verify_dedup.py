import duckdb

con = duckdb.connect('../data/duckdb_local.db')

result = con.execute("""
    select
        count(*) as total,
        count(distinct url) as distinct_urls,
        sum(case when url = '' then 1 else 0 end) as empty_urls
    from stg_jobs
""").fetchall()

print(result)