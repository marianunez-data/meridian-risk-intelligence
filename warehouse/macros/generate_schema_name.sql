{#- Use the layer name as the schema (silver, gold, reference) instead of
    dbt's default "<target>_<custom>" so the warehouse reads like a medallion. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
