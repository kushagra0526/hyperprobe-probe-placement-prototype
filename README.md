# probeplan: where should the next read-only probes go?

HyperProbe's on-call agent "drops read-only probes into your running service" to read exact variable state at the moment of failure, with a stated overhead budget (under 1% CPU) (https://hyperprobe.co). Each round of probes needs another failing request to come through, so the question is where to put the few probes you can afford. This prototype is a simulator with a known root cause for that question. It does not use their SDK or any service of theirs.

## The setup
`probeplan/world.py`: an incident is a data-flow graph (60 or 140 values, 1-3 inputs each). One value is corrupted (the root cause); the corruption flows downstream and is sometimes hidden on the way (a clamp, a default); some values differ between any two requests (timestamps, ids), and 90% of those are known as nondeterministic from two healthy requests. A probe shows whether a value differs from a healthy request.
`probeplan/search.py`: four ways to choose K probes per round: random log lines (each round is a redeploy, 0.75 h); walk back from the failing value like a stack trace; bisect (a posterior over candidate causes, greedy choice of probes that split the candidates evenly); bisect plus a prior that favours recently changed code. Done when a value differs while every input it was computed from was seen and is fine. Each round waits for a failing request (exponential, 3 per hour in dev, 1.5 in held-out).

## Results (150 dev incidents; 200 held-out incidents with 140 values, more hiding and nondeterminism, 3 probes per round; fixed in git before the first run)
| | dev: right root cause | dev: median rounds / hours | held-out: right root cause | held-out: not confirmed | held-out: median rounds / hours / probes |
|---|---|---|---|---|---|
| random log lines, redeploy each round | 52% | 10 / 10.8 | 10% | 34% | 20 / 29.1 / 60 |
| walk back from the failure | 62% | 5 / 1.5 | 22% | 2% | 6 / 4.0 / 18 |
| bisect | 78% | 4 / 1.5 | 54% | 2% | 7 / 4.6 / 21 |
| bisect + prior from changed code | 79% | 4 / 1.4 | **60%** | 0% | 7 / 4.6 / 21 |

- Without redeploys, rounds are cheap: probes cut the median time from about 29 hours to 4-5 on the held-out incidents, mostly because random log lines need a redeploy per round.
- Bisecting is not faster than walking back in rounds on the large graphs, but it is much more often right (54-60% vs 22%): walking back probes many values and one of them, a nondeterministic value that was not flagged, looks like a root cause. The posterior treats one odd value as weak evidence.
- Even the best strategy is wrong 40% of the time on the hard held-out incidents. A value hidden downstream looks clean and steers the search the wrong way, and the confirmation rule trusts a single differing value. A real system needs a second confirmation (probe the suspected value's inputs and outputs, or replay).
- The changed-code prior helps a little (+6 points) because 70% of simulated bugs are in recently changed code, an assumption I made up.

## Read this before believing the table
The graph, hiding rates, nondeterminism and arrival rates are invented; real services have loops, concurrency and values that cannot be probed. No claim about how HyperProbe places probes (I have not seen its agent).

## Run it (3 commands)
```
pip install numpy pytest
python -m pytest -q tests
python -m probeplan.run
```
numpy only. 5 tests; the run takes a few seconds.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with HyperProbe.
