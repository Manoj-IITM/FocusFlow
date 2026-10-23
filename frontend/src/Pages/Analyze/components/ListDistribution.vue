<script setup>
// Share of focus time per study list, shown as one stacked bar plus a breakdown.
defineProps({
  lists: { type: Array, required: true },
});
</script>

<template>
  <section class="card">
    <header class="card-header">
      <h2 class="card-title">Distribution by List</h2>
    </header>

    <div class="stack-bar">
      <span
        v-for="item in lists"
        :key="item.name"
        class="stack-seg"
        :style="{ width: `${item.share}%`, background: item.color }"
      ></span>
    </div>

    <ul class="list-rows">
      <li v-for="item in lists" :key="item.name" class="list-row">
        <span class="row-dot" :style="{ background: item.color }"></span>
        <span class="row-name">{{ item.name }}</span>
        <span class="row-meta">({{ item.share }}% share, {{ item.tag }})</span>
        <span class="row-duration">{{ item.duration }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.card {
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
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

.stack-bar {
  display: flex;
  height: 10px;
  border-radius: 6px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
}

.stack-seg {
  height: 100%;
  display: block;
}

.list-rows {
  list-style: none;
  margin: 22px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
}

.row-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.row-name {
  color: #ffffff;
  font-weight: 600;
}

.row-meta {
  color: #a0a0a0;
}

.row-duration {
  margin-left: auto;
  color: #ffffff;
  font-weight: 600;
  white-space: nowrap;
}
</style>
