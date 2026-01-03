# Building Recommendation Systems for AI Tool Configuration Wizards

A desktop application recommending AI model configurations faces a specific engineering challenge: balancing **40+ capability dimensions** against **hardware constraints** while serving users ranging from beginners to experts. The optimal architecture uses a three-layer approach—constraint satisfaction filtering, content-based feature matching, and multi-criteria scoring—paired with progressive preference elicitation that captures meaningful input without causing fatigue. This report synthesizes research across UX design, recommendation algorithms, product configurators, and analogous systems to provide concrete implementation guidance.

## The 5-question threshold determines onboarding success

Research consistently identifies **5-7 questions** as the maximum before significant quality degradation occurs. SurveyMonkey data shows respondents spend **75 seconds** on question 1 but only **19 seconds** by questions 26-30. More critically, InMoment research found that **74% of users** are only willing to answer 5 questions or fewer, with completion rates dropping **18%** when increasing from just 3 to 4 questions.

For a technical configuration wizard, this suggests a two-phase approach. The **first-run experience** should capture only essential information: primary use case, experience level, and one preference slider (such as quality-versus-speed priority). This maps directly to the Spotify model, which asks for **3-10 artist selections** during signup and immediately begins recommendations. Hardware detection should be automatic, eliminating questions entirely for that dimension.

The semantic anchoring of scales significantly affects response quality. Research from TASO and Nielsen Norman Group establishes that **all anchor points must be labeled**, not just endpoints. For a 5-point assistance preference scale, effective anchoring looks like: (1) Only when I ask → (2) Gentle suggestions → (3) Balanced assistance → (4) Proactive guidance → (5) Maximum automation. This specificity prevents the midpoint from becoming an escape hatch and produces actionable differentiation in responses.

Progressive disclosure should follow the **80/20 pattern**: expose 20% of settings that cover 80% of use cases initially, with "Advanced settings" available but collapsed. JetBrains' IDE wizards demonstrate this effectively—they auto-detect existing tool installations, offer selective import, and provide a Customize tab without requiring its use. The key insight from game settings wizards is that **presets plus override** outperforms either approach alone. Offering "Beginner / Balanced / Power User" configurations with visible drill-down produces higher satisfaction than either pure presets or granular-only interfaces.

## Constraint satisfaction plus TOPSIS handles mixed requirements elegantly

For 40+ dimensions with both hard constraints (VRAM limits) and soft preferences (style priorities), the research strongly favors a **three-layer architecture**. The first layer applies constraint satisfaction programming to eliminate infeasible configurations immediately—if a model requires 12GB VRAM and the user has 8GB, that option simply disappears. The second layer uses content-based feature matching, scoring remaining viable options against user requirements without requiring historical data. The third layer applies TOPSIS (Technique for Order Preference by Similarity to Ideal Solution) for final ranking based on weighted soft preferences.

This architecture specifically avoids **Analytic Hierarchy Process (AHP)**, which requires *(n²-n)/2* pairwise comparisons. For 40 dimensions, that's 780 comparisons—computationally expensive and impossible to calibrate. TOPSIS scales linearly and provides interpretable results as "closeness to ideal solution." MDPI benchmarking studies confirm TOPSIS handles high-dimensional problems effectively, though it shows sensitivity to weight changes on heavily-weighted criteria.

| MCDA Method | Scalability for 40+ Dimensions | Constraint Handling | Implementation Complexity |
|-------------|-------------------------------|---------------------|--------------------------|
| Weighted Sum | Excellent | Poor (no native support) | Very Low |
| TOPSIS | Good | Limited | Low |
| AHP | Poor (780 comparisons) | Yes via hierarchy | High |
| ELECTRE | Moderate | Yes (discordance) | Medium-High |

**Content-based filtering is the correct choice** for technical tool selection, not collaborative filtering. Technical tools have well-defined attributes—model architecture, parameter count, supported tasks, hardware requirements—that enable immediate recommendations without user history. Crucially, content-based approaches produce **explainable recommendations** ("This model fits your 8GB VRAM and supports image-to-image"), which matters for technical users who want to understand why something was suggested. Collaborative signals ("users like you also chose...") can be added later as usage data accumulates, but shouldn't be the primary mechanism.

The cold-start problem is largely solved by combining automatic hardware detection with 3-5 onboarding questions. Netflix asks for **3-5 show/genre selections** during registration; Amazon starts with popular items and immediately incorporates purchase signals. For your configurator, the equivalent is: detect hardware automatically, ask about primary use case and experience level, then apply the matching preset with transparent explanation of what was configured and why.

## Forty dimensions internally, five to seven exposed to users

The cognitive science is clear: humans can meaningfully evaluate **4±1 constructs** simultaneously (Cowan's updated finding from 2001, more accurate than Miller's "7±2" which concerned memory recall, not comparative evaluation). Research in the Journal of Consumer Psychology shows measurable cognitive fatigue after comparing more than **7-9 product attributes**, with satisfaction decreasing and abandonment increasing exponentially beyond this threshold.

This does not mean 40+ internal dimensions is overengineering—it means the **architecture must be layered**. Maintain comprehensive internal dimensions for accurate matching and filtering, while exposing aggregated factor scores to users. Factor analysis with rotation identifies interpretable clusters that can become user-facing categories:

- **Performance** (speed, throughput, latency, efficiency)
- **Quality** (photorealism, consistency, fidelity, detail)
- **Capabilities** (editing, generation, control, flexibility)  
- **Compatibility** (hardware fit, platform support, integration)
- **Accessibility** (ease of use, documentation, community)

Each user-facing factor aggregates multiple internal dimensions. Users see a "Quality" score of 8.5/10; experts can drill down to see photorealism: 9, consistency: 8, fidelity: 8.5. This pattern appears in successful tech products—Apple's comparison pages show 5-7 key differentiating attributes despite tracking hundreds internally.

For **correlated dimensions** like speed versus quality, the solution is explicit trade-off modeling rather than elimination. Define the Pareto frontier between competing factors and let users specify their position: "I prioritize speed over quality" becomes a weighted preference that adjusts internal calculations. Alternatively, use entropy weighting or the CRITIC method to automatically reduce the combined weight of highly correlated dimensions. The key principle from MCDM research: correlation in alternatives is acceptable—the fact that fast systems tend to have lower quality is a feature of the domain, not a data problem.

Score normalization across heterogeneous scales uses straightforward formulas. **Min-Max normalization** maps any scale to [0,1]: for Likert 1-5 scales, *(score - 1) / 4* produces the range. Hardware constraints typically remain binary (compatible/incompatible) in the first filtering layer. For continuous performance metrics, apply Z-score normalization if approximately normal, log-transform first if power-law distributed, or use robust scaling (median and interquartile range) if outliers exist. The TOPSIS method specifically uses vector normalization: *x' = x / √(Σx²)*.

## Presets with customization outperforms either pure approach

The research on personas versus granular control converges on a **hybrid pattern**: presets as starting points with visible customization available. God of War: Ragnarök offers 70+ accessibility features but provides accessibility presets for quick customization—users can accept the preset or drill into specifics. This reduces cognitive load for the 80% who accept defaults while preserving power for the 20% who want control.

The optimal number of presets is **3-5**. More creates choice paralysis; fewer fails to capture meaningful variation. For an AI tool configurator, this might be:

- **Minimal Setup**: Conservative settings, works on all hardware, least automation
- **Balanced**: Smart defaults based on detected hardware, moderate automation  
- **Power User**: Maximum capabilities enabled, assumes high-end hardware, proactive features
- **Custom**: Start from scratch (hidden behind "I know what I want")

Each preset should **show what it configures**—transparency builds trust and teaches users about available options. Dell's configurator displays "Standard Configurations" as validated bundles that users customize from, not black boxes. Tesla's configurator shows real-time visualization as options change, creating immediate feedback loops.

For users with diverse expertise levels, **auto-detection plus self-selection** handles the range. JetBrains IDEs detect other installed tools and offer selective import; game engines run brief benchmarks and map results to preset tiers. The first-run flow should be: (1) Auto-detect hardware and existing installations, (2) Ask 2-3 profiling questions via decision tree ("What best describes you?"), (3) Apply smart defaults with transparent summary, (4) Offer immediate "Use recommended" or "Customize" choice.

Returning users should **skip onboarding entirely**—check for existing configuration on launch. Inactive returning users get a "What's New" summary. The principle from Userpilot research: "A good onboarding experience doesn't overwhelm users by providing too much information upfront—users can be onboarded to different areas as they become comfortable over time."

## Implementation patterns from games and configurators translate directly

The most applicable implementation patterns come from game graphics settings and enterprise CPQ (Configure, Price, Quote) systems. Both domains solve the same problem: complex multi-attribute selection with hard constraints and soft preferences.

**Auto-detection** in games (Unreal Engine, NVIDIA GeForce Experience) follows a consistent pattern: run a brief benchmark that returns a performance index, map that index to a preset tier, then apply settings. The benchmark creates a **hardware score** (Unreal uses 100.0 as "average good hardware") that enables configuration without asking users to know their specs. The critical lesson: **err conservative**—set defaults lower than detected capability to prevent first-run frustration, then suggest upgrades based on observed performance.

**Constraint propagation** from CPQ systems handles compatibility elegantly. When a user selects Option A, dependent options auto-update or become disabled. The best UX **prevents invalid selections** rather than allowing them and showing errors—hide or grey out incompatible options with explanatory tooltips rather than blocking after selection. Salesforce's constraint rules engine evaluates all possible combinations in real-time, filtering dynamically as selections change.

The **decision tree versus scoring matrix** choice depends on context. Use decision trees for user-facing guidance (clear branching, deterministic paths, easy to understand) and scoring matrices for internal ranking (handles multi-factor decisions, flexible combinations, gradual rather than binary). The practical implementation: decision tree to narrow the option space through filtering questions, scoring matrix to rank remaining viable options.

| Situation | Recommended Approach |
|-----------|---------------------|
| Few clear branches, user needs guidance | Decision Tree (Wizard) |
| Many independent factors, complex tradeoffs | Scoring Matrix |
| Hard constraints (hardware limits) | Decision Tree / Boolean filtering |
| Soft preferences (style, priorities) | Scoring Matrix / TOPSIS |

For **validation and feedback**, real-time is essential. Framework laptop's configurator highlights incomplete steps in red immediately rather than after submission. Show resource impact (VRAM usage, storage requirements) updating live as selections change, similar to Tesla's real-time pricing display.

## Warning signs help calibrate engineering effort

**Over-engineering indicators** for capability dimensions:
- Users cannot explain what dimensions mean
- Many dimensions have near-zero variance across options
- High multi-collinearity (dimensions >0.9 correlated)
- Users consistently skip or ignore most dimension inputs
- Recommendation quality doesn't improve with additional dimensions

**Under-engineering indicators**:
- Users frequently ask "what about X?" for missing considerations
- Cannot meaningfully distinguish between similar modules
- Important tradeoffs are hidden from users
- Matching quality is poor despite correct inputs
- Expert users consistently override recommendations

The **40-dimension question** resolves to: 40+ is appropriate for internal matching and filtering if those dimensions genuinely differentiate options. It becomes overengineering if many dimensions are redundant, highly correlated, or don't affect recommendation quality. Run correlation analysis on your dimension set—dimensions with >0.85 correlation should be candidates for aggregation. Monitor recommendation acceptance rates and override patterns to identify which dimensions actually influence decisions.

## Concrete implementation architecture

The synthesized recommendation for your AI tool configurator:

```
FIRST-RUN FLOW (< 90 seconds)
├── Hardware Detection (automatic, 0 questions)
│   └── GPU/VRAM, RAM, storage, platform detection
├── Profile Selection (2-3 questions)
│   ├── "What will you primarily use this for?"
│   ├── "How technical is your workflow?"  
│   └── "Quality vs speed priority?" (slider)
├── Smart Defaults Applied
│   └── Preset selection + hardware constraints = configuration
└── Summary Screen
    ├── "Here's what we configured and why"
    └── [Use Recommended] [Customize] buttons

RECOMMENDATION ENGINE
├── Layer 1: Constraint Satisfaction (hard filters)
│   └── Eliminate options violating hardware limits
├── Layer 2: Content-Based Matching (feature similarity)
│   └── Score options against user requirements  
└── Layer 3: TOPSIS Ranking (soft preference weighting)
    └── Order by closeness to ideal solution

USER-FACING DIMENSIONS (5-7 aggregated factors)
├── Performance factor (aggregates speed, efficiency, throughput)
├── Quality factor (aggregates photorealism, consistency, fidelity)
├── Capability factor (aggregates editing, generation, control)
├── Compatibility factor (aggregates hardware fit, integrations)
└── [Drill-down available for expert users]

PROGRESSIVE DISCLOSURE
├── Default view: Essential settings (collapsed advanced)
├── After 3 sessions: Prompt for calibration ("How's performance?")
├── After 10 sessions: Surface "Advanced Settings" option
└── Expert mode: Full dimension access via toggle
```

This architecture handles the scale requirement (4 modules now → N modules) by keeping the constraint and scoring layers module-agnostic. Each module contributes its capability dimensions to the shared taxonomy; the recommendation engine operates on the unified dimension space. New modules require only adding their dimensions and constraints to the existing framework.

## Conclusion

The core insight across all research domains is **layered architecture**: comprehensive internal representation with simplified external presentation. Your 40+ dimensions are appropriate for accurate matching but must surface to users as 5-7 interpretable factors. Hardware constraints filter absolutely via constraint satisfaction; user preferences weight via TOPSIS scoring. The 5-question onboarding limit is not arbitrary—it reflects measured cognitive thresholds that determine whether users complete setup or abandon.

The game settings pattern—auto-detect hardware, map to preset tier, allow override—solves the cold-start problem elegantly and has decades of validation across PC gaming. Combined with the IDE pattern of detecting existing installations and offering selective import, first-run configuration can feel intelligent rather than interrogative. The hybrid preset-plus-customization approach satisfies both beginners who want guidance and experts who want control without maintaining separate paths.

The decision against AHP for high-dimensional problems, the preference for content-based over collaborative filtering for technical tools, and the constraint satisfaction plus TOPSIS hybrid architecture emerge consistently from MCDA research and recommender systems literature. These aren't merely preferences—they're engineering constraints imposed by computational complexity and the specific characteristics of technical product configuration.