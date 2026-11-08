# Stanford Agentic Reviewer 评审报告 (4.9/10)
- **送审论文**：WHEN RESEARCH PILOTS ARE INCONCLUSIVE: AN AUDIT OF PRUNING, DEFERRAL, AND DECISION COST
- **评审目标会议**：ICLR (ICLR 2026 规范)
- **提交时间**：2026-11-08T06:59:12.461296
- **出分时间**：2026-11-08T07:03:19.006333
- **综合打分**：**4.9 / 10**
- **送审 Token**：6ZtvxO58wvyHxff-aQ1KZrPt3VPGupaSuP9QE86Zsw
- **在线查阅链接**：https://paperreview.ai/review?token=f6ZtvxO58wvyHxff-aQ1KZrPt3VPGupaSuP9QE86Zsw

---

## 核心评分维度 (Triple Scores)
- **Claims_Support (论据支撑度)**: **+1** (支持充分，实验证据确凿)
- **Experimental_Soundness (方法完备性)**: **+1** (实验设计严谨，多项分布精确积分)
- **Writing_Clarity (写作清晰度)**: 0
- **Prior_Work_Context (相关工作脉络)**: 0
- **Question_Importance (问题重要性)**: 0
- **Originality (创新度)**: 0
- **Value_to_Community (社区学术价值)**: 0

---

## 评审全文 (Review Content)

1. Summary
This paper audits fixed-look decision policies for small evaluation pilots that compare a candidate model against a baseline under a paired categorical outcome model. It disentangles three axes—interval construction (paired-normal vs a conservative joint Clopper-Pearson bound), decision logic (binary vs tri-state with an explicit defer region), and decision costs (for GO on futile, NO_GO on useful, and DEFER)—and measures how these choices affect false-prune/false-go probabilities, “automatic coverage” (non-deferred decisions), and expected cost. Using exact multinomial integration over synthetic regimes and finite-benchmark replay from four classification datasets, the study finds that a tri-state policy can dramatically reduce false pruning at the price of high deferral rates, normal-approximation intervals can have poor coverage in sparse-discordance settings, and that targeted deferral is often—but not universally—cheaper than binary or matched-random deferral controls under illustrative cost triples.

2. Strengths
- Technical novelty and innovation
  - The study cleanly decomposes interval construction, decision rules, and explicit deferral costs in a fixed-look, paired-categorical setting, which is often conflated in practice.
  - Exact multinomial integration (rather than Monte Carlo) systematically covers the full space of outcome counts for synthetic regimes, removing simulation noise and enabling fine-grained auditing.
  - The joint Clopper-Pearson composition via a union bound is a simple, transparent construction that guarantees conservative coverage in the fixed-look setting; contrasting it with paired-normal intervals surfaces a concrete sparse-discordance failure mode.
- Experimental rigor and validation
  - Broad condition grid: 420 synthetic and 540 empirical (finite-benchmark) conditions across multiple n, effect sizes, discordance rates, thresholds, two interval methods, and six policies, with additional matched-random deferral controls and 27 cost triples.
  - Clear reporting of unconditional error masses, automatic vs interval coverage, and expected cost under prespecified mixtures and losses; careful distinction between synthetic and finite-benchmark replay.
  - Reproducibility is strong: procedures, seeds, dataset choices, model configs, and CSV outputs are described, with hashes and automated checks.
- Clarity of presentation
  - The paper is explicit about scope and non-claims (no statistical novelty, not a sequential design), and carefully defines its terminology (gain, discordance, mixtures, error/loss notions).
  - Results consistently tie back to the design axes (intervals, policies, costs), avoiding overgeneralization.
- Significance of contributions
  - The audit highlights a practically important trade-off: deferral can materially reduce harmful false pruning but at nontrivial cost and with fewer automatic actions; importantly, it is not universally best and depends on costs and effect mixtures.
  - The observation that paired-normal intervals can be severely miscalibrated in sparse-discordance regimes is actionable for practitioners relying on normal approximations.

3. Weaknesses
- Technical limitations or concerns
  - The joint interval is obtained by composing two marginal CP intervals with a union bound; while valid, it can be overly conservative and ignores established exact or score-based intervals tailored to paired binary differences (e.g., McNemar-related CIs, Newcombe score-type intervals), which could be fairer comparators than a naive normal approximation.
  - The policies are not cost-sensitive in a principled sense: alpha and delta are fixed and not tuned to the stated decision costs; under a known cost model, Bayes/Wald-optimal fixed-look policies or oracle/posterior-thresholding baselines could provide stronger context.
- Experimental gaps or methodological issues
  - Empirical replay uses small tabular UCI datasets and three simple model pairs; these benchmarks may not reflect the intended “research agent” setting, limiting external validity.
  - Matched-random deferral is matched at the mixture level rather than within latent truth strata or conditional on observable uncertainty; this may over- or under-credit targeted deferral in heterogeneous mixtures.
  - The study fixes alpha=0.05; sensitivity to alpha (and how it trades against deferral and expected cost) is not explored.
- Clarity or presentation issues
  - The term “coverage” is overloaded: “automatic coverage” (fraction of non-deferred actions) is different from interval coverage; despite the clarifications, tables labeling “Coverage” as action probability can still mislead.
  - Some future-dated references (e.g., “contributors, 2026”) and the emphasis on “research agents” without direct data from such agents may distract from the core statistical audit.
- Missing related work or comparisons
  - The paper omits classical “reject option” decision-theory and selective classification literature that formalizes abstention under explicit costs, and hypothesis testing with reject/inconclusive outcomes (e.g., works on fixed-horizon tests with a reject option, McNemar/paired-proportion CIs, and operational abstention selection as in cost-aware abstention pipelines).
  - No comparison to fixed-horizon decision-theoretic rules that optimize expected loss at the fixed look given the observed counts and a prior or minimax criterion.

4. Detailed Comments
- Technical soundness evaluation
  - Modeling: The IID trinomial model with difference D∈{-1,0,+1} parameterized by (g,q) is standard for paired binary outcomes with ties. Enumerating multinomial count triples and summing their probabilities is exact and avoids MC variance.
  - Intervals: The paired-normal CI uses the unbiased variance of D; the paper convincingly shows its failure in sparse-discordance settings (degenerate variance and zero-width intervals). The joint CP-by-union-bound construction is conservative but correct at a fixed look; however, it is not the only valid fixed-look approach for paired differences and is known to be conservative relative to score-based or exact unconditional intervals for paired data.
  - Policies and metrics: The tri-state decision defined by CI placement relative to delta is logically consistent and its acceptance region alignment with delta-binary is correctly noted; automatic coverage versus interval coverage separation is appropriate. The expected-loss definition aligns with explicit nonzero deferral and asymmetric GO/NO_GO error costs.
- Experimental evaluation assessment
  - Breadth: The grid over n, effect sizes, discordance, thresholds, and cost triples is extensive, enabling a thorough sensitivity analysis. The integration over all count states makes reported masses exact under the model.
  - Controls: Matched-random deferral is a thoughtful baseline to test whether simply deferring less makes you look better; that tri-state often beats it indicates targeted allocation yields real gains. However, matching within observable uncertainty bands or truth strata could isolate targeting benefits more precisely.
  - Findings: The central claims are supported: tri-state dramatically reduces false-prune mass at the expense of high deferral; exact-joint intervals inflate deferral and virtually eliminate false-prune; normal approximation coverage can be unacceptably low at small n and low discordance; and tri-state is frequently but not universally cheaper given costs. The non-monotonicity with n (more automatic actions can increase error mass) is an insightful nuance.
  - Limitations: The empirical replay from four small UCI datasets and a handful of model pairs is sufficient as a conditional reference but not representative of “research agents”; this is acknowledged but still narrows practical implications. No analysis varies alpha, and the delta thresholds are not adapted to the loss triples.
- Comparison with related work (using the summaries provided)
  - Fixed-look vs sequential: The paper correctly distinguishes its fixed-look scope from confidence sequences and anytime-valid inference (e.g., Howard et al.; Waudby‑Smith/AsympCS adaptations). This is appropriate.
  - Reject/abstention literature: There is a rich body of work on tests with a reject option and abstention under explicit costs (e.g., M-ary testing with reject options, two-phase tests with a reject then continue design, and cost-aware abstention selection pipelines). While the paper’s goal is measurement under fixed simple rules, situating against such decision-theoretic/operational abstention work would strengthen context and suggest natural extensions (e.g., choosing alpha/delta to minimize expected loss under stated costs; oracle or Bayes-risk benchmarks).
  - Interval literature: The CP interval’s conservatism and alternatives (e.g., coverage-adjusted CP, Wilson/Newcombe) are relevant. For paired binary differences, McNemar-type CIs and exact unconditional approaches provide closer comparators than a naive normal approximation; adding one or two such intervals would improve the audit’s balance.
- Discussion of broader impact and significance
  - The study offers a careful, reproducible quantification of a practical but under-discussed trade-off: replacing forced rejection with deferral reduces harmful false pruning but shifts costs to delayed decisions and fewer automatic actions. It provides actionable cautions (avoid naive normals under sparse discordance) and a framework to think about terminal decision costs. Its conservative scoping and transparency about non-claims are commendable.
  - The main risk is overgeneralization: the results depend on mixtures, costs, and fixed alpha/delta; the authors largely avoid this by framing the work as an audit rather than a prescriptive policy.

5. Questions for Authors
1. Why not include one or two standard paired-difference CIs (e.g., score-based/Newcombe, exact unconditional/McNemar-related) as additional interval baselines, given the conservatism of the joint CP-by-union-bound and the pitfalls of the naive normal?
2. Since you define explicit costs, did you consider optimizing alpha and/or delta to minimize expected loss at the fixed look (per mixture), or reporting an oracle/Bayes-risk lower bound using the observed counts and a prior over regimes?
3. How sensitive are your tri-state vs matched-random conclusions to alternative matching schemes (e.g., matching deferral rates within truth strata, within bins of observed uncertainty/interval width, or conditional on observed discordance)?
4. Could you provide operating characteristics stratified by (g,q) regimes (not just by mixtures) to isolate when tri-state loses to always-DEFER or matched-random, and characterize those failure regions?
5. Can you quantify sensitivity to alpha and to different delta choices beyond the three tested values, particularly to illustrate how “automatic coverage” and expected loss evolve?
6. Do your conclusions persist on larger-scale ML settings (e.g., modern vision/NLP tasks or actual “research agent” pilots)? If not currently available, can you outline a plan to apply the audit to real agent traces?

6. Overall Assessment
This is a careful and transparent measurement study that disentangles interval construction, decision logic, and explicit deferral costs for fixed-look paired comparisons. The methodology is sound (exact integration under the model), the findings are clearly supported, and the practical messages—particularly about the benefits and costs of tri-state deferral and the hazards of naive normal intervals—are useful. However, novelty is limited; the work stops short of connecting the fixed-look decision to principled cost-sensitive optimization, omits stronger paired-CI baselines, and evaluates empirical replay only on small UCI datasets, which blunts the claimed relevance to “research agents.” I view this as a solid and reproducible audit with moderate practical value but not yet at the level of originality and generality expected for ICLR. I recommend rejection in its current form, with encouragement to (i) add standard paired-CI baselines, (ii) incorporate cost-aware calibration of alpha/delta and an oracle/baseline that optimizes fixed-look expected loss, and (iii) validate on more realistic agent pilot traces. These steps would substantially strengthen both the methodological context and the practical significance.

7. Triple Scores
TRIPLE_SCORES:
- Claims_Support: +1  # Are the central claims adequately supported with evidence?
- Experimental_Soundness: +1  # Are the experimental setup and research methodology sound?
- Writing_Clarity: 0  # Is the writing clear and well-organized?
- Prior_Work_Context: 0  # Is the work properly contextualized relative to prior work?
- Question_Importance: 0  # Are the research questions being asked important?
- Originality: 0  # Does the paper bring significant originality of ideas and/or execution?
- Value_to_Community: 0  # Are the results valuable to share with the broader ICLR community?
