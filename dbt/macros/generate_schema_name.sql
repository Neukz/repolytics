{#
    Use the configured custom schema name verbatim (e.g. `staging`, `marts`)
    instead of dbt default `{target_schema}_{custom}` concatenation, so the
    warehouse layers map to clean schema names.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
