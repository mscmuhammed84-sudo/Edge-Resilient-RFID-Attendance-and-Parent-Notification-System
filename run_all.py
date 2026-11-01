"""Runs every experiment, writes results/*.json|csv|md.  All data synthetic (lab), none from a school."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from experiments import suite as S, bench, longrun as LR

N = int(os.environ.get("N_TRIALS", S.N_TRIALS)); os.makedirs("results", exist_ok=True)
CFGS = [("LSASP v1", S.V1), ("LSASP v2", S.V2)]
res = {"n_trials": N, "tuned": {}, "attacks": {}, "faults": {}, "scenarios": {}, "ablation_build_up": {}, "ablation_leave_one_out": {}}


def cell(a):
    return "n/a" if a["trials"] == 0 else f'{a["success"]}/{a["trials"]}'


for lab, cfg in CFGS:
    res["attacks"][lab] = S.run_attacks(cfg, N)
    res["faults"][lab] = {"buffer_delay_accepted": S.f_buffer_delay(cfg), "batch_poisoning": S.f_batch_poisoning(cfg),
                          "clock_skew_accepted": S.f_clock_skew(cfg)}
    res["scenarios"][lab] = {n: f(cfg) for n, f in S.SCENARIOS}
for key, lst in (("ablation_build_up", S.BUILD_UP), ("ablation_leave_one_out", S.LEAVE_ONE_OUT)):
    for lab, cfg in lst:
        res[key][lab] = {"attacks": S.run_attacks(cfg, N), "faults": S.f_buffer_delay(cfg),
                         "poison": S.f_batch_poisoning(cfg), "outage": S.s_outage_one_hour(cfg),
                         "lost_acks": S.s_lost_acks(cfg), "replay_after_restart": S.s_restart_replay(cfg)}
for lab, cfg in S.TUNED_BASELINES:
    res["tuned"][lab] = {"attacks": S.run_attacks(cfg, N), "delay": S.f_buffer_delay(cfg), "outage": S.s_outage_one_hour(cfg),
                         "replay_restart": S.replay_after_restart_by_delay(cfg), "poison": S.f_batch_poisoning(cfg)}
res["longrun"] = LR.sweep()
res["bench"] = bench.run(int(os.environ.get("BENCH_N", 5000)))
json.dump(res, open("results/results.json", "w"), indent=1)

md = ["# Results (laboratory, synthetic data -- not school data, not Raspberry Pi)\n",
      f"Trials per attack: {N}. Cell = attacker successes / trials. Lower is better.\n",
      "## Attacks\n", "| Attack | v1 | v2 |", "|---|---|---|"]
for name, _ in S.ATTACKS:
    md.append(f"| {name} | {cell(res['attacks']['LSASP v1'][name])} | {cell(res['attacks']['LSASP v2'][name])} |")
md += ["\n## Legitimate record delayed in local buffer (accepted?)\n", "| Delay | v1 | v2 |", "|---|---|---|"]
for d in res["faults"]["LSASP v1"]["buffer_delay_accepted"]:
    md.append(f"| {d} | {res['faults']['LSASP v1']['buffer_delay_accepted'][d]} | {res['faults']['LSASP v2']['buffer_delay_accepted'][d]} |")
md += ["\n## Batch poisoning (legit records accepted)\n", "| Case | v1 | v2 |", "|---|---|---|"]
for d in res["faults"]["LSASP v1"]["batch_poisoning"]:
    md.append(f"| {d} | {res['faults']['LSASP v1']['batch_poisoning'][d]} | {res['faults']['LSASP v2']['batch_poisoning'][d]} |")
md += ["\n## Terminal clock offset (accepted? accepted != correct)\n", "| Offset | v1 | v2 |", "|---|---|---|"]
for d in res["faults"]["LSASP v1"]["clock_skew_accepted"]:
    md.append(f"| {d} | {res['faults']['LSASP v1']['clock_skew_accepted'][d]} | {res['faults']['LSASP v2']['clock_skew_accepted'][d]} |")
md += ["\n## System scenarios (simulated clock/link)\n"]
for n, _ in S.SCENARIOS:
    md += [f"**{n}**\n", "| | " + " | ".join(res["scenarios"]["LSASP v1"][n]) + " |",
           "|---|" + "---|" * len(res["scenarios"]["LSASP v1"][n])]
    for lab, _c in CFGS:
        md.append(f"| {lab} | " + " | ".join(str(v) for v in res["scenarios"][lab][n].values()) + " |")
    md.append("")
for key, title in (("ablation_build_up", "Ablation: build-up (L0 -> v2)"), ("ablation_leave_one_out", "Ablation: leave-one-out")):
    md += [f"\n## {title}\n", "| Config | attacks succeeded (of 11) | delay 6 min | delay 24 h | poison 1/50 legit accepted | outage 1 h delivered | lost-ack pending+quarantined (of 100) | replay dups after restart |", "|---|---|---|---|---|---|---|---|"]
    for lab, r in res[key].items():
        sa = sum(1 for a in r["attacks"].values() if a["trials"] and a["success"])
        na = sum(1 for a in r["attacks"].values() if not a["trials"])
        md.append(f"| {lab} | {sa}" + (f" (+{na} n/a)" if na else "") + f" | {r['faults']['6 min']} | {r['faults']['1500 min']} | {r['poison']['1 corrupted of 50']} | {r['outage']['stored_in_cloud']}/{r['outage']['recorded']} | {r['lost_acks']['pending_at_end']}+{r['lost_acks']['quarantined']} | {r['replay_after_restart']['duplicates_in_cloud']} |")
md += ["\n## 50 simulated school days, 150 virtual students (10 seeds per cell; synthetic workload)\n",
       "Outage days = days on which one random outage occurred (30% of outages 1-4 min, 70% 10-120 min). Mean (min-max) over seeds.\n",
       "| Config | outage days | events | stored in cloud | delivered % | still pending | e-mails queued->sent | latency p95 s (max of max) |", "|---|---|---|---|---|---|---|---|"]
import statistics as _st
for k, runs in res["longrun"].items():
    f = lambda key: _st.mean(x[key] for x in runs)
    dl = [100 * x["stored_in_cloud"] / x["events"] for x in runs]
    md.append(f"| {k} | {f('outage_days'):.1f} | {f('events'):.0f} | {f('stored_in_cloud'):.0f} | {_st.mean(dl):.1f} ({min(dl):.1f}-{max(dl):.1f}) | {f('pending_at_end'):.0f} | {f('emails_sent'):.0f} | {_st.mean(x['lat_p95_s'] for x in runs):.0f} ({max(x['lat_max_s'] for x in runs):.0f}) |")
md += ["\n## Sensitivity of the v1 baseline to its freshness window\n",
       "| Config | attacks succeeded | delay accepted 6 min / 1 h / 4 h / 25 h | 1-h outage stored | replay after restart accepted at 30 s / 10 min / 2 h / 25 h | corrupted 1/50: legit accepted |", "|---|---|---|---|---|---|"]
for lab, r in res["tuned"].items():
    sa = sum(1 for a in r["attacks"].values() if a["trials"] and a["success"])
    d = r["delay"]; rr = r["replay_restart"]
    md.append(f"| {lab} | {sa} | {d['6 min']} / {d['60 min']} / {d['240 min']} / {d['1500 min']} | {r['outage']['stored_in_cloud']}/{r['outage']['recorded']} | {' / '.join(str(v) for v in rr.values())} | {r['poison']['1 corrupted of 50']} |")
md += ["\n## Micro-benchmarks (this machine)\n", "```", json.dumps(res["bench"]["machine"]), "```",
       "| Operation | mean us | p50 | p95 | p99 |", "|---|---|---|---|---|"]
for k, v in res["bench"]["results"].items():
    md.append(f"| {k} | {v['mean_us']} | {v['p50_us']} | {v['p95_us']} | {v['p99_us']} |")
open("results/results.md", "w").write("\n".join(md) + "\n")
with open("results/attacks.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["attack", "v1", "v2"])
    for name, _ in S.ATTACKS: w.writerow([name, cell(res["attacks"]["LSASP v1"][name]), cell(res["attacks"]["LSASP v2"][name])])
print("done")
