import numpy as np

from probeplan import search, world


def test_incident_has_root_that_reaches_the_failure_and_failure_diverges():
    for s in range(10):
        inc = world.Incident(s)
        assert inc.reach[inc.root, inc.fail] and inc.div[inc.fail] and inc.root in inc.cands and not inc.benign[inc.root]


def test_confirm_requires_clean_inputs():
    inc = world.Incident(1)
    r = inc.root
    obs = {r: True}
    assert search.confirmed(inc, obs) is None or not inc.parents[r]
    obs.update({p: False for p in inc.parents[r]})
    assert search.confirmed(inc, obs) == r


def test_posterior_prefers_ancestors_of_divergent_probes():
    inc = world.Incident(2)
    c, p = search.posterior(inc, {inc.fail: True}, False)
    assert abs(p.sum() - 1) < 1e-9
    c2, p2 = search.posterior(inc, {inc.fail: True, inc.root: True}, False)
    assert p2[list(c2).index(inc.root)] >= p[list(c).index(inc.root)]


def test_every_strategy_finishes_and_bisect_beats_random_logs_on_time():
    inc_seeds = range(20)
    t = {s: [] for s in search.STRATEGIES}
    for sd in inc_seeds:
        inc = world.Incident(sd)
        for s in search.STRATEGIES:
            r = search.investigate(inc, s, rng=np.random.default_rng(sd))
            assert r["rounds"] >= 1
            t[s].append(r["hours"])
    assert np.median(t[search.STRATEGIES[2]]) < np.median(t[search.STRATEGIES[0]])


def test_spread_picks_split_the_candidates():
    inc = world.Incident(3)
    c, p = search.posterior(inc, {}, False)
    picks = search.pick_spread(inc, {}, p, c, 3)
    assert len(set(picks)) == 3
