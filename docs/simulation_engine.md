# SimArch Discrete-Event Simulation Engine

## 1. Overview
The simulation engine models organizational, economic, and product dynamics over time. Unlike conversational frameworks that simulate agents waiting around in real time, SimArch uses a discrete-event clock that can advance through months or years in milliseconds.

---

## 2. World State Specification

The world state (`WorldState`) tracks quantitative metrics across each simulation step:
- `sim_time_days`: Simulated clock progression in days.
- `cash`: Liquid cash reserves in USD.
- `monthly_revenue`: Recurring monthly revenue ($N_{\text{cust}} \times \text{ARPU}$).
- `monthly_burn`: Total monthly expenditures (headcount cost + marketing spend).
- `customers`: Total active customer accounts.
- `team_size`: Total headcount.
- `product_readiness_pct`: Progress towards full product completion (0-100%).
- `churn_rate_pct`: Percentage of customer base churning each month.
- `runway_months`: Remaining cash runway at current burn.

---

## 3. Causal Feedback Loops

1. **Expenditures & Burn**:
   $$\text{Monthly Burn} = (\text{Team Size} \times \text{Salary}) + \text{Marketing Spend}$$

2. **Customer Acquisition & Churn**:
   $$\Delta \text{New Customers} = \left(\frac{\text{Marketing Budget}}{\text{CAC}}\right) \times \left(1 + \frac{\text{Product Readiness}}{100}\right) \times (1 \pm \epsilon)$$
   $$\text{Churned Customers} = \text{Customers} \times \left(\frac{\text{Churn Rate}}{100}\right)$$

3. **Cash Flow & Runway**:
   $$\Delta \text{Cash} = \text{Monthly Revenue} - \text{Monthly Burn}$$

4. **Product Progress**:
   $$\Delta \text{Product Readiness} = \text{Team Size} \times 1.5\% \quad (\text{capped at } 100\%)$$

---

## 4. Monte Carlo Evaluation

To evaluate uncertainty, the simulation engine runs Monte Carlo batches across randomized seeds ($N \ge 25$):
- Outputs $P_{10}$ (pessimistic 10th percentile).
- Outputs $P_{50}$ (median expectation).
- Outputs $P_{90}$ (optimistic 90th percentile).
- Computes overall **Survival Probability** percentage (chance cash remains $>0$ throughout timeline).
