{#-
  Resolve a fact repository_key against SCD2 dim_repositories using a half-open date
  range (event_date >= valid_from AND < valid_to), so each event maps to the
  repository version current when it occurred. Select `<alias>.repository_key` after.

    repo_expr - SQL expression for the repository full name (owner/name)
    date_expr - SQL expression for the event date (cast to date)
    alias     - alias bound to dim_repositories (default 'r')
-#}
{% macro scd2_repository_join(repo_expr, date_expr, alias='r') -%}
left join {{ ref('dim_repositories') }} {{ alias }}
    on {{ repo_expr }} = {{ alias }}.repository_name
    and {{ date_expr }} >= {{ alias }}.valid_from
    and {{ date_expr }} < {{ alias }}.valid_to
{%- endmacro %}
