<script setup>
import { ref } from "vue";

import AnalyzeSidebar from "./components/AnalyzeSidebar.vue";
import MetricCard from "./components/MetricCard.vue";
import DailyFocusChart from "./components/DailyFocusChart.vue";
import ListDistribution from "./components/ListDistribution.vue";
import SessionTable from "./components/SessionTable.vue";

// Placeholder analytics data — swap for API data once the backend exposes it.
const range = ref("30");
const dateRange = "16-10-2026 – 22-10-2026";

const metrics = [
  {
    label: "Total Focus Time",
    value: "4h 18m",
    sub: "↑ +14% vs last week",
    tone: "up",
  },
  {
    label: "Tasks Completed",
    value: "6 / 8",
    sub: "75% completion rate",
  },
  {
    label: "Daily Average",
    value: "1h 05m",
    sub: "Target: 1h 30m / day",
  },
  {
    label: "Consistency Streak",
    value: "4 Days",
    sub: "Personal Best: 12 days",
    tone: "accent",
  },
];

const activity = [
  { day: "Fri", date: "16", minutes: 0 },
  { day: "Sat", date: "17", minutes: 0 },
  { day: "Sun", date: "18", minutes: 0 },
  { day: "Mon", date: "19", minutes: 0 },
  { day: "Tue", date: "20", minutes: 0 },
  { day: "Wed", date: "21", minutes: 0 },
  { day: "Thu", date: "22", minutes: 108 },
];

const lists = [
  { name: "Maths", share: 52, tag: "SSC", duration: "1h 39m", color: "#f59e0b" },
  { name: "Reasoning", share: 32, tag: "SSC", duration: "1h 00m", color: "#3b82f6" },
  { name: "GS & Revision", share: 16, tag: "SSC", duration: "45m", color: "#00ff9d" },
];

const sessions = [
  {
    dateTime: "Today, Oct 22 • 04:02 PM",
    task: "Maths – Quadratic Equations Practice",
    list: "SSC",
    duration: "4m 07s",
    status: "completed",
    rating: "100% Flow",
  },
  {
    dateTime: "Today, Oct 22 • 02:15 PM",
    task: "Reasoning – Syllogism & Puzzles",
    list: "SSC",
    duration: "1h 00m",
    status: "completed",
    rating: "94% Flow",
  },
  {
    dateTime: "Today, Oct 22 • 11:30 AM",
    task: "General Studies – Modern Indian History",
    list: "SSC",
    duration: "45m 00s",
    status: "completed",
    rating: "88% Flow",
  },
  {
    dateTime: "Yesterday, Oct 21 • 06:10 PM",
    task: "DSA – Binary Search & Two Pointers",
    list: "DSA",
    duration: "12m 30s",
    status: "skipped",
    rating: "— Disrupted",
  },
];
</script>

<template>
  <div class="analyze-page">
    <AnalyzeSidebar />

    <main class="analytics">
      <header class="page-header">
        <div class="page-heading">
          <h1 class="page-title">Analytics Overview</h1>
          <p class="page-subtitle">
            Track consistency, session intensity, and completion trends across lists.
          </p>
        </div>

        <div class="controls">
          <div class="segmented">
            <button
              type="button"
              class="seg-btn"
              :class="{ active: range === '7' }"
              @click="range = '7'"
            >
              7 Days
            </button>
            <button
              type="button"
              class="seg-btn"
              :class="{ active: range === '30' }"
              @click="range = '30'"
            >
              30 Days
            </button>
          </div>

          <div class="date-range">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <rect x="3" y="5" width="18" height="16" rx="2" />
              <line x1="3" y1="10" x2="21" y2="10" />
              <line x1="8" y1="3" x2="8" y2="7" />
              <line x1="16" y1="3" x2="16" y2="7" />
            </svg>
            <span>{{ dateRange }}</span>
          </div>

          <button type="button" class="apply-btn">Apply</button>

          <button type="button" class="icon-btn" aria-label="Chart settings">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <line x1="4" y1="8" x2="20" y2="8" />
              <line x1="4" y1="16" x2="20" y2="16" />
              <circle cx="9" cy="8" r="2" />
              <circle cx="15" cy="16" r="2" />
            </svg>
          </button>
        </div>
      </header>

      <section class="metric-grid">
        <MetricCard
          v-for="metric in metrics"
          :key="metric.label"
          :label="metric.label"
          :value="metric.value"
          :sub="metric.sub"
          :tone="metric.tone"
        />
      </section>

      <section class="insight-grid">
        <DailyFocusChart :data="activity" />
        <ListDistribution :lists="lists" />
      </section>

      <SessionTable :sessions="sessions" />
    </main>
  </div>
</template>

<style scoped>
.analyze-page {
  display: flex;
  min-height: 100vh;
  background: #0d0d0d;
  color: #ffffff;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.analytics {
  flex: 1;
  min-width: 0;
  padding: 28px 32px 48px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: #a0a0a0;
}

.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.segmented {
  display: flex;
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 3px;
  gap: 3px;
}

.seg-btn {
  border: none;
  background: transparent;
  color: #a0a0a0;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.seg-btn:hover {
  color: #ffffff;
}

.seg-btn.active {
  background: #00ff9d;
  color: #062018;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 13px;
  color: #e5e5e5;
}

.date-range svg {
  width: 16px;
  height: 16px;
  color: #a0a0a0;
}

.apply-btn {
  background: transparent;
  border: 1px solid rgba(0, 255, 157, 0.5);
  color: #00ff9d;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 22px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.apply-btn:hover {
  background: rgba(0, 255, 157, 0.1);
}

.icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #a0a0a0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.icon-btn:hover {
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.2);
}

.icon-btn svg {
  width: 18px;
  height: 18px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.insight-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 18px;
  align-items: stretch;
}

/* Let the chart and distribution cards shrink with the viewport instead of
   forcing the grid wider than the screen. */
.insight-grid > * {
  min-width: 0;
}

@media (max-width: 1180px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .insight-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1024px) {
  .analyze-page {
    flex-direction: column;
  }

  .analytics {
    padding: 22px 20px 40px;
  }
}

@media (max-width: 560px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
