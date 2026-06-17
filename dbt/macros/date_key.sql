{#-
  Surrogate date key (YYYYMMDD integer) from a timestamp/date expression.
  Centralizes the format used by every fact join to dim_dates.
-#}
{% macro date_key(ts) -%}
    cast(strftime({{ ts }}, '%Y%m%d') as integer)
{%- endmacro %}
