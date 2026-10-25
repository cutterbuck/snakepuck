{#
    Reconcile a model against its Phase 0 golden snapshot (the old Python pipeline's output).

    Joins the two on `keys` and compares every golden column. Returns one row per
    key that is missing on either side or has any cell that differs, with the
    names of the differing columns. Numbers match within `tolerance` (rounded
    stats can differ by one unit in the last place from summation order).
    `column_tolerance` overrides it per column, e.g. {tot_atoi: 0.11} for
    one-decimal values where an exact .x5 tie can round either way.
    Single pass over both tables, so the cost is one scan of each.
#}
{% test matches_golden(model, golden, keys, tolerance=0.0011, column_tolerance={}, ignore=[]) %}

{%- set numeric_types = ['INT64', 'INTEGER', 'FLOAT64', 'FLOAT', 'NUMERIC', 'BIGNUMERIC'] -%}
{%- set columns = [] -%}
{%- for col in adapter.get_columns_in_relation(golden) -%}
    {%- if col.name not in keys and col.name not in ignore -%}
        {%- do columns.append(col) -%}
    {%- endif -%}
{%- endfor -%}

with model_rows as (
    select *, true as _in_model from {{ model }}
),

golden_rows as (
    select *, true as _in_golden from {{ golden }}
),

compared as (
    select
        {% for key in keys %}
        coalesce(m.{{ key }}, g.{{ key }}) as {{ key }},
        {% endfor %}
        case
            when g._in_golden is null then 'only in model'
            when m._in_model is null then 'only in golden'
        end as missing,
        array_concat(
            {% for col in columns %}
            {% if col.data_type | upper in numeric_types %}
            if(
                (m.{{ col.name }} is null and g.{{ col.name }} is null)
                or abs(m.{{ col.name }} - g.{{ col.name }}) <= {{ column_tolerance.get(col.name, tolerance) }},
                [], ['{{ col.name }}']
            ){{ ',' if not loop.last }}
            {% else %}
            if(m.{{ col.name }} is not distinct from g.{{ col.name }}, [], ['{{ col.name }}']){{ ',' if not loop.last }}
            {% endif %}
            {% endfor %}
        ) as mismatched_columns
    from model_rows as m
    full outer join golden_rows as g
        on {% for key in keys %}m.{{ key }} = g.{{ key }}{{ ' and ' if not loop.last }}{% endfor %}
)

select *
from compared
where missing is not null or array_length(mismatched_columns) > 0

{% endtest %}
