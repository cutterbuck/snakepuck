-- Every tracking snapshot belongs to an event in the same game.
select t.game_id, t.sl_event_id
from {{ ref('stg_halo__tracking') }} as t
left join {{ ref('stg_halo__events') }} as e
    using (game_id, sl_event_id)
where e.sl_event_id is null
