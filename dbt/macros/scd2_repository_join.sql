{#-
  Resolve a fact repository_key against SCD2 dim_repositories using a half-open date
  range (event_date >= valid_from AND < valid_to), so each event maps to the
  repository version current when it occurred. Select `<alias>.repository_key` after.

  The mutable `_repo` string is first resolved to the immutable GitHub
  `repository_id` via int_repository_mapping; the SCD2 join is then keyed on the
  ID. This survives repository renames and transfers. Callers must not use the
  internal `_repo_map` alias.

    repo_expr - SQL expression for the repository full name (owner/name)
    date_expr - SQL expression for the event date (cast to date)
    alias     - alias bound to dim_repositories (default 'r')
-#}
{% macro scd2_repository_join(repo_expr, date_expr, alias='r') -%}
left join {{ ref('int_repository_mapping') }} _repo_map
    on {{ repo_expr }} = _repo_map.repo
left join {{ ref('dim_repositories') }} {{ alias }}
    on _repo_map.repository_id = {{ alias }}.repository_id
    and {{ date_expr }} >= {{ alias }}.valid_from
    and {{ date_expr }} < {{ alias }}.valid_to
{%- endmacro %}
