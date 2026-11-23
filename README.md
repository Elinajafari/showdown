# Showdown - two stakes on one proposition, won by whichever side's evidence page is stronger

A GenLayer Intelligent Contract for a bet that needs a referee. One person
opens a proposition, stakes an amount on it being **TRUE** and names the public
web page that is their evidence. Anyone else takes the other side by staking the
**same** amount on it being **FALSE** and naming **their** evidence page. Then
anyone calls `judge()`. The contract **fetches both pages itself** with
`gl.nondet.web.render`, and the validators decide which page better supports its
own side, reading the two pages in both orders. The winner takes both stakes. If
neither page is clearly stronger, each side gets its own stake back. If nobody
takes the other side, the opener is refunded.

- **Contract:** [`packages/contracts/showdown.py`](packages/contracts/showdown.py)
- **Tests:** `pnpm test` (or `python -m pytest packages/contracts/tests -q`): nothing to install but `pytest`
- **Mutation pass:** `python packages/contracts/scripts/mutate.py`
- **Deployed:** see [It is live](#it-is-live-and-every-path-is-on-chain) below, and [`packages/contracts/deployments/studionet.json`](packages/contracts/deployments/studionet.json)
- **Verify a deployment:** `pnpm verify:contract` - reads the source back off chain, diffs it with this file and lints those bytes
- **License:** MIT

---

## It is live, and every path is on chain

<!-- measured:deployment:start -->
Deployed on studionet at [`0x1F26056DDd9a228d74DAEEDC06cA59EE9524f80b`](https://explorer-studio.genlayer.com/address/0x1F26056DDd9a228d74DAEEDC06cA59EE9524f80b) (deploy [`0xd264e1de...`](https://explorer-studio.genlayer.com/tx/0xd264e1de33b8255ae75dd64540d57a94f6601e556a79979ec72fcb13e904a8cf)). Every value below was read back from the chain by `pnpm demo:contract` and written to [`deployments/studionet.json`](packages/contracts/deployments/studionet.json); none of it is typed by hand. The four pages the contract fetched are real, public files in this repository: [`strong_pro`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/strong_pro.md), [`weak_con`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/weak_con.md), [`vague_a`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/vague_a.md), [`vague_b`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/vague_b.md).

| Showdown | Proposition | Pro's page | Con's page | Verdict | Status | Paid to pro | Paid to con |
|---|---|---|---|---|---|---|---|
| 0 | The Aurelia library version 2.0 was released in 2019. | [`demo/strong_pro.md`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/strong_pro.md) | [`demo/weak_con.md`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/weak_con.md) | **pro** | decided | 0.1 GEN | 0 GEN |
| 1 | The Harbour Festival was moved from May to June this year. | [`demo/vague_a.md`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/vague_a.md) | [`demo/vague_b.md`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/vague_b.md) | **neither** | decided | 0.05 GEN | 0.05 GEN |
| 2 | The Aurelia library version 2.0 was released in 2019. | [`demo/strong_pro.md`](https://raw.githubusercontent.com/Elinajafari/showdown/main/demo/strong_pro.md) | - | - | cancelled | 0.05 GEN | 0 GEN |

What the leader's model said about the pages (not consensus):

| Showdown | Reason the leader gave |
|---|---|
| 0 | Page one gives a specific release date, version tag, and corroborating release details; page two relies only on vague, unnamed forum posts a |
| 1 | Both pages make vague, unverified hearsay claims and openly express uncertainty, so neither provides stronger support for its side. |

StudioNet charges a fee on every write, so a wallet's balance alone cannot show what it was paid. What each wallet received is read from the chain's own index: the transfers the contract sent it, against what the contract says it sent:

| Wallet | Received from the contract | The contract sent | Transfer |
|---|---|---|---|
| pro | 0.2 GEN | 0.2 GEN | [`0x13969261...`](https://explorer-studio.genlayer.com/tx/0x139692618d7c85127e920506369f5b7116a725a8e65e8f55dfac07f8ec07e8c6), [`0x47cb8f15...`](https://explorer-studio.genlayer.com/tx/0x47cb8f1531f71ce70c49b9d6314f29506275f6e5b97d87e1450fd4bb53ad9b48), [`0x01aaba48...`](https://explorer-studio.genlayer.com/tx/0x01aaba48e8b0718998d74cbc2a7f79f71994ea047751b733103fb34f9d767da5) |
| con | 0.05 GEN | 0.05 GEN | [`0xf0cde65d...`](https://explorer-studio.genlayer.com/tx/0xf0cde65d55ed46b36d9cc81ba1ae4c816859ced84af421dd2d4b1412dc2f9669) |

Held by the contract afterwards: 0 wei.

Every transaction, in order, refusals included, with the wallet that sent it:

| Step | From | Outcome | Transaction |
|---|---|---|---|
| showdown 0 opened: the pro side stakes 0.05 GEN and names dated release notes | pro | ok | [`0xbde2127c...`](https://explorer-studio.genlayer.com/tx/0xbde2127c37d4143f78c2c731958017a072f3b5384b55bad9ab052269467fb2a7) |
| the opener takes the other side of its own showdown: refused | pro | refused: the opener cannot take the other side of its own showdown | [`0x0bb1c7b4...`](https://explorer-studio.genlayer.com/tx/0x0bb1c7b45181dba0db8dbfa734bb3303a07c4302cb446056727dda19952e812f) |
| a judgment before the other side is in: refused | stranger | refused: this showdown is open; only one with both sides in is judged | [`0xe8446f41...`](https://explorer-studio.genlayer.com/tx/0xe8446f419da1aab9b2e16edd65faeaefad863aab925a63370dd24ba21145c2c9) |
| the other side names the opener's own page: refused | con | refused: both sides cannot name the same evidence page | [`0x6317b83c...`](https://explorer-studio.genlayer.com/tx/0x6317b83c2a58f1f9fcc42925c9816f1cb4fe133224b5bb54a6f9ebd7edc24d2d) |
| showdown 0: the other side matches the stake and names a vague post | con | ok | [`0xf34f186e...`](https://explorer-studio.genlayer.com/tx/0xf34f186e58fb50a029379b68e6640e818ff261e7aaf1b72fe37d570d4882c4ea) |
| showdown 0 judged: both pages fetched and weighed, both orders | stranger | ok | [`0xc12c0579...`](https://explorer-studio.genlayer.com/tx/0xc12c05798db778f47e7f6107e30d5fbed0691a9c33c68dad65d266f05e84e2a6) |
| a second judgment on a decided showdown: refused | stranger | refused: this showdown is decided; only one with both sides in is judged | [`0x6dd1ad2a...`](https://explorer-studio.genlayer.com/tx/0x6dd1ad2a629a266bb76c92d6d7304ca57d11b3279b10e80c0eb21ae3aaf4a835) |
| showdown 1 opened: a festival date, one anecdote on each side | pro | ok | [`0xd2e13c1e...`](https://explorer-studio.genlayer.com/tx/0xd2e13c1e550173e0b26501224cddc3590cf8d966c346e2ca0393a8dc2f417bb8) |
| showdown 1: the other side matches the stake with the opposite anecdote | con | ok | [`0x538e8c55...`](https://explorer-studio.genlayer.com/tx/0x538e8c5513138fbd37e503a53dc9376df3e53d627844e59bc97fc59f3c27bbb1) |
| showdown 1 judged: two thin anecdotes, neither stronger | stranger | ok | [`0x37232af8...`](https://explorer-studio.genlayer.com/tx/0x37232af8dbebf9625ecb4724fc33f829a2bcf68882916329e5190ccfe0c26da9) |
| showdown 2 opened: nobody will take the other side | pro | ok | [`0x3572a381...`](https://explorer-studio.genlayer.com/tx/0x3572a38197e3fcb0ca7c280917bba53b08ffcf7f88361eab5b96b43ea5b3ea94) |
| a refund while the other side can still come: refused | stranger | refused: the other side is open until 2026-11-23T22:34:58Z | [`0x94d17cb5...`](https://explorer-studio.genlayer.com/tx/0x94d17cb594634b8f96801f971b3082629d94397559f174c4e945de6f78d2e788) |
| showdown 2 settled: nobody came, the opener's stake comes back | stranger | ok | [`0xebdd54f0...`](https://explorer-studio.genlayer.com/tx/0xebdd54f0cd39176f79002b1d29e85d0a301286b02986079ad7717f65ced23a28) |
<!-- measured:deployment:end -->

## The problem

A bet between two parties needs a referee. A human referee can be bribed,
absent or biased. A model asked "who is right?" is asked for the truth about the
world, which it may not know and cannot check.

Showdown asks something narrower and checkable: **given these two pages, which
one makes the better case for the side it was brought to support?** Both pages
are named in advance by the two people with money on them, and both are read by
the contract itself, not described by the parties.

## How consensus is used

### Before any page is fetched, and before any model

The contract refuses for free what no answer could change: a judgment before
both sides are in, a judgment after the judging window, a second judgment, a
second stake that does not match the first, the opener taking the other side of
its own showdown, and both sides naming the same page (in any spelling).

### The fetch, then two presentations

The block fetches both pages, independently on the leader and on each validator,
and asks the model to pick one of three options the contract wrote, labelled
`[0]` `[1]` `[2]` inside an `<options>` block: `pro`, `con`, `neither`. It asks
twice. **The second time the two pages swap places and the options are reversed
and renumbered**, so neither the position of a page nor the position of an
option can decide the result. Each answer is read back through the order it was
asked in. **The same option both ways stands; anything else is `neither`**: a
page has to win in both orders to win.

The model is never shown the stakes, the addresses, or who staked first.

### The validator, in two layers

1. **Structural, and free.** The verdict is `pro`, `con` or `neither`. A payload that fails this is refused before the validator spends a prompt.
2. **Exact agreement**, after the validator has fetched both pages and asked both presentations itself.

A page that cannot be fetched, or a model answer that is unusable, is raised as
`[FETCH_ERROR]` or `[LLM_ERROR]`, which no validator agrees with, so a broken
fetch or a broken model can never move the stakes.

## What the contract decides, not the model

| verdict | pays |
|---|---|
| `pro` | both stakes to the pro side |
| `con` | both stakes to the con side |
| `neither` | each side its own stake back |
| nobody took the other side | the opener's stake back, after the window |
| nobody judged in time | each side its own stake back, after the judging window |

## The state machine and its clock

```
open --(accept)--> joined --(judge)--> decided
open --(join window closes, settle)--> cancelled
joined --(judging window closes, settle)--> expired
```

`join_by = open + window`; `judge_by = joined + window`.

## Who may write

| Method | Who | Why |
|---|---|---|
| `open(proposition, evidence_url, window)` payable | anyone | the caller is the pro side |
| `accept(id, evidence_url)` payable | anyone but the pro side | the caller is the con side; the stake must match exactly |
| `judge(id)` | anyone | both sides are already recorded and named; who asks cannot change who is paid |
| `settle(id)` | anyone | refunds go to the recorded sides, only after a deadline; it reads no page and no model |

## Running the tests

```bash
pip install -r packages/contracts/requirements-dev.txt
python -m pytest packages/contracts/tests -q
python packages/contracts/scripts/mutate.py
```

<!-- measured:tests:start -->
Measured: **95 passed**.
<!-- measured:tests:end -->

### The tests have teeth

<!-- measured:mutations:start -->
Measured: **77 mutations, 77 caught, 0 escaped.**

| Mutation | Caught by |
|---|---|
| an option past the list is accepted | `test_an_answer_is_an_option_number_and_nothing_else` |
| an answer in words is read as a number | `test_an_answer_is_an_option_number_and_nothing_else` |
| the second ask keeps the pages in the first order | `test_the_pages_swap_places_and_the_options_reverse_between_the_two_asks` |
| the second ask keeps the options in the first order | `test_a_side_that_wins_only_in_one_presentation_does_not_win` |
| the reversed order is not reversed | `test_an_option_is_read_back_through_its_order` |
| a disagreement between the presentations keeps the first | `test_a_side_has_to_win_both_ways_to_win` |
| a disagreement between the presentations gives the pro side the win | `test_a_side_has_to_win_both_ways_to_win` |
| a disagreement between the presentations gives the con side the win | `test_a_side_has_to_win_both_ways_to_win` |
| an answer is not read back through its order | `test_an_option_is_read_back_through_its_order` |
| an unusable answer is not retried | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| an unusable answer is read as a win for the pro side | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| an answer that is not an object crashes the block | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| a fetch error is swallowed and read as an empty page | `test_fetch_wraps_a_non_user_error_as_fetch_error` |
| a short or empty page is still judged | `test_fetch_refuses_a_page_shorter_than_min_page` |
| a page is never actually fetched | `test_both_pages_are_fetched_by_the_leader_and_by_the_validator` |
| the con page is not fetched | `test_both_pages_are_fetched_by_the_leader_and_by_the_validator` |
| the validator agrees with an error | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| the validator skips the structural check | `test_a_leader_that_sends_an_unsound_verdict_is_refused_before_any_prompt` |
| the validator agrees with anything sound | `test_nodes_that_decide_differently_do_not_agree` |
| the validator agrees when its own fetch or model fails | `test_a_validator_whose_own_fetch_fails_does_not_agree` |
| agreement ignores soundness | `test_agreement_is_exact_symmetric_and_over_sound_verdicts` |
| a verdict that is not one of the three is sound | `test_the_structural_check` |
| the agreed verdict is not checked again | `test_the_contract_does_not_trust_a_consensus_value_it_cannot_read` |
| a pro win pays the con side | `test_the_winner_takes_both_stakes_and_neither_returns_each_its_own` |
| a con win pays the pro side | `test_the_winner_takes_both_stakes_and_neither_returns_each_its_own` |
| a win takes only the winner's own stake back | `test_the_winner_takes_both_stakes_and_neither_returns_each_its_own` |
| neither keeps one stake | `test_the_winner_takes_both_stakes_and_neither_returns_each_its_own` |
| the pro side is not paid | `test_the_stronger_pro_page_takes_both_stakes` |
| the con side is not paid | `test_the_stronger_con_page_takes_both_stakes` |
| the verdict is not recorded | `test_the_stronger_pro_page_takes_both_stakes` |
| the showdown is not marked decided | `test_the_stronger_pro_page_takes_both_stakes` |
| what was paid to the pro side is not recorded | `test_the_stronger_pro_page_takes_both_stakes` |
| what was paid to the con side is not recorded | `test_when_neither_is_stronger_each_side_gets_its_own_stake_back` |
| the decision time is not recorded | `test_the_stronger_pro_page_takes_both_stakes` |
| a leader's reason is stored as sent | `test_a_leader_s_reason_is_stored_clean_and_capped_even_if_the_validator_never_saw_it` |
| a leader's reason is stored uncapped | `test_the_reason_is_sanitised_and_capped` |
| the opener may take the other side | `test_the_opener_cannot_take_the_other_side` |
| the other side is taken on a showdown that is not open | `test_only_one_other_side_is_taken` |
| the other side never closes | `test_the_other_side_closes_with_the_window` |
| the other side's evidence is not checked | `test_the_evidence_must_be_a_plain_address` |
| both sides may name the same page | `test_both_sides_cannot_name_the_same_page_in_any_spelling` |
| any stake matches | `test_the_stake_is_matched_exactly` |
| the other side is not recorded | `test_the_other_side_matches_the_stake_and_names_its_own_page` |
| the other side's page is not recorded | `test_the_other_side_matches_the_stake_and_names_its_own_page` |
| the showdown is not marked joined | `test_the_other_side_matches_the_stake_and_names_its_own_page` |
| the judging window is not set | `test_the_other_side_matches_the_stake_and_names_its_own_page` |
| the joining time is not recorded | `test_the_other_side_matches_the_stake_and_names_its_own_page` |
| a showdown is judged before the other side is in | `test_a_judgment_needs_both_sides_in` |
| judging never closes | `test_a_judgment_closes_with_its_window` |
| an unanswered showdown is refunded while the other side can still come | `test_an_unanswered_proposition_is_not_settled_while_the_other_side_can_still_come` |
| a joined showdown is returned while it can still be judged | `test_a_showdown_nobody_judged_returns_both_stakes_after_the_judging_window` |
| a decided showdown settles again | `test_a_decided_or_settled_showdown_does_not_settle_again` |
| an unanswered showdown refunds less than the stake | `test_an_unanswered_proposition_refunds_the_opener_once_the_window_has_closed` |
| an expired showdown returns nothing to the con side | `test_a_showdown_nobody_judged_returns_both_stakes_after_the_judging_window` |
| an expired showdown returns nothing to the pro side | `test_a_showdown_nobody_judged_returns_both_stakes_after_the_judging_window` |
| an unanswered showdown is not marked cancelled | `test_an_unanswered_proposition_refunds_the_opener_once_the_window_has_closed` |
| an expired showdown is not marked expired | `test_a_showdown_nobody_judged_returns_both_stakes_after_the_judging_window` |
| a stake of nothing is accepted | `test_the_proposition_the_evidence_the_window_and_the_stake_are_bounded` |
| the held counter is not raised at open | `test_a_showdown_opens_with_the_stake_held_and_the_evidence_named` |
| the held counter is not raised at accept | `test_the_other_side_matches_the_stake_and_names_its_own_page` |
| a payout beyond what is held is sent | `test_a_payout_beyond_what_is_held_is_refused` |
| the held counter is not lowered | `test_the_stronger_pro_page_takes_both_stakes` |
| the window is unbounded | `test_the_proposition_the_evidence_the_window_and_the_stake_are_bounded` |
| the window does not set the clock | `test_a_showdown_opens_with_the_stake_held_and_the_evidence_named` |
| the proposition is unbounded | `test_the_proposition_the_evidence_the_window_and_the_stake_are_bounded` |
| the opener's evidence is not checked | `test_the_proposition_the_evidence_the_window_and_the_stake_are_bounded` |
| a page with angle brackets is accepted | `test_a_fetchable_address` |
| a host without a dot is accepted | `test_a_fetchable_address` |
| the fence is removed | `test_the_fence_replaces_and_preserves_length` |
| the fence leaves square brackets | `test_the_fence_replaces_and_preserves_length` |
| the first page reaches the prompt unfenced | `test_hostile_content_cannot_close_a_block_or_forge_an_option` |
| the second page reaches the prompt unfenced | `test_hostile_content_cannot_close_a_block_or_forge_an_option` |
| the proposition reaches the prompt unfenced | `test_hostile_content_cannot_close_a_block_or_forge_an_option` |
| a whole page, however long, reaches the prompt | `test_only_the_first_part_of_a_long_page_is_shown` |
| the second page is labelled with the first page's side | `test_each_page_is_labelled_with_the_side_it_argues_wherever_it_is_shown` |
| the prompt lets the model decide which side is right | `test_the_prompt_judges_the_case_a_page_makes_and_nothing_else` |
| control characters are stored | `test_clean_text_collapses_whitespace_and_control_characters` |
<!-- measured:mutations:end -->

## Design rules applied

- **One label crosses consensus**, from a closed set; the reason sentence is display only.
- **Uncertainty goes in the value:** a disagreement between the two presentations is `neither`, and `neither` refunds.
- **Both presentations**, with the pages swapped and the options reversed.
- **Every write is bound to an address**, and a test fails when a write is added without being classified.
- **Untrusted text is fenced** at the prompt boundary (replace, never delete), and a test fails when a prompt value is not.
- **The deployed bytes are the repository's bytes:** `pnpm verify:contract`.

## Known limits

- The model reads the first 5,000 characters of each page.
- A showdown is only as good as the pages the two sides can find: it measures which page makes the better case, not which side is right about the world. The demo's pages are fixtures committed to this repository.
- A page that cannot be read makes `judge()` fail until it can; if nobody can judge before the judging window ends, both stakes go back.
