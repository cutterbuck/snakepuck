{# Game situations, as (column prefix, flag column on int_stints__enriched). #}
{% macro situations() %}
    {{ return([('es', 'is_even'), ('ev5', 'is_5v5'), ('pp', 'is_pp'), ('pk', 'is_pk')]) }}
{% endmacro %}

{# Stats split by situation on each stint, and how they roll up. #}
{% macro situational_stats() %}
    {{ return({
        'i_xg': 'xg', 'oi_xgf': 'xg', 'oi_xga': 'xg',
        'goals': 'count', 'assists': 'count', 'points': 'count',
        'shots': 'count', 'faceoffs_won': 'count', 'faceoffs_lost': 'count',
        'blocks': 'count', 'checks': 'count',
        'toi': 'seconds',
    }) }}
{% endmacro %}
