// Put the demo on the explorer: a showdown won on the evidence, a showdown that
// is a draw, an unanswered proposition, and the refusals.
//
//   pnpm demo:contract        (after pnpm deploy:contract)
//
// Every page the contract fetches is a real, public file in this repository,
// read through raw.githubusercontent.com:
//
//   strong_pro.md   release notes with a date, a signed tag and a build number
//   weak_con.md     a vague post that only says "it was not 2019"
//   vague_a.md      one anecdote about a festival date
//   vague_b.md      the opposite anecdote, equally thin
//
// StudioNet charges a fee on every write, so a wallet's balance cannot show what
// it was paid. What each wallet received is read from the chain's own index: the
// transfers the contract sent it.

import { readFileSync, writeFileSync } from "node:fs";
import { RECORD_FILE, accountFrom, clientFor, fundAccount, loadEnv, network, readRetry, recorder, sleep, sourceSha256 } from "./lib.mjs";

loadEnv();
const net = network();
const record = JSON.parse(readFileSync(RECORD_FILE, "utf8"));
if (record.source_sha256 !== sourceSha256()) throw new Error("showdown.py changed since it was deployed; run pnpm deploy:contract first");
const address = record.contract;
const GEN = 10n ** 18n;
const RAW = "https://raw.githubusercontent.com/Elinajafari/showdown/main/demo";
const STRONG = `${RAW}/strong_pro.md`;
const WEAK = `${RAW}/weak_con.md`;
const VAGUE_A = `${RAW}/vague_a.md`;
const VAGUE_B = `${RAW}/vague_b.md`;
const STAKE = GEN / 20n; // 0.05 GEN a side
const PROP_0 = "The Aurelia library version 2.0 was released in 2019.";
const PROP_1 = "The Harbour Festival was moved from May to June this year.";

const ROLES = ["pro", "con", "stranger"];
const who = Object.fromEntries(ROLES.map((k) => [k, accountFrom(`${k.toUpperCase()}_PRIVATE_KEY`, net)]));
const as = Object.fromEntries(ROLES.map((k) => [k, clientFor(net, who[k])]));
const ro = clientFor(net, null);
const read = (fn, args = []) => readRetry(() => ro.readContract({ address, functionName: fn, args }));
const plain = (v) => JSON.parse(JSON.stringify(v, (_, x) => (typeof x === "bigint" ? Number(x) : x instanceof Map ? Object.fromEntries(x) : x)));
const rec = recorder();

async function waitUntil(stamp, label) {
  const target = Date.parse(stamp) + 15_000;
  const left = target - Date.now();
  if (left > 0) { console.log(`  waiting ${Math.ceil(left / 1000)}s for ${label}`); await sleep(left); }
}

/** The finalized transfers the contract sent `to`, from the chain's own index. */
async function incoming(to) {
  const rows = await readRetry(() => ro.request({ method: "sim_getTransactionsForAddress", params: [to] }));
  return rows.filter((r) => String(r.from_address ?? "").toLowerCase() === address.toLowerCase()
    && String(r.to_address ?? "").toLowerCase() === to.toLowerCase() && String(r.status) === "FINALIZED")
    .sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
}

console.log(`\ncontract ${address}`);
if (Number(await read("count")) !== 0) throw new Error("the demo expects a fresh contract");
if (net.name === "studionet") for (const k of ROLES) await fundAccount(net, ro, who[k].address, 2n * GEN);

const w = (k, fn, args, opts) => rec.write(as[k], who[k], address, fn, args, opts);

await w("pro", "open", [PROP_0, STRONG, 1200n], { step: "showdown 0 opened: the pro side stakes 0.05 GEN and names dated release notes", value: STAKE });
await w("pro", "accept", [0n, WEAK], { step: "the opener takes the other side of its own showdown: refused", expect: "refused", value: STAKE });
await w("stranger", "judge", [0n], { step: "a judgment before the other side is in: refused", expect: "refused" });
await w("con", "accept", [0n, STRONG], { step: "the other side names the opener's own page: refused", expect: "refused", value: STAKE });
await w("con", "accept", [0n, WEAK], { step: "showdown 0: the other side matches the stake and names a vague post", value: STAKE });
await w("stranger", "judge", [0n], { step: "showdown 0 judged: both pages fetched and weighed, both orders" });
await w("stranger", "judge", [0n], { step: "a second judgment on a decided showdown: refused", expect: "refused" });

await w("pro", "open", [PROP_1, VAGUE_A, 1200n], { step: "showdown 1 opened: a festival date, one anecdote on each side", value: STAKE });
await w("con", "accept", [1n, VAGUE_B], { step: "showdown 1: the other side matches the stake with the opposite anecdote", value: STAKE });
await w("stranger", "judge", [1n], { step: "showdown 1 judged: two thin anecdotes, neither stronger" });

await w("pro", "open", [PROP_0, STRONG, 240n], { step: "showdown 2 opened: nobody will take the other side", value: STAKE });
await w("stranger", "settle", [2n], { step: "a refund while the other side can still come: refused", expect: "refused" });
await waitUntil((await read("showdown", [2n])).join_by, "showdown 2's other-side window to close");
await w("stranger", "settle", [2n], { step: "showdown 2 settled: nobody came, the opener's stake comes back" });

const n = Number(await read("count"));
const matches = [];
for (let k = 0; k < n; k++) matches.push(plain(await read("showdown", [BigInt(k)])));
const owed = { pro: 0n, con: 0n };
for (const m of matches) { owed.pro += BigInt(m.paid_pro); owed.con += BigInt(m.paid_con); }

// The payouts land after the receipt: read the index until they have arrived.
const payouts = {}, received = {};
for (const k of ["pro", "con"]) {
  let rows = [];
  for (let i = 0; i < 40; i++) {
    rows = await incoming(who[k].address);
    if (rows.reduce((s, r) => s + BigInt(r.value), 0n) >= owed[k]) break;
    await sleep(8_000);
  }
  payouts[k] = rows.map((r) => ({ tx: r.hash, value: String(BigInt(r.value)), created_at: String(r.created_at) }));
  received[k] = String(rows.reduce((s, r) => s + BigInt(r.value), 0n));
}

record.steps.push(...rec.steps);
record.demo = {
  pages: { strong_pro: STRONG, weak_con: WEAK, vague_a: VAGUE_A, vague_b: VAGUE_B },
  stake_wei: String(STAKE),
  matches,
  owed: Object.fromEntries(Object.entries(owed).map(([k, v]) => [k, String(v)])),
  received, payouts,
  held_after: String(await read("held_total")),
  accounts: Object.fromEntries(ROLES.map((k) => [k, who[k].address])),
};
writeFileSync(RECORD_FILE, JSON.stringify(record, null, 2) + "\n");
console.log(`\npro received ${received.pro} (owed ${owed.pro}); con received ${received.con} (owed ${owed.con}); record written to ${RECORD_FILE}\n`);
