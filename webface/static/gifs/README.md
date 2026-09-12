# Benny's reaction GIF pack

Benny serves these from HIS OWN box — localhost-only, nothing fetched, nothing tracked.
He picks by mood (his emoji-vault logic, scaled to animation).

## How it works

The frontend scans each benny reply for a mood keyword, then looks for a matching file
here (`webface/static/gifs/`). If a match exists it's appended to the reply bubble. If
the folder's empty (or no keyword matches), benny just answers in text — the pack is a
spice rack, never a requirement.

## The pack manifest

Drop files with these EXACT names. Any mood with no file keeps benny text-only.

| filename          | mood              | triggers                          |
|-------------------|-------------------|-----------------------------------|
| `grin.gif`        | happy / good      | "done", "shipped", "nice", "got it" |
| `laugh.gif`       | big laugh         | "😂", "🤣", funny phrases         |
| `kudos.gif`       | praise, flex      | "kudos", "locked", "shipped"      |
| `think.gif`       | thinking/puzzle   | "pattern", "hmm", "actually"      |
| `fire.gif`        | hype/groove       | "cooking", "🔥", "runs", "live"   |
| `salute.gif`      | respect           | "respect", "on it", "boss"        |
| `t_t.gif`         | drama/comic sad   | "T_T", "sorry", "rip", "oops"     |
| `win.gif`         | battle/win        | "battle", "win", "victory", "flex"|
| `blink.gif`       | surprise/whoa     | "no way", "wait", "actually?"     |
| `gg.gif`          | end / good game   | "gg", "done!", "that's it", "fin" |

## Sources (all must be CC0 / public domain / your own)

- https://commons.wikimedia.org (search "animated GIF") — verify the license badge
- https://www.pexels.com/gifs/ (free license)
- Or make your own tiny ones — even 2-3 frames read fine.

## Rule

Same as the emoji vault: restraint. One gif per punchline, never a flood.