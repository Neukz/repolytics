"""Business queries over the marts star schema.

Every function takes an open DuckDB connection plus filters and returns a pandas
DataFrame.

Conventions honored from the warehouse contract:
- Facts key dates as integer `date_key` (YYYYMMDD); join `dim_dates` for real dates.
- Facts carry `repository_key` (an SCD2 version); join `dim_repositories` and group
  by `repository_name` (stable across versions) for display.
- `repos` is always a list of `repository_name`s; queries filter with `= ANY(?)`.
"""

from datetime import date

import duckdb
import pandas as pd

from lib.data import run_query


def _date_clause(date_from: date | None, date_to: date | None) -> tuple[str, list]:
    """`(sql_fragment, params)` bounding `d.full_date`, or empty when unset."""
    if date_from is None or date_to is None:
        return "", []
    return "and d.full_date between ? and ?", [date_from, date_to]


def all_repo_names(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Current repository names, for the sidebar filter (read dynamically)."""
    rows = conn.execute(
        "select repository_name from marts.dim_repositories "
        "where is_current order by repository_name"
    ).fetchall()
    return [r[0] for r in rows]


# ----- Overview -----
def overview_kpis(conn: duckdb.DuckDBPyConnection, repos: list[str]) -> pd.DataFrame:
    """Single-row headline KPIs across the selected repos."""
    sql = """
    with sel as (
        select repository_key, repository_name
        from marts.dim_repositories
        where repository_name = any(?)
    ),
    latest_metrics as (
        select m.repository_name, m.stars, m.forks,
               row_number() over (partition by m.repository_name
                                  order by m.date_key desc) as rn
        from marts.fct_repository_metrics m
        where m.repository_name = any(?)
    )
    select
        (select count(distinct repository_name) from sel) as repos,
        (select count(*)
           from marts.fct_commits join sel using (repository_key)) as commits,
        (select count(distinct contributor_key)
           from marts.fct_commits join sel using (repository_key)) as contributors,
        (select count(*)
           from marts.fct_pull_requests join sel using (repository_key)) as prs,
        (select coalesce(avg(is_merged::int), 0)
           from marts.fct_pull_requests join sel using (repository_key))
           as pr_merge_rate,
        (select count(*)
           from marts.fct_issues join sel using (repository_key)) as issues,
        (select coalesce(avg(is_closed::int), 0)
           from marts.fct_issues join sel using (repository_key))
           as issue_close_rate,
        (select count(*)
           from marts.fct_releases join sel using (repository_key)) as releases,
        (select coalesce(sum(stars), 0) from latest_metrics where rn = 1) as stars,
        (select coalesce(sum(forks), 0) from latest_metrics where rn = 1) as forks
    """
    return run_query(conn, sql, [repos, repos])


def repo_snapshot(conn: duckdb.DuckDBPyConnection, repos: list[str]) -> pd.DataFrame:
    """Current per-repo attributes + latest stars/forks/open_issues snapshot."""
    sql = """
    with latest as (
        select repository_name, stars, forks, open_issues,
               row_number() over (
                   partition by repository_name order by date_key desc
               ) as rn
        from marts.fct_repository_metrics
        where repository_name = any(?)
    )
    select
        d.repository_name, d.language, d.license_spdx, d.topics, d.created_at,
        l.stars, l.forks, l.open_issues
    from marts.dim_repositories d
    left join latest l on d.repository_name = l.repository_name and l.rn = 1
    where d.is_current and d.repository_name = any(?)
    order by l.stars desc nulls last
    """
    return run_query(conn, sql, [repos, repos])


def commits_per_month(
    conn: duckdb.DuckDBPyConnection,
    repos: list[str],
    date_from: date | None = None,
    date_to: date | None = None,
) -> pd.DataFrame:
    """Commit counts per calendar month per repo."""
    clause, params = _date_clause(date_from, date_to)
    sql = f"""
    select date_trunc('month', d.full_date) as month,
           dr.repository_name, count(*) as commits
    from marts.fct_commits c
    join marts.dim_dates d on c.date_key = d.date_key
    join marts.dim_repositories dr on c.repository_key = dr.repository_key
    where dr.repository_name = any(?) {clause}
    group by 1, 2 order by 1, 2
    """
    return run_query(conn, sql, [repos, *params])


# ----- Popularity & health -----
def stars_forks_over_time(
    conn: duckdb.DuckDBPyConnection, repos: list[str]
) -> pd.DataFrame:
    """Daily stars/forks snapshots per repo (sparse until snapshots accrue)."""
    sql = """
    select d.full_date as date, m.repository_name, m.stars, m.forks, m.open_issues
    from marts.fct_repository_metrics m
    join marts.dim_dates d on m.date_key = d.date_key
    where m.repository_name = any(?)
    order by 1, 2
    """
    return run_query(conn, sql, [repos])


def downloads_over_time(
    conn: duckdb.DuckDBPyConnection, repos: list[str]
) -> pd.DataFrame:
    """Daily PyPI download counts per package (sparse until backfilled)."""
    sql = """
    select d.full_date as date, f.package, f.download_count as downloads
    from marts.fct_daily_downloads f
    join marts.dim_dates d on f.date_key = d.date_key
    join marts.dim_repositories dr
      on f.repository_key = dr.repository_key and dr.repository_name = any(?)
    order by 1, 2
    """
    return run_query(conn, sql, [repos])


def downloads_vs_stars(
    conn: duckdb.DuckDBPyConnection, repos: list[str]
) -> pd.DataFrame:
    """Latest-day downloads vs current stars per repo (popularity correlation)."""
    sql = """
    with latest_stars as (
        select repository_name, repository_key, stars,
               row_number() over (
                   partition by repository_name order by date_key desc
               ) as rn
        from marts.fct_repository_metrics
        where repository_name = any(?)
    ),
    latest_dl as (
        select dr.repository_name, f.download_count,
               row_number() over (
                   partition by dr.repository_name order by f.date_key desc
               ) as rn
        from marts.fct_daily_downloads f
        join marts.dim_repositories dr on f.repository_key = dr.repository_key
    )
    select s.repository_name, s.stars, coalesce(dl.download_count, 0) as downloads
    from latest_stars s
    left join latest_dl dl on s.repository_name = dl.repository_name and dl.rn = 1
    where s.rn = 1
    """
    return run_query(conn, sql, [repos])


def health_components(
    conn: duckdb.DuckDBPyConnection, repos: list[str]
) -> pd.DataFrame:
    """Raw per-repo inputs to the composite health score (see lib.health)."""
    sql = """
    with base as (
        select repository_name from marts.dim_repositories
        where is_current and repository_name = any(?)
    ),
    commits90 as (
        select dr.repository_name, count(*) as commits_90d
        from marts.fct_commits c
        join marts.dim_repositories dr on c.repository_key = dr.repository_key
        where c.committed_at >= now() - interval '90 days'
          and dr.repository_name = any(?)
        group by 1
    ),
    pr12 as (
        select dr.repository_name, avg(p.is_merged::int) as pr_merge_rate
        from marts.fct_pull_requests p
        join marts.dim_dates d on p.opened_date_key = d.date_key
        join marts.dim_repositories dr on p.repository_key = dr.repository_key
        where d.full_date >= now() - interval '365 days'
          and dr.repository_name = any(?)
        group by 1
    ),
    iss12 as (
        select dr.repository_name, avg(i.is_closed::int) as issue_close_rate
        from marts.fct_issues i
        join marts.dim_dates d on i.opened_date_key = d.date_key
        join marts.dim_repositories dr on i.repository_key = dr.repository_key
        where d.full_date >= now() - interval '365 days'
          and dr.repository_name = any(?)
        group by 1
    ),
    rel as (
        select dr.repository_name,
               date_diff('day', max(r.published_at), now()) as days_since_release
        from marts.fct_releases r
        join marts.dim_repositories dr on r.repository_key = dr.repository_key
        where dr.repository_name = any(?)
        group by 1
    ),
    stars as (
        select repository_name, stars,
               row_number() over (
                   partition by repository_name order by date_key desc
               ) as rn
        from marts.fct_repository_metrics
        where repository_name = any(?)
    )
    select b.repository_name,
           coalesce(c.commits_90d, 0) as commits_90d,
           coalesce(p.pr_merge_rate, 0) as pr_merge_rate,
           coalesce(i.issue_close_rate, 0) as issue_close_rate,
           r.days_since_release,
           coalesce(s.stars, 0) as stars
    from base b
    left join commits90 c on b.repository_name = c.repository_name
    left join pr12 p on b.repository_name = p.repository_name
    left join iss12 i on b.repository_name = i.repository_name
    left join rel r on b.repository_name = r.repository_name
    left join stars s on b.repository_name = s.repository_name and s.rn = 1
    order by b.repository_name
    """
    # One bind per `any(?)`: base + commits90 + pr12 + iss12 + rel + stars.
    return run_query(conn, sql, [repos, repos, repos, repos, repos, repos])


# ----- Development velocity -----
def pr_velocity_monthly(
    conn: duckdb.DuckDBPyConnection,
    repos: list[str],
    date_from: date | None = None,
    date_to: date | None = None,
) -> pd.DataFrame:
    """Median time-to-merge (hours) by merge month, per repo."""
    clause, params = _date_clause(date_from, date_to)
    sql = f"""
    select date_trunc('month', d.full_date) as month,
           dr.repository_name,
           median(p.time_to_merge_hours) as median_merge_hours
    from marts.fct_pull_requests p
    join marts.dim_dates d on p.merged_date_key = d.date_key
    join marts.dim_repositories dr on p.repository_key = dr.repository_key
    where p.is_merged and dr.repository_name = any(?) {clause}
    group by 1, 2 order by 1, 2
    """
    return run_query(conn, sql, [repos, *params])


def pr_throughput_monthly(
    conn: duckdb.DuckDBPyConnection,
    repos: list[str],
    date_from: date | None = None,
    date_to: date | None = None,
) -> pd.DataFrame:
    """PRs opened, PRs merged, and merge rate by open month, per repo."""
    clause, params = _date_clause(date_from, date_to)
    sql = f"""
    select date_trunc('month', d.full_date) as month,
           dr.repository_name,
           count(*) as opened,
           sum(p.is_merged::int) as merged,
           avg(p.is_merged::int) as merge_rate
    from marts.fct_pull_requests p
    join marts.dim_dates d on p.opened_date_key = d.date_key
    join marts.dim_repositories dr on p.repository_key = dr.repository_key
    where dr.repository_name = any(?) {clause}
    group by 1, 2 order by 1, 2
    """
    return run_query(conn, sql, [repos, *params])


def issue_resolution_monthly(
    conn: duckdb.DuckDBPyConnection,
    repos: list[str],
    date_from: date | None = None,
    date_to: date | None = None,
) -> pd.DataFrame:
    """Median time-to-close (hours) and close rate by open month, per repo."""
    clause, params = _date_clause(date_from, date_to)
    sql = f"""
    select date_trunc('month', d.full_date) as month,
           dr.repository_name,
           median(i.time_to_close_hours) as median_close_hours,
           avg(i.is_closed::int) as close_rate
    from marts.fct_issues i
    join marts.dim_dates d on i.opened_date_key = d.date_key
    join marts.dim_repositories dr on i.repository_key = dr.repository_key
    where dr.repository_name = any(?) {clause}
    group by 1, 2 order by 1, 2
    """
    return run_query(conn, sql, [repos, *params])


def issue_label_breakdown(
    conn: duckdb.DuckDBPyConnection, repos: list[str], limit: int = 15
) -> pd.DataFrame:
    """Top issue labels by volume across the selected repos, split open vs closed.

    A triage view of what the open-source backlog is made of.
    """
    sql = """
    select dl.label_name,
           count(*) as issues,
           sum((not i.is_closed)::int) as open,
           sum(i.is_closed::int) as closed
    from marts.bridge_issue_labels b
    join marts.fct_issues i on b.issue_key = i.issue_key
    join marts.dim_repositories dr on i.repository_key = dr.repository_key
    join marts.dim_labels dl on b.label_key = dl.label_key
    where dr.repository_name = any(?)
    group by 1
    order by issues desc
    limit ?
    """
    return run_query(conn, sql, [repos, limit])


# ----- Contributors & community -----
def commit_share(conn: duckdb.DuckDBPyConnection, repos: list[str]) -> pd.DataFrame:
    """Commits per contributor per repo (feeds bus factor + Lorenz curve)."""
    sql = """
    select dr.repository_name, co.username, count(*) as commits
    from marts.fct_commits c
    join marts.dim_repositories dr on c.repository_key = dr.repository_key
    join marts.dim_contributors co on c.contributor_key = co.contributor_key
    where dr.repository_name = any(?)
    group by 1, 2
    """
    return run_query(conn, sql, [repos])


def contributor_leaderboard(
    conn: duckdb.DuckDBPyConnection, repos: list[str], limit: int = 20
) -> pd.DataFrame:
    """Top contributors by commits across the selected repos."""
    sql = """
    select co.username, count(*) as commits,
           count(distinct dr.repository_name) as projects
    from marts.fct_commits c
    join marts.dim_repositories dr on c.repository_key = dr.repository_key
    join marts.dim_contributors co on c.contributor_key = co.contributor_key
    where dr.repository_name = any(?)
    group by 1 order by commits desc limit ?
    """
    return run_query(conn, sql, [repos, limit])


def retention_cohort(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Monthly contributor retention: % of a first-active cohort active N months on.

    Repo-agnostic: the mart's grain is contributor x month with no repository_key, so
    retention spans the whole tracked set and cannot be filtered by repo.
    """
    sql = """
    with active as (
        select distinct contributor_key, date_trunc('month', event_month) as month
        from marts.fct_contributor_activity_monthly
    ),
    cohort as (
        select contributor_key, min(month) as cohort_month
        from active group by 1
    ),
    joined as (
        select c.cohort_month,
               date_diff('month', c.cohort_month, a.month) as months_since,
               a.contributor_key
        from active a join cohort c on a.contributor_key = c.contributor_key
    ),
    sizes as (select cohort_month, count(*) as cohort_size from cohort group by 1)
    select j.cohort_month,
           j.months_since,
           count(distinct j.contributor_key) as active,
           s.cohort_size,
           count(distinct j.contributor_key) * 1.0 / s.cohort_size as retention
    from joined j join sizes s on j.cohort_month = s.cohort_month
    where j.months_since >= 0
    group by 1, 2, s.cohort_size
    order by 1, 2
    """
    return run_query(conn, sql, [])


def active_contributors_monthly(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Monthly active contributors, split into new vs. returning.

    Repo-agnostic like `retention_cohort` (the mart has no repository grain).
    """
    sql = """
    with monthly as (
        select distinct contributor_key, date_trunc('month', event_month) as month
        from marts.fct_contributor_activity_monthly
    ),
    cohort as (
        select contributor_key, min(month) as first_month from monthly group by 1
    )
    select m.month,
           count(*) as active,
           sum((m.month = c.first_month)::int) as new_contributors,
           sum((m.month > c.first_month)::int) as returning_contributors
    from monthly m join cohort c using (contributor_key)
    group by 1 order by 1
    """
    return run_query(conn, sql, [])


def multi_project_contributors(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Contributors active across more than one tracked project."""
    sql = """
    select username, total_commits, total_prs_opened, total_prs_merged,
           distinct_projects_count, primary_project
    from marts.dim_contributors
    where distinct_projects_count > 1
    order by distinct_projects_count desc, total_commits desc
    """
    return run_query(conn, sql, [])


# ----- Releases & cadence -----
def releases(conn: duckdb.DuckDBPyConnection, repos: list[str]) -> pd.DataFrame:
    """All releases with publish timestamps, per repo (timeline)."""
    sql = """
    select dr.repository_name, r.tag_name, r.release_name, r.published_at
    from marts.fct_releases r
    join marts.dim_repositories dr on r.repository_key = dr.repository_key
    where dr.repository_name = any(?)
    order by r.published_at
    """
    return run_query(conn, sql, [repos])


def release_gaps(conn: duckdb.DuckDBPyConnection, repos: list[str]) -> pd.DataFrame:
    """Days between consecutive releases per repo (cadence distribution)."""
    sql = """
    select repository_name, gap_days
    from (
        select dr.repository_name,
               date_diff('day',
                   lag(r.published_at) over (
                       partition by dr.repository_name order by r.published_at
                   ),
                   r.published_at) as gap_days
        from marts.fct_releases r
        join marts.dim_repositories dr on r.repository_key = dr.repository_key
        where dr.repository_name = any(?)
    ) t
    where gap_days is not null
    """
    return run_query(conn, sql, [repos])
