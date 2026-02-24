# 🛠️ ROSForge PRD Supplement: CLI UX Design & Open Question Strategies
**Corresponding PRD Version: v1.0**

## 1. CLI UX & Flow Design
[cite_start]To enhance the developer experience and tool stickiness, we further define the interactive flow for core commands (such as `rosforge migrate <path>` and `rosforge analyze <path>` [cite: 64, 65]):

* **Cost Estimator Safety Net**
  * [cite_start]**PRD Alignment:** Addresses the blocking open question in Section 8 regarding how API call costs are communicated to users[cite: 102, 103].
  * [cite_start]**Implementation Concept:** When a user inputs `rosforge analyze <path>` [cite: 65][cite_start], the tool not only outputs the dependency graph but also estimates the token consumption and approximate API costs based on the selected AI engine (e.g., Claude or Codex) [cite: 58-61]. This sets clear cost expectations before the developer executes the migration.

* **Traffic Light Confidence Score**
  * [cite_start]**PRD Alignment:** Fulfills US-06 (flagging untranslatable code segments and providing manual intervention suggestions)[cite: 39, 40].
  * **Implementation Concept:** The AI engine assigns a "Confidence Score" to each translated file. [cite_start]If a file's score drops below 60%, the terminal displays a yellow warning and mandates that this high-risk section, along with manual intervention suggestions, be logged directly into `migration_report.md`[cite: 68].

* **Interactive Diff Review**
  * [cite_start]**PRD Alignment:** Fulfills US-03 (providing detailed changelogs and diff reports for code review)[cite: 35].
  * **Implementation Concept:** After migration, launch an interactive mode (similar to `git add -p`) directly in the terminal. Developers can review code chunks and press `y` to accept, `n` to reject, or `r` to request the AI to regenerate that specific block.

---

## 2. Concrete Solutions for "Open Questions"
[cite_start]Regarding the open questions raised in Section 8 [cite: 101-105], we recommend adopting the following strategies as the baseline for the v1.0 release:

* **ROS1 Version Support Range (Strictly Noetic)**
  * [cite_start]**PRD Alignment:** Resolves the blocking question regarding the supported ROS1 versions in v1[cite: 102, 103].
  * [cite_start]**Implementation Concept:** We strongly recommend restricting v1.0 to support only ROS1 Noetic (Ubuntu 20.04)[cite: 109]. [cite_start]Since Noetic is the final ROS1 release and defaults to Python 3, it offers the highest compatibility with ROS2[cite: 109, 113]. Backward compatibility with Melodic (Python 2) would drastically increase the AI's syntax parsing complexity and error rates.

* **Bridge Fallback Mode for Mixed ROS1/ROS2 Packages**
  * [cite_start]**PRD Alignment:** Addresses the non-blocking question of supporting mixed ROS1 + ROS2 packages (bridge mode) [cite: 104, 105] [cite_start]and aligns with the Section 3 non-goal of excluding Hardware Abstraction Layer (HAL) migrations[cite: 30].
  * **Implementation Concept:** Treat this as the ultimate "Fallback Strategy." [cite_start]If the AI determines a package's logic is too complex or involves hardware drivers (HAL)[cite: 30], ROSForge should automatically generate a corresponding `ros1_bridge` Launch file and configuration. This allows legacy ROS1 nodes to temporarily communicate with the new ROS2 architecture via the bridge.

* **Automated Dependency Installation (`rosdep` Integration)**
  * [cite_start]**PRD Alignment:** Answers the non-blocking question regarding `rosdep` integration[cite: 104, 105].
  * **Implementation Concept:** This is a mandatory step for a truly automated pipeline! [cite_start]Before executing `colcon build` to verify the compilation[cite: 72, 73], the pipeline must automatically inject a `rosdep install` command. This ensures that all new dependencies mapped by the AI are correctly installed, allowing the build validation to succeed in a clean sandbox environment.