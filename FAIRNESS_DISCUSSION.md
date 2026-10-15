# Fairness and tradeoff discussion framework

Use the following five steps to build a short group discussion. Keep claims tied to the static simulated batch; no long-run fairness experiment has been performed.

## 1. State what fairness means

Fairness can mean respecting arrival order, prioritizing imminent expiry, distributing access across donors, or serving recipients with greater need. These objectives can conflict. The current program implements arrival priority through FIFO and expiry priority through greedy; it does not measure need or equal opportunity across groups.

Discussion prompt: Which priority would we defend to a donor whose food was rejected, and why?

## 2. Explain the evidence

Use the tested two-donation scenario: LATE arrives first with 20 units expiring at 14:00; URGENT arrives second with 10 units expiring at 11:00. One compatible recipient has 20 units of capacity.

| Rule | Who receives priority? | Benefit | Cost |
|---|---|---|---|
| FIFO | LATE | Rescues 20 units and respects arrival order | URGENT is not rescued |
| Greedy | URGENT | Rescues the imminent-expiry donation | LATE no longer fits; only 10 units are rescued |

Both assign one donation. Greedy gains 100 percentage points in urgent rescue rate but loses 10 rescued units. Explain both outcomes rather than choosing whichever metric makes one algorithm look best.

## 3. Identify who can be disadvantaged

- **FIFO:** later arrivals can lose access to capacity even when they expire earlier.
- **Greedy:** less urgent donations can be repeatedly displaced if a future repeated-batch system keeps adding more urgent work. The current one-batch application demonstrates displacement, not measured long-run starvation.
- **Smaller-quantity tie-break:** when expiry ties, smaller donations get priority. This may favor count over quantity or prevent a larger donation from fitting later; it does not guarantee a higher count.
- **First feasible recipient/volunteer:** earlier CSV entries are preferred. No rotation balances workload or recipient access.
- **Whole donations and area equality:** large donations and locations without compatible recipients may be excluded even when spare capacity exists elsewhere.

A lower utilization rate does not by itself establish unfairness. Likewise, a high utilization rate does not establish equitable service.

## 4. Discuss one possible improvement, without claiming it exists

| Possible future change | Intended benefit | Tradeoff or evidence needed |
|---|---|---|
| Waiting-time aging | Give deferred work higher priority over time | Requires persistent history; may displace urgent food |
| Recipient/volunteer rotation | Reduce fixed input-order preference | Requires workload tracking; may change rescued quantity |
| Quantity-aware priority | Try to rescue more units | May reduce urgent rescue; needs comparative tests |
| Donation splitting | Use spare capacity across recipients | Requires a changed data model, multiple assignments, and handling assumptions |

Choose one proposal and name the additional test and metric required. Do not implement all of them simply to make the project sound more advanced.

## 5. Close with a defensible position

Suggested paragraph to adapt:

> Our greedy strategy prioritizes earlier expiry because the project's food donations are time-sensitive. This is a local scheduling choice, not a guarantee of the best overall outcome. In our controlled case, greedy rescues the urgent donation but saves 10 fewer units than FIFO. FIFO respects arrival order and saves more quantity in that case, but misses the urgent donation. We therefore report quantity and urgent rescue together and explain which donations lose access to capacity. Our static prototype has no starvation-prevention or need-based allocation rule; evaluating those would require additional history, metrics, and tests.

Before presenting, each member should be able to explain the priority order, the capacity arithmetic, who is disadvantaged, and what evidence would justify changing the rule.
