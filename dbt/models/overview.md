{% docs __overview__ %}
# SnakePuck data pipeline

The dbt project behind [SnakePuck](https://github.com/cutterbuck/snakepuck): AHL 2023-24
player tracking data (HALO) modelled in BigQuery.

**Layers**
- **staging**: typed, renamed views over the raw HALO tables (games, players, events,
  stints, tracking), plus the `ahl_teams` seed.
- **intermediate**: game situation (5v5, PP, PK), ice time, and shift number for every
  stint; events credited to each stint.
- **marts**: what the site serves: player season, game, and stint stats, standings,
  shifts, and the events and tracking snapshots behind the game-report rink.

**Testing**
Besides key, null, relationship, and accepted-value tests, every stats mart was
reconciled row by row and column by column against snapshots of the original Python
pipeline (`matches_golden`). That reconciliation found three bugs in the original,
now fixed. `dbt build --vars 'legacy_parity: true'` still reproduces the old numbers
exactly, so the proof can be re-run at any time.

Use the lineage graph (bottom right) to trace any mart back to its raw sources.
{% enddocs %}
