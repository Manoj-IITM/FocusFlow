<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import { apiUrl } from "../../api.js";
import { clearSession, buildAuthHeaders, readStoredUserOr } from "../../session.js";
import { themeMode } from "../../theme.js";

const route = useRoute();
const router = useRouter();
const user = ref(readStoredUserOr({ username: "Account" }));

const title = computed(() => route.meta.title || "FocusFlow");
const icon = computed(() => route.meta.icon || "ti ti-layout-dashboard");
const isLightMode = computed(() => themeMode.value === "light");
const dateKey = (date) => {
  const localDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  return `${localDate.getFullYear()}-${String(localDate.getMonth() + 1).padStart(2, "0")}-${String(localDate.getDate()).padStart(2, "0")}`;
};
const endDate = new Date();
const startDate = new Date(endDate);
startDate.setDate(startDate.getDate() - 6);
const analyticsStart = ref(dateKey(startDate));
const analyticsEnd = ref(dateKey(endDate));
const analyticsDays = ref([]);
const analyticsDistribution = ref([]);
const analyticsSessions = ref([]);
const analyticsTaskLists = ref([]);
const analyticsLoading = ref(false);
const analyticsError = ref("");
const analyticsPreviousSeconds = ref(null);
const personalBestStreak = ref(0);
// Daily focus goal drawn as the dashed "Target" line on the activity chart.
const DAILY_TARGET_SECONDS = 90 * 60;
const analyticsTotals = computed(() => analyticsDays.value.reduce((totals, day) => ({
  studySeconds: totals.studySeconds + Number(day.study_seconds || 0),
  completed: totals.completed + Number(day.scheduled_completed_occurrences ?? day.completed_occurrences ?? 0),
  scheduled: totals.scheduled + Number(day.scheduled_occurrences || 0),
  skipped: totals.skipped + Number(day.skipped_occurrences || 0),
}), { studySeconds: 0, completed: 0, scheduled: 0, skipped: 0 }));
const dailyAverageSeconds = computed(() => analyticsDays.value.length
  ? Math.round(analyticsTotals.value.studySeconds / analyticsDays.value.length)
  : 0);
const activeDaysCount = computed(() => analyticsDays.value.filter((day) => Number(day.study_seconds) > 0).length);
const completionRate = computed(() => analyticsTotals.value.scheduled
  ? Math.round(analyticsTotals.value.completed / analyticsTotals.value.scheduled * 100)
  : 0);
const selectedRangeDays = computed(() => {
  const start = new Date(`${analyticsStart.value}T00:00:00`);
  const end = new Date(`${analyticsEnd.value}T00:00:00`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return 0;
  return Math.round((end - start) / 86400000) + 1;
});
const focusDeltaPercent = computed(() => {
  if (analyticsPreviousSeconds.value === null) return null;
  if (!analyticsPreviousSeconds.value) {
    return analyticsTotals.value.studySeconds > 0 ? 100 : 0;
  }
  return Math.round(
    (analyticsTotals.value.studySeconds - analyticsPreviousSeconds.value) / analyticsPreviousSeconds.value * 100,
  );
});
const focusDeltaLabel = computed(() => {
  if (focusDeltaPercent.value === null) return "No comparison available";
  const rangeLabel = selectedRangeDays.value === 7 ? "vs last week" : `vs previous ${selectedRangeDays.value} days`;
  if (focusDeltaPercent.value === 0) return `No change ${rangeLabel}`;
  const sign = focusDeltaPercent.value > 0 ? "+" : "";
  return `${focusDeltaPercent.value > 0 ? "↑" : "↓"} ${sign}${focusDeltaPercent.value}% ${rangeLabel}`;
});
const longestStreakOf = (days) => days.reduce((result, day) => {
  if (Number(day.study_seconds) > 0) {
    result.current += 1;
    result.longest = Math.max(result.longest, result.current);
  } else {
    result.current = 0;
  }
  return result;
}, { current: 0, longest: 0 }).longest;
const longestFocusStreak = computed(() => longestStreakOf(analyticsDays.value));
const currentFocusStreak = computed(() => {
  let streak = 0;
  for (let index = analyticsDays.value.length - 1; index >= 0; index -= 1) {
    if (Number(analyticsDays.value[index].study_seconds) > 0) streak += 1;
    else break;
  }
  return streak;
});
const chartMaxSeconds = computed(() => {
  const maxDay = Math.max(0, ...analyticsDays.value.map((day) => Number(day.study_seconds) || 0));
  // Keep at least one grid step of headroom above the target line.
  const targetHeadroom = Math.ceil(DAILY_TARGET_SECONDS / 1800) * 1800 + 1800;
  return Math.max(targetHeadroom, Math.ceil(maxDay / 1800) * 1800);
});
const chartTicks = computed(() => [1, 0.75, 0.5, 0.25, 0].map((fraction) => chartMaxSeconds.value * fraction));
const chartContentWidth = computed(() => `${Math.max(640, analyticsDays.value.length * 36)}px`);
const targetLinePercent = computed(() => Math.min(100, DAILY_TARGET_SECONDS / chartMaxSeconds.value * 100));
const targetLineTopPercent = computed(() => 100 - targetLinePercent.value * (226 / 252));
const sparklineDays = computed(() => analyticsDays.value.slice(-12));
const maxDailyStudySeconds = computed(() => Math.max(1, ...analyticsDays.value.map((day) => Number(day.study_seconds) || 0)));
const sparklineHeight = (day) => Number(day.study_seconds)
  ? `${Math.max(4, Math.round(Number(day.study_seconds) / maxDailyStudySeconds.value * 24))}px`
  : "3px";
const listDistributionTotal = computed(() => analyticsDistribution.value.reduce(
  (total, item) => total + Number(item.study_seconds || 0), 0,
));
const totalSessionCount = computed(() => analyticsDistribution.value.reduce(
  (total, item) => total + Number(item.session_count || 0), 0,
));
const distributionColors = ["#f59e0b", "#3b82f6", "#10b981", "#a78bfa", "#f97316", "#ec4899"];
const listDistribution = computed(() => analyticsDistribution.value.map((item, index) => {
  const list = analyticsTaskLists.value.find((candidate) => String(candidate.id) === String(item.task_list_id));
  const seconds = Number(item.study_seconds || 0);
  return {
    ...item,
    name: list?.name || (item.task_list_id ? "Task list" : "Unsorted"),
    color: list?.color || distributionColors[index % distributionColors.length],
    studySeconds: seconds,
    percent: listDistributionTotal.value ? Math.round(seconds / listDistributionTotal.value * 100) : 0,
  };
}));
const activeDayRate = computed(() => analyticsDays.value.length
  ? Math.round(activeDaysCount.value / analyticsDays.value.length * 100)
  : 0);
const strongestFocusDay = computed(() => {
  const daysWithFocus = analyticsDays.value.filter((day) => Number(day.study_seconds) > 0);
  if (!daysWithFocus.length) return null;
  return daysWithFocus.reduce((strongest, day) => (
    Number(day.study_seconds) > Number(strongest.study_seconds) ? day : strongest
  ));
});
const leadingList = computed(() => listDistribution.value[0] || null);
const formatStudyDuration = (seconds) => {
  const minutes = Math.floor((Number(seconds) || 0) / 60);
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
};
// Chart & stat labels pad minutes when hours are present ("1h 05m", "2h 00m").
const formatClockDuration = (seconds) => {
  const minutes = Math.floor((Number(seconds) || 0) / 60);
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}h ${String(minutes % 60).padStart(2, "0")}m` : `${minutes}m`;
};
// Session table durations keep seconds for sub-hour entries ("4m 07s").
const formatSessionDuration = (seconds) => {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const minutes = Math.floor(total / 60);
  const hours = Math.floor(minutes / 60);
  if (hours) return `${hours}h ${String(minutes % 60).padStart(2, "0")}m`;
  return `${minutes}m ${String(total % 60).padStart(2, "0")}s`;
};
const formatAnalyticsDate = (dateString) => {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
};
const formatActivityLabel = (dateString) => {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", { weekday: "short", day: "numeric" });
};
const formatSessionDateTime = (dateString) => {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  const today = new Date();
  const dayDiff = Math.round(
    (new Date(today.getFullYear(), today.getMonth(), today.getDate())
      - new Date(date.getFullYear(), date.getMonth(), date.getDate())) / 86400000,
  );
  const dayLabel = dayDiff === 0
    ? "Today"
    : dayDiff === 1
      ? "Yesterday"
      : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const dated = dayDiff > 1
    ? dayLabel
    : `${dayLabel}, ${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
  const time = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  return `${dated} • ${time}`;
};
const sessionStatus = (session) => session.completed ? "Completed" : session.skipped ? "Skipped" : "Recorded";
const sessionListName = (session) => {
  const list = analyticsTaskLists.value.find((candidate) => String(candidate.id) === String(session.task_list_id));
  return list?.name || (session.task_list_id ? "Task list" : "Unsorted");
};
// "Maths – Quadratic Equations Practice" style labels: list first, then task.
const sessionTaskLabel = (session) => {
  const list = analyticsTaskLists.value.find((candidate) => String(candidate.id) === String(session.task_list_id));
  return list?.name ? `${list.name} – ${session.title}` : session.title;
};
const sessionListPill = (session) => session.tag || sessionListName(session);
const pillPalette = ["#f59e0b", "#3b82f6", "#10b981", "#a78bfa", "#f97316", "#ec4899"];
const sessionListColor = (session) => {
  const list = analyticsTaskLists.value.find((candidate) => String(candidate.id) === String(session.task_list_id));
  if (list?.color) return list.color;
  const seed = String(session.tag || sessionListName(session));
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) hash = (hash * 31 + seed.charCodeAt(index)) % 997;
  return pillPalette[hash % pillPalette.length];
};
// Flow rating compares the recorded session against the task's planned duration.
const sessionFlow = (session) => {
  if (session.skipped) return null;
  const planned = Number(session.duration_minutes || 0) * 60;
  const actual = Number(session.duration_seconds || 0);
  if (!planned) return 100;
  return Math.max(0, Math.min(100, Math.round(actual / planned * 100)));
};
const presetIsActive = (days) => {
  if (analyticsEnd.value !== dateKey(new Date())) return false;
  const rangeStart = new Date(`${analyticsStart.value}T00:00:00`);
  const rangeEnd = new Date(`${analyticsEnd.value}T00:00:00`);
  return Math.round((rangeEnd - rangeStart) / 86400000) + 1 === days;
};
const setAnalyticsPreset = (days) => {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - days + 1);
  analyticsStart.value = dateKey(start);
  analyticsEnd.value = dateKey(end);
  fetchAnalytics();
};
const fetchPreviousPeriod = async () => {
  const spanDays = selectedRangeDays.value;
  if (!spanDays) {
    analyticsPreviousSeconds.value = null;
    return;
  }
  const rangeEnd = new Date(`${analyticsStart.value}T00:00:00`);
  rangeEnd.setDate(rangeEnd.getDate() - 1);
  const rangeStart = new Date(rangeEnd);
  rangeStart.setDate(rangeStart.getDate() - spanDays + 1);
  try {
    const response = await axios.get(apiUrl("/analytics"), {
      params: { start: dateKey(rangeStart), end: dateKey(rangeEnd) },
    });
    analyticsPreviousSeconds.value = (response.data.days || []).reduce(
      (total, day) => total + Number(day.study_seconds || 0),
      0,
    );
  } catch {
    analyticsPreviousSeconds.value = null;
  }
};
const fetchAnalytics = async () => {
  analyticsLoading.value = true;
  analyticsError.value = "";
  try {
    const [response] = await Promise.all([
      axios.get(apiUrl("/analytics"), {
        params: { start: analyticsStart.value, end: analyticsEnd.value },
      }),
      fetchPreviousPeriod(),
    ]);
    analyticsDays.value = response.data.days || [];
    analyticsDistribution.value = response.data.distribution_by_list || [];
    analyticsSessions.value = response.data.recent_sessions || [];
  } catch (error) {
    analyticsError.value = error.response?.data?.error || "Unable to load study analytics.";
  } finally {
    analyticsLoading.value = false;
  }
};
const fetchPersonalBest = async () => {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 365);
  try {
    const response = await axios.get(apiUrl("/analytics"), {
      params: { start: dateKey(start), end: dateKey(end) },
    });
    personalBestStreak.value = longestStreakOf(response.data.days || []);
  } catch {
    personalBestStreak.value = 0;
  }
};

watch(() => route.name, (name) => {
  if (name !== "analyse") return;
  try {
    const saved = JSON.parse(localStorage.getItem(`focusflow_task_lists_${user.value.id}`) || "null");
    analyticsTaskLists.value = Array.isArray(saved?.lists) ? saved.lists : [];
  } catch {
    analyticsTaskLists.value = [];
  }
  fetchAnalytics();
  fetchPersonalBest();
}, { immediate: true });

const downloadAnalyticsCsv = () => {
  const escapeCsv = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const rows = [
    ["Date & time", "Task", "List", "Duration", "Status", "Focus rating"],
    ...analyticsSessions.value.map((session) => [
      formatSessionDateTime(session.started_at),
      sessionTaskLabel(session),
      sessionListPill(session),
      formatSessionDuration(session.duration_seconds),
      sessionStatus(session),
      sessionFlow(session) === null ? "Disrupted" : `${sessionFlow(session)}% Flow`,
    ]),
  ];
  const file = new Blob(["\uFEFF", rows.map((row) => row.map(escapeCsv).join(",")).join("\r\n")], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = `focusflow-analytics-${analyticsStart.value}-to-${analyticsEnd.value}.csv`;
  link.click();
  URL.revokeObjectURL(url);
};

const navItems = [
  { name: "Study Environment", icon: "ti ti-leaf", to: "/dashboard" },
  { name: "Analyse", icon: "ti ti-chart-bar", to: "/analyse" },
  { name: "Settings", icon: "ti ti-settings", to: "/settings" },
];

const handleLogout = () => {
  // Capture the token before clearing the session so the server can revoke it.
  const headers = buildAuthHeaders() || undefined;
  axios.post(apiUrl("/auth/logout"), {}, { headers }).catch(() => {});
  clearSession();
  router.push("/");
};
</script>

<template>
  <div class="section-layout">
    <aside class="section-sidebar">
      <div class="section-sidebar-top">
        <router-link class="section-logo" to="/" aria-label="FocusFlow home">
          <span class="section-logo-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12c0-2.25.744-4.327 2-6l8 6z" />
              <path d="M12 2c2.5 3.5 3 7 1 10" />
            </svg>
          </span>
          <span>Focus Flow</span>
        </router-link>

        <nav class="section-nav" aria-label="Main navigation">
          <router-link
            v-for="item in navItems"
            :key="item.name"
            :to="item.to"
            class="section-nav-link"
            active-class="active"
            exact-active-class="active"
          >
            <i :class="item.icon" aria-hidden="true"></i>
            <span>{{ item.name }}</span>
          </router-link>
        </nav>
      </div>

      <div class="section-sidebar-bottom">
        <section class="section-motivation-card" aria-label="Focus motivation">
          <div class="section-motivation-content">
            <p>"Small steps every day lead to big results."</p>
            <i class="ti ti-leaf" aria-hidden="true"></i>
          </div>
        </section>
        <div class="section-account-row">
          <button
            class="section-account"
            type="button"
            @click="router.push('/profile')"
            :title="`Open ${user.username || 'account'} profile`"
          >
            <span class="section-avatar">{{ user.username?.charAt(0).toUpperCase() || "A" }}</span>
            <span class="section-account-details">
              <strong>{{ user.username || "Account" }}</strong>
              <small>View profile</small>
            </span>
          </button>
          <button class="section-logout" type="button" @click="handleLogout" title="Log out" aria-label="Log out">
            <i class="ti ti-logout" aria-hidden="true"></i>
          </button>
        </div>
      </div>
    </aside>

    <main class="section-main">
      <header v-if="route.name !== 'analyse'" class="section-header">
        <span class="section-header-icon"><i :class="icon" aria-hidden="true"></i></span>
        <div>
          <p>FOCUS FLOW</p>
          <h1>{{ title }}</h1>
        </div>
        <button class="section-mobile-logout" type="button" @click="handleLogout">
          <i class="ti ti-logout" aria-hidden="true"></i>
          <span>Log out</span>
        </button>
      </header>

      <section v-if="route.name === 'settings'" class="settings-panel" aria-labelledby="settings-heading">
        <div class="settings-panel-heading">
          <div>
            <p>APPEARANCE</p>
            <h2 id="settings-heading">Display theme</h2>
            <span>Choose the look that feels right for your workspace.</span>
          </div>
          <i class="ti ti-palette" aria-hidden="true"></i>
        </div>
        <div class="theme-setting-row">
          <div class="theme-setting-copy">
            <span class="theme-setting-title">{{ isLightMode ? "Light mode" : "Dark mode" }}</span>
            <span class="theme-setting-description">Use the theme switcher at the bottom-right on any page.</span>
          </div>
        </div>
      </section>

      <section v-else-if="route.name === 'analyse'" class="analysis-page" aria-label="Study analytics">
        <div class="analysis-toolbar">
          <div class="analysis-title-lockup">
            <span class="analysis-title-icon"><i class="ti ti-chart-infographic" aria-hidden="true"></i></span>
            <div class="analysis-title-block">
              <p class="analysis-eyebrow">YOUR STUDY SNAPSHOT</p>
              <h1>Analytics Overview</h1>
              <p>Track consistency, session intensity, and completion trends across lists.</p>
            </div>
          </div>
          <form class="analysis-range" @submit.prevent="fetchAnalytics">
            <div class="analysis-presets" aria-label="Quick date ranges">
              <button type="button" :class="{ active: presetIsActive(7) }" :aria-pressed="presetIsActive(7)" @click="setAnalyticsPreset(7)">7 Days</button>
              <button type="button" :class="{ active: presetIsActive(30) }" :aria-pressed="presetIsActive(30)" @click="setAnalyticsPreset(30)">30 Days</button>
            </div>
            <div class="analysis-date-range">
              <i class="ti ti-calendar-event" aria-hidden="true"></i>
              <label><input v-model="analyticsStart" type="date" aria-label="Start date" required /></label>
              <span aria-hidden="true">→</span>
              <label><input v-model="analyticsEnd" type="date" aria-label="End date" required /></label>
            </div>
            <button class="analysis-apply" type="submit" :disabled="analyticsLoading">{{ analyticsLoading ? 'Loading…' : 'Apply' }}</button>
            <button class="analysis-export" type="button" :disabled="!analyticsSessions.length" title="Download recent sessions as CSV" aria-label="Download analytics CSV" @click="downloadAnalyticsCsv">
              <i class="ti ti-download" aria-hidden="true"></i>
            </button>
          </form>
          <button class="section-mobile-logout" type="button" @click="handleLogout">
            <i class="ti ti-logout" aria-hidden="true"></i>
            <span>Log out</span>
          </button>
        </div>
        <p v-if="analyticsError" class="analysis-error" role="alert">{{ analyticsError }}</p>
        <div v-else class="analysis-content">
          <section class="analysis-summary" aria-label="Analytics summary">
            <article class="analysis-metric metric-focus">
              <div class="analysis-metric-heading"><span>Total focus time</span><i class="ti ti-clock-hour-4" aria-hidden="true"></i></div>
              <div class="analysis-metric-value">{{ formatStudyDuration(analyticsTotals.studySeconds) }}</div>
              <div class="analysis-metric-footer">
                <small>{{ totalSessionCount }} recorded {{ totalSessionCount === 1 ? 'session' : 'sessions' }}</small>
                <div class="analysis-sparkline" aria-hidden="true">
                  <span v-for="day in sparklineDays" :key="day.date" :class="{ zero: !Number(day.study_seconds) }" :style="{ height: sparklineHeight(day) }"></span>
                </div>
              </div>
            </article>
            <article class="analysis-metric metric-completed">
              <div class="analysis-metric-heading"><span>Tasks completed</span><i class="ti ti-circle-check" aria-hidden="true"></i></div>
              <div class="analysis-metric-value">{{ analyticsTotals.completed }} <span>/ {{ analyticsTotals.scheduled }}</span></div>
              <div class="analysis-metric-footer metric-completion-footer">
                <small>{{ analyticsTotals.scheduled ? `${completionRate}% completion rate` : 'No scheduled occurrences in range' }}</small>
                <div class="metric-progress-track" role="progressbar" :aria-valuenow="completionRate" aria-valuemin="0" aria-valuemax="100" :aria-label="`${completionRate}% task completion rate`">
                  <span :style="{ width: `${Math.min(100, completionRate)}%` }"></span>
                </div>
              </div>
            </article>
            <article class="analysis-metric metric-average">
              <div class="analysis-metric-heading"><span>Daily average</span><i class="ti ti-chart-bar" aria-hidden="true"></i></div>
              <div class="analysis-metric-value">{{ formatStudyDuration(dailyAverageSeconds) }}</div>
              <div class="analysis-metric-footer">
                <small>{{ activeDaysCount }} of {{ analyticsDays.length }} days with focus</small>
                <div class="analysis-day-dots" aria-hidden="true">
                  <span v-for="day in analyticsDays.slice(-14)" :key="day.date" :class="{ active: Number(day.study_seconds) > 0 }"></span>
                </div>
              </div>
            </article>
            <article class="analysis-metric metric-streak">
              <div class="analysis-metric-heading"><span>Best focus streak</span><i class="ti ti-flame" aria-hidden="true"></i></div>
              <div class="analysis-metric-value">{{ longestFocusStreak }} <span>{{ longestFocusStreak === 1 ? 'day' : 'days' }}</span></div>
              <div class="analysis-metric-footer">
                <small>Longest run in selected period</small>
                <span class="analysis-streak-mark"><i class="ti ti-flame" aria-hidden="true"></i> {{ activeDaysCount }} active</span>
              </div>
            </article>
          </section>

          <section class="analysis-focus-pulse" aria-labelledby="focus-pulse-title">
            <div class="focus-pulse-intro">
              <div
                class="focus-pulse-ring"
                :style="{ '--completion': `${Math.min(100, completionRate)}%` }"
                role="img"
                :aria-label="`${completionRate}% completion rate`">
                <div><strong>{{ completionRate }}%</strong><span>complete</span></div>
              </div>
              <div class="focus-pulse-copy">
                <p class="analysis-eyebrow">PERIOD RHYTHM</p>
                <h2 id="focus-pulse-title">Your focus is taking shape</h2>
                <p v-if="analyticsTotals.studySeconds">You recorded {{ formatStudyDuration(analyticsTotals.studySeconds) }} across {{ activeDaysCount }} active {{ activeDaysCount === 1 ? 'day' : 'days' }} in this range.</p>
                <p v-else>Start a focus session to build a view of your study rhythm here.</p>
              </div>
            </div>
            <dl class="focus-pulse-facts">
              <div>
                <dt>Consistency</dt>
                <dd>{{ activeDayRate }}%</dd>
                <small>{{ activeDaysCount }} of {{ analyticsDays.length || 0 }} days active</small>
              </div>
              <div>
                <dt>Peak day</dt>
                <dd>{{ strongestFocusDay ? formatStudyDuration(strongestFocusDay.study_seconds) : '—' }}</dd>
                <small>{{ strongestFocusDay ? formatActivityLabel(strongestFocusDay.date) : 'No focus logged yet' }}</small>
              </div>
              <div>
                <dt>Leading list</dt>
                <dd class="focus-pulse-list"><span v-if="leadingList" :style="{ backgroundColor: leadingList.color }"></span>{{ leadingList?.name || '—' }}</dd>
                <small>{{ leadingList ? `${leadingList.percent}% of focused time` : 'No list data yet' }}</small>
              </div>
            </dl>
          </section>

          <div class="analysis-overview-grid">
            <section class="analysis-panel analysis-activity-panel" aria-labelledby="daily-activity-title">
              <div class="analysis-panel-heading">
                <div class="analysis-panel-title">
                  <span class="analysis-panel-icon"><i class="ti ti-chart-histogram" aria-hidden="true"></i></span>
                  <div>
                    <h2 id="daily-activity-title">Daily Focus Activity</h2>
                    <p>Recorded focus time for each day in this date range.</p>
                  </div>
                </div>
                <div class="analysis-panel-meta">
                  <span v-if="strongestFocusDay" class="analysis-peak-chip"><i class="ti ti-sparkles" aria-hidden="true"></i> Peak {{ formatStudyDuration(strongestFocusDay.study_seconds) }}</span>
                  <div class="analysis-legend"><span class="legend-actual"></span>Actual<span class="legend-average"></span>Daily average</div>
                </div>
              </div>
              <div v-if="analyticsDays.length" class="analysis-chart">
                <div class="analysis-chart-y-axis" aria-hidden="true">
                  <span v-for="tick in chartTicks" :key="tick">{{ formatStudyDuration(tick) }}</span>
                </div>
                <div class="analysis-chart-scroll">
                  <div class="analysis-chart-inner" :style="{ minWidth: chartContentWidth }">
                    <div class="analysis-chart-plot" role="img" :aria-label="`Daily focus activity. Average ${formatStudyDuration(dailyAverageSeconds)} per day.`">
                      <span v-for="(tick, index) in chartTicks" :key="index" class="analysis-grid-line" :class="{ 'grid-line-base': index === chartTicks.length - 1 }"></span>
                      <span v-if="dailyAverageSeconds" class="analysis-average-line" :style="{ top: `${activityAverageTopPercent}%` }"></span>
                      <div class="analysis-chart-columns" :style="{ gridTemplateColumns: `repeat(${analyticsDays.length}, minmax(0, 1fr))` }">
                        <div v-for="day in analyticsDays" :key="day.date" class="analysis-chart-column" :class="{ 'is-today': day.date === dateKey(new Date()) }" :title="`${formatAnalyticsDate(day.date)} · ${formatStudyDuration(day.study_seconds)}`">
                          <div class="analysis-bar-area">
                            <span v-if="Number(day.study_seconds) && analyticsDays.length <= 14" class="analysis-bar-value" :style="{ bottom: `${Math.min(96, Number(day.study_seconds) / chartMaxSeconds * 100 + 2)}%` }">{{ formatStudyDuration(day.study_seconds) }}</span>
                            <span class="analysis-bar" :class="{ 'bar-zero': !Number(day.study_seconds) }" :style="{ height: `${Math.max(Number(day.study_seconds) ? 2 : 0, (Number(day.study_seconds) || 0) / chartMaxSeconds * 100)}%` }"></span>
                          </div>
                          <span class="analysis-chart-label">{{ formatActivityLabel(day.date) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="analysis-panel-empty">No activity recorded in this date range.</div>
            </section>

            <section class="analysis-panel analysis-distribution-panel" aria-labelledby="list-distribution-title">
              <div class="analysis-panel-heading">
                <div class="analysis-panel-title">
                  <span class="analysis-panel-icon distribution-icon"><i class="ti ti-chart-donut-3" aria-hidden="true"></i></span>
                  <div>
                    <h2 id="list-distribution-title">Distribution by List</h2>
                    <p>Focus time grouped by your task lists.</p>
                  </div>
                </div>
              </div>
              <div v-if="listDistribution.length" class="analysis-distribution-content">
                <div class="analysis-distribution-summary">
                  <span>Focus split across {{ listDistribution.length }} {{ listDistribution.length === 1 ? 'list' : 'lists' }}</span>
                  <strong>{{ formatStudyDuration(listDistributionTotal) }}</strong>
                </div>
                <div class="analysis-distribution-bar" aria-hidden="true">
                  <span v-for="(list, index) in listDistribution" :key="`${list.task_list_id || 'unsorted'}-${index}`" :style="{ width: `${listDistributionTotal ? Number(list.study_seconds) / listDistributionTotal * 100 : 0}%`, backgroundColor: list.color }"></span>
                </div>
                <div class="analysis-list-breakdown">
                  <article v-for="(list, index) in listDistribution" :key="`${list.task_list_id || 'unsorted'}-${index}`" class="analysis-list-row" :style="{ '--list-color': list.color }">
                    <span class="analysis-list-dot" :style="{ backgroundColor: list.color }"></span>
                    <div class="analysis-list-copy">
                      <strong>{{ list.name }}</strong>
                      <small>{{ list.percent }}% share · {{ list.session_count }} {{ list.session_count === 1 ? 'session' : 'sessions' }}</small>
                      <span class="analysis-list-progress"><span :style="{ width: `${list.percent}%`, backgroundColor: list.color }"></span></span>
                    </div>
                    <strong class="analysis-list-duration">{{ formatStudyDuration(list.studySeconds) }}</strong>
                  </article>
                </div>
              </div>
              <div v-else class="analysis-panel-empty">Your list breakdown will appear after a focus session.</div>
            </section>
          </div>

          <section class="analysis-panel analysis-sessions-panel" aria-labelledby="recent-sessions-title">
            <div class="analysis-panel-heading">
              <div class="analysis-panel-title">
                <span class="analysis-panel-icon sessions-icon"><i class="ti ti-history" aria-hidden="true"></i></span>
                <div>
                  <h2 id="recent-sessions-title">Recent Session Occurrences</h2>
                  <p>Focus sessions recorded during the selected period.</p>
                </div>
              </div>
              <span class="analysis-session-count">{{ analyticsSessions.length }} {{ analyticsSessions.length === 1 ? 'session' : 'sessions' }}</span>
            </div>
            <div v-if="analyticsSessions.length" class="analysis-table-scroll">
              <table class="analysis-session-table">
                <thead>
                  <tr><th>Date &amp; time</th><th>Task occurrence</th><th>List</th><th>Duration</th><th>Status</th></tr>
                </thead>
                <tbody>
                  <tr v-for="session in analyticsSessions" :key="session.id">
                    <td class="session-date">{{ formatSessionDateTime(session.started_at) }}</td>
                    <td class="session-task"><strong>{{ session.title }}</strong><small>{{ session.tag || 'Study' }}</small></td>
                    <td><span class="session-list-pill">{{ sessionListName(session) }}</span></td>
                    <td class="session-duration">{{ formatStudyDuration(session.duration_seconds) }}</td>
                    <td>
                      <span class="session-status" :class="`status-${sessionStatus(session).toLowerCase()}`">
                        <i :class="sessionStatus(session) === 'Completed' ? 'ti ti-check' : sessionStatus(session) === 'Skipped' ? 'ti ti-x' : 'ti ti-circle-dot'" aria-hidden="true"></i>
                        {{ sessionStatus(session) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="analysis-table-empty">No focus sessions have been recorded in this date range.</div>
          </section>
        </div>
      </section>

      <section v-else class="section-empty-state" aria-label="Page is under construction">
        <span class="section-empty-icon"><i :class="icon" aria-hidden="true"></i></span>
        <h2>{{ title }} is coming soon</h2>
        <p>This page is ready for your next step. Your study environment is still available whenever you need it.</p>
        <router-link class="section-home-link" to="/dashboard">
          <i class="ti ti-leaf" aria-hidden="true"></i>
          Go to Study Environment
        </router-link>
      </section>
    </main>
  </div>
</template>

<style scoped>
@property --motivation-glow-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

.section-layout {
  display: flex;
  width: 100%;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 70% 20%, rgba(45, 212, 191, 0.08), transparent 44%),
    #080b14;
  color: #f1f5f9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.section-sidebar {
  width: 248px;
  flex: 0 0 248px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 20px 14px 14px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(9, 13, 25, 0.9);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.35);
}

.section-logo {
  min-height: 96px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 0 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  color: #fff;
  font-size: 20px;
  font-weight: 750;
  letter-spacing: -0.025em;
  text-decoration: none;
}

.section-logo-icon {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  color: #2dd4bf;
  filter: drop-shadow(0 0 12px rgba(45, 212, 191, 0.26));
}

.section-logo-icon svg {
  width: 100%;
  height: 100%;
}

.section-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-nav-link {
  min-height: 50px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  border: 1px solid transparent;
  border-radius: 13px;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  transition: color 0.18s ease, background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.section-nav-link i {
  width: 24px;
  flex: 0 0 24px;
  text-align: center;
  font-size: 23px;
}

.section-nav-link:hover {
  transform: translateX(2px);
  border-color: rgba(148, 163, 184, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #fff;
}

.section-nav-link.active {
  border-color: rgba(45, 212, 191, 0.2);
  background: rgba(45, 212, 191, 0.12);
  color: #5eead4;
  box-shadow: inset 3px 0 #2dd4bf;
}

.section-sidebar-bottom {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: auto;
  padding-bottom: 2px;
}

.section-motivation-card {
  position: relative;
  height: 105px;
  overflow: hidden;
  border: 1px solid rgba(45, 212, 191, 0.22);
  border-radius: 14px;
  background:
    radial-gradient(ellipse at 100% 100%, rgba(45, 212, 191, 0.2), transparent 58%),
    radial-gradient(ellipse at 0% 0%, rgba(99, 102, 241, 0.15), transparent 62%),
    linear-gradient(145deg, rgba(19, 31, 54, 0.98), rgba(8, 15, 31, 0.98));
  box-shadow: 0 0 22px rgba(45, 212, 191, 0.16), inset 0 1px rgba(255, 255, 255, 0.05);
}

.section-motivation-card::before {
  position: absolute;
  z-index: 1;
  inset: 0;
  padding: 1px;
  border-radius: inherit;
  background: conic-gradient(
    from var(--motivation-glow-angle),
    transparent 0deg 270deg,
    rgba(45, 212, 191, 0.42) 294deg,
    rgba(94, 234, 212, 0.95) 316deg,
    rgba(56, 189, 248, 0.58) 332deg,
    transparent 350deg 360deg
  );
  content: "";
  pointer-events: none;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  mask-composite: exclude;
  animation: motivation-glow-travel 4s linear infinite;
}

.section-motivation-content {
  position: relative;
  z-index: 2;
  box-sizing: border-box;
  display: flex;
  height: 100%;
  flex-direction: column;
  justify-content: space-between;
  padding: 12px;
}

.section-motivation-content p {
  margin: 0;
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.45;
}

.section-motivation-content i {
  align-self: flex-end;
  color: #2dd4bf;
  font-size: 15px;
}

@keyframes motivation-glow-travel {
  to {
    --motivation-glow-angle: 360deg;
  }
}

@media (prefers-reduced-motion: reduce) {
  .section-motivation-card::before {
    animation: none;
  }
}

.section-account-row {
  display: flex;
  gap: 7px;
}

.section-account,
.section-logout {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.76);
  color: #e2e8f0;
  cursor: pointer;
}

.section-account {
  min-width: 0;
  min-height: 68px;
  flex: 1;
  display: flex;
  box-sizing: border-box;
  align-items: center;
  gap: 11px;
  padding: 11px 12px;
  border-radius: 14px;
  text-align: left;
}

.section-account:hover,
.section-logout:hover {
  border-color: rgba(45, 212, 191, 0.32);
  background: rgba(20, 32, 52, 0.92);
}

.section-avatar {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  box-sizing: border-box;
  display: grid;
  place-items: center;
  border: 1px solid rgba(186, 230, 253, 0.45);
  border-radius: 50%;
  background: linear-gradient(135deg, #0284c7, #38bdf8);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
}

.section-account-details {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.section-account-details strong,
.section-account-details small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-account-details strong {
  font-size: 13px;
}

.section-account-details small {
  color: #94a3b8;
  font-size: 11px;
}

.section-logout {
  width: 42px;
  flex: 0 0 42px;
  border-radius: 12px;
  color: #94a3b8;
  font-size: 17px;
}

.section-logout:hover {
  border-color: rgba(251, 113, 133, 0.35);
  background: rgba(244, 63, 94, 0.12);
  color: #fda4af;
}

.section-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 20px 28px;
}

.section-header {
  min-height: 96px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 24px;
  border: 1px solid rgba(148, 163, 184, 0.13);
  border-radius: 18px;
  background:
    radial-gradient(ellipse at 0% 0%, rgba(45, 212, 191, 0.12), transparent 48%),
    radial-gradient(ellipse at 100% 100%, rgba(99, 102, 241, 0.1), transparent 50%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(8, 13, 27, 0.98));
}

.section-mobile-logout {
  display: none;
}

.section-header-icon {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(45, 212, 191, 0.2);
  border-radius: 13px;
  background: rgba(45, 212, 191, 0.1);
  color: #5eead4;
  font-size: 23px;
}

.section-header p {
  margin: 0 0 4px;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.section-header h1 {
  margin: 0;
  color: #fff;
  font-size: 22px;
  font-weight: 750;
}

.analysis-page {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 16px;
}

.analysis-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.analysis-toolbar h2 {
  margin: 0;
  color: #f8fafc;
  font-size: 17px;
}

.analysis-toolbar p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 12px;
}

.analysis-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.analysis-range label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #94a3b8;
  font-size: 11px;
}

.analysis-range input,
.analysis-range button {
  min-height: 34px;
  padding: 0 9px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.7);
  color: #e2e8f0;
  font: inherit;
  font-size: 11px;
}

.analysis-range button {
  border-color: rgba(45, 212, 191, 0.32);
  background: rgba(45, 212, 191, 0.12);
  color: #5eead4;
  font-weight: 700;
}

.analysis-range button:disabled {
  opacity: 0.6;
}

.analysis-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.analysis-metric {
  display: flex;
  min-height: 98px;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.66);
}

.analysis-metric span {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.analysis-metric strong {
  color: #f8fafc;
  font-size: 22px;
}

.analysis-metric small {
  color: #64748b;
  font-size: 10px;
}

.analysis-days {
  display: flex;
  flex-direction: column;
  border-top: 1px solid rgba(148, 163, 184, 0.14);
}

.analysis-day-row {
  display: grid;
  grid-template-columns: 110px minmax(80px, 1fr) 72px 70px;
  align-items: center;
  gap: 14px;
  min-height: 48px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.analysis-day-name {
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 600;
}

.analysis-day-track {
  height: 7px;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(148, 163, 184, 0.16);
}

.analysis-day-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--brand-accent);
}

.analysis-day-row strong {
  color: #e2e8f0;
  font-size: 12px;
  text-align: right;
}

.analysis-day-row small {
  color: #94a3b8;
  font-size: 10px;
  text-align: right;
}

.analysis-empty,
.analysis-error {
  padding: 24px;
  border: 1px dashed rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
}

.analysis-error {
  border-color: rgba(248, 113, 113, 0.35);
  color: #fca5a5;
}

.section-empty-state {
  width: min(540px, 100%);
  box-sizing: border-box;
  align-self: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: auto;
  padding: 38px 28px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 20px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(8, 13, 27, 0.84));
  text-align: center;
}

.settings-panel {
  width: min(680px, 100%);
  box-sizing: border-box;
  align-self: center;
  margin: auto;
  padding: 26px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 20px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(8, 13, 27, 0.84));
}

.settings-panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
}

.settings-panel-heading p {
  margin: 0 0 7px;
  color: #5eead4;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.12em;
}

.settings-panel-heading h2 {
  margin: 0;
  color: #f8fafc;
  font-size: 20px;
}

.settings-panel-heading span {
  display: block;
  margin-top: 7px;
  color: #94a3b8;
  font-size: 13px;
}

.settings-panel-heading > i {
  color: #5eead4;
  font-size: 24px;
}

.theme-setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding-top: 20px;
}

.theme-setting-copy {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.theme-setting-title {
  color: #f1f5f9;
  font-size: 14px;
  font-weight: 700;
}

.theme-setting-description {
  color: #94a3b8;
  font-size: 12px;
}

.theme-switch {
  position: relative;
  display: flex;
  width: 58px;
  height: 32px;
  flex: 0 0 58px;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  border: 1px solid rgba(45, 212, 191, 0.34);
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.16);
  color: #5eead4;
  cursor: pointer;
}

.theme-switch > i {
  font-size: 13px;
}

.theme-switch-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e2e8f0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.28);
  transition: transform 0.2s ease, background-color 0.2s ease;
}

.theme-switch[aria-checked="true"] .theme-switch-thumb {
  transform: translateX(26px);
  background: #fff;
}

.theme-switch:focus-visible {
  outline: 2px solid #5eead4;
  outline-offset: 3px;
}

.section-empty-icon {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(45, 212, 191, 0.22);
  border-radius: 18px;
  background: rgba(45, 212, 191, 0.1);
  color: #5eead4;
  font-size: 28px;
}

.section-empty-state h2 {
  margin: 18px 0 7px;
  color: #f8fafc;
  font-size: 19px;
}

.section-empty-state p {
  max-width: 390px;
  margin: 0;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.6;
}

.section-home-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  margin-top: 22px;
  padding: 0 16px;
  border: 1px solid rgba(45, 212, 191, 0.3);
  border-radius: 12px;
  background: rgba(45, 212, 191, 0.12);
  color: #5eead4;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.section-home-link:hover {
  background: rgba(45, 212, 191, 0.2);
  color: #ccfbf1;
}

.section-nav-link:focus-visible,
.section-logo:focus-visible,
.section-account:focus-visible,
.section-logout:focus-visible,
.section-mobile-logout:focus-visible,
.section-home-link:focus-visible {
  outline: 2px solid rgba(94, 234, 212, 0.8);
  outline-offset: 3px;
}

@media (max-width: 860px) {
  .section-sidebar {
    display: none;
  }

  .section-main {
    padding: 18px;
  }

  .analysis-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .analysis-range {
    width: 100%;
    flex-wrap: wrap;
  }

  .section-mobile-logout {
    min-height: 38px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    margin-left: auto;
    padding: 0 11px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.76);
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 650;
    cursor: pointer;
  }
}

@media (max-width: 560px) {
  .section-main {
    gap: 18px;
    padding: 12px;
  }

  .analysis-summary {
    grid-template-columns: 1fr;
  }

  .analysis-day-row {
    grid-template-columns: 80px minmax(40px, 1fr) 58px;
    gap: 8px;
  }

  .analysis-day-row small {
    display: none;
  }

  .section-header {
    min-height: 82px;
    gap: 10px;
    padding: 12px;
  }

  .section-header-icon {
    width: 38px;
    height: 38px;
    flex-basis: 38px;
    font-size: 20px;
  }

  .section-header h1 {
    font-size: 18px;
  }

  .section-mobile-logout {
    width: 38px;
    min-height: 38px;
    padding: 0;
  }

  .section-mobile-logout span {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }

  .section-empty-state {
    padding: 30px 20px;
  }
}

/* Analytics dashboard layout */
.analysis-page {
  gap: 18px;
}

.analysis-toolbar {
  min-width: 0;
  gap: 22px;
}

.analysis-title-block {
  min-width: 235px;
}

.analysis-title-block .analysis-eyebrow {
  margin: 0 0 6px;
  color: var(--brand-accent-strong) !important;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.14em;
}

.analysis-title-block h1 {
  margin: 0;
  color: var(--mono-text);
  font-size: clamp(24px, 2.1vw, 32px);
  font-weight: 760;
  letter-spacing: -0.035em;
}

.analysis-title-block > p:last-child {
  margin: 6px 0 0;
  color: var(--mono-muted) !important;
  font-size: 13px;
}

.analysis-range {
  flex: 0 1 auto;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
}

.analysis-presets,
.analysis-date-range {
  display: flex;
  align-items: center;
  gap: 7px;
}

.analysis-date-range {
  min-height: 40px;
  gap: 9px;
  padding: 0 10px;
  border: 1px solid var(--mono-border);
  border-radius: 10px;
  background: var(--mono-panel);
  color: var(--mono-muted);
}

.analysis-date-range label {
  display: flex;
  min-width: 0;
}

.analysis-date-range input {
  width: 126px;
  min-width: 0;
  min-height: 36px;
  padding: 0;
  border: 0 !important;
  outline: 0;
  background: transparent !important;
  color: var(--mono-text) !important;
  font: inherit;
  font-size: 11px;
  color-scheme: inherit;
}

.analysis-presets button,
.analysis-apply,
.analysis-export {
  min-height: 40px;
  box-sizing: border-box;
  border: 1px solid var(--mono-border);
  border-radius: 10px;
  background: var(--mono-panel);
  color: var(--mono-muted);
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color 150ms ease, background-color 150ms ease, color 150ms ease;
}

.analysis-presets button {
  min-width: 72px;
  padding: 0 12px;
}

.analysis-presets button.active {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.analysis-apply {
  min-width: 76px;
  padding: 0 15px;
  border-color: var(--brand-accent);
  background: var(--brand-accent);
  color: var(--brand-accent-ink);
}

.analysis-export {
  width: 42px;
  padding: 0;
  font-size: 16px;
}

.analysis-presets button:hover,
.analysis-export:hover:not(:disabled) {
  border-color: var(--brand-accent-border);
  color: var(--brand-accent-strong);
}

.analysis-apply:hover:not(:disabled) {
  background: var(--brand-accent-hover);
}

.analysis-presets button:focus-visible,
.analysis-apply:focus-visible,
.analysis-export:focus-visible,
.analysis-date-range:focus-within {
  outline: 2px solid var(--brand-accent-strong);
  outline-offset: 2px;
}

.analysis-apply:disabled,
.analysis-export:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.analysis-summary {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.analysis-metric {
  min-width: 0;
  min-height: 112px;
  gap: 7px;
  padding: 16px 18px;
  border-color: var(--mono-border);
  border-radius: 16px;
  background: var(--mono-panel);
  box-shadow: 0 7px 24px rgba(0, 0, 0, 0.04);
}

.analysis-metric-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--mono-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.analysis-metric-heading i {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  place-items: center;
  border-radius: 10px;
  background: var(--metric-tint, var(--brand-accent-soft));
  color: var(--metric-color, var(--brand-accent-strong)) !important;
  font-size: 16px;
}

.metric-focus { --metric-color: #10b981; --metric-tint: rgba(16, 185, 129, 0.12); }
.metric-completed { --metric-color: #3b82f6; --metric-tint: rgba(59, 130, 246, 0.12); }
.metric-average { --metric-color: #f59e0b; --metric-tint: rgba(245, 158, 11, 0.13); }
.metric-streak { --metric-color: #f97316; --metric-tint: rgba(249, 115, 22, 0.13); }

.analysis-metric > strong {
  overflow: hidden;
  color: var(--mono-text);
  font-size: clamp(21px, 1.8vw, 27px);
  font-weight: 760;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analysis-metric small {
  overflow: hidden;
  color: var(--mono-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analysis-overview-grid {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1.7fr) minmax(310px, 0.95fr);
  gap: 16px;
}

.analysis-panel {
  min-width: 0;
  box-sizing: border-box;
  padding: 20px;
  border: 1px solid var(--mono-border);
  border-radius: 16px;
  background: var(--mono-panel);
  box-shadow: 0 7px 24px rgba(0, 0, 0, 0.04);
}

.analysis-activity-panel,
.analysis-distribution-panel {
  min-height: 350px;
}

.analysis-panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 22px;
}

.analysis-panel-heading h2 {
  margin: 0;
  color: var(--mono-text);
  font-size: 16px;
  font-weight: 730;
}

.analysis-panel-heading p {
  margin: 5px 0 0;
  color: var(--mono-muted) !important;
  font-size: 12px;
}

.analysis-legend {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 7px;
  color: var(--mono-muted);
  font-size: 11px;
}

.analysis-legend > span {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.analysis-legend .legend-actual { background: var(--brand-accent); }
.analysis-legend .legend-average {
  width: 14px;
  height: 0;
  margin-left: 9px;
  border-top: 2px dashed var(--mono-subtle);
  border-radius: 0;
}

.analysis-chart {
  display: grid;
  min-width: 0;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: stretch;
}

.analysis-chart-y-axis {
  display: flex;
  height: 252px;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
  padding: 0 10px 26px 0;
  color: var(--mono-muted);
  font-size: 10px;
}

.analysis-chart-scroll {
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
}

.analysis-chart-inner { width: 100%; }

.analysis-chart-plot {
  position: relative;
  height: 252px;
  min-width: 0;
}

.analysis-grid-line {
  position: absolute;
  right: 0;
  left: 0;
  height: 1px;
  border-top: 1px dashed color-mix(in srgb, var(--mono-border) 78%, transparent);
}

.analysis-grid-line:nth-child(1) { top: 0; }
.analysis-grid-line:nth-child(2) { top: 25%; }
.analysis-grid-line:nth-child(3) { top: 50%; }
.analysis-grid-line:nth-child(4) { top: 75%; }
.analysis-grid-line:nth-child(5) { top: calc(100% - 26px); }
.analysis-grid-line.grid-line-base { border-top-style: solid; }

.analysis-average-line {
  position: absolute;
  z-index: 1;
  right: 0;
  left: 0;
  border-top: 1px dashed var(--mono-subtle);
  pointer-events: none;
}

.analysis-chart-columns {
  position: absolute;
  inset: 0;
  display: grid;
}

.analysis-chart-column {
  display: grid;
  min-width: 0;
  grid-template-rows: minmax(0, 1fr) 26px;
  justify-items: center;
}

.analysis-bar-area {
  display: flex;
  width: 100%;
  align-items: flex-end;
  justify-content: center;
  box-sizing: border-box;
  padding: 0 5px;
}

.analysis-bar {
  width: min(34px, 68%);
  min-height: 3px;
  border-radius: 7px 7px 2px 2px;
  background: var(--brand-accent);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--brand-accent) 18%, transparent);
  transition: filter 140ms ease, height 180ms ease;
}

.analysis-bar-area:hover .analysis-bar:not(.bar-zero) { filter: brightness(1.14); }
.analysis-bar.bar-zero { background: var(--mono-hover); box-shadow: none; }

.analysis-chart-label {
  max-width: 100%;
  overflow: hidden;
  align-self: end;
  padding-top: 7px;
  color: var(--mono-muted);
  font-size: 10px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analysis-panel-empty,
.analysis-table-empty {
  display: grid;
  min-height: 218px;
  place-items: center;
  color: var(--mono-muted);
  font-size: 12px;
  text-align: center;
}

.analysis-distribution-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.analysis-distribution-bar {
  display: flex;
  height: 12px;
  overflow: hidden;
  gap: 2px;
  border-radius: 99px;
  background: var(--mono-hover);
}

.analysis-distribution-bar span { min-width: 3px; border-radius: inherit; }

.analysis-list-breakdown {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.analysis-list-row {
  display: grid;
  min-width: 0;
  min-height: 61px;
  grid-template-columns: 12px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  padding: 9px 11px;
  border: 1px solid var(--mono-border);
  border-radius: 12px;
  background: var(--mono-surface);
}

.analysis-list-dot { width: 10px; height: 10px; border-radius: 50%; }

.analysis-list-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.analysis-list-copy strong {
  overflow: hidden;
  color: var(--mono-text);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analysis-list-copy small { color: var(--mono-muted); font-size: 10px; }
.analysis-list-duration { color: var(--mono-text); font-size: 13px; white-space: nowrap; }
.analysis-sessions-panel { padding-bottom: 10px; }

.analysis-session-count {
  padding: 5px 9px;
  border: 1px solid var(--mono-border);
  border-radius: 999px;
  background: var(--mono-surface);
  color: var(--mono-muted);
  font-size: 10px;
  white-space: nowrap;
}

.analysis-table-scroll { width: 100%; overflow-x: auto; }

.analysis-session-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.analysis-session-table th {
  padding: 0 12px 11px;
  border-bottom: 1px solid var(--mono-border);
  color: var(--mono-muted);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  white-space: nowrap;
}

.analysis-session-table td {
  padding: 12px;
  border-bottom: 1px solid color-mix(in srgb, var(--mono-border) 68%, transparent);
  color: var(--mono-text);
  font-size: 12px;
}

.analysis-session-table tbody tr:last-child td { border-bottom: 0; }
.analysis-session-table .session-date { min-width: 150px; color: var(--mono-muted); white-space: nowrap; }
.analysis-session-table .session-task { min-width: 220px; }

.session-task strong,
.session-task small {
  display: block;
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-task strong { color: var(--mono-text); font-size: 12px; font-weight: 650; }
.session-task small { margin-top: 4px; color: var(--mono-muted); font-size: 10px; }

.session-list-pill {
  display: inline-block;
  max-width: 150px;
  overflow: hidden;
  padding: 5px 8px;
  border: 1px solid var(--brand-accent-border);
  border-radius: 7px;
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analysis-session-table .session-duration { font-weight: 650; white-space: nowrap; }

.session-status {
  display: inline-block;
  padding: 5px 9px;
  border: 1px solid var(--mono-border);
  border-radius: 7px;
  background: var(--mono-surface);
  color: var(--mono-muted);
  font-size: 10px;
  font-weight: 650;
  white-space: nowrap;
}

.session-status.status-completed {
  border-color: color-mix(in srgb, #10b981 44%, var(--mono-border));
  background: color-mix(in srgb, #10b981 12%, var(--mono-panel));
  color: #10b981;
}

.session-status.status-skipped {
  border-color: color-mix(in srgb, #ef4444 42%, var(--mono-border));
  background: color-mix(in srgb, #ef4444 10%, var(--mono-panel));
  color: #ef4444;
}

.analysis-error {
  border-color: rgba(248, 113, 113, 0.35);
  color: #ef4444;
}

@media (max-width: 1240px) {
  .analysis-toolbar { align-items: flex-start; flex-direction: column; }
  .analysis-range { width: 100%; justify-content: flex-start; }
}

@media (max-width: 1020px) {
  .analysis-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analysis-overview-grid { grid-template-columns: minmax(0, 1fr); }
  .analysis-activity-panel,
  .analysis-distribution-panel { min-height: auto; }
}

@media (max-width: 560px) {
  .analysis-summary { grid-template-columns: minmax(0, 1fr); }
  .analysis-toolbar { gap: 15px; }
  .analysis-title-block { min-width: 0; }
  .analysis-title-block h1 { font-size: 25px; }
  .analysis-title-block > p:last-child { max-width: 40ch; font-size: 12px; line-height: 1.5; }
  .analysis-range { gap: 7px; }
  .analysis-presets { flex: 1 0 100%; }
  .analysis-date-range { flex: 1; justify-content: space-between; }
  .analysis-date-range input { width: 105px; font-size: 10px; }
  .analysis-apply { min-width: 68px; }
  .analysis-export { width: 40px; }
  .analysis-panel { padding: 15px; border-radius: 14px; }
  .analysis-panel-heading { flex-direction: column; gap: 10px; }
  .analysis-legend { font-size: 10px; }
  .analysis-chart { grid-template-columns: 46px minmax(0, 1fr); }
  .analysis-chart-y-axis { font-size: 9px; }
  .analysis-chart-inner { min-width: 640px; }
  .analysis-session-table { min-width: 690px; }
}

.analysis-page {
  position: relative;
  isolation: isolate;
}

.analysis-page::before {
  position: absolute;
  z-index: -1;
  top: -70px;
  right: -45px;
  width: min(55vw, 760px);
  height: 290px;
  border-radius: 50%;
  background: radial-gradient(ellipse, color-mix(in srgb, var(--brand-accent) 9%, transparent), transparent 70%);
  content: "";
  pointer-events: none;
}

.analysis-title-lockup {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 16px;
}

.analysis-title-icon {
  display: grid;
  width: 54px;
  height: 54px;
  flex: 0 0 54px;
  place-items: center;
  border: 1px solid var(--brand-accent-border);
  border-radius: 17px;
  background: linear-gradient(145deg, var(--brand-accent-soft), color-mix(in srgb, var(--brand-accent) 5%, var(--mono-panel)));
  box-shadow: 0 8px 25px color-mix(in srgb, var(--brand-accent) 12%, transparent), inset 0 1px rgba(255, 255, 255, 0.08);
  color: var(--brand-accent-strong);
  font-size: 24px;
}

.analysis-title-icon i { color: inherit !important; }
.analysis-title-block { min-width: 0; }

.analysis-metric {
  position: relative;
  min-height: 138px;
  overflow: hidden;
  isolation: isolate;
  gap: 9px;
  border-radius: 17px;
  background: linear-gradient(145deg, color-mix(in srgb, var(--mono-panel) 96%, white), var(--mono-panel));
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  transition: transform 170ms ease, border-color 170ms ease, box-shadow 170ms ease;
}

.analysis-metric::before {
  position: absolute;
  z-index: -1;
  top: 0;
  right: 16px;
  left: 16px;
  height: 2px;
  border-radius: 0 0 99px 99px;
  background: linear-gradient(90deg, transparent, var(--metric-color, var(--brand-accent)), transparent);
  opacity: 0.9;
  content: "";
}

.analysis-metric::after {
  position: absolute;
  z-index: -1;
  top: -60px;
  right: -42px;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--metric-color, var(--brand-accent)) 10%, transparent), transparent 72%);
  content: "";
  pointer-events: none;
}

.analysis-metric:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--metric-color, var(--brand-accent)) 36%, var(--mono-border));
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.1);
}

.analysis-metric-heading > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analysis-metric-heading > i {
  border: 1px solid color-mix(in srgb, var(--metric-color, var(--brand-accent)) 22%, transparent);
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.09);
}

.analysis-metric-value {
  color: var(--mono-text);
  font-size: clamp(24px, 2vw, 30px);
  font-weight: 780;
  letter-spacing: -0.045em;
  line-height: 1.05;
}

.analysis-metric-value > span {
  color: var(--mono-muted);
  font-size: 0.72em;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.analysis-metric-footer {
  display: flex;
  min-width: 0;
  min-height: 24px;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
}

.analysis-metric-footer > small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.analysis-sparkline {
  display: flex;
  width: 86px;
  height: 25px;
  flex: 0 0 86px;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 3px;
}

.analysis-sparkline span {
  width: 5px;
  min-height: 3px;
  border-radius: 3px 3px 1px 1px;
  background: color-mix(in srgb, var(--metric-color) 67%, transparent);
  transition: height 180ms ease, background-color 180ms ease;
}

.analysis-sparkline span:last-child { background: var(--metric-color); }
.analysis-sparkline span.zero { background: var(--mono-hover); }

.metric-completion-footer {
  display: block;
}

.metric-completion-footer > small {
  display: block;
  margin: 0 0 7px;
}

.metric-progress-track {
  height: 5px;
  overflow: hidden;
  border-radius: 99px;
  background: color-mix(in srgb, var(--metric-color) 12%, var(--mono-hover));
}

.metric-progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, color-mix(in srgb, var(--metric-color) 70%, white), var(--metric-color));
  box-shadow: 0 0 10px color-mix(in srgb, var(--metric-color) 30%, transparent);
}

.analysis-day-dots {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
}

.analysis-day-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--mono-hover);
}

.analysis-day-dots span.active {
  background: var(--metric-color);
  box-shadow: 0 0 7px color-mix(in srgb, var(--metric-color) 40%, transparent);
}

.analysis-streak-mark {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
  padding: 4px 7px;
  border: 1px solid color-mix(in srgb, var(--metric-color) 25%, transparent);
  border-radius: 99px;
  background: var(--metric-tint);
  color: var(--metric-color);
  font-size: 9px;
  font-weight: 700;
  white-space: nowrap;
}

.analysis-streak-mark i { color: inherit !important; }

.analysis-panel {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  background: linear-gradient(155deg, color-mix(in srgb, var(--mono-panel) 97%, white), var(--mono-panel) 70%);
  box-shadow: 0 13px 32px rgba(15, 23, 42, 0.055);
}

.analysis-panel-heading { align-items: center; margin-bottom: 20px; }

.analysis-panel-title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 11px;
}

.analysis-panel-icon {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  border: 1px solid var(--brand-accent-border);
  border-radius: 11px;
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
  font-size: 17px;
}

.analysis-panel-icon i { color: inherit !important; }
.distribution-icon { border-color: rgba(59, 130, 246, 0.23); background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.sessions-icon { border-color: rgba(245, 158, 11, 0.23); background: rgba(245, 158, 11, 0.1); color: #f59e0b; }

.analysis-legend {
  padding: 7px 10px;
  border: 1px solid var(--mono-border);
  border-radius: 999px;
  background: var(--mono-surface);
}

.analysis-chart-y-axis { padding-right: 12px; }

.analysis-grid-line { border-top-color: color-mix(in srgb, var(--mono-border) 64%, transparent); }

.analysis-average-line {
  border-top: 1px dashed color-mix(in srgb, var(--mono-muted) 70%, transparent);
}

.analysis-bar {
  position: relative;
  width: min(38px, 66%);
  border: 1px solid color-mix(in srgb, var(--brand-accent) 75%, white);
  background: linear-gradient(180deg, color-mix(in srgb, var(--brand-accent-hover) 70%, white), var(--brand-accent));
  box-shadow: 0 5px 16px color-mix(in srgb, var(--brand-accent) 25%, transparent), inset 0 1px rgba(255, 255, 255, 0.18);
}

.analysis-bar.bar-zero { border: 0; }

.analysis-bar-value {
  position: absolute;
  z-index: 2;
  left: 50%;
  transform: translateX(-50%);
  padding: 3px 5px;
  border: 1px solid var(--brand-accent-border);
  border-radius: 6px;
  background: var(--mono-inset);
  color: var(--brand-accent-strong);
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 120ms ease;
  pointer-events: none;
}

.analysis-chart-column:hover .analysis-bar-value,
.analysis-chart-column.is-today .analysis-bar-value { opacity: 1; }

.analysis-chart-column.is-today .analysis-chart-label {
  color: var(--brand-accent-strong);
  font-weight: 750;
}

.analysis-chart-column.is-today .analysis-bar {
  box-shadow: 0 0 0 3px var(--brand-accent-soft), 0 7px 18px color-mix(in srgb, var(--brand-accent) 28%, transparent);
}

.analysis-distribution-bar {
  height: 14px;
  gap: 3px;
  padding: 2px;
  box-sizing: border-box;
  background: var(--mono-inset);
}

.analysis-distribution-bar span { min-width: 4px; }

.analysis-list-row {
  border-left: 3px solid var(--list-color, var(--brand-accent));
  border-radius: 10px 13px 13px 10px;
  transition: transform 150ms ease, border-color 150ms ease, background-color 150ms ease;
}

.analysis-list-row:hover {
  transform: translateX(2px);
  border-color: var(--list-color, var(--brand-accent));
  background: var(--mono-hover);
}

.analysis-list-copy { gap: 4px; }

.analysis-list-progress {
  display: block;
  height: 3px;
  overflow: hidden;
  margin-top: 1px;
  border-radius: 99px;
  background: var(--mono-hover);
}

.analysis-list-progress span { display: block; height: 100%; border-radius: inherit; }

.analysis-session-count {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.analysis-session-table th {
  padding-top: 5px;
  letter-spacing: 0.055em;
}

.analysis-session-table td { transition: background-color 120ms ease; }
.analysis-session-table tbody tr:hover td { background: color-mix(in srgb, var(--brand-accent) 4%, var(--mono-panel)); }

.session-task small {
  width: fit-content;
  max-width: 100%;
  padding: 2px 6px;
  border: 1px solid var(--mono-border);
  border-radius: 5px;
  background: var(--mono-surface);
}

.session-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
}

.session-status i { color: inherit !important; font-size: 11px; }

/* Analytics: the period overview joins the headline metrics to the detailed charts. */
.analysis-focus-pulse {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(330px, 1.08fr) minmax(0, 1fr);
  gap: 24px;
  align-items: center;
  padding: 19px 22px;
  border: 1px solid color-mix(in srgb, var(--brand-accent) 23%, var(--mono-border));
  border-radius: 18px;
  background:
    radial-gradient(circle at 8% 130%, color-mix(in srgb, var(--brand-accent) 13%, transparent), transparent 34%),
    linear-gradient(112deg, color-mix(in srgb, var(--mono-panel) 95%, var(--brand-accent-soft)), var(--mono-panel) 54%);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.055), inset 0 1px rgba(255, 255, 255, 0.06);
}

.focus-pulse-intro {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 16px;
}

.focus-pulse-ring {
  position: relative;
  display: grid;
  width: 76px;
  height: 76px;
  flex: 0 0 76px;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(var(--brand-accent) 0 var(--completion), var(--mono-hover) var(--completion) 100%);
  box-shadow: 0 7px 17px color-mix(in srgb, var(--brand-accent) 16%, transparent);
}

.focus-pulse-ring::before {
  position: absolute;
  inset: 6px;
  border: 1px solid color-mix(in srgb, var(--mono-border) 84%, transparent);
  border-radius: inherit;
  background: var(--mono-panel);
  content: "";
}

.focus-pulse-ring > div {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1;
}

.focus-pulse-ring strong {
  color: var(--mono-text);
  font-size: 17px;
  font-weight: 780;
  letter-spacing: -0.045em;
}

.focus-pulse-ring span {
  margin-top: 4px;
  color: var(--mono-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.focus-pulse-copy {
  min-width: 0;
}

.focus-pulse-copy .analysis-eyebrow {
  margin: 0 0 5px;
  color: var(--brand-accent-strong) !important;
  font-size: 9px;
  font-weight: 760;
  letter-spacing: 0.13em;
}

.focus-pulse-copy h2 {
  margin: 0;
  color: var(--mono-text);
  font-size: 16px;
  font-weight: 760;
  letter-spacing: -0.025em;
}

.focus-pulse-copy > p:last-child {
  margin: 5px 0 0;
  color: var(--mono-muted);
  font-size: 12px;
  line-height: 1.45;
}

.focus-pulse-facts {
  display: grid;
  min-width: 0;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 0;
}

.focus-pulse-facts > div {
  min-width: 0;
  padding: 3px 17px;
  border-left: 1px solid var(--mono-border);
}

.focus-pulse-facts > div:first-child { border-left: 0; }

.focus-pulse-facts dt {
  margin: 0 0 7px;
  color: var(--mono-muted);
  font-size: 9px;
  font-weight: 760;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.focus-pulse-facts dd {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 6px;
  margin: 0;
  overflow: hidden;
  color: var(--mono-text);
  font-size: 15px;
  font-weight: 730;
  letter-spacing: -0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-pulse-facts small {
  display: block;
  overflow: hidden;
  margin-top: 5px;
  color: var(--mono-muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-pulse-list span {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 3px;
  box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 5%, transparent);
}

.analysis-panel-meta {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
}

.analysis-peak-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 9px;
  border: 1px solid color-mix(in srgb, #f59e0b 30%, var(--mono-border));
  border-radius: 999px;
  background: color-mix(in srgb, #f59e0b 9%, var(--mono-panel));
  color: #d97706;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

.analysis-peak-chip i { color: inherit !important; }

.analysis-distribution-summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  margin-top: -3px;
}

.analysis-distribution-summary span {
  color: var(--mono-muted);
  font-size: 11px;
}

.analysis-distribution-summary strong {
  color: var(--mono-text);
  font-size: 18px;
  font-weight: 760;
  letter-spacing: -0.035em;
  white-space: nowrap;
}

@media (max-width: 1180px) {
  .analysis-focus-pulse { grid-template-columns: 1fr; gap: 18px; }
  .focus-pulse-facts { max-width: 680px; }
  .focus-pulse-facts > div:first-child { padding-left: 0; }
}

@media (max-width: 560px) {
  .analysis-title-lockup { align-items: flex-start; gap: 11px; }
  .analysis-title-icon { width: 44px; height: 44px; flex-basis: 44px; border-radius: 14px; font-size: 20px; }
  .analysis-metric { min-height: 130px; padding: 15px; }
  .analysis-metric-value { font-size: 27px; }
  .analysis-panel-title { align-items: flex-start; }
  .analysis-panel-icon { width: 32px; height: 32px; flex-basis: 32px; font-size: 15px; }
  .analysis-chart-label { font-size: 9px; }
  .analysis-focus-pulse { gap: 16px; padding: 16px; border-radius: 15px; }
  .focus-pulse-intro { align-items: flex-start; gap: 13px; }
  .focus-pulse-ring { width: 64px; height: 64px; flex-basis: 64px; }
  .focus-pulse-ring::before { inset: 5px; }
  .focus-pulse-ring strong { font-size: 15px; }
  .focus-pulse-copy h2 { font-size: 15px; }
  .focus-pulse-copy > p:last-child { font-size: 11px; }
  .focus-pulse-facts { grid-template-columns: 1fr; gap: 11px; }
  .focus-pulse-facts > div { padding: 10px 0 0; border-top: 1px solid var(--mono-border); border-left: 0; }
  .focus-pulse-facts > div:first-child { padding-top: 0; border-top: 0; }
  .analysis-panel-meta { width: 100%; flex-wrap: wrap; }
  .analysis-legend { margin-left: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .analysis-metric,
  .analysis-list-row,
  .analysis-bar,
  .analysis-bar-value,
  .analysis-session-table td { transition: none; }
}
</style>
