# Statistics Monitor Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the statistics summary into three metric rows and keep the monitor table's account column visible during horizontal scrolling.

**Architecture:** Keep the existing Vue page-level data and formatting logic. Change only the summary markup/styles in `StatisticsPage.vue` and add Element Plus's `fixed="left"` option to the account column in `MonitorPage.vue`.

**Tech Stack:** Vue 3 Composition API, TypeScript, Element Plus, scoped CSS, Vite.

---

### Task 1: Rebuild the statistics summary layout

**Files:**
- Modify: `src/pages/statistics/StatisticsPage.vue`

- [x] **Step 1: Replace the summary template loop**

Change the summary block to render one `.summary-line` per `group`, with a `.summary-card` for each metric and the existing `summary(group.key)` formatting expressions inside each card.

- [x] **Step 2: Update scoped styles**

Define `.summary-cards` as a vertical grid, `.summary-line` as a six-column grid (group label plus five metrics), and `.summary-card` as the existing bordered white card. Add responsive rules that let metric cards wrap below 1280px while keeping the group label aligned.

- [x] **Step 3: Run the formatter check**

Run `npm run format:check`.

Expected: the command exits with code 0 and reports no formatting violations.

### Task 2: Fix the monitor account column

**Files:**
- Modify: `src/pages/monitor/MonitorPage.vue`

- [x] **Step 1: Fix the account column on the left**

Add `fixed="left"` to the first `el-table-column` for `account_name`. Keep its `min-width="140"` and leave the remaining columns unchanged.

- [x] **Step 2: Build the frontend**

Run `npm run build`.

Expected: Vite completes successfully and emits the production bundle without TypeScript or template errors.
