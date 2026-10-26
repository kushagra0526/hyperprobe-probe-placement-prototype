"""Choose where to put read-only probes, round by round, until the root cause is confirmed."""
import numpy as np

STRATEGIES = ["random log lines (redeploy each round)", "walk back from the failure", "bisect: spread probes over the posterior", "bisect + prior from changed code"]
EPS_MASK = 0.2        # chance a corrupted value is hidden at a node downstream of the bug
EPS_BENIGN = 0.02     # chance an unflagged nondeterministic value shows as 'differs' for another reason


def posterior(inc, obs, use_prior):
    c = np.array(inc.cands)
    prior = np.ones(len(c))
    if use_prior:
        prior = np.where([x in inc.changed for x in c], 6.0, 1.0)
    lik = np.ones(len(c))
    for q, differs in obs.items():
        if differs is None:
            continue
        below = inc.reach[c, q]                                   # candidate c would reach q
        lik *= np.where(below, 1.0 if differs else EPS_MASK, EPS_BENIGN if differs else 1.0)
    p = prior * lik
    return c, p / p.sum()


def confirmed(inc, obs):
    """A value that differs while every input it was computed from was seen and is fine (inputs known to be nondeterministic do not count against it)."""
    for q, differs in obs.items():
        if differs is True and all(p in obs and obs[p] is not True for p in inc.parents[q]):
            return q
    return None


def pick_spread(inc, obs, p, c, k):
    """Greedy: choose k probes whose answers split the candidate causes as evenly as possible."""
    code = np.zeros(len(c), int)
    chosen = []
    pool = [q for q in range(inc.n) if q not in obs and inc.reach[c, q].any()]
    for _ in range(k):
        best, bq = -1.0, None
        for q in pool:
            if q in chosen:
                continue
            cc = code * 2 + inc.reach[c, q]
            w = np.bincount(cc, weights=p)
            w = w[w > 0]
            ent = -(w * np.log(w)).sum()
            if ent > best:
                best, bq = ent, q
        if bq is None:
            break
        chosen.append(bq)
        code = code * 2 + inc.reach[c, bq]
    return chosen


def investigate(inc, strategy, k=4, max_rounds=25, arrival_per_hour=3.0, redeploy_hours=0.75, rng=None):
    rng = rng or np.random.default_rng(0)
    obs, hours, probes = {}, 0.0, 0
    frontier = [inc.fail]
    for rnd in range(1, max_rounds + 1):
        if strategy == STRATEGIES[0]:
            pool = [q for q in range(inc.n) if q not in obs]
            batch = rng.choice(pool, size=min(k, len(pool)), replace=False).tolist() if pool else []
            hours += redeploy_hours
        elif strategy == STRATEGIES[1]:
            batch = []
            while frontier and len(batch) < k:
                q = frontier.pop(0)
                if q not in obs and q not in batch:
                    batch.append(q)
                    frontier += [p for p in inc.parents[q] if p not in obs]
        else:
            c, p = posterior(inc, obs, strategy == STRATEGIES[3])
            batch = pick_spread(inc, obs, p, c, k)
        if not batch:
            break
        hours += rng.exponential(1.0 / arrival_per_hour)             # wait for a failing request to come through
        for q in batch:
            differs, flagged = inc.probe(q)
            probes += 1
            if not flagged:                                           # a value known to be nondeterministic tells us nothing
                obs[q] = differs
            else:
                obs[q] = None
        found = confirmed(inc, obs)
        if found is not None:
            return {"rounds": rnd, "hours": hours, "probes": probes, "correct": found == inc.root, "confirmed": True}
    return {"rounds": max_rounds, "hours": hours, "probes": probes, "correct": False, "confirmed": False}
