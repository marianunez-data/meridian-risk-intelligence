{#- Household figure for joint applications, individual figure otherwise. -#}
{% macro effective(column) -%}
    case when application_type = 'joint app' then {{ column }}_joint else {{ column }} end
{%- endmacro %}
