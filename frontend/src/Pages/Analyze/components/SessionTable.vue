<script setup>
// Recent session occurrences table.
defineProps({
  sessions: { type: Array, required: true },
});

const columns = [
  "Date & Time",
  "Task Occurrence",
  "List",
  "Duration",
  "Status",
  "Focus Rating",
];
</script>

<template>
  <section class="card">
    <header class="card-header">
      <h2 class="card-title">Recent Session Occurrences</h2>
    </header>

    <div class="table-scroll">
      <table class="session-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column">{{ column }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in sessions" :key="session.task">
            <td class="cell-muted">{{ session.dateTime }}</td>
            <td class="cell-strong">{{ session.task }}</td>
            <td class="cell-muted">{{ session.list }}</td>
            <td class="cell-strong">{{ session.duration }}</td>
            <td>
              <span class="badge" :class="`badge-${session.status}`">
                {{ session.status === "completed" ? "Completed" : "Skipped" }}
              </span>
            </td>
            <td class="cell-muted">{{ session.rating }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.card {
  background: #161616;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 20px 22px 8px;
}

.card-header {
  margin-bottom: 18px;
}

.card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
}

.table-scroll {
  overflow-x: auto;
}

.session-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.session-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #a0a0a0;
  padding: 0 14px 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.session-table td {
  padding: 16px 14px 16px 0;
  font-size: 13.5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  vertical-align: middle;
}

.session-table tbody tr:last-child td {
  border-bottom: none;
}

.cell-strong {
  color: #ffffff;
  font-weight: 500;
}

.cell-muted {
  color: #a0a0a0;
}

.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-completed {
  background: #064e3b;
  color: #10b981;
}

.badge-skipped {
  background: #7f1d1d;
  color: #ef4444;
}
</style>
