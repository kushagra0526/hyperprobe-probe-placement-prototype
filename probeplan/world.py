"""An incident in a service, as a data-flow graph with a known root cause.

Nodes are values in the program (topologically ordered); the failing value is the last node. A bug corrupts one node and the corruption flows downstream, sometimes
masked on the way (a clamp, a default). Some values differ between any two requests (timestamps, ids). All numbers are invented."""
import numpy as np


class Incident:
    def __init__(self, seed, n=60, mask=0.1, benign=0.1, changed_share=0.1, bug_in_changed=0.7):
        rng = np.random.default_rng(seed)
        while True:
            self.n = n
            self.parents = [[]]
            for j in range(1, n):
                k = int(rng.integers(1, 4))
                w = np.exp(-np.arange(j)[::-1] / 6.0)
                self.parents.append(sorted(set(rng.choice(j, size=min(k, j), replace=False, p=w / w.sum()).tolist())))
            self.reach = np.zeros((n, n), bool)                      # reach[i, j]: i is an ancestor of j or j itself
            for j in range(n):
                self.reach[j, j] = True
                for p in self.parents[j]:
                    self.reach[:, j] |= self.reach[:, p]
            anc = [i for i in range(n - 1) if self.reach[i, n - 1]]
            if len(anc) >= 8:
                break
        self.fail = n - 1
        self.cands = anc                                             # possible root causes
        self.changed = set(rng.choice(n, size=max(1, int(changed_share * n)), replace=False).tolist())
        in_changed = [c for c in anc if c in self.changed]
        self.root = int(rng.choice(in_changed)) if in_changed and rng.random() < bug_in_changed else int(rng.choice(anc))
        for _ in range(100):
            masked = rng.random(n) < mask
            div = np.zeros(n, bool)
            div[self.root] = True
            for j in range(self.root + 1, n):
                div[j] = (not masked[j]) and any(div[p] for p in self.parents[j])
            if div[self.fail]:
                break
        else:
            div = self.reach[self.root].copy()
        self.div = div
        self.benign = rng.random(n) < benign
        self.benign[self.root] = False
        self.flagged = self.benign & (rng.random(n) < 0.9)           # seen to differ between two healthy requests, so ignorable
        self.rng = rng

    def probe(self, q):
        """What a read-only probe at q shows when the failing request is captured: (differs from a healthy request, known to be nondeterministic)."""
        return bool(self.div[q] or self.benign[q]), bool(self.flagged[q])
