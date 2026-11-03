# Expected Threat Model Plan

A re-implementation of Elliot Kervin's HALO conference model, "Optimus Reimer":
a sequence-aware expected threat (xT) model that values every on-ice action.
It ends in a blog post. This is a learning project, so each phase ships
something we can look at and can be reordered or dropped.

Credit: the method is Kervin's, inspired by Michael Schuckers's THoR. The
for/against valuation is the VAEP framework (Decroos et al., 2019). The post
should say so plainly and frame this as a rebuild, plus whatever we add.

## What we know about his model (from the talk)

| Piece | What he said |
|---|---|
| Target | 3 classes: acting team scores in the next 20 s / opponent scores / no goal. Under 4% of events are positive. |
| Inputs | rink x/y, distance and angle to net; distance, time, speed and angle from the previous event; period, clock, score diff, skaters per side, empty net, home flag; event type; outcome; embedded description text |
| Shots | knows whether a shot was on net, not whether it went in |
| Leakage | a "with goal" tag in the text let the model score every goal perfectly; he stripped it |
| Validation | 5-fold CV split by game; "4-5x better than random" (probably average precision vs. the base rate) |
| Credit | xT for = change in P(my team scores) from the inherited state; xT against = change in P(opponent scores); net = for − against |
| Goalies | a save row is injected after every on-net shot that isn't a goal |

What we have to choose ourselves: context window length, how the text is
encoded, model size, class weighting, and how credit is split across players
(the talk describes both a per-action ledger and an equal split).

## The data (checked 2026-11-03)

- 480 games, 1.80M events (~3,750 per game, the same data he used).
- `goal` and `assist` are their own event rows. They are labels, not inputs:
  drop them from the sequence.
- **His leak is in `flags`:** shots and deflections carry `withgoal` (2,816 +
  264 rows). Other flags describe what happened *after* the event too, e.g.
  `withrebound` on shots and `withplayafter` on carries. Every flag needs an
  audit for "known at the time of the event?" before it becomes an input.
- `description` has only 397 distinct values (e.g. `SLOT SHOT FOR ONNET`,
  `DZ OUTLET PASS+`). The trailing `+`/`-` restates the outcome. `flags` has
  3,675 distinct combinations of a smaller tag vocabulary.
- Shootout and penalty-shot events (`so*`, `ps*`, `shootout`, `penaltyshot`)
  are excluded.
- Game state (skaters, empty net, score) comes from stints. Tracking has one
  position snapshot per event (not continuous frames), used in phase 6.

## Phase 0: Setup

- [ ] Decide where the code lives: a `model/` Python package in this repo,
      using the `halo_hockey` env. Training data and weights stay out of git
      (public repo, licensed data).
- [ ] Add `torch` (with MPS on the Mac), `lightgbm`, `scikit-learn` to the env.
- [ ] Fix the 5 game folds once (seeded, stratified by team) and save them, so
      every model is scored on the same splits.

## Phase 1: Labels and features (dbt)

- [ ] `int_xt_events`: in-play events in game order, with goal, assist and
      shootout rows removed, joined to the stint for game state.
- [ ] Labels: for each event, does the acting team / the opponent score
      within 20 s of game clock, without crossing a period end? Check the
      base rate is under 4%.
- [ ] Features: geometry (normalized so the acting team attacks one way),
      deltas from the previous event, game state, event type, outcome.
- [ ] Flag audit: sort every flag into "known at the time" or "future", and
      write a dbt test that fails if a future flag reaches the features.
- [ ] Save rows: inject one after each on-net, non-goal shot, credited to the
      opposing goalie.
- [ ] Export to Parquet for training (local and `gs://snakepuck-data`).

## Phase 2: Baseline (VAEP with gradient boosting)

- [ ] LightGBM on the current event plus the previous 2-3 events (classic
      VAEP).
- [ ] Metrics per fold: log loss, average precision against the base rate
      (his "4-5x"), Brier score, and a calibration plot.
- [ ] Action values: for/against/net, summed per player per game.
- [ ] Sanity checks: do the top passers come out as defensemen, and do puck
      recoveries carry the most value, as in his talk?

The baseline is the bar the transformer has to clear. If it doesn't, that's
a finding for the post.

## Phase 3: Transformer

- [ ] Sequence building: a window of the last N events (try 32/64/128), reset
      at period starts. Ablate whether to also reset on whistles.
- [ ] Tokens: event-type, outcome and flag embeddings + continuous features
      through a small MLP, plus a time/position encoding.
- [ ] Text: start with learned embeddings of `description` (only 397 values).
      Then try a frozen sentence-embedding model to see if it helps, which is
      the closest match to what he described.
- [ ] Model: causal encoder, 2-4 layers, d=64-128, 3-class head. Weighted or
      focal loss for the imbalance. Calibrate on a held-out slice.
- [ ] Same folds and metrics as phase 2. Compare.
- [ ] Look at attention on a few known goals (e.g. his Colorado vs. Ontario
      sequence from 2024-04-20, if it's in our data).

## Phase 4: Player valuation

- [ ] For/against/net xT per action. Group event types into macro buckets
      (passing, hustle/recoveries, shooting, defense, faceoffs, goaltending).
- [ ] Per-player totals and per-60 rates, with minimum-TOI filters.
- [ ] Stability: split-half correlation of player ratings, to see how much is
      signal at our sample sizes.
- [ ] Compare against Sportlogiq xG and our LPR work.

## Phase 5: Blog post

- [ ] Explain xG → VAEP → transformer xT in plain hockey language.
- [ ] Walk through one goal sequence with the probability rising event by
      event (a chart on the site).
- [ ] Baseline vs. transformer results, the leakage story, what didn't work.
- [ ] Player leaderboards with the caveats.
- [ ] Credits and links (Kervin's talk, THoR, VAEP).

## Phase 6 (stretch): Add tracking

His stated next step. Add per-event skater snapshots (positions and
velocities of all skaters) as extra input to each token, and measure the gain
over phase 3. This is the part that would be our own contribution.

## Open questions

- Is 20 s the right horizon, or should we compare 10/20/30 s?
- Should credit go per action (VAEP) or be split across the possession, as
  the talk also suggests?
- Do we show the model's output on the site (needs a mart and a page) or only
  in the post?
