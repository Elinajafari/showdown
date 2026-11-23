"""Mutation pass: break every defence on purpose, confirm a test notices.

Passing tests prove nothing on their own. Each entry below is a small edit to
the contract that removes a defence. The suite must fail for every one of them,
and this script records WHICH test caught it, so the table in the README is
measured rather than claimed.

    python scripts/mutate.py            # run them all, print what caught what
    python scripts/mutate.py --md       # emit the markdown table for the README

An escaping mutation is a finding, not a nuisance: either a missing test, or a
later defence strict enough that an earlier test can no longer fail. The script
exits non-zero if anything escapes, and refuses to run on a red baseline. A find
string that is missing, or matches more than once, is a failure of the harness,
never a skip, so refactoring cannot quietly turn a row off.
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).absolute().parent.parent
TARGET = "showdown.py"

FENCE = '    return str(raw).replace("<", "(").replace(">", ")").replace("[", "(").replace("]", ")")'

MUTATIONS = [
    # -- reading the answer
    ("an option past the list is accepted", "    if k < 0 or k >= n:\n        return \"\"", "    if k < 0:\n        return \"\""),
    ("an answer in words is read as a number",
     '    if s == "" or any(ch not in "0123456789" for ch in s) or len(s) > 2:', '    if s == "":'),

    # -- the two presentations
    ("the second ask keeps the pages in the first order",
     "            rev, _ = ask(proposition, (CON, con_page), (PRO, pro_page), REVERSED)",
     "            rev, _ = ask(proposition, (PRO, pro_page), (CON, con_page), REVERSED)"),
    ("the second ask keeps the options in the first order",
     "            rev, _ = ask(proposition, (CON, con_page), (PRO, pro_page), REVERSED)",
     "            rev, _ = ask(proposition, (CON, con_page), (PRO, pro_page), FORWARD)"),
    ("the reversed order is not reversed", "REVERSED = [NEITHER, CON, PRO]", "REVERSED = [PRO, CON, NEITHER]"),
    ("a disagreement between the presentations keeps the first",
     "    return forward if forward == reverse else NEITHER", "    return forward"),
    ("a disagreement between the presentations gives the pro side the win",
     "    return forward if forward == reverse else NEITHER", "    return forward if forward == reverse else PRO"),
    ("a disagreement between the presentations gives the con side the win",
     "    return forward if forward == reverse else NEITHER", "    return forward if forward == reverse else CON"),
    ("an answer is not read back through its order", "    return order[int(choice)]", "    return FORWARD[int(choice)]"),

    # -- reading the model
    ("an unusable answer is not retried",
     "    for _ in range(2):\n        raw = gl.nondet.exec_prompt(", "    for _ in range(1):\n        raw = gl.nondet.exec_prompt("),
    ("an unusable answer is read as a win for the pro side",
     '    raise gl.vm.UserError(f"{ERR_LLM} the model named no option")', '    return PRO, ""'),
    ("an answer that is not an object crashes the block",
     "        if isinstance(raw, dict):\n            choice", "        if True:\n            choice"),

    # -- the fetch
    ("a fetch error is swallowed and read as an empty page",
     '    except Exception:\n        raise gl.vm.UserError(f"{ERR_FETCH} an evidence page could not be read")',
     '    except Exception:\n        text = ""'),
    ("a short or empty page is still judged", "    if len(body.strip()) < MIN_PAGE:", "    if False:"),
    ("a page is never actually fetched", "        text = gl.nondet.web.render(url)", "        text = url"),
    ("the con page is not fetched", "            con_page = fetch(con_url)", "            con_page = pro_page"),

    # -- the validator
    ("the validator agrees with an error", "                return False\n            theirs", "                return True\n            theirs"),
    ("the validator skips the structural check",
     "            if not verdict_sound(proposed):\n                return False", "            if False:\n                return False"),
    ("the validator agrees with anything sound", '            return showdown_agrees(mine["verdict"], proposed)', "            return True"),
    ("the validator agrees when its own fetch or model fails",
     "            except gl.vm.UserError:\n                return False", "            except gl.vm.UserError:\n                return True"),
    ("agreement ignores soundness",
     "    return verdict_sound(mine) and verdict_sound(theirs) and str(mine) == str(theirs)", "    return str(mine) == str(theirs)"),
    ("a verdict that is not one of the three is sound",
     "    return verdict == PRO or verdict == CON or verdict == NEITHER", "    return True"),

    # -- the deterministic half
    ("the agreed verdict is not checked again",
     "        if not verdict_sound(verdict):\n            raise", "        if False:\n            raise"),
    ("a pro win pays the con side", "    if verdict == PRO:\n        return 2 * s, 0", "    if verdict == PRO:\n        return 0, 2 * s"),
    ("a con win pays the pro side", "    if verdict == CON:\n        return 0, 2 * s", "    if verdict == CON:\n        return 2 * s, 0"),
    ("a win takes only the winner's own stake back", "    if verdict == PRO:\n        return 2 * s, 0", "    if verdict == PRO:\n        return s, 0"),
    ("neither keeps one stake", "    return s, s", "    return s, 0"),
    ("the pro side is not paid", "        self._send(m.pro, to_pro)", "        pass"),
    ("the con side is not paid", "        self._send(m.con, to_con)", "        pass"),
    ("the verdict is not recorded", "        m.verdict = verdict", "        pass"),
    ("the showdown is not marked decided", "        m.status = DECIDED", "        pass"),
    ("what was paid to the pro side is not recorded", "        m.paid_pro = u256(to_pro)", "        pass"),
    ("what was paid to the con side is not recorded", "        m.paid_con = u256(to_con)", "        pass"),
    ("the decision time is not recorded", "        m.settled_at = u256(self._now())", "        pass"),
    ("a leader's reason is stored as sent", "        m.why = sanitise_reason(res.get(\"because\", \"\"))", "        m.why = str(res.get(\"because\", \"\"))"),
    ("a leader's reason is stored uncapped", '    return " ".join("".join(out).split())[:limit]', '    return " ".join("".join(out).split())'),

    # -- accepting the other side
    ("the opener may take the other side", "        if sender == m.pro:\n            raise", "        if False:\n            raise"),
    ("the other side is taken on a showdown that is not open",
     '        if str(m.status) != OPEN:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this showdown is {m.status}; only an open one takes the other side")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this showdown is {m.status}; only an open one takes the other side")'),
    ("the other side never closes", "        if now > int(m.join_by):", "        if False:"),
    ("the other side's evidence is not checked", "        if not bounded(link, MIN_URL, MAX_URL) or not is_http_url(link):\n            raise gl.vm.UserError(f\"{ERR_EXPECTED} the evidence is a plain http or https address of \"\n                                  f\"{MIN_URL} to {MAX_URL} characters\")\n        if url_key(link)", "        if url_key(link)"),
    ("both sides may name the same page", "        if url_key(link) == url_key(str(m.pro_url)):", "        if False:"),
    ("any stake matches", "        if paid != int(m.stake):", "        if False:"),
    ("the other side is not recorded", "        m.con = sender", "        pass"),
    ("the other side's page is not recorded", "        m.con_url = link", "        pass"),
    ("the showdown is not marked joined", "        m.status = JOINED", "        pass"),
    ("the judging window is not set", "        m.judge_by = u256(now + int(m.window))", "        m.judge_by = u256(now + 10 ** 9)"),
    ("the joining time is not recorded", "        m.joined_at = u256(now)", "        pass"),

    # -- judging
    ("a showdown is judged before the other side is in",
     '        if str(m.status) != JOINED:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this showdown is {m.status}; only one with both sides in is judged")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this showdown is {m.status}; only one with both sides in is judged")'),
    ("judging never closes", "        if now > int(m.judge_by):", "        if False:"),

    # -- settle
    ("an unanswered showdown is refunded while the other side can still come",
     "            if now <= int(m.join_by):\n                raise", "            if False:\n                raise"),
    ("a joined showdown is returned while it can still be judged",
     "            if now <= int(m.judge_by):\n                raise", "            if False:\n                raise"),
    ("a decided showdown settles again",
     '        raise gl.vm.UserError(f"{ERR_EXPECTED} this showdown is {m.status}; nothing to settle")', "        return"),
    ("an unanswered showdown refunds less than the stake",
     "            m.paid_pro = u256(stake)\n            self._send(m.pro, stake)\n            return\n        if str(m.status) == JOINED:",
     "            m.paid_pro = u256(stake)\n            self._send(m.pro, stake - 1)\n            return\n        if str(m.status) == JOINED:"),
    ("an expired showdown returns nothing to the con side", "            self._send(m.con, stake)\n            return", "            return"),
    ("an expired showdown returns nothing to the pro side", "            self._send(m.pro, stake)\n            self._send(m.con, stake)", "            self._send(m.con, stake)"),
    ("an unanswered showdown is not marked cancelled", "            m.status = CANCELLED", "            pass"),
    ("an expired showdown is not marked expired", "            m.status = EXPIRED", "            pass"),

    # -- money
    ("a stake of nothing is accepted", "        if stake < 1 or stake > MAX_STAKE:", "        if stake > MAX_STAKE:"),
    ("the held counter is not raised at open", "        self.held = u256(int(self.held) + stake)", "        pass"),
    ("the held counter is not raised at accept", "        self.held = u256(int(self.held) + paid)", "        pass"),
    ("a payout beyond what is held is sent", "        if amount > int(self.held):", "        if False:"),
    ("the held counter is not lowered", "        self.held = u256(int(self.held) - amount)", "        pass"),

    # -- opening
    ("the window is unbounded", "        if w < MIN_WINDOW or w > MAX_WINDOW:", "        if False:"),
    ("the window does not set the clock", "join_by=u256(now + w)", "join_by=u256(now + MAX_WINDOW)"),
    ("the proposition is unbounded", "        if not bounded(text, MIN_PROPOSITION, MAX_PROPOSITION):", "        if False:"),
    ("the opener's evidence is not checked", "        if not bounded(link, MIN_URL, MAX_URL) or not is_http_url(link):\n            raise gl.vm.UserError(f\"{ERR_EXPECTED} the evidence is a plain http or https address of \"\n                                  f\"{MIN_URL} to {MAX_URL} characters\")\n        w = int(window)", "        w = int(window)"),
    ("a page with angle brackets is accepted", '    if rest == "" or any(ch in s for ch in " <>\\"\'`\\\\"):', '    if rest == "":'),
    ("a host without a dot is accepted", '    return "." in host and not host.startswith(".") and not host.endswith(".")', "    return True"),

    # -- the prompt boundary
    ("the fence is removed", FENCE, "    return str(raw)"),
    ("the fence leaves square brackets", FENCE, '    return str(raw).replace("<", "(").replace(">", ")")'),
    ("the first page reaches the prompt unfenced", "{fence(first[1][:MAX_PAGE_SHOWN])}", "{first[1][:MAX_PAGE_SHOWN]}"),
    ("the second page reaches the prompt unfenced", "{fence(second[1][:MAX_PAGE_SHOWN])}", "{second[1][:MAX_PAGE_SHOWN]}"),
    ("the proposition reaches the prompt unfenced", "{fence(proposition)}", "{proposition}"),
    ("a whole page, however long, reaches the prompt", "{fence(first[1][:MAX_PAGE_SHOWN])}", "{fence(first[1])}"),
    ("the second page is labelled with the first page's side", '{arg[second[0]]}', '{arg[first[0]]}'),
    ("the prompt lets the model decide which side is right",
     "Do not use what\nyou already know about the subject, and do not decide which side you think is\nright.",
     "Use what you already know about the subject and decide which side is right."),
    ("control characters are stored", '            out.append(" ")\n        else:', "            out.append(ch)\n        else:"),
]


PYTEST = [sys.executable, "-m", "pytest", "tests", "-x", "-q", "--no-header", "-p", "no:cacheprovider"]


def copy_repo(tmp):
    dst = pathlib.Path(tmp) / "pkg"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".git", "node_modules", "*.pyc"))
    return dst


def run_one(label, find, replace):
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        target = dst / TARGET
        src = target.read_text(encoding="utf-8")
        hits = src.count(find)
        if hits == 0:
            return "PATTERN NOT FOUND", None
        if hits > 1:
            return "PATTERN NOT UNIQUE", None
        target.write_text(src.replace(find, replace, 1), encoding="utf-8", newline="\n")
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            return "ESCAPED", None
        text = proc.stdout + proc.stderr
        m = re.search(r"^(?:FAILED|ERROR) (\S+?)::(\S+?)(?:\[|\s|$)", text, re.M)
        if m:
            return "caught", m.group(2).split("::")[-1]
        m = re.search(r"^E\s+(\w*(?:Error|Exception))", text, re.M)
        if m:
            return "caught", m.group(1) + " at import"
        return "caught", "unnamed failure"


def baseline_is_green():
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="emit the README table")
    args = ap.parse_args()

    green, tail = baseline_is_green()
    if not green:
        print("the unmutated suite is not green; every mutation would look caught:\n" + tail, file=sys.stderr)
        return 2

    rows, escaped = [], []
    for label, find, replace in MUTATIONS:
        status, test = run_one(label, find, replace)
        if status == "caught":
            rows.append((label, test))
            if not args.md:
                print("  caught   %-70s %s" % (label, test), flush=True)
        else:
            escaped.append((label, status))
            print("  %-8s %s" % (status, label), file=sys.stderr, flush=True)

    if args.md:
        print("| Mutation | Caught by |")
        print("|---|---|")
        for label, test in rows:
            print("| %s | `%s` |" % (label, test))
    else:
        print()
        print("  %d mutations, %d caught, %d escaped" % (len(MUTATIONS), len(rows), len(escaped)))
    return 1 if escaped else 0


if __name__ == "__main__":
    sys.exit(main())
