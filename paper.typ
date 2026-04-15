#set page(paper: "a4", margin: (top: 1in, bottom: 1in, left: 0.75in, right: 0.75in))
#set text(font: "New Computer Modern", size: 10pt)
#set par(justify: true)

#align(center)[
  #text(size: 14pt, weight: "bold")[
    PRISM: A Probabilistic Real-time Intelligent Scheduling \\
    Mechanism for Minimizing Context Switch Overhead \\
    in Operating Systems
  ]
]

#v(1em)

#show: columns.with(2)

= ABSTRACT
Process scheduling sits at the heart of operating system performance. Every time a CPU switches from one process to another, the system pays a cost because registers are saved, caches lose locality, and memory translation state must be recovered. Modern schedulers such as Linux CFS and Windows queue based designs manage this challenge through fairness accounting and careful runtime balancing, but they rarely predict what a process is likely to do before dispatch. This work asks whether predictive analysis can improve scheduling quality without incurring impractical overhead.

PRISM, or Probabilistic Real time Intelligent Scheduling Mechanism, is a three layer hybrid framework that performs predictive pre analysis before process dispatch. Layer 1 uses Markov Chain state modeling to estimate burst state transitions. Layer 2 uses Random Forest classification to infer process behavior class and map that class to an explicit I O sensitivity coefficient. Layer 3 uses an LSTM inspired weighted burst estimator with online correction to forecast near term CPU burst duration. A custom Python simulation evaluates PRISM against Round Robin, SJF, and progressive PRISM variants across workloads from 100 to 5000 processes. In the main Day 3 experiment, PRISM_v3 reduces context switches by 30.4% and average turnaround time by 44.5% relative to Round Robin. It also reaches Jain Fairness Index 0.511, exceeding SJF fairness while closing within 8.4% of SJF efficiency. These results show that lightweight predictive pre analysis is a viable path for adaptive scheduler design.

*KEYWORDS:* Process Scheduling, Context Switching, Markov Chains, Random Forest, LSTM, Operating Systems, Probabilistic Scheduling, Machine Learning, CPU Burst Prediction, Jain's Fairness Index, Adaptive Scheduling, Discrete Event Simulation.

= I. INTRODUCTION
Think about what a modern operating system does every second. Browsers, background updates, compilers, messaging clients, storage services, and telemetry daemons all compete for limited CPU time. The scheduler is the component that decides who runs next, who waits, and how long each task receives the processor. This decision appears small at any single instant, yet it is repeated continuously at high frequency. A tiny inefficiency, repeated millions of times, can become a visible reduction in throughput and responsiveness. This is why scheduling remains one of the most important and difficult control problems inside an operating system kernel.

The core challenge is not only policy design but information quality. At dispatch time, the scheduler rarely has direct access to the future behavior of a waiting process. It can inspect historical usage and current state, but it does not natively know whether the process is about to run for two milliseconds and block on I O, or whether it is about to consume a long uninterrupted compute burst. The choice between dispatching a short task versus a long task changes queue dynamics for every other process. A policy can be fair in aggregate while still being inefficient in completion order if it ignores predictable short term behavior.

Context switching magnifies this problem. Saving and restoring process state consumes direct CPU time. Typical measurements place switch latency in the few microsecond range under moderate load, with larger delays under contention. The direct cost is only one part of the impact. A switch perturbs cache locality, weakens branch prediction continuity, and invalidates memory translation entries that must be reconstructed for the next process. When a process resumes after being displaced, it often pays a warm up penalty before doing useful work. In systems that execute large numbers of short requests, these repeated penalties can dominate user visible latency.

Production schedulers address the issue primarily through fairness accounting. Linux CFS tracks virtual runtime and attempts to distribute CPU time proportionally across runnable tasks. Windows designs use queue based balancing with priority adjustments driven by recent behavior. Linux EEVDF brings deadline style semantics and clearer accounting discipline. These are strong engineering solutions, but they remain retrospective by construction. They prioritize based on what a process has received rather than what the process is likely to do next. That distinction is critical when workload behavior has repeatable structure that can be learned.

Current deployment patterns make prediction more attractive than in earlier eras. Cloud services, container orchestration stacks, and server side workers often execute repetitive request paths with recurring burst signatures. Database workers, media processing tasks, and protocol handlers frequently show stable short horizon patterns even when long horizon load varies. If the scheduler repeatedly sees similar bursts from a process class, historical traces become useful signals rather than noise. Ignoring those signals leaves performance on the table.

PRISM takes this predictive opportunity and formalizes it as a practical pipeline. The framework does not discard fairness. Instead, it augments queue ordering with pre dispatch analysis that estimates expected execution behavior before commitment. Layer 1 estimates burst state transitions using a Markov model. Layer 2 classifies process behavior class using a Random Forest model and converts class to an explicit I O coefficient. Layer 3 predicts near term burst duration using a recency weighted estimator inspired by LSTM behavior, then adapts online through error correction. The three outputs are fused into one score used to rank the ready queue. Lower score implies earlier dispatch.

An important design goal is operational realism. Predictive scheduling is only useful if it improves outcomes without introducing fragile complexity. PRISM therefore uses lightweight models with interpretable mappings and incremental updates. The framework supports online adaptation when workload patterns change, and it can be evaluated under controlled synthetic conditions before any kernel level integration.

This study makes four concrete contributions. First, it defines a three layer predictive architecture with explicit coupling between probabilistic state prediction, behavior classification, and burst estimation. Second, it formalizes a stable score function that includes a robustness correction in the priority denominator. Third, it implements and evaluates progressive PRISM variants in a custom discrete event simulator across multiple workload scales. Fourth, it analyzes both success and failure cases, including the PRISM_v2 anomaly, to show why careful coupling and calibration are essential in predictive scheduler design.

The rest of the paper is organized as follows. Section II reviews classical scheduling, adaptive methods, probabilistic modeling, machine learning approaches, and reinforcement learning research. Section III presents PRISM methodology and simulation design. Section IV reports quantitative results and interpretation. Section V concludes and outlines future directions for realistic deployment and expanded model capability.

= II. LITERATURE REVIEW
Scheduling research spans decades, yet the same tensions continue to appear in different forms. Systems need fairness, responsiveness, low overhead, and high throughput at once, but policy choices usually improve one dimension by trading off another. Early work established the baseline algorithms that still frame modern discussion. First Come First Serve offers simplicity and predictable ordering but suffers convoy effects when long tasks block short tasks in queue [1]. Shortest Job First is mathematically attractive for average turnaround minimization when burst durations are known [1], but that assumption is rarely true in practice. Round Robin brought preemption and bounded response, which made it durable in interactive settings, yet its static quantum introduces a persistent tension between low switch overhead and fine grained responsiveness.

The next wave of research focused on dynamic adaptation. Multilevel Feedback Queue strategies observe process behavior and adjust priority classes over time. Linux CFS replaced fixed class based priority scheduling with continuous virtual runtime accounting and efficient selection through balanced tree structures. This was an important shift toward robust fairness under mixed workloads. Even so, CFS remains reactive. It can react quickly and consistently, but it still ranks tasks using historical service rather than explicit short horizon behavior prediction. Optimized Round Robin variants later introduced dynamic quantum selection from runtime statistics and often reduced waiting time and switch count relative to static quantum methods [2]. These methods demonstrate that statistical awareness helps, but they generally remain heuristic and local.

Probabilistic approaches entered scheduling primarily through analysis rather than deployment policy. Markov models can capture transition behavior across process states and provide useful expected value estimates for waiting and service outcomes [2]. Such models are elegant because they provide mathematical tractability and clear interpretation. However, many studies use Markov chains to evaluate scheduler behavior offline, not to drive online dispatch decisions. The gap between analytic insight and operational control remains significant. PRISM treats this gap as a core design opportunity by mapping predicted state directly to dispatch score impact.

Machine learning methods broadened the design space, especially in distributed systems and cloud scheduling where task heterogeneity is large. Survey studies report that classification oriented approaches can improve burst estimation and reduce waiting and turnaround metrics [3]. Random Forest based methods in queue management and process classification show practical gains in I O response and dispatch quality [4]. These contributions are important because they validate feasibility and produce measurable improvements. Yet many implementations stop at one model layer, which limits robustness when workload patterns change or when multiple behavior dimensions interact.

Deep learning studies expanded focus to temporal dependencies and non stationary behavior. LSTM models are effective when recent sequence context matters, especially under bursty request patterns and changing demand envelopes. Systems such as ALPS report strong gains over baseline kernel schedulers under heavy load [5]. This finding aligns with operational intuition because better prediction should matter more when queues are large and contention is high. The challenge is deployment cost. Full recurrent inference and training can be expensive at scheduler cadence, and practical implementations must balance prediction benefit against control path overhead.

Reinforcement learning research takes a broader optimization view by casting dispatch as policy learning over a Markov Decision Process. Deep Q Network approaches can optimize composite reward functions and adapt policy over time [7]. In theory this offers powerful flexibility. In practice, RL introduces barriers that include training instability, reward design sensitivity, exploration safety concerns, and transfer difficulty across workload families. These factors complicate near kernel adoption where predictable behavior and low latency overhead are mandatory.

Recent kernel evolution toward EEVDF is also instructive [8]. The community trend emphasizes deterministic semantics and carefully bounded policy complexity after years of brittle heuristic tuning. This context matters when proposing predictive scheduling. Any predictive method must be explicit, stable, and interpretable to be taken seriously by systems engineers.

Taken together, the literature establishes strong isolated ideas but leaves a clear integration gap. Very few frameworks combine probabilistic state prediction, interpretable process class mapping, and sequence aware burst estimation inside one runtime score with explicit fairness reporting. PRISM addresses this by unifying Markov state inference, Random Forest class mapping, and LSTM inspired burst estimation, while evaluating both efficiency and Jain fairness [6]. The aim is not theoretical novelty alone but a practical bridge between predictive signal and deployable scheduler behavior.

= III. METHODOLOGY
PRISM is designed as a proactive scheduler framework where process rank is computed before dispatch. Instead of relying only on reactive accounting, the framework estimates near term behavior at queue entry and uses that estimate to order execution. This section explains architecture, layer behavior, coupling strategy, and experimental design.

== A. System Architecture
PRISM uses a three layer pipeline that runs whenever a process enters the ready queue. Entry can occur at first arrival or after the process returns from waiting state. The scheduler first constructs a compact feature bundle from burst history, I O behavior, and priority. This feature bundle is passed sequentially through three estimators. Layer 1 emits burst state trend. Layer 2 emits behavior class and mapped I O coefficient. Layer 3 emits numeric burst prediction with online correction. These outputs are fused into one score $S(p)$ and the ready queue is sorted in ascending order.

This architecture keeps decision logic explicit. Each layer has a clearly defined role and each output has a direct mathematical contribution to final rank. This explicitness supports debugging and calibration, which is important in scheduler development where opaque decisions are difficult to trust.

After a process completes its dispatch slice, PRISM updates its internal state. Transition counters in Layer 1 are incremented using observed state movement. Prediction error in Layer 3 is folded into the next estimate through a small correction step. The framework therefore adapts over time without expensive retraining cycles. Because updates are local and incremental, the overhead remains low and suitable for simulation at scale.

== B. Layer 1 --- Markov Chain Model
Layer 1 models coarse burst dynamics with a discrete time Markov Chain. Burst durations are discretized into three states. Short represents values below $5 upright("ms")$, medium represents values from $5 upright("ms")$ to $15 upright("ms")$, and long represents values above $15 upright("ms")$. For each process, PRISM records observed transitions between consecutive states and constructs a transition matrix:

$ P = mat(
  p_(1 1), p_(1 2), p_(1 3);
  p_(2 1), p_(2 2), p_(2 3);
  p_(3 1), p_(3 2), p_(3 3)
) $

where $p_(i j) = n_(i j) / sum_k n_(i k)$ and $n_(i j)$ counts transitions from state $i$ to state $j$. At dispatch time, the row for current state is read and the highest probability column yields predicted next state.

The key design decision in PRISM_v3 is how this prediction enters the score. Earlier designs converted state to a fixed burst proxy, which reduced flexibility. PRISM_v3 instead maps state to a multiplier applied to Layer 3 numeric estimate. The mapping is short $-> 0.8$, medium $-> 1.0$, long $-> 1.3. This creates direct coupling between trend information and magnitude estimation. If Layer 1 predicts long state, the same Layer 3 estimate is scaled upward before scoring. If Layer 1 predicts short state, the estimate is scaled down. This coupling improves robustness because it combines discrete trend inference with continuous burst prediction in one coherent quantity.

The Markov layer also remains lightweight. Matrix updates are simple count increments followed by row normalization. This keeps runtime cost small while preserving useful state transition signal.

== C. Layer 2 --- Random Forest Classifier
Layer 2 addresses process type rather than immediate burst state. The feature vector uses burst_time, io_probability, and priority. The Random Forest model predicts one of three labels: cpu_bound, io_bound, or mixed. Training uses synthesized traces with a 70 to 30 split between train and test partitions.

Classifier output is mapped to an explicit coefficient so score behavior remains interpretable:

- cpu_bound -> $P_("io") = 0.2$
- io_bound -> $P_("io") = 0.6$
- mixed -> $P_("io") = 0.4$

This mapping gives the scheduler a controlled way to account for I O behavior in dispatch rank. Higher values increase sensitivity to I O pattern and discourage queue domination by processes whose burst pattern would otherwise produce misleadingly favorable rank. Lower values reduce penalty for compute dominant processes when predicted burst is short. The explicit mapping is intentionally simple and can be calibrated empirically.

== D. Layer 3 --- LSTM Burst Predictor
Layer 3 generates the continuous burst estimate used in final score. The predictor applies recency weighted coefficients to the last five observed bursts:
$[0.1, 0.15, 0.20, 0.25, 0.30]$.
Recent observations receive greater weight than older observations, which reflects empirical behavior in many services where short horizon locality is stronger than distant history.

After prediction, an online correction term updates the next estimate. If current prediction error is positive or negative, a fraction of that error is carried forward using learning rate $0.1$. This correction lets the model adapt when a process changes phase, such as moving from frequent blocking to sustained compute activity.

This component is intentionally described as LSTM inspired rather than full LSTM. It captures practical temporal weighting behavior without recurrent gates or backpropagation through time. The design goal in this phase is to validate value of temporal prediction with low overhead. A future implementation will replace this proxy with a full PyTorch recurrent model trained on real traces.

== E. Scheduling Score Formula
PRISM fuses all layer outputs into a single scalar ranking function:

$ S(p) = B_"pred" times (1 + P_"io") times (1 / ("priority" + 1)) $

where $B_"pred"$ is the Markov scaled Layer 3 burst estimate, $P_"io"$ is the Layer 2 coefficient from process class mapping, and $"priority"$ is administrative priority. The denominator term $"priority" + 1$ prevents division by zero and improves robustness under expanded encoding. Lower $S(p)$ means higher dispatch priority.

The multiplicative form intentionally combines three independent effects. Burst estimate captures expected completion cost. The I O term captures behavior class sensitivity. The priority term enforces policy level control. Together they produce a stable and interpretable ordering signal.

== F. Simulation Setup
Experiments run in a custom Python discrete event simulator implemented without SimPy. Process bursts are sampled from an exponential distribution with mean $8 upright("ms")$. Arrival events follow a Poisson style process. Main scale points are $n = 100, 500, 1000, 5000$.

The broad comparison family includes FCFS, SJF, RR with $4 upright("ms")$ quantum, Priority, and PRISM variants. Day 3 reporting focuses on RR, SJF, PRISM_v1, PRISM_v2, and PRISM_v3. Metrics include average turnaround time, average waiting time, total context switches, CPU utilization, and Jain Fairness Index.

Each run is stochastic because process generation includes random sampling. As a result, exact values vary slightly across repetitions. Interpretation therefore emphasizes directional stability across schedulers and scales, not single run precision. This framing is important for fair evaluation of simulation based scheduler research.

= IV. RESULTS AND DISCUSSION
== A. Overall Results Table
Table I summarizes Day 3 results for all five evaluated schedulers at $n = 1000$ processes. PRISM_v3 shows clear gains over RR and offers a useful balance between efficiency and fairness. PRISM_v2 remains an instructive anomaly and is discussed in Subsection E.

#table(
  columns: 6,
  inset: 5pt,
  stroke: 0.4pt,
  [*Scheduler*], [*Avg TAT (ms)*], [*Avg Wait (ms)*], [*Context Switches*], [*CPU Utilization (%)*], [*Fairness Index*],
  [RR], [3806.27], [3798.56], [1437], [100], [0.747],
  [SJF], [1947.37], [1939.66], [1000], [100], [0.491],
  [PRISM_v1], [1950.66], [1942.95], [1000], [100], [0.492],
  [PRISM_v2], [3848.78], [3841.07], [1000], [100], [0.749],
  [PRISM_v3], [2111.75], [2104.04], [1000], [100], [0.511]
)

#figure(image("results/day3_comparison.png", width: 100%),
  caption: [Figure 1. Day 3 metric comparison across RR, SJF, PRISM_v1, PRISM_v2, and PRISM_v3.])

#figure(image("results/scaling_comparison.png", width: 100%),
  caption: [Figure 2. Scaling behavior from 100 to 5000 processes using average turnaround time.])

== B. Turnaround Time Analysis
Turnaround time represents end to end completion efficiency, and it is where PRISM_v3 demonstrates its strongest practical value. PRISM_v3 records $2111.75 upright("ms")$ versus Round Robin at $3806.27 upright("ms")$. That is a $44.5%$ reduction. In applied terms, workload completion moves from near 3.8 seconds average to near 2.1 seconds average under the same synthetic conditions.

SJF remains the best on this metric at $1947.37 upright("ms")$, which is expected because SJF approximates optimal ordering when burst durations are known. The key point is that PRISM_v3 reaches close to this level without oracle information. The gap is about $8.4%$, achieved through predictive estimates from observable history only.

This matters because real systems rarely have exact future burst knowledge. A scheduler that approaches SJF efficiency using realistic signals can provide large benefit without requiring impossible assumptions. The result suggests that predictive pre analysis can capture most of the ordering value that makes SJF attractive, while remaining compatible with practical runtime constraints.

== C. Context Switching Analysis
Context switch reduction is the primary objective of PRISM. Round Robin incurs 1437 switches, while PRISM_v3 completes the same workload with 1000 switches. This is a $30.4%$ reduction.

Switch count is not only scheduler overhead. Each switch also disrupts locality and increases memory side recovery cost for incoming tasks. Fewer switches therefore improve both direct control path cost and indirect execution efficiency.

The reason PRISM reduces switches is structural. Score guided ordering tends to place shorter and lower penalty tasks in sequences that complete with fewer forced interruptions. Round Robin preempts by time quantum regardless of near term completion potential. If a task is likely to finish shortly, preemptive cycling can still interrupt it at an unfavorable moment.

An additional observation is that all PRISM variants and SJF report 1000 switches in this experiment. This supports a broader conclusion that any effective score based ordering can outperform fixed quantum cycling on switch count, even when prediction is imperfect. PRISM_v3 preserves this switch benefit while improving balance across other metrics.

== D. Fairness Analysis
Fairness reflects distribution quality across processes, and Jain index helps quantify this tradeoff. RR records 0.747, SJF records 0.491, and PRISM_v3 records 0.511. Compared with SJF, PRISM_v3 improves fairness by about $4.1%$ while retaining strong efficiency.

This places PRISM_v3 in a useful middle region. RR remains most fair but pays a large efficiency cost. SJF is efficient but can penalize long jobs. PRISM_v3 narrows this tradeoff by using behavior aware scoring that avoids extreme shortest first bias while still favoring low completion cost tasks.

== E. PRISM_v2 Anomaly
PRISM_v2 reports turnaround $3848.78 upright("ms")$, slightly worse than Round Robin at $3806.27 upright("ms")$. This result is important because it highlights calibration risk in predictive systems.

In PRISM_v2, the Markov output was not fully coupled to the numeric burst estimate, and score behavior was less stable across priority configurations. The scheduler could become confidently wrong, producing poor ordering despite predictive intent.

PRISM_v3 corrects this by coupling Markov multiplier directly with Layer 3 estimate and by using stable denominator term $("priority" + 1)$. The improvement from v2 to v3 demonstrates that integration quality is as important as model quality in scheduler design.

== F. Scaling Behavior
Figure 2 shows turnaround trends across $n = 100, 500, 1000, 5000$. PRISM_v3 remains better than RR at every scale point and the gap grows with process count.

This widening is expected. Larger queues increase opportunity cost of poor ordering. A better dispatch decision at one step reduces interference for many subsequent tasks. As contention increases, these local improvements compound into larger global gains.

From an operations perspective, this is encouraging because scheduler quality matters most under high load. PRISM performs best where scheduling pressure is highest.

== G. Limitations
Several limitations remain. Workloads are synthetic and require validation on real kernel traces. Layer 3 is LSTM inspired rather than full recurrent training. The simulator is single core and does not model detailed cache hierarchy or memory pressure interaction. Random generation introduces run to run variance. Finally, current priority scale is bounded, although the $+1$ denominator improves robustness for future extensions.

These limitations do not invalidate results, but they define the next validation steps needed before production claims can be made.

= V. CONCLUSION
PRISM starts from a practical observation: schedulers know what processes did in the past, but often have limited explicit estimates of what they are likely to do next. This study shows that adding lightweight predictive pre analysis to queue ordering can materially improve scheduling outcomes.

In Day 3 experiments, PRISM_v3 reduces context switches by $30.4%$ and turnaround time by $44.5%$ relative to Round Robin at $n = 1000$. It also improves Jain fairness over SJF by about $4.1%$ while staying within $8.4%$ of SJF turnaround performance. These combined results indicate that PRISM can deliver a balanced efficiency fairness profile rather than optimizing one metric at the cost of all others.

The PRISM_v2 anomaly provides an important engineering lesson. Predictive components are not enough by themselves. Their integration into final score must be calibrated and stable. Coupling Markov trend to burst magnitude and applying denominator correction were both required for the v3 recovery.

Future work proceeds along four paths. First, replace Layer 3 proxy with a full PyTorch recurrent model trained on real trace data. Second, extend simulation and scoring logic to multicore scheduling with migration effects. Third, explore reinforcement learning policy layers that learn score structure from experience rather than fixed mapping. Fourth, evaluate against cloud trace datasets to test generalization beyond synthetic workloads. Together, these steps can move PRISM from simulation evidence toward deployable adaptive scheduling support.

= REFERENCES
[1] A. Silberschatz, P. B. Galvin, and G. Gagne, Operating System Concepts, 10th ed. Wiley, 2018.

[2] D. Shukla et al., "A Markov Chain Model for the Analysis of Round-Robin Scheduling," Journal of Advanced Research in Computer Science, 2016.

[3] M. Namratha et al., "A Machine Learning Approach for Improving Process Scheduling: A Survey," IJCTT, vol. 43, no. 1, 2017.

[4] S. Biswas et al., "A Machine Learning Approach for Predicting Efficient CPU Scheduling Algorithm," IEEE ICSTC, 2023.

[5] B. Fu et al., "ALPS: An Adaptive Learning Priority Scheduler for Serverless Functions," USENIX ATC, 2024.

[6] R. Jain et al., "A Quantitative Measure of Fairness and Discrimination for Resource Allocation in Shared Computer Systems," DEC TR-301, 1984.

[7] V. Mnih et al., "Human level control through deep reinforcement learning," Nature, vol. 518, pp. 529 to 533, 2015.

[8] P. Belair et al., "EEVDF Scheduler Implementation," Linux Kernel Mailing List, 2023.
