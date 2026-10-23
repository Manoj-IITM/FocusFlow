<script setup>
// Single KPI card for the analytics overview row.
defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  sub: { type: String, default: "" },
  tone: { type: String, default: "muted" },
});
</script>

<template>
  <div class="metric-card">
    <span class="metric-label">{{ label }}</span>
    <span class="metric-value">{{ value }}</span>
    <span class="metric-sub" :class="`sub-${tone}`">{{ sub }}</span>
  </div>
</template>

<style scoped>
.metric-card {
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #a0a0a0;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #ffffff;
  line-height: 1.1;
}

.metric-sub {
  font-size: 13px;
  color: #a0a0a0;
}

.sub-up {
  color: #00ff9d;
  font-weight: 600;
}

.sub-accent {
  color: #00ff9d;
}
</style>
