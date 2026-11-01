# Example — an over-eager "GO" caught by the premortem

A worked `auto-mediator` run on the *yes* side. The agent was about to approve shipping a change.

---

**AUTO-MEDIATOR**

1. **Initial verdict + confidence:** "The new caching layer cut p95 latency 40% in the load test — SHIP IT." (80%)
2. **Steelman the opposite + verification questions:** The strongest case for *don't ship yet*: a load test
   is not production traffic.
   - Q: Did the load test use realistic cache-miss ratios, or a warm cache? → *warm cache — misses were ~2%
     vs ~25% in prod logs.*
   - Q: What happens to the origin on a cache stampede / cold start? → *untested.*
   - Q: Is the 40% an average over a benign window, or does it hold at peak? → *measured off-peak only.*
3. **Not tried yet:** replaying real prod cache-miss ratios; a cold-start / stampede test.
4. **Bias:** confirmation (I like this result); measuring in a favorable window.
5. **Cheap evidence that would change it:** re-run the load test with the prod miss ratio (one afternoon).
6. **Premortem (assume it blew up in 3 months — why?):** the warm-cache test hid a cold-start stampede that
   hammers the origin at peak → an outage on the first deploy or cache flush. Cheap to close now.
7. **Final verdict:** `changed to "not yet / need X"` → ship *after* a cold-start + realistic-miss test.

---

**To the user:** The 40% win is real but measured with a warm cache (~2% misses vs ~25% in prod). Before we
ship, I want one more test at the real miss ratio plus a cold-start/stampede check — the failure that would
bite us isn't in the current data. A few hours of testing vs a possible peak-time outage.
