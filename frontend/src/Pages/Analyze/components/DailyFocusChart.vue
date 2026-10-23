<script setup>
// Bar chart of minutes focused per day, with a fixed 2h scale.
const MAX_MINUTES = 120;

defineProps({
  data: { type: Array, required: true },
});

// 0m at the bottom, 2h 00m at the top; positions are percentages of the plot height.
const gridLines = [
  { label: "2h 00m", position: 100 },
  { label: "1h 30m", position: 75 },
  { label: "1h 00m", position: 50 },
  { label: "30m", position: 25 },
  { label: "0m", position: 0 },
];

function barHeight(minutes) {
  return `${(minutes / MAX_MINUTES) * 100}%`;
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;

  if (!hours) return `${rest}m`;
  return rest ? `${hours}h ${String(rest).padStart(2, "0")}m` : `${hours}h`;
}
</script>

<template>
  <section class="card">
    <header class="card-header">
      <h2 class="card-title">Daily Focus Activity</h2>
    </header>

    <div class="chart-body">
      <div class="y-axis">
        <span
          v-for="line in gridLines"
          :key="line.label"
          class="y-label"
          :style="{ bottom: `${line.position}%` }"
        >
          {{ line.label }}
        </span>
      </div>

      <div class="plot-wrap">
        <div class="plot">
          <span
            v-for="line in gridLines"
            :key="line.label"
            class="grid-line"
            :style="{ bottom: `${line.position}%` }"
          ></span>

          <div class="bars">
            <div v-for="entry in data" :key="entry.day" class="bar-col">
              <span v-if="entry.minutes" class="bar-value">{{ formatDuration(entry.minutes) }}</span>
              <div class="bar" :style="{ height: barHeight(entry.minutes) }"></div>
            </div>
          </div>
        </div>

        <div class="x-axis">
          <span
            v-for="entry in data"
            :key="entry.day"
            class="x-label"
            :class="{ active: entry.minutes > 0 }"
          >
            <span class="x-day">{{ entry.day }}</span>
            <span class="x-date">{{ entry.date }}</span>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.card {
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 20px 22px 18px;
  min-width: 0;
}

.card-header {
  margin-bottom: 22px;
}

.card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
}

.chart-body {
  display: flex;
  gap: 14px;
  min-width: 0;
}

.y-axis {
  position: relative;
  width: 56px;
  height: 220px;
  flex-shrink: 0;
}

.y-label {
  position: absolute;
  right: 0;
  transform: translateY(50%);
  font-size: 11px;
  color: #a0a0a0;
  white-space: nowrap;
}

.plot-wrap {
  flex: 1;
  min-width: 0;
}

.plot {
  position: relative;
  height: 220px;
}

.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(255, 255, 255, 0.07);
}

.bars {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.bar-col {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
}

.bar-value {
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 6px;
  white-space: nowrap;
}

.bar {
  width: 60%;
  max-width: 54px;
  background: #00ff9d;
  border-radius: 6px 6px 0 0;
}

.x-axis {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.x-label {
  flex: 1;
  min-width: 0;
  text-align: center;
  font-size: 12px;
  color: #a0a0a0;
  white-space: nowrap;
}

.x-label.active {
  color: #ffffff;
  font-weight: 600;
}

.x-date {
  margin-left: 3px;
}

/* Narrow screens: drop the date so the seven day columns always fit. */
@media (max-width: 560px) {
  .y-axis {
    width: 46px;
  }

  .y-label,
  .x-label {
    font-size: 11px;
  }

  .x-axis {
    gap: 4px;
  }

  .x-date {
    display: none;
  }
}
</style>
