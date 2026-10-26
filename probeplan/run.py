import json

import numpy as np

from . import search, world

CONFIG = {"dev": dict(n=60, mask=0.1, benign=0.1), "held": dict(n=140, mask=0.25, benign=0.2)}
K = {"dev": 4, "held": 3}
ARRIVAL = {"dev": 3.0, "held": 1.5}


def score(seeds, which):
    acc = {s: {"rounds": [], "hours": [], "probes": [], "correct": 0, "unconfirmed": 0} for s in search.STRATEGIES}
    for sd in seeds:
        inc = world.Incident(sd, **CONFIG[which])
        for s in search.STRATEGIES:
            r = search.investigate(inc, s, k=K[which], arrival_per_hour=ARRIVAL[which], rng=np.random.default_rng(sd + 1))
            a = acc[s]
            a["rounds"].append(r["rounds"]), a["hours"].append(r["hours"]), a["probes"].append(r["probes"])
            a["correct"] += r["correct"]
            a["unconfirmed"] += not r["confirmed"]
    n = len(list(seeds))
    return {s: {"correct_root_cause_pct": round(100 * a["correct"] / n), "not_confirmed_pct": round(100 * a["unconfirmed"] / n), "median_rounds": float(np.median(a["rounds"])),
                "median_hours": round(float(np.median(a["hours"])), 1), "median_probes": float(np.median(a["probes"]))} for s, a in acc.items()}


def main():
    res = {"dev": score(range(0, 150), "dev"), "held_out": score(range(1000, 1200), "held")}
    json.dump(res, open("out/result.json", "w"), indent=1)
    for k, v in res.items():
        print(k)
        for m, d in v.items():
            print("  ", m, d)


if __name__ == "__main__":
    main()
