"""Measure, do not estimate. Write the numbers into the README.

    python scripts/measure.py            # measure and print, write nothing
    python scripts/measure.py --write    # measure and write between the markers

Three sections of the README are generated, between `<!-- measured:NAME:start -->`
and `<!-- measured:NAME:end -->`:

    tests        the suite's own count, from a run made now
    mutations    the mutation table, from a run made now
    deployment   the live run, rendered from deployments/studionet.json

It refuses to write anything if the suite is red, if a mutation escapes, or if
the recorded deployment is not of the contract file in this repository, so a
number in the README is always one that was checked.
"""

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

PKG = pathlib.Path(__file__).absolute().parent.parent
README = PKG.parent.parent / "README.md"
RECORD = PKG / "deployments" / "studionet.json"
SOURCE = PKG / "showdown.py"
EXPLORER = "https://explorer-studio.genlayer.com"
GEN = 10 ** 18


def gen(wei):
    v = int(wei) / GEN
    return f"{v:.4f}".rstrip("0").rstrip(".") + " GEN"


def tx(h):
    return f"[`{h[:10]}...`]({EXPLORER}/tx/{h})"


def short(url):
    return url.replace("https://", "").replace("raw.githubusercontent.com/Elinajafari/showdown/main/", "")


def run_tests():
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
                          cwd=PKG, capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1]
    if proc.returncode != 0:
        raise SystemExit("the suite is red; nothing written:\n" + tail)
    return int(re.search(r"(\d+) passed", tail).group(1))


def run_mutations():
    proc = subprocess.run([sys.executable, "scripts/mutate.py", "--md"], cwd=PKG, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("a mutation escaped or the baseline is red; nothing written:\n" + proc.stderr[-2000:])
    rows = [line for line in proc.stdout.splitlines() if line.startswith("| ") and "`" in line]
    return len(rows), proc.stdout.strip()


def steps_table(rec, names):
    out = ["", "Every transaction, in order, refusals included, with the wallet that sent it:", "",
           "| Step | From | Outcome | Transaction |", "|---|---|---|---|"]
    for s in rec["steps"]:
        if s["step"] == "deploy":
            continue
        outcome = "ok" if s["ok"] else "refused: " + s["refusal"].replace("[EXPECTED] ", "").replace("|", "/")
        out.append(f"| {s['step']} | {names.get(str(s.get('from', '')).lower(), '-')} | {outcome} | {tx(s['tx'])} |")
    return out


def payouts_table(demo):
    out = ["", "StudioNet charges a fee on every write, so a wallet's balance alone cannot show what it was paid. "
               "What each wallet received is read from the chain's own index: the transfers the contract sent "
               "it, against what the contract says it sent:", "",
           "| Wallet | Received from the contract | The contract sent | Transfer |", "|---|---|---|---|"]
    for name, owed in demo["owed"].items():
        txs = ", ".join(tx(x["tx"]) for x in demo["payouts"][name]) or "-"
        out.append(f"| {name} | {gen(demo['received'][name])} | {gen(owed)} | {txs} |")
    out += ["", f"Held by the contract afterwards: {demo['held_after']} wei."]
    return out


def render_deployment(rec):
    here = hashlib.sha256(SOURCE.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if rec["source_sha256"] != here:
        raise SystemExit("deployments/studionet.json records a different contract file; redeploy first")
    d = rec["demo"]
    addr = rec["contract"]
    deploy = [s for s in rec["steps"] if s["step"] == "deploy"][0]
    out = [
        f"Deployed on studionet at [`{addr}`]({EXPLORER}/address/{addr}) (deploy {tx(deploy['tx'])}). Every value "
        f"below was read back from the chain by `pnpm demo:contract` and written to "
        f"[`deployments/studionet.json`](packages/contracts/deployments/studionet.json); none of it is typed by "
        f"hand. The four pages the contract fetched are real, public files in this repository: "
        + ", ".join(f"[`{k}`]({v})" for k, v in d["pages"].items()) + ".",
        "",
        "| Showdown | Proposition | Pro's page | Con's page | Verdict | Status | Paid to pro | Paid to con |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for k, m in enumerate(d["matches"]):
        pro = f"[`{short(m['pro_url'])}`]({m['pro_url']})"
        con = f"[`{short(m['con_url'])}`]({m['con_url']})" if m["con_url"] else "-"
        out.append(f"| {k} | {m['proposition']} | {pro} | {con} | {('**' + m['verdict'] + '**') if m['verdict'] else '-'} | "
                   f"{m['status']} | {gen(m['paid_pro'])} | {gen(m['paid_con'])} |")
    out += ["", "What the leader's model said about the pages (not consensus):", "", "| Showdown | Reason the leader gave |", "|---|---|"]
    for k, m in enumerate(d["matches"]):
        if m["why"]:
            out.append(f"| {k} | {m['why'].replace('|', '/')} |")
    out += payouts_table(d)
    names = {a.lower(): n for n, a in d["accounts"].items()}
    out += steps_table(rec, names)
    return "\n".join(out)


def replace(text, name, body):
    start, end = f"<!-- measured:{name}:start -->", f"<!-- measured:{name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"README.md has no {name} markers")
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    passed = run_tests()
    tests = f"Measured: **{passed} passed**."
    n, table = run_mutations()
    mutations = f"Measured: **{n} mutations, {n} caught, 0 escaped.**\n\n{table}"
    if not RECORD.exists() or "demo" not in json.loads(RECORD.read_text(encoding="utf-8")):
        raise SystemExit("no finished deployment record; run pnpm deploy:contract and pnpm demo:contract first")
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    deployment = render_deployment(rec)

    text = README.read_text(encoding="utf-8")
    text = replace(text, "tests", tests)
    text = replace(text, "mutations", mutations)
    text = replace(text, "deployment", deployment)
    print(f"  tests      {passed} passed")
    print(f"  mutations  {n} caught, 0 escaped")
    print(f"  deployment {rec['contract']}")
    if args.write:
        README.write_text(text, encoding="utf-8", newline="\n")
        print("  README.md written")


if __name__ == "__main__":
    main()