{#
    prod: models land in their folder's dataset as-is (staging, marts, ...).
    dev:  prefixed with the target dataset (dbt_dev_staging, dbt_dev_marts, ...)
          so development never overwrites what the site serves.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
