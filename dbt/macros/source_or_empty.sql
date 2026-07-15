{#-
  Return `select * from <source>` when the source relation exists, otherwise a typed
  empty result. dlt only materializes a child table when some row populated the list,
  so a list empty across every ingested row leaves the child table absent; this keeps
  the build resilient to that case.

  `columns` is a mapping of column name -> SQL type covering the columns the caller reads.
-#}
{% macro source_or_empty(source_name, table_name, columns) -%}
    {%- set rel = source(source_name, table_name) -%}
    {%- set existing = adapter.get_relation(
        database=rel.database, schema=rel.schema, identifier=rel.identifier
    ) -%}
    {%- if existing is not none -%}
        select * from {{ rel }}
    {%- else -%}
        select
        {%- for col, dtype in columns.items() %}
            cast(null as {{ dtype }}) as {{ col }}{{ "," if not loop.last }}
        {%- endfor %}
        where false
    {%- endif -%}
{%- endmacro %}
