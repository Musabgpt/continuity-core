# Continuity Protocol v0.1

At the beginning of a work session:

1. Read `continuity/state.json`.
2. Read the tail of `continuity/events.jsonl` when evidence is needed.
3. Treat `constraints` as hard requirements.
4. Do not silently reverse an accepted decision; record a superseding decision.
5. After a meaningful failure, record what failed and why before retrying.
6. Before ending work, set exactly one concrete `next_action`.
7. Run `python continuity.py handoff` and make sure another worker could continue from it.

## Event types
- `decision`: an accepted technical/product choice.
- `success`: verified progress.
- `failure`: an observed failure and its cause/evidence.
- `note`: useful context that does not fit another type.

## State philosophy
`state.json` answers "where are we now?"
`events.jsonl` answers "how did we get here?"

Never put secrets in either file.
