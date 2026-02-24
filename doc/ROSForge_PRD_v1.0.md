# ROSForge — 產品需求文件 (PRD)

**ROS 鎔爐｜次世代 ROS 遷移自動化代理**

| 欄位 | 內容 |
|------|------|
| 文件版本 | v1.0 |
| 日期 | 2026-02-24 |
| 狀態 | Draft |
| 作者 | RLin / Claude |

---

## 1. 問題陳述 (Problem Statement)

ROS (Robot Operating System) 生態系正經歷 ROS1 至 ROS2 的世代交替。ROS2 帶來了全新的通訊中介層 (DDS)、生命週期管理節點、重新設計的建構系統 (ament) 以及全面翻新的 API，這代表兩代系統之間存在根本性的架構斷層。

對於仍維護大量 ROS1 套件的團隊而言，手動遷移是一項極度耗時、容易出錯的工程任務。**平均一個中型 ROS1 套件 (約 5,000–10,000 行程式碼) 需要一位資深工程師花費 2–4 週進行重構**，涵蓋 CMakeLists.txt / package.xml 格式轉換、API 替換 (如 `ros::Publisher` → `rclcpp::Publisher`)、Launch 檔案重寫 (XML → Python)、以及訊息/服務介面調整等。這導致許多優秀的舊有演算法與套件被遺棄，成為開發者難以償還的技術債。

### 誰受到影響？

- **機器人研發公司：** 產品線仍依賴 ROS1 的自駕車、工業機器人、無人機廠商
- **ROS 開發工程師：** 需要在日常工作中同時維護 ROS1/ROS2 的個人開發者
- **學術研究機構：** 累積多年研究成果在 ROS1 上，面臨論文復現性與新環境相容性的雙重壓力

### 不解決的代價

- 技術債持續累積，團隊被迫維護兩套並行系統
- ROS1 官方支援已於 2025 年 5 月結束 (Noetic EOL)，安全漏洞與相容性問題將無人修復
- 優秀的開源套件因無人遷移而被社群遺棄，造成重複造輪子
- 企業因遷移成本過高而延遲 ROS2 採用，錯失次世代架構的效能與安全優勢

---

## 2. 目標 (Goals)

### 使用者目標 (User Goals)

1. **大幅縮短遷移時間：** 將單一中型 ROS1 套件的遷移時間從 2–4 週縮減至 1–2 天（降低 80%+ 工時）
2. **降低出錯率：** 透過 AI 自動化轉換，減少人工重構引入的編譯錯誤與運行時 Bug，目標首次編譯通過率 > 70%
3. **零學習門檻上手：** 開發者無需深入了解 ROS2 所有 API 變更細節，ROSForge 自動處理差異映射
4. **保留原始邏輯意圖：** 遷移後的程式碼不僅能編譯通過，還應保持與原始 ROS1 版本等效的行為語義

### 商業目標 (Business Goals)

5. 建立 ROS 遷移工具領域的品牌心智佔有率，成為社群首選方案
6. 在發布後 6 個月內達成 GitHub 1,000+ Stars 與 500+ CLI 安裝量
7. 透過 BYOM 架構吸引企業用戶，為後續商業化方案（如企業版、託管服務）奠定基礎

---

## 3. 非目標 (Non-Goals)

| 非目標 | 排除原因 |
|--------|----------|
| 支援 ROS2 → ROS1 的反向遷移 | 需求極低，ROS1 已 EOL，投入產出比不合理 |
| 自動遷移 ROS1 硬體驅動層 (HAL) | 硬體驅動高度客製化，需人工驗證安全性，AI 自動化風險過高 |
| 提供圖形化使用者介面 (GUI) | v1 聚焦 CLI 體驗，GUI 為獨立 initiative，列入 v2 規劃 |
| 內建 AI 模型推理能力 | ROSForge 為編排框架，透過 BYOM 調用外部模型，不自行託管模型 |
| 自動部署遷移後的套件至機器人 | 部署流程因環境而異，屬於 CI/CD 範疇，超出遷移工具職責 |

---

## 4. 使用者故事 (User Stories)

### 核心遷移流程

- **US-01:** 身為一位 ROS 開發工程師，我想透過一行指令 (`rosforge migrate ./legacy_pkg`) 啟動自動化遷移流程，以便在不深入了解 ROS2 API 變更細節的情況下，快速將 ROS1 套件重構為 ROS2 架構。
- **US-02:** 身為一位機器人系統架構師，我想在遷移前查看 ROSForge 的分析報告（影響範圍、風險評估、預估工時），以便在不實際動手之前評估遷移複雜度並向管理層回報。
- **US-03:** 身為一位 ROS 開發工程師，我想在遷移完成後獲得詳細的變更紀錄 (changelog) 與 diff 報告，以便逐一審查 AI 所做的每一項變更並進行程式碼審查。

### AI 引擎管理 (BYOM)

- **US-04:** 身為一位注重資料隱私的企業工程師，我想自由選擇使用本地部署的 AI 模型（如透過 Ollama）作為遷移引擎，以便確保公司程式碼不會外洩至第三方雲端服務。
- **US-05:** 身為一位個人開發者，我想透過 `rosforge config set engine claude-code` 一行指令切換 AI 引擎，以便根據 API 成本或個人偏好靈活選擇最合適的模型。

### 錯誤處理與邊界情境

- **US-06:** 身為一位開發者，當遷移過程中遇到無法自動轉換的程式碼段落時，我希望 ROSForge 能標記該區塊並提供人工介入建議，而非靜默跳過或產生錯誤程式碼。
- **US-07:** 身為一位開發者，我想在遷移後自動執行 `colcon build` 驗證編譯結果，若失敗則由 AI Agent 自動嘗試修復，以便實現真正的端到端自動化。
- **US-08:** 身為一位開發者，當我的 ROS1 套件包含自定義訊息類型 (custom msgs/srvs) 時，我希望 ROSForge 能自動偵測並一併遷移這些介面定義檔。

---

## 5. 需求規格 (Requirements)

### 5.1 Must-Have (P0) — 最小可行版本

#### R-01: ROS1 套件靜態分析引擎

ROSForge 能解析一個 ROS1 套件的完整結構，包含 `package.xml`、`CMakeLists.txt`、Launch 檔案、原始碼 (C++/Python)、msg/srv/action 定義檔，並產出結構化的抽象語法樹 (AST) 或中介表示 (IR)。

> **驗收標準：** 給定一個標準 ROS1 Catkin 套件，ROSForge 能在 30 秒內完成解析並輸出 JSON 格式的分析報告，涵蓋所有檔案的依賴關係圖。

#### R-02: 核心程式碼轉換引擎

基於分析結果，自動執行以下轉換：

- `package.xml`: format 1/2 → format 3 (ament)
- `CMakeLists.txt`: catkin → ament_cmake
- C++ API: `roscpp` → `rclcpp` (NodeHandle → Node, Publisher/Subscriber API 等)
- Python API: `rospy` → `rclpy`
- Launch 檔案: XML (roslaunch) → Python (launch_ros)
- msg/srv/action 定義: 格式微調與 CMake 整合

> **驗收標準：** 對 ROS Wiki 上官方 Tutorials 中的 10 個示範套件，首次編譯通過率 ≥ 70%。

#### R-03: BYOM — 多 AI 引擎抽象介面

提供統一的 AI 引擎抽象層，v1 支援至少三種引擎後端：

- Claude Code (Anthropic)
- Gemini CLI (Google)
- Codex / ChatGPT CLI (OpenAI)

> **驗收標準：** 使用者透過 `rosforge config set engine <name>` 切換引擎後，相同的遷移指令能正確調用對應的 AI 後端完成任務。

#### R-04: CLI 介面與核心指令

| 指令 | 功能 |
|------|------|
| `rosforge migrate <path>` | 對指定 ROS1 套件執行自動化遷移 |
| `rosforge analyze <path>` | 僅執行靜態分析，輸出遷移報告（不修改程式碼） |
| `rosforge config set engine <name>` | 設定 AI 引擎 |
| `rosforge config list` | 列出目前所有設定 |
| `rosforge status` | 查看上次遷移的狀態與結果摘要 |

#### R-05: 遷移報告與變更紀錄

每次遷移完成後自動產出：

- `migration_report.md`：包含遷移摘要、變更清單、警告、手動介入建議
- 完整的 git diff 風格變更對照

> **驗收標準：** 報告涵蓋所有被修改的檔案，並對每項變更提供原因說明。

### 5.2 Nice-to-Have (P1) — 快速迭代

#### R-06: 自動編譯驗證與修復迴圈

遷移完成後自動執行 `colcon build`，若編譯失敗則將錯誤訊息回饋給 AI Agent，由其嘗試自動修復，最多重試 N 次。

#### R-07: 互動式遷移模式

提供 `rosforge migrate --interactive` 模式，在每個重大轉換步驟暫停並徵求使用者確認，適合對遷移品質有高度要求的場景。

#### R-08: 批次遷移 (Workspace-level)

支援 `rosforge migrate --workspace <ws_path>`，一次遷移整個 Catkin Workspace 下的所有套件，並自動處理套件間的交叉依賴。

#### R-09: 自訂轉換規則

允許使用者透過 `.rosforge/rules.yaml` 定義自訂的 API 映射規則，覆寫或擴充內建的轉換邏輯。

### 5.3 Future Considerations (P2)

#### R-10: Plugin 生態系

開放 Plugin API，讓社群貢獻針對特定領域 (如導航、感知、操控) 的遷移最佳化策略。

#### R-11: Web Dashboard

提供 Web 介面，視覺化呈現遷移進度、程式碼差異對照、以及歷史遷移紀錄。

#### R-12: CI/CD 整合

提供 GitHub Action / GitLab CI Template，讓團隊可在 CI Pipeline 中自動觸發遷移驗證。

---

## 6. 成功指標 (Success Metrics)

### 領先指標 (Leading Indicators) — 發布後 1–4 週

| 指標 | 目標值 | 衡量方式 |
|------|--------|----------|
| CLI 安裝量 (npm / pip / brew) | ≥ 500 within 30 days | 套件管理器下載統計 |
| 首次遷移成功率 (首次 colcon build 通過) | ≥ 70% | CLI 內建匿名遙測 (opt-in) |
| 平均遷移時間 (中型套件) | < 30 分鐘 (含 AI 處理) | CLI 遙測 |
| 使用者完成完整遷移流程的比率 | ≥ 60% | CLI 遙測 (analyze → migrate → build) |
| GitHub Issues 中的 Bug 回報率 | < 20% of total issues | GitHub API |

### 落後指標 (Lagging Indicators) — 發布後 3–6 個月

| 指標 | 目標值 | 衡量方式 |
|------|--------|----------|
| GitHub Stars | ≥ 1,000 | GitHub API |
| 社群貢獻者 (PR merged) | ≥ 15 unique contributors | GitHub Insights |
| 企業試用申請 | ≥ 10 organizations | Landing Page 表單 |
| ROS Discourse 提及次數 | ≥ 30 posts | 社群搜尋 |
| 重複使用率 (同一使用者遷移 2+ 套件) | ≥ 40% | CLI 遙測 |

---

## 7. 技術架構概覽 (Technical Architecture)

ROSForge 採用模組化管線 (Pipeline) 架構，遷移流程分為以下階段：

| 階段 | 模組 | 說明 |
|------|------|------|
| 1. Ingest | Source Parser | 讀取並解析 ROS1 套件結構，產出中介表示 (IR) |
| 2. Analyze | Dependency Resolver | 分析套件內外部依賴，識別遷移風險與衝突 |
| 3. Transform | AI Migration Engine | 調用 BYOM 引擎，基於 IR 與轉換規則生成 ROS2 程式碼 |
| 4. Validate | Build Verifier | 自動執行 colcon build 並檢查編譯結果 |
| 5. Report | Report Generator | 產出遷移報告、changelog 與 diff |

### BYOM 引擎抽象層

所有 AI 引擎均實作統一的 `EngineInterface`，定義以下核心方法：

- `analyze(source_ir)` → `MigrationPlan`
- `transform(source_file, plan)` → `TransformedFile`
- `fix(error_log, source_file)` → `FixedFile`

引擎切換透過策略模式 (Strategy Pattern) 實現，新增引擎只需實作介面並註冊至 Engine Registry。

---

## 8. 開放問題 (Open Questions)

### 阻塞性問題 (Blocking)

| 問題 | 負責人 | 截止日 |
|------|--------|--------|
| BYOM 引擎的 API 呼叫成本如何傳達給使用者？是否需要內建用量追蹤？ | Product / Engineering | Sprint 1 |
| 匿名遙測 (telemetry) 的 opt-in/opt-out 機制是否需通過法務審查？ | Legal / Engineering | Sprint 1 |
| v1 支援的 ROS1 版本範圍？(僅 Noetic 或也包含 Melodic/Kinetic？) | Engineering | Sprint 1 |

### 非阻塞性問題 (Non-blocking)

| 問題 | 負責人 |
|------|--------|
| 是否需要支援 ROS1 + ROS2 混合套件 (bridge 模式)？ | Engineering |
| 社群貢獻指南的規範何時制定？ | DevRel |
| 企業版的定價模型初步方向？ | Product / Business |
| 是否整合 rosdep 自動安裝遷移後的新依賴？ | Engineering |

---

## 9. 時程規劃 (Timeline)

| 階段 | 時程 | 交付物 |
|------|------|--------|
| Phase 0: Spike & Prototype | Week 1–2 | 可執行的 PoC：對 1 個簡單 ROS1 套件完成端到端遷移 |
| Phase 1: Core Engine (P0) | Week 3–8 | R-01 ~ R-05 全部完成，CLI 可用，支援 3 種 AI 引擎 |
| Phase 2: Polish & P1 | Week 9–12 | R-06 ~ R-09 完成，互動模式、批次遷移、自訂規則 |
| Phase 3: Beta Launch | Week 13–14 | 公開 Beta，發布至 GitHub / PyPI / npm |
| Phase 4: GA & Community | Week 15–20 | GA 正式版，社群貢獻指南，Plugin API 開放 |

### 硬性截止日

- ROS1 Noetic 已於 2025 年 5 月 EOL，市場時間窗口正在收窄 — Beta 版應在 2026 Q2 前發布
- ROSCon 2026 (預計 Q4) 為理想的 GA 宣傳時機

---

## 10. 附錄 (Appendix)

### ROS1 → ROS2 關鍵差異速查表

| 面向 | ROS1 | ROS2 |
|------|------|------|
| 通訊中介層 | 自研 TCPROS/UDPROS | DDS (Data Distribution Service) |
| 建構系統 | catkin (CMake-based) | ament_cmake / ament_python |
| 節點管理 | NodeHandle | Node (含 Lifecycle 管理) |
| Launch 系統 | XML (roslaunch) | Python (launch_ros) |
| 套件描述 | package.xml format 1/2 | package.xml format 3 |
| C++ API | roscpp | rclcpp |
| Python API | rospy | rclpy |
| 參數系統 | 全域 Parameter Server | 節點本地 Parameters |

---

*— End of Document —*
