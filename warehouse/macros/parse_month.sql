{#- Lending Club stores months as text like 'Dec-2015'. -#}
{% macro parse_month(column) -%}
    cast(try_strptime({{ column }}, '%b-%Y') as date)
{%- endmacro %}
