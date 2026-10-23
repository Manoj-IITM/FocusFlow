<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import ThemeSwitcher from "../../components/ThemeSwitcher.vue";
import { apiUrl } from "../../api.js";
import { clearSession, buildAuthHeaders, readStoredUserOr } from "../../session.js";

const router = useRouter();

// User state
const user = ref(readStoredUserOr({ id: 1, username: "Alex" }));

// Time & Greeting
const currentTime = ref("");
const currentDate = ref("");
const greeting = ref("Good Evening");
const greetingWaveKey = ref(0);

const waveGreeting = () => {
  greetingWaveKey.value += 1;
};

const updateClock = () => {
  const now = new Date();
  const hrs = now.getHours();
  if (hrs < 12) greeting.value = "Good Morning";
  else if (hrs < 17) greeting.value = "Good Afternoon";
  else greeting.value = "Good Evening";

  currentDate.value = now.toLocaleDateString("en-US", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  currentTime.value = now.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
};

let clockInterval = null;

const showNotificationPanel = ref(false);
const notificationPanelRef = ref(null);
const navItems = [
  { name: "Study Environment", icon: "ti ti-leaf", to: "/dashboard" },
  { name: "Analyse", icon: "ti ti-chart-bar", to: "/analyse" },
  { name: "Settings", icon: "ti ti-settings", to: "/settings" },
];

// Tasks & Filters
const localDateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};
const taskFilter = ref("All"); // 'All', 'Pending', 'Completed'
const taskFilterMenuOpen = ref(false);
const taskDateFilter = ref("Today");
const selectedStudyDate = ref(localDateKey(new Date()));
const isTaskCalendarOpen = ref(false);
const taskCalendarAnchorRef = ref(null);
const taskCalendarPanelRef = ref(null);
const taskCalendarPopoverStyle = ref({ top: "8px", left: "8px" });
const calendarMonth = ref(new Date());
const calendarEvents = ref({});
const calendarLoading = ref(false);
const showAddTaskModal = ref(false);
const taskFormError = ref("");
const newTaskTitle = ref("");
const newTaskTag = ref("Study");
const newTaskMinutes = ref(45);
const shiftDateKey = (dateKey, offset) => {
  const [year, month, day] = dateKey.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  date.setDate(date.getDate() + offset);
  return localDateKey(date);
};
const selectedStudyDateLabel = computed(() => {
  const [year, month, day] = selectedStudyDate.value.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric",
  });
});
const chooseTaskDateFilter = (filter) => {
  taskDateFilter.value = filter;
  if (filter === "Today") selectedStudyDate.value = getTodayDateKey();
  else if (filter === "Tomorrow") selectedStudyDate.value = shiftDateKey(getTodayDateKey(), 1);
  fetchTasks();
};
const shiftSelectedStudyDate = (offset) => {
  taskDateFilter.value = "Date";
  selectedStudyDate.value = shiftDateKey(selectedStudyDate.value, offset);
  fetchTasks();
};
const setSelectedStudyDate = () => {
  taskDateFilter.value = "Date";
  fetchTasks();
};
const calendarMonthLabel = computed(() => calendarMonth.value.toLocaleDateString("en-US", { month: "long", year: "numeric" }));
const calendarGridDays = computed(() => {
  const firstDay = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth(), 1);
  firstDay.setDate(firstDay.getDate() - ((firstDay.getDay() + 6) % 7));
  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(firstDay);
    day.setDate(firstDay.getDate() + index);
    const key = localDateKey(day);
    return {
      key,
      number: day.getDate(),
      inMonth: day.getMonth() === calendarMonth.value.getMonth(),
      isSelected: key === selectedStudyDate.value,
      event: calendarEvents.value[key] || null,
    };
  });
});
const fetchCalendarMonth = async () => {
  calendarLoading.value = true;
  const year = calendarMonth.value.getFullYear();
  const month = calendarMonth.value.getMonth();
  const start = localDateKey(new Date(year, month, 1));
  const end = localDateKey(new Date(year, month + 1, 0));
  try {
    const response = await axios.get(apiUrl("/calendar"), { params: { start, end } });
    calendarEvents.value = Object.fromEntries((response.data || []).map((event) => [event.scheduled_date, event]));
  } catch (error) {
    console.error("Unable to load calendar occurrences:", error);
  } finally {
    calendarLoading.value = false;
  }
};
const positionTaskCalendarPopover = () => {
  const anchor = taskCalendarAnchorRef.value;
  const panel = taskCalendarPanelRef.value;
  if (!isTaskCalendarOpen.value || !anchor || !panel) return;

  const anchorBounds = anchor.getBoundingClientRect();
  const panelWidth = panel.offsetWidth;
  const panelHeight = panel.offsetHeight;
  const viewportPadding = 8;
  const maxLeft = Math.max(viewportPadding, window.innerWidth - panelWidth - viewportPadding);
  const left = Math.max(viewportPadding, Math.min(maxLeft, anchorBounds.right - panelWidth));
  const belowTop = anchorBounds.bottom + viewportPadding;
  const top = belowTop + panelHeight <= window.innerHeight - viewportPadding
    ? belowTop
    : Math.max(viewportPadding, anchorBounds.top - panelHeight - viewportPadding);

  taskCalendarPopoverStyle.value = { top: `${top}px`, left: `${left}px` };
};
const toggleTaskCalendar = async () => {
  isTaskCalendarOpen.value = !isTaskCalendarOpen.value;
  if (isTaskCalendarOpen.value) {
    const [year, month] = selectedStudyDate.value.split("-").map(Number);
    calendarMonth.value = new Date(year, month - 1, 1);
    await nextTick();
    positionTaskCalendarPopover();
    await fetchCalendarMonth();
  }
};
const changeCalendarMonth = async (offset) => {
  calendarMonth.value = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth() + offset, 1);
  await fetchCalendarMonth();
};
const selectCalendarDay = (dateKey) => {
  selectedStudyDate.value = dateKey;
  taskDateFilter.value = "Date";
  isTaskCalendarOpen.value = false;
  fetchTasks();
};
const defaultTaskListId = "default";
const taskListColors = [
  "#14b8a6",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#f97316",
  "#eab308",
  "#22c55e",
  "#ef4444",
];
const taskListIcons = ["ti-book-2", "ti-bulb", "ti-code", "ti-briefcase-2", "ti-heart", "ti-star"];
const taskListStorageKey = `focusflow_task_lists_${user.value.id}`;
const taskTimersStorageKey = `focusflow_task_timers_${user.value.id}`;
const activeTaskStorageKey = `focusflow_active_task_${user.value.id}`;
// Focus stats and sessions are user scoped as well, so switching accounts in the
// same browser never shows another account's focus data.
const statsStorageKey = `focusflow_stats_${user.value.id}`;
const focusSessionsStorageKey = `focusflow_sessions_${user.value.id}`;
const currentFocusStorageKey = `focusflow_current_focus_${user.value.id}`;
const savedTaskListState = (() => {
  try {
    return JSON.parse(localStorage.getItem(taskListStorageKey) || "null");
  } catch (error) {
    return null;
  }
})();
const taskLists = ref(
  Array.isArray(savedTaskListState?.lists)
    ? savedTaskListState.lists.map((list, index) => ({
        ...list,
        color: list.color || taskListColors[index % taskListColors.length],
        icon: list.icon || (index === 0 ? "ti-list-check" : "ti-book-2"),
      }))
    : [{ id: defaultTaskListId, name: "My Tasks", color: taskListColors[0], icon: "ti-list-check" }],
);
const activeTaskListId = ref(
  taskLists.value.some((list) => list.id === savedTaskListState?.activeListId)
    ? savedTaskListState.activeListId
    : taskLists.value[0]?.id || null,
);
const makeDefaultRecurrence = (startDate = selectedStudyDate.value) => ({
  frequency: "none",
  interval: 1,
  unit: "weeks",
  weekdays: [],
  day_of_month: Number(startDate.split("-")[2]) || 1,
  end_condition: "never",
  end_date: "",
  occurrence_count: 10,
});
const newTaskSchedule = ref({
  task_list_id: activeTaskListId.value,
  scheduled_date: selectedStudyDate.value,
  due_date: "",
  start_date: selectedStudyDate.value,
  priority: "medium",
  notes: "",
  recurrence: makeDefaultRecurrence(),
});
const editTaskSchedule = ref({
  task_list_id: activeTaskListId.value,
  scheduled_date: "",
  due_date: "",
  start_date: selectedStudyDate.value,
  priority: "medium",
  notes: "",
  recurrence: makeDefaultRecurrence(),
});
const editTaskScope = ref("this");
const taskBeingDeleted = ref(null);
const taskDeleteScope = ref("this");
const showDeleteTaskModal = ref(false);
const recurrenceWeekdays = [
  { label: "M", value: 0, title: "Monday" },
  { label: "T", value: 1, title: "Tuesday" },
  { label: "W", value: 2, title: "Wednesday" },
  { label: "T", value: 3, title: "Thursday" },
  { label: "F", value: 4, title: "Friday" },
  { label: "S", value: 5, title: "Saturday" },
  { label: "S", value: 6, title: "Sunday" },
];
const toggleRecurrenceWeekday = (form, day) => {
  const recurrence = form.recurrence || form.value.recurrence;
  const selected = recurrence.weekdays;
  const index = selected.indexOf(day);
  if (index >= 0) selected.splice(index, 1);
  else selected.push(day);
  selected.sort((left, right) => left - right);
};
const setEditRecurrenceFrequency = (frequency) => {
  const recurrence = editTaskSchedule.value.recurrence;
  recurrence.frequency = frequency;
  const usesWeekdays = frequency === "weekly"
    || (frequency === "custom" && recurrence.unit === "weeks");
  if (usesWeekdays && !recurrence.weekdays.length) {
    const dateKey = editTaskSchedule.value.scheduled_date
      || editTaskSchedule.value.start_date
      || getTodayDateKey();
    const [year, month, day] = dateKey.split("-").map(Number);
    recurrence.weekdays = [(new Date(year, month - 1, day).getDay() + 6) % 7];
  }
};
const buildRecurrenceRule = (form) => {
  const rule = form.recurrence;
  if (rule.frequency === "none") return { frequency: "none" };
  const result = {
    frequency: rule.frequency,
    interval: Math.max(1, Number(rule.interval) || 1),
    unit: rule.frequency === "custom" ? rule.unit : undefined,
    weekdays: rule.weekdays,
    day_of_month: Number(rule.day_of_month) || 1,
    end_condition: rule.end_condition,
  };
  if (rule.end_condition === "date") result.end_date = rule.end_date;
  if (rule.end_condition === "count") result.occurrence_count = Number(rule.occurrence_count) || 1;
  return result;
};
const recurrenceSummary = (rule) => {
  if (rule.frequency === "none") return "Does not repeat";
  const interval = Math.max(1, Number(rule.interval) || 1);
  const unit = rule.frequency === "custom"
    ? rule.unit
    : rule.frequency === "daily"
      ? "days"
      : rule.frequency === "weekly"
        ? "weeks"
        : "months";
  const unitName = unit === "days" ? "day" : unit === "weeks" ? "week" : "month";
  let summary = `Repeats every ${interval > 1 ? `${interval} ${unitName}s` : unitName}`;
  if (unit === "weeks") {
    const names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    const days = (rule.weekdays || []).map((day) => names[day]).filter(Boolean);
    if (days.length) summary += ` on ${days.join(", ")}`;
  }
  if (unit === "months") {
    const day = Number(rule.day_of_month) || 1;
    const suffix = day % 100 >= 11 && day % 100 <= 13
      ? "th"
      : day % 10 === 1
        ? "st"
        : day % 10 === 2
          ? "nd"
          : day % 10 === 3
            ? "rd"
            : "th";
    summary += ` on the ${day}${suffix}`;
  }
  if (rule.end_condition === "date" && rule.end_date) summary += ` until ${rule.end_date}`;
  if (rule.end_condition === "count") summary += ` for ${rule.occurrence_count} occurrences`;
  return `${summary}.`;
};
const openAddTaskModal = () => {
  newTaskTitle.value = "";
  newTaskTag.value = "Study";
  newTaskMinutes.value = 45;
  taskFormError.value = "";
  newTaskSchedule.value = {
    task_list_id: activeTaskListId.value,
    scheduled_date: selectedStudyDate.value,
    due_date: "",
    start_date: selectedStudyDate.value,
    priority: "medium",
    notes: "",
    recurrence: makeDefaultRecurrence(selectedStudyDate.value),
  };
  showAddTaskModal.value = true;
};
const activeTaskList = computed(
  () => taskLists.value.find((list) => list.id === activeTaskListId.value) || taskLists.value[0] || null,
);
const taskListByTaskId = ref(
  savedTaskListState?.taskListByTaskId && typeof savedTaskListState.taskListByTaskId === "object"
    ? savedTaskListState.taskListByTaskId
    : {},
);
const deletedTaskIds = ref(
  Array.isArray(savedTaskListState?.deletedTaskIds) ? savedTaskListState.deletedTaskIds : [],
);
const showCreateTaskListModal = ref(false);
const editingTaskListId = ref(null);
const taskListToDelete = ref(null);
const openTaskListMenu = ref(null);
const draggedTaskListId = ref(null);
const newTaskListName = ref("");
const newTaskListColor = ref(taskListColors[0]);
const newTaskListIcon = ref(taskListIcons[0]);
const getTaskListIdForTask = (task) =>
  task?.task_list_id || taskListByTaskId.value[task?.id] || taskLists.value[0]?.id || null;
const taskBelongsToList = (task, listId) => {
  const taskListId = getTaskListIdForTask(task);
  return taskListId != null && listId != null && String(taskListId) === String(listId);
};
const activeListTaskCount = (listId) =>
  tasks.value.filter((task) => taskBelongsToList(task, listId)).length;
const getTaskListColor = (listId) =>
  taskLists.value.find((list) => list.id === listId)?.color || "#14b8a6";
// Shared by the list tabs and the "Create a task list" preview chip so a list
// colour never carries text that is unreadable on it.
const taskListForegroundForColor = (color) => {
  const channels = /^#[\da-f]{6}$/i.test(color)
    ? color.slice(1).match(/.{2}/g).map((channel) => parseInt(channel, 16))
    : [20, 184, 166];
  const luminance = channels
    .map((channel) => {
      const normalized = channel / 255;
      return normalized <= 0.04045
        ? normalized / 12.92
        : ((normalized + 0.055) / 1.055) ** 2.4;
    })
    .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);

  return luminance > 0.179 ? "#111827" : "#ffffff";
};
const getTaskListForeground = (listId) => taskListForegroundForColor(getTaskListColor(listId));

const saveTaskLists = () => {
  localStorage.setItem(taskListStorageKey, JSON.stringify({
    lists: taskLists.value,
    activeListId: activeTaskListId.value,
    taskListByTaskId: taskListByTaskId.value,
    deletedTaskIds: deletedTaskIds.value,
    tasks: tasks.value,
    taskTimers: taskTimers.value,
    activeFocusTask: activeFocusTask.value,
  }));
};

const tasks = ref(
  Array.isArray(savedTaskListState?.tasks)
    ? savedTaskListState.tasks
    : [
        { id: 1, task_list_id: defaultTaskListId, title: "Maths Revision - Chapter 5", tag: "Study", duration_minutes: 85, completed: false, completed_time: null },
        { id: 2, task_list_id: defaultTaskListId, title: "Physics Numericals", tag: "Study", duration_minutes: 45, completed: true, completed_time: "Today, 06:15 PM" },
        { id: 3, task_list_id: defaultTaskListId, title: "Chemistry Notes", tag: "Study", duration_minutes: 120, completed: false, completed_time: null },
        { id: 4, task_list_id: defaultTaskListId, title: "Read Chapter 3 (English)", tag: "Study", duration_minutes: 60, completed: false, completed_time: null },
        { id: 5, task_list_id: defaultTaskListId, title: "DSA Practice Questions", tag: "Study", duration_minutes: 90, completed: true, completed_time: "Today, 04:20 PM" },
      ],
);

const taskMatchesCurrentDateFilter = (task) => {
  const today = getTodayDateKey();
  const tomorrow = shiftDateKey(today, 1);
  const scheduled = task.scheduled_date;
  if (taskDateFilter.value === "Upcoming") return Boolean(scheduled && scheduled >= today && !task.completed && !task.skipped);
  if (taskDateFilter.value === "Overdue") return Boolean(task.due_date && task.due_date < today && !task.completed && !task.skipped);
  if (taskDateFilter.value === "All") return true;
  const targetDate = taskDateFilter.value === "Today"
    ? today
    : taskDateFilter.value === "Tomorrow"
      ? tomorrow
      : selectedStudyDate.value;
  return !scheduled || scheduled === targetDate;
};

const allDateFilteredTasks = computed(() => tasks.value.filter(taskMatchesCurrentDateFilter));
const dateFilteredTaskListCounts = computed(() => {
  const counts = new Map();
  for (const task of allDateFilteredTasks.value) {
    const listId = getTaskListIdForTask(task);
    if (listId == null) continue;
    const key = String(listId);
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return counts;
});
const dateFilteredTaskListCount = (listId) => {
  return dateFilteredTaskListCounts.value.get(String(listId)) || 0;
};

const activeListTasks = computed(() =>
  tasks.value.filter((task) => taskBelongsToList(task, activeTaskListId.value)),
);

const dateFilteredTasks = computed(() => activeListTasks.value.filter(taskMatchesCurrentDateFilter));

const getTaskListPosition = (task) => {
  const index = activeListTasks.value.findIndex((listTask) => listTask.id === task.id);
  return String(index + 1).padStart(2, "0");
};

const filteredTasks = computed(() => {
  let result = dateFilteredTasks.value;
  if (taskFilter.value === "Pending") result = result.filter((task) => !task.completed && !task.skipped);
  else if (taskFilter.value === "Completed") result = result.filter((task) => task.completed);
  else if (taskFilter.value === "Skipped") result = result.filter((task) => task.skipped);
  else if (taskFilter.value === "Overdue") {
    const today = getTodayDateKey();
    result = result.filter((task) => task.due_date && task.due_date < today && !task.completed && !task.skipped);
  }
  else if (taskFilter.value === "High priority") result = result.filter((task) => task.priority === "high");
  else if (taskFilter.value === "Recurring") result = result.filter((task) => Boolean(task.series_id));

  return result;
});

const taskCounts = computed(() => {
  const total = dateFilteredTasks.value.length;
  const pending = dateFilteredTasks.value.filter((t) => !t.completed && !t.skipped).length;
  const completed = dateFilteredTasks.value.filter((t) => t.completed).length;
  const skipped = dateFilteredTasks.value.filter((t) => t.skipped).length;
  return { total, pending, completed, skipped };
});
const taskCompletionPercent = computed(() =>
  taskCounts.value.total
    ? Math.round((taskCounts.value.completed / taskCounts.value.total) * 100)
    : 0,
);
const selectTaskList = (listId) => {
  activeTaskListId.value = listId;
  taskFilter.value = "All";
  taskFilterMenuOpen.value = false;
  saveTaskLists();
};

const taskListWheelAnimations = new WeakMap();
const handleTaskListSwitcherWheel = (event) => {
  const scroller = event.currentTarget;
  const maxScrollLeft = scroller.scrollWidth - scroller.clientWidth;
  if (maxScrollLeft <= 0) return;

  const wheelDelta = event.deltaX || event.deltaY;
  if (!wheelDelta) return;

  const deltaScale = event.deltaMode === WheelEvent.DOM_DELTA_LINE
    ? 16
    : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
      ? scroller.clientWidth
      : 1;
  const animation = taskListWheelAnimations.get(scroller) || {
    target: scroller.scrollLeft,
    frame: 0,
    lastFrameTime: 0,
  };
  const nextScrollLeft = Math.max(
    0,
    Math.min(maxScrollLeft, animation.target + wheelDelta * deltaScale),
  );
  if (nextScrollLeft === animation.target) return;

  event.preventDefault();
  animation.target = nextScrollLeft;
  taskListWheelAnimations.set(scroller, animation);

  if (!animation.frame) {
    const animateScroll = (time) => {
      if (!scroller.isConnected) {
        taskListWheelAnimations.delete(scroller);
        return;
      }

      const distance = animation.target - scroller.scrollLeft;
      if (Math.abs(distance) < 0.5) {
        scroller.scrollLeft = animation.target;
        taskListWheelAnimations.delete(scroller);
        return;
      }

      const elapsed = Math.max(1, time - animation.lastFrameTime);
      const easedStep = 1 - Math.exp(-elapsed / 90);
      animation.lastFrameTime = time;
      scroller.scrollLeft += distance * easedStep;
      animation.frame = requestAnimationFrame(animateScroll);
    };

    animation.lastFrameTime = performance.now();
    animation.frame = requestAnimationFrame(animateScroll);
  }
};

const selectTaskFilter = (filter) => {
  taskFilter.value = filter;
  taskFilterMenuOpen.value = false;
};

const getTaskListName = (listId) =>
  taskLists.value.find((list) => list.id === listId)?.name || "Unsorted";

const getTaskRemainingSeconds = (task) => {
  if (task.completed) return 0;
  if (activeFocusTask.value && activeFocusTask.value.id === task.id) {
    return Math.max(0, Number(timerSecondsRemaining.value) || 0);
  }
  const savedRemaining = taskTimers.value[task.id]?.remaining;
  return typeof savedRemaining === "number"
    ? Math.max(0, savedRemaining)
    : Math.max(0, (Number(task.duration_minutes) || 45) * 60);
};
const getTaskProgressPercent = (task) => {
  if (task.completed) return 100;
  const total = Math.max(1, (Number(task.duration_minutes) || 45) * 60);
  return Math.min(100, Math.max(0, ((total - getTaskRemainingSeconds(task)) / total) * 100));
};

const startTaskListDrag = (event, listId) => {
  draggedTaskListId.value = listId;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", String(listId));
};

const reorderTaskList = (event, targetListId) => {
  const sourceListId = draggedTaskListId.value;
  if (!sourceListId || sourceListId === targetListId) return;
  event.preventDefault();

  const sourceIndex = taskLists.value.findIndex((list) => list.id === sourceListId);
  const targetIndex = taskLists.value.findIndex((list) => list.id === targetListId);
  if (sourceIndex === -1 || targetIndex === -1) return;

  const targetBounds = event.currentTarget.getBoundingClientRect();
  let insertIndex = targetIndex + (event.clientX >= targetBounds.left + targetBounds.width / 2 ? 1 : 0);
  const [draggedList] = taskLists.value.splice(sourceIndex, 1);
  if (sourceIndex < insertIndex) insertIndex -= 1;
  taskLists.value.splice(insertIndex, 0, draggedList);
};

const finishTaskListDrag = () => {
  if (!draggedTaskListId.value) return;
  draggedTaskListId.value = null;
  saveTaskLists();
};

const openCreateTaskListModal = () => {
  editingTaskListId.value = null;
  newTaskListName.value = "";
  newTaskListColor.value = taskListColors[0];
  newTaskListIcon.value = taskListIcons[0];
  showCreateTaskListModal.value = true;
};

const openEditTaskListModal = (list) => {
  openTaskListMenu.value = null;
  editingTaskListId.value = list.id;
  newTaskListName.value = list.name;
  newTaskListColor.value = list.color;
  newTaskListIcon.value = list.icon;
  showCreateTaskListModal.value = true;
};

const toggleTaskListMenu = (event, list) => {
  if (openTaskListMenu.value?.listId === list.id) {
    openTaskListMenu.value = null;
    return;
  }

  const bounds = event.currentTarget.getBoundingClientRect();
  const menuWidth = 136;
  const menuHeight = 86;
  const left = Math.min(
    Math.max(8, bounds.right - menuWidth),
    window.innerWidth - menuWidth - 8,
  );
  const top =
    bounds.bottom + menuHeight <= window.innerHeight - 8
      ? bounds.bottom + 4
      : Math.max(8, bounds.top - menuHeight - 4);
  openTaskListMenu.value = { listId: list.id, top, left };
};

const closeTaskListMenuOnOutsideClick = (event) => {
  if (
    isTaskCalendarOpen.value &&
    !taskCalendarAnchorRef.value?.contains(event.target) &&
    !taskCalendarPanelRef.value?.contains(event.target)
  ) {
    isTaskCalendarOpen.value = false;
  }
  if (!event.target.closest(".task-more-filter-menu")) {
    taskFilterMenuOpen.value = false;
  }
  if (!event.target.closest(".task-list-actions-menu, .task-list-actions-dropdown")) {
    openTaskListMenu.value = null;
  }
};

const createTaskList = () => {
  const name = newTaskListName.value.trim();
  if (!name) return;

  if (editingTaskListId.value) {
    const list = taskLists.value.find((candidate) => candidate.id === editingTaskListId.value);
    if (!list) return;
    list.name = name;
    list.color = newTaskListColor.value;
    list.icon = newTaskListIcon.value;
    editingTaskListId.value = null;
    showCreateTaskListModal.value = false;
    saveTaskLists();
    return;
  }

  const list = {
    id: `list-${Date.now()}`,
    name,
    color: newTaskListColor.value,
    icon: newTaskListIcon.value,
  };
  taskLists.value.push(list);
  activeTaskListId.value = list.id;
  taskFilter.value = "All";
  newTaskListName.value = "";
  newTaskListColor.value = taskListColors[0];
  newTaskListIcon.value = taskListIcons[0];
  showCreateTaskListModal.value = false;
  saveTaskLists();
};

const confirmDeleteTaskList = async () => {
  const list = taskListToDelete.value;
  if (!list || taskLists.value.length <= 1) return;

  const removedTasks = tasks.value.filter((task) => task.task_list_id === list.id);
  const removedTaskIds = new Set(removedTasks.map((task) => task.id));
  removedTaskIds.forEach((taskId) => {
    if (!deletedTaskIds.value.includes(taskId)) deletedTaskIds.value.push(taskId);
    delete taskListByTaskId.value[taskId];
    delete taskTimers.value[taskId];
  });
  tasks.value = tasks.value.filter((task) => task.task_list_id !== list.id);

  taskLists.value = taskLists.value.filter((candidate) => candidate.id !== list.id);
  const destination = taskLists.value.find((candidate) => candidate.id === activeTaskListId.value) || taskLists.value[0];
  if (activeTaskListId.value === list.id) {
    activeTaskListId.value = destination?.id || null;
    taskFilter.value = "All";
  }

  taskListToDelete.value = null;

  if (removedTaskIds.has(activeFocusTask.value?.id)) {
    if (isTimerRunning.value) {
      clearInterval(timerInterval);
      isTimerRunning.value = false;
    }

    const nextTask = tasks.value.find((task) => !task.completed) || tasks.value[0];
    if (nextTask) {
      selectTaskForTimer(nextTask);
    } else {
      clearActiveFocusTask();
    }
  }

  saveTaskLists();
  saveTimersToStorage();

  // A recurring series can have many visible occurrences. Deleting it once
  // removes its pending occurrences; issuing one request per occurrence makes
  // the remaining requests fail with 404 after the first succeeds.
  const deleteTargets = new Map();
  for (const task of removedTasks) {
    const key = task.series_id ? `series-${task.series_id}` : `task-${task.id}`;
    if (!deleteTargets.has(key)) deleteTargets.set(key, task);
  }
  const deleteResults = await Promise.allSettled(
    [...deleteTargets.values()].map((task) => axios.delete(apiUrl(`/tasks/${task.id}`), {
      data: { scope: task.series_id ? "series" : "this" },
    })),
  );
  const failures = deleteResults.filter((result) => result.status === "rejected");
  if (failures.length) {
    console.error(
      `Deleted the task list locally, but ${failures.length} task(s) could not be removed from the server:`,
      failures.map((failure) => failure.reason),
    );
  }
};

// Format minutes to hh:mm:ss string
const formatTimeDuration = (minutes) => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:00`;
};

// API calls for tasks and stats
const fetchTasks = async () => {
  try {
    const res = await axios.get(apiUrl("/tasks"), {
      // Keep a complete server snapshot locally. Date and status filtering is
      // applied by computed properties; stale server rows must not be restored
      // as if they were offline-created tasks.
      params: { date: selectedStudyDate.value, view: "all" },
    });
    const savedTasksById = new Map(tasks.value.map((task) => [String(task.id), task]));
    const visibleServerTasks = (res.data || []).filter(
      (task) => !deletedTaskIds.value.some((id) => String(id) === String(task.id)),
    );
    const serverTaskIds = new Set(visibleServerTasks.map((task) => String(task.id)));
    const serverTasks = visibleServerTasks.map((task) => {
      const savedTask = savedTasksById.get(String(task.id));
      // The API is authoritative after a task is moved. Local mappings are only
      // a compatibility fallback for older task records without a list id.
      const listId = task.task_list_id || savedTask?.task_list_id || taskListByTaskId.value[task.id] || taskLists.value[0]?.id || null;
      if (listId) taskListByTaskId.value[task.id] = listId;
      return { ...savedTask, ...task, task_list_id: listId };
    });
    const localOnlyTasks = tasks.value.filter((task) => {
      if (serverTaskIds.has(String(task.id))) return false;
      if (deletedTaskIds.value.some((id) => String(id) === String(task.id))) return false;
      return task.local_only === true;
    });
    tasks.value = [...serverTasks, ...localOnlyTasks];
    saveTaskLists();
  } catch (e) {
    console.log("Using local tasks state");
  }
};

const getTodayDateKey = () => {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
};

const formatTaskCalendarDate = (dateKey) => {
  if (!dateKey) return "";
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

const fetchStats = async () => {
  try {
    // The access token identifies the user on the server - no user_id is sent.
    const res = await axios.get(apiUrl("/stats"));
    if (res.data) {
      if (typeof res.data.streak_days === "number") stats.value.streak_days = res.data.streak_days;
      if (typeof res.data.focus_minutes_today === "number") stats.value.focus_minutes_today = res.data.focus_minutes_today;
      if (typeof res.data.focus_seconds_today === "number") stats.value.focus_seconds_today = res.data.focus_seconds_today;
      if (typeof res.data.stats_date === "string") stats.value.stats_date = res.data.stats_date;
      if (typeof res.data.focus_minutes_week === "number") stats.value.focus_minutes_week = res.data.focus_minutes_week;
      if (typeof res.data.focus_seconds_week === "number") stats.value.focus_seconds_week = res.data.focus_seconds_week;
    }
  } catch (e) {
    const saved = localStorage.getItem(statsStorageKey);
    if (saved) {
      try {
        const savedStats = JSON.parse(saved);
        if (savedStats.stats_date !== getTodayDateKey()) {
          savedStats.focus_minutes_today = 0;
          savedStats.focus_seconds_today = 0;
        } else if (typeof savedStats.focus_seconds_today !== "number") {
          savedStats.focus_seconds_today = (Number(savedStats.focus_minutes_today) || 0) * 60;
        }
        if (typeof savedStats.focus_seconds_week !== "number") {
          savedStats.focus_seconds_week = (Number(savedStats.focus_minutes_week) || 0) * 60;
        }
        savedStats.stats_date = getTodayDateKey();
        stats.value = savedStats;
      } catch (err) {}
    }
  }
};

const recordFocusSeconds = async (seconds) => {
  const secondCount = Math.max(0, Math.floor(Number(seconds) || 0));
  if (secondCount <= 0) return;
  const minNum = Math.round(secondCount / 60);
  stats.value.focus_seconds_today += secondCount;
  stats.value.focus_minutes_today = Math.round(stats.value.focus_seconds_today / 60);
  stats.value.stats_date = getTodayDateKey();
  stats.value.focus_seconds_week += secondCount;
  stats.value.focus_minutes_week = Math.round(stats.value.focus_seconds_week / 60);
  localStorage.setItem(statsStorageKey, JSON.stringify(stats.value));

  try {
    await axios.post(apiUrl("/stats/record"), {
      minutes: minNum,
      seconds: secondCount,
    });
  } catch (e) {}
};

const recordUnrecordedFocusTime = () => {
  const unrecordedSeconds = Math.max(
    0,
    currentFocusSeconds.value - currentFocusRecordedSeconds.value,
  );
  if (unrecordedSeconds <= 0) return;

  recordFocusSeconds(unrecordedSeconds);
  currentFocusRecordedSeconds.value = currentFocusSeconds.value;
};

const toggleTask = async (task) => {
  if (task.skipped) {
    try {
      await axios.post(apiUrl(`/tasks/${task.id}/skip`), { skipped: false });
      task.skipped = false;
      saveTaskLists();
    } catch (error) {
      console.error("Unable to reopen skipped occurrence:", error);
    }
    return;
  }
  task.completed = !task.completed;
  if (task.completed) {
    playTaskCompletionTick();
    const now = new Date();
    task.completed_time = `Today, ${now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;
    const savedTimer = taskTimers.value[task.id] || {};
    const taskDuration = (Number(task.duration_minutes) || 45) * 60;
    if (activeFocusTask.value?.id === task.id && isTimerRunning.value) {
      syncTimerFromClock();
      flushTimerSession();
      clearInterval(timerInterval);
      timerInterval = null;
      isTimerRunning.value = false;
      timerDeadlineAt = null;
      timerLastUpdatedAt = null;
    }
    const remainingBeforeCompletion =
      activeFocusTask.value?.id === task.id
        ? timerSecondsRemaining.value
        : Number(savedTimer.remaining) > 0
          ? savedTimer.remaining
          : Number(savedTimer.resumeRemaining) > 0
            ? savedTimer.resumeRemaining
            : Number(savedTimer.total) > 0
              ? Math.min(savedTimer.total, taskDuration)
              : taskDuration;
    const totalSeconds =
      activeFocusTask.value?.id === task.id
        ? totalTimerDuration.value
        : Number(savedTimer.total) || taskDuration;

    taskTimers.value[task.id] = {
      ...savedTimer,
      remaining: 0,
      total: totalSeconds,
      resumeRemaining: remainingBeforeCompletion,
      studiedSeconds: Math.max(0, totalSeconds - remainingBeforeCompletion),
    };

    if (activeFocusTask.value && activeFocusTask.value.id === task.id) {
      if (isTimerRunning.value) {
        clearInterval(timerInterval);
        isTimerRunning.value = false;
      }
      recordUnrecordedFocusTime();
      activeFocusTask.value.completed = true;
      activeFocusTask.value.completed_time = task.completed_time;
      timerSecondsRemaining.value = 0;
    }
  } else {
    task.completed_time = null;
    const savedTimer = taskTimers.value[task.id] || {};
    const resumeRemaining = Number(savedTimer.resumeRemaining);
    taskTimers.value[task.id] = {
      ...savedTimer,
      remaining: Number.isFinite(resumeRemaining) && resumeRemaining > 0
        ? resumeRemaining
        : Number(savedTimer.remaining) || (Number(task.duration_minutes) || 45) * 60,
    };
    delete taskTimers.value[task.id].resumeRemaining;
    if (activeFocusTask.value && activeFocusTask.value.id === task.id) {
      activeFocusTask.value.completed = false;
      activeFocusTask.value.completed_time = null;
      totalTimerDuration.value = Number(savedTimer.total) || task.duration_minutes * 60;
      timerSecondsRemaining.value = taskTimers.value[task.id].remaining;
    }
  }
  saveTimersToStorage();
  saveTaskLists();

  try {
    await axios.post(apiUrl(`/tasks/${task.id}/toggle`), {
      completed: task.completed,
    });
  } catch (e) {
    // Local fallback keeps working
  }
};

const addNewTask = async () => {
  if (!newTaskTitle.value.trim()) return;
  taskFormError.value = "";
  const schedule = newTaskSchedule.value;
  const recurrenceRule = buildRecurrenceRule(schedule);
  const taskObj = {
    id: Date.now(),
    task_list_id: schedule.task_list_id || activeTaskListId.value,
    title: newTaskTitle.value.trim(),
    tag: newTaskTag.value,
    duration_minutes: Number(newTaskMinutes.value) || 45,
    scheduled_date: schedule.scheduled_date || null,
    due_date: schedule.due_date || null,
    start_date: schedule.start_date || schedule.scheduled_date || getTodayDateKey(),
    priority: schedule.priority,
    notes: schedule.notes,
    recurrence_rule: recurrenceRule,
    completed: false,
    completed_time: null,
  };

  tasks.value.unshift(taskObj);
  saveTaskLists();

  try {
    const res = await axios.post(apiUrl("/tasks"), {
      title: taskObj.title,
      tag: taskObj.tag,
      duration_minutes: taskObj.duration_minutes,
      task_list_id: taskObj.task_list_id,
      scheduled_date: taskObj.scheduled_date,
      due_date: taskObj.due_date,
      start_date: taskObj.start_date,
      priority: taskObj.priority,
      notes: taskObj.notes,
      recurrence_rule: taskObj.recurrence_rule,
    });
    const localId = taskObj.id;
    Object.assign(taskObj, res.data);
    delete taskListByTaskId.value[localId];
    taskListByTaskId.value[taskObj.id] = taskObj.task_list_id;
    saveTaskLists();
  } catch (error) {
    if (error.response) {
      tasks.value = tasks.value.filter((task) => task.id !== taskObj.id);
      saveTaskLists();
      taskFormError.value = error.response.data?.error || "Unable to save this task.";
      return;
    }
    taskObj.local_only = true;
    saveTaskLists();
  }

  newTaskTitle.value = "";
  if (taskObj.scheduled_date) {
    selectedStudyDate.value = taskObj.scheduled_date;
    taskDateFilter.value = "Date";
    await fetchTasks();
  }
  showAddTaskModal.value = false;
  if (!hasActiveFocusTask.value && (!taskObj.scheduled_date || taskObj.scheduled_date === getTodayDateKey())) {
    selectTaskForTimer(taskObj);
  }
};

// Edit Task Modal state & functions
const showEditTaskModal = ref(false);
const editingTaskId = ref(null);
const editTaskTitle = ref("");
const editTaskTag = ref("Study");
const editTaskMinutes = ref(45);

const openEditTask = (task) => {
  editingTaskId.value = task.id;
  editTaskTitle.value = task.title;
  editTaskTag.value = task.tag || "Study";
  editTaskMinutes.value = task.duration_minutes || 45;
  editTaskScope.value = task.series_id ? "this" : "this";
  taskFormError.value = "";
  editTaskSchedule.value = {
    task_list_id: task.task_list_id || activeTaskListId.value,
    scheduled_date: task.scheduled_date || "",
    due_date: task.due_date || "",
    start_date: task.series_start_date || task.start_date || task.scheduled_date || getTodayDateKey(),
    priority: task.priority || "medium",
    notes: task.notes || "",
    recurrence: { ...makeDefaultRecurrence(task.scheduled_date || getTodayDateKey()), ...(task.recurrence_rule || {}) },
  };
  showEditTaskModal.value = true;
};

const saveEditedTask = async () => {
  if (!editTaskTitle.value.trim() || !editingTaskId.value) return;
  const task = tasks.value.find((t) => t.id === editingTaskId.value);
  if (task) {
    const schedule = editTaskSchedule.value;
    const seriesId = task.series_id || undefined;
    const payload = {
      scope: seriesId ? editTaskScope.value : "this",
      title: editTaskTitle.value.trim(),
      tag: editTaskTag.value.trim() || "Study",
      duration_minutes: Number(editTaskMinutes.value) || 45,
      task_list_id: schedule.task_list_id,
      scheduled_date: schedule.scheduled_date || null,
      due_date: schedule.due_date || null,
      start_date: schedule.start_date,
      priority: schedule.priority,
      notes: schedule.notes,
      recurrence_rule: buildRecurrenceRule(editTaskSchedule.value),
    };

    try {
      const res = await axios.put(apiUrl(`/tasks/${task.id}`), payload);
      if (payload.scope === "this" && !res.data?.series_id) Object.assign(task, res.data);
      else await fetchTasks();
    } catch (error) {
      if (error.response?.status === 404) {
        tasks.value = tasks.value.filter((item) => String(item.id) !== String(task.id));
        if (!deletedTaskIds.value.some((id) => String(id) === String(task.id))) {
          deletedTaskIds.value.push(task.id);
        }
        saveTaskLists();
        await fetchTasks();
        taskFormError.value = "This task was removed elsewhere. The task list has been refreshed.";
      } else {
        taskFormError.value = error.response?.data?.error
          || (error.response ? `Unable to update this task (HTTP ${error.response.status}).` : "Unable to reach the server. Check your connection and try again.");
      }
      return;
    }

    // If active in timer, update timer title too
    if (activeFocusTask.value && activeFocusTask.value.id === task.id) {
      activeFocusTask.value.title = payload.title;
      activeFocusTask.value.tag = payload.tag;
      activeFocusTask.value.durationMinutes = payload.duration_minutes;
      // If timer is not running, adjust total & remaining
      if (!isTimerRunning.value) {
        totalTimerDuration.value = task.duration_minutes * 60;
        timerSecondsRemaining.value = task.duration_minutes * 60;
      }
    }
    saveTaskLists();
    saveTimersToStorage();
  }
  showEditTaskModal.value = false;
};

const deleteTask = async (task) => {
  taskBeingDeleted.value = task;
  taskDeleteScope.value = task.series_id ? "series" : "this";
  showDeleteTaskModal.value = true;
};

const confirmDeleteTask = async () => {
  const task = taskBeingDeleted.value;
  if (!task) return;
  taskFormError.value = "";
  let taskWasAlreadyRemoved = false;
  try {
    await axios.delete(apiUrl(`/tasks/${task.id}`), {
      data: { scope: task.series_id ? taskDeleteScope.value : "this" },
    });
  } catch (error) {
    if (error.response?.status === 404) {
      taskWasAlreadyRemoved = true;
    } else {
      taskFormError.value = error.response?.data?.error
        || (error.response ? `Unable to remove this task (HTTP ${error.response.status}).` : "Unable to reach the server. Check your connection and try again.");
      return;
    }
  }

  if (taskWasAlreadyRemoved) {
    tasks.value = tasks.value.filter((item) => String(item.id) !== String(task.id));
    if (!deletedTaskIds.value.some((id) => String(id) === String(task.id))) {
      deletedTaskIds.value.push(task.id);
    }
    await fetchTasks();
  } else if (task.series_id && taskDeleteScope.value === "this") {
    task.skipped = true;
  } else if (task.series_id) {
    await fetchTasks();
  } else {
    tasks.value = tasks.value.filter((item) => String(item.id) !== String(task.id));
    delete taskListByTaskId.value[task.id];
    delete taskTimers.value[task.id];
    if (!deletedTaskIds.value.some((id) => String(id) === String(task.id))) {
      deletedTaskIds.value.push(task.id);
    }
  }

  if (activeFocusTask.value?.id === task.id) {
    stopRunningTimer();
    const nextTask = tasks.value.find((item) => item.id !== task.id && !item.completed && !item.skipped);
    if (nextTask) selectTaskForTimer(nextTask);
    else clearActiveFocusTask();
  }

  saveTimersToStorage();
  saveTaskLists();
  showDeleteTaskModal.value = false;
  taskBeingDeleted.value = null;
};

// Center Focus Timer with per-task state & localStorage preservation
const activeFocusTask = ref({
  ...(savedTaskListState?.activeFocusTask || {
    id: 1,
    title: "Maths Revision - Chapter 5",
    tag: "Study",
    durationMinutes: 85,
  }),
});

// Map of task id -> { remainingSeconds, totalSeconds }
const taskTimers = ref(
  savedTaskListState?.taskTimers && typeof savedTaskListState.taskTimers === "object"
    ? savedTaskListState.taskTimers
    : {},
);

// Focus history is populated from saved sessions, not placeholder records.
const focusSessions = ref([]);

const timerSecondsRemaining = ref(85 * 60);
const isTimerRunning = ref(false);
const totalTimerDuration = ref(85 * 60);
let timerInterval = null;
let timerDeadlineAt = null;
let timerLastUpdatedAt = null;
let timerSessionStartedAt = null;
let timerSessionId = null;
let lastTimerStorageAt = 0;
const isFocusFullscreenOpen = ref(false);
const focusFullscreenRoot = ref(null);
const focusPanelStorageKey = `focusflow_fullscreen_panels_${user.value.id}`;
const focusFullscreenOpenStorageKey = `focusflow_fullscreen_open_${user.value.id}`;
const createDefaultFocusPanels = () => ({
  timer: { open: false, pinned: false, x: null, y: null, z: 1 },
  competitors: { open: false, pinned: false, x: null, y: null, z: 1 },
  video: { open: false, pinned: false, x: null, y: null, z: 1 },
  music: { open: false, pinned: false, x: null, y: null, z: 1 },
});
const loadFocusPanels = () => {
  const savedPanels = localStorage.getItem(focusPanelStorageKey);
  if (!savedPanels) return createDefaultFocusPanels();

  try {
    const parsedPanels = JSON.parse(savedPanels);
    const defaults = createDefaultFocusPanels();
    const restoredPanels = {};
    for (const panelId of Object.keys(defaults)) {
      const savedPanel = parsedPanels?.[panelId];
      if (!savedPanel || typeof savedPanel !== "object") {
        restoredPanels[panelId] = defaults[panelId];
        continue;
      }

      restoredPanels[panelId] = {
        open: typeof savedPanel.open === "boolean" ? savedPanel.open : false,
        pinned: typeof savedPanel.pinned === "boolean" ? savedPanel.pinned : false,
        x: Number.isFinite(savedPanel.x) ? savedPanel.x : null,
        y: Number.isFinite(savedPanel.y) ? savedPanel.y : null,
        z: Number.isFinite(savedPanel.z) ? Math.max(1, savedPanel.z) : 1,
      };
    }
    return restoredPanels;
  } catch (error) {
    console.error("Failed to restore fullscreen panel layout:", error);
    return createDefaultFocusPanels();
  }
};
const focusPanels = ref(loadFocusPanels());
const focusPanelSavedPositions = Object.fromEntries(
  Object.entries(focusPanels.value).map(([panelId, panel]) => [
    panelId,
    { x: panel.x, y: panel.y },
  ]),
);
let focusPanelDrag = null;
let focusPanelZIndex = 1;
const focusVideoInput = ref(null);
const focusBackgroundVideoRef = ref(null);
const focusBackgroundEmbedRef = ref(null);
const isFocusVideoFilePickerOpen = ref(false);
const shouldRestoreFullscreenAfterVideoPicker = ref(false);
const focusVideoStorageKey = `focusflow_focus_video_${user.value.id}`;
const focusVideoUrl = ref(localStorage.getItem(focusVideoStorageKey) || "");
const focusVideoName = ref("");
const focusVideoLink = ref("");
const isFocusVideoPickerOpen = ref(false);
const isFocusVideoPlaying = ref(true);
const focusVideoVolume = ref(65);
const isFocusVideoMuted = ref(false);
const focusVideoError = ref("");
const focusFullscreenError = ref("");
const focusVideoPoster = ref("");
const focusVideoThumbnailFallback = ref(false);
const isFocusVideoIntroActive = ref(false);
let localFocusVideoObjectUrl = null;
let focusVideoQualityTimeout = null;
let focusVideoIntroTimeout = null;
let focusVideoAudioSyncTimeout = null;
let focusVideoAudioSyncAttempts = 0;

const hasActiveFocusTask = computed(() => activeFocusTask.value?.id != null);
const hasResumableCompletedTask = computed(() => {
  if (!activeFocusTask.value?.completed) return false;
  return Number(taskTimers.value[activeFocusTask.value.id]?.resumeRemaining) > 0;
});

const focusPanelPositionStyle = (panelId) => {
  const panel = focusPanels.value[panelId];
  return panel.x === null || panel.y === null
    ? { zIndex: panel.z }
    : {
        left: `${panel.x}px`,
        right: "auto",
        top: `${panel.y}px`,
        bottom: "auto",
        zIndex: panel.z,
      };
};

const saveFocusPanels = (positionPanelId = null) => {
  if (positionPanelId) {
    const panel = focusPanels.value[positionPanelId];
    focusPanelSavedPositions[positionPanelId] = { x: panel.x, y: panel.y };
  }
  const panelsToSave = Object.fromEntries(
    Object.entries(focusPanels.value).map(([panelId, panel]) => [
      panelId,
      { ...panel, ...focusPanelSavedPositions[panelId] },
    ]),
  );
  localStorage.setItem(focusPanelStorageKey, JSON.stringify(panelsToSave));
};

const updateFocusPanel = (panelId, changes, persist = true) => {
  focusPanels.value = {
    ...focusPanels.value,
    [panelId]: { ...focusPanels.value[panelId], ...changes },
  };
  if (persist) saveFocusPanels();
};

const resolveFocusPanelPosition = (panel, root, element, fallback, margin) => {
  const rect = element.getBoundingClientRect();
  if (Number.isFinite(panel.x) && Number.isFinite(panel.y)) {
    return { x: panel.x, y: panel.y };
  }
  return {
    x: Math.max(margin, Math.min(root.clientWidth - rect.width - margin, fallback.x)),
    y: Math.max(margin, Math.min(root.clientHeight - rect.height - margin, fallback.y)),
  };
};

const raiseFocusPanel = (panelId) => {
  focusPanelZIndex += 1;
  updateFocusPanel(panelId, { z: focusPanelZIndex });
};

const openFocusPanel = async (panelId) => {
  const panel = focusPanels.value[panelId];
  updateFocusPanel(panelId, { open: true });
  raiseFocusPanel(panelId);

  await nextTick();
  const root = focusFullscreenRoot.value;
  const element = root?.querySelector(`[data-focus-panel="${panelId}"]`);
  if (!root || !element) return;

  const panelRect = element.getBoundingClientRect();
  const margin = 20;
  const positions = {
    timer: { x: margin, y: margin },
    competitors: { x: root.clientWidth - panelRect.width - margin, y: margin },
    video: { x: margin, y: root.clientHeight - panelRect.height - margin - 76 },
    music: { x: root.clientWidth - panelRect.width - margin, y: root.clientHeight - panelRect.height - margin },
  };
  const position = positions[panelId];
  const hadSavedPosition = Number.isFinite(panel.x) && Number.isFinite(panel.y);
  const resolvedPosition = resolveFocusPanelPosition(panel, root, element, position, margin);
  updateFocusPanel(panelId, resolvedPosition, false);
  if (!hadSavedPosition) saveFocusPanels(panelId);
};

const closeFocusPanel = (panelId) => {
  updateFocusPanel(panelId, { open: false });
  if (panelId === "video") isFocusVideoPickerOpen.value = false;
};

const toggleFocusPanelPin = (panelId) => {
  const panel = focusPanels.value[panelId];
  updateFocusPanel(panelId, { pinned: !panel.pinned });
};

const startFocusPanelDrag = (event, panelId) => {
  const dragHandle = event.target.closest(".focus-panel-drag-handle");
  if (
    event.button !== 0 ||
    focusPanels.value[panelId].pinned ||
    (["video", "music"].includes(panelId) && !dragHandle) ||
    (
      event.target.closest("button, input, select, textarea, a, [contenteditable='true'], .focus-video-picker") &&
      !dragHandle
    )
  ) return;
  event.preventDefault();
  const root = focusFullscreenRoot.value;
  const element = event.currentTarget;
  if (!root || !element) return;

  const rootRect = root.getBoundingClientRect();
  const panelRect = element.getBoundingClientRect();
  const panel = focusPanels.value[panelId];
  const x = panel.x ?? panelRect.left - rootRect.left;
  const y = panel.y ?? panelRect.top - rootRect.top;
  focusPanelDrag = {
    panelId,
    pointerId: event.pointerId,
    originX: event.clientX,
    originY: event.clientY,
    x,
    y,
    width: panelRect.width,
    height: panelRect.height,
    rootWidth: root.clientWidth,
    rootHeight: root.clientHeight,
  };
  event.currentTarget.setPointerCapture(event.pointerId);
  raiseFocusPanel(panelId);
  updateFocusPanel(panelId, { x, y });
};

const moveFocusPanel = (event, panelId) => {
  if (!focusPanelDrag || focusPanelDrag.panelId !== panelId || focusPanelDrag.pointerId !== event.pointerId) return;
  const drag = focusPanelDrag;
  const root = focusFullscreenRoot.value;
  const element = event.currentTarget;
  if (!root || !element) return;
  const panelRect = element.getBoundingClientRect();
  const margin = 8;
  const maxX = Math.max(margin, root.clientWidth - panelRect.width - margin);
  const maxY = Math.max(margin, root.clientHeight - panelRect.height - margin);
  updateFocusPanel(panelId, {
    x: Math.max(margin, Math.min(maxX, drag.x + event.clientX - drag.originX)),
    y: Math.max(margin, Math.min(maxY, drag.y + event.clientY - drag.originY)),
  }, false);
};

const finishFocusPanelDrag = (event, panelId) => {
  if (focusPanelDrag?.panelId === panelId && focusPanelDrag.pointerId === event.pointerId) {
    focusPanelDrag = null;
    saveFocusPanels(panelId);
  }
};

const clearActiveFocusTask = () => {
  clearInterval(timerInterval);
  timerInterval = null;
  isTimerRunning.value = false;
  stopGracePeriod();
  activeFocusTask.value = {
    id: null,
    title: "",
    tag: "",
    durationMinutes: 45,
    completed: false,
    completed_time: null,
  };
  totalTimerDuration.value = 45 * 60;
  timerSecondsRemaining.value = totalTimerDuration.value;
  saveTimersToStorage();
};

// Session duration formatter for Recent Focus and Best Focus
const formatSessionDuration = (session) => {
  if (!session) return "0 min";
  const sec = typeof session.durationSec === "number" ? session.durationSec : ((session.durationMin || 0) * 60);
  if (sec < 60) {
    return `${sec}s`;
  }
  const hrs = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  const remSecs = sec % 60;
  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  return remSecs > 0 ? `${mins}m ${remSecs}s` : `${mins} min`;
};

// Total Study Time (This Week):
// combines recorded weekly study minutes + current continuous study seconds
const totalStudySecondsThisWeek = computed(() => {
  const baseSecs = Number(stats.value.focus_seconds_week) || (Number(stats.value.focus_minutes_week) || 0) * 60;
  return baseSecs + unrecordedCurrentFocusSeconds.value;
});

const totalStudySecondsToday = computed(() =>
  (Number(stats.value.focus_seconds_today) || 0) + unrecordedCurrentFocusSeconds.value
);

// Formats total study time into clean readable string
const formatTotalStudyTime = (totalSeconds) => {
  const sec = Number(totalSeconds) || 0;
  const hrs = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  const remSec = sec % 60;
  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  if (mins > 0) {
    return `${mins}m ${remSec}s`;
  }
  return `${remSec}s`;
};

// Previous best session from history
const previousBestFromHistory = computed(() => {
  if (!focusSessions.value.length) return null;
  return [...focusSessions.value].sort((a, b) => {
    const aSec = typeof a.durationSec === "number" ? a.durationSec : ((a.durationMin || 0) * 60);
    const bSec = typeof b.durationSec === "number" ? b.durationSec : ((b.durationMin || 0) * 60);
    return bSec - aSec;
  })[0];
});

// Best focus calculation: dynamically updates with Current Focus if Current Focus is greater than Best Focus!
const bestFocusSession = computed(() => {
  const prevBest = previousBestFromHistory.value;
  const prevBestSecs = prevBest
    ? (typeof prevBest.durationSec === "number" ? prevBest.durationSec : ((prevBest.durationMin || 0) * 60))
    : 0;

  // If current focus has exceeded previous best, current focus is the new best record!
  if (currentFocusSeconds.value > prevBestSecs && currentFocusSeconds.value > 0) {
    return {
      id: "live-record",
      title: activeFocusTask.value?.title || "Current Flow",
      durationSec: currentFocusSeconds.value,
      durationMin: Math.max(1, Math.round(currentFocusSeconds.value / 60)),
      isNewRecord: true,
    };
  }

  return prevBest;
});

// Dynamic Next Task calculation: the first pending task other than the currently active one
const nextPendingTask = computed(() => {
  return tasks.value.find((t) => !t.completed && t.id !== activeFocusTask.value.id) || null;
});

// Timer formatting helper
const timerFormatted = computed(() => {
  const hrs = Math.floor(timerSecondsRemaining.value / 3600);
  const mins = Math.floor((timerSecondsRemaining.value % 3600) / 60);
  const secs = timerSecondsRemaining.value % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
});

const focusVideoDisplayName = computed(() => {
  if (focusVideoName.value) return focusVideoName.value;
  if (!focusVideoUrl.value) return "No background video selected";
  try {
    const url = new URL(focusVideoUrl.value);
    if (["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"].includes(url.hostname)) {
      return "YouTube video";
    }
    if (url.hostname === "vimeo.com" || url.hostname === "www.vimeo.com" || url.hostname === "player.vimeo.com") {
      return "Vimeo video";
    }
    return url.pathname.split("/").filter(Boolean).pop() || "Video from link";
  } catch {
    return "Video from link";
  }
});

const focusVideoEmbedUrl = computed(() => {
  if (!focusVideoUrl.value || focusVideoUrl.value.startsWith("blob:")) return "";
  let url;
  try {
    url = new URL(focusVideoUrl.value);
  } catch {
    return "";
  }

  const hostname = url.hostname.toLowerCase();
  const youtubeHosts = ["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"];
  if (youtubeHosts.includes(hostname)) {
    const videoId = hostname.endsWith("youtu.be")
      ? url.pathname.split("/").filter(Boolean)[0]
      : url.searchParams.get("v") ||
        url.pathname.match(/^\/(?:embed|shorts|live)\/([^/?]+)/)?.[1];
    if (!videoId || !/^[\w-]{11}$/.test(videoId)) return "";
    const params = new URLSearchParams({
      autoplay: "1",
      mute: "0",
      loop: "1",
      playlist: videoId,
      controls: "0",
      disablekb: "1",
      fs: "0",
      modestbranding: "1",
      iv_load_policy: "3",
      rel: "0",
      playsinline: "1",
      enablejsapi: "1",
      vq: "highres",
      origin: window.location.origin,
    });
    return `https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`;
  }

  if (["vimeo.com", "www.vimeo.com", "player.vimeo.com"].includes(hostname)) {
    const pathSegments = url.pathname.split("/").filter(Boolean);
    const videoId = pathSegments.find((segment) => /^\d+$/.test(segment));
    if (!videoId) return "";
    return `https://player.vimeo.com/video/${videoId}?autoplay=1&muted=0&loop=1&background=1&quality=4k`;
  }

  return "";
});

const focusVideoThumbnailUrl = computed(() => {
  if (focusVideoPoster.value) return focusVideoPoster.value;
  if (!focusVideoUrl.value) return "";

  try {
    const url = new URL(focusVideoUrl.value);
    const hostname = url.hostname.toLowerCase();
    const videoId = hostname.endsWith("youtu.be")
      ? url.pathname.split("/").filter(Boolean)[0]
      : url.searchParams.get("v") ||
        url.pathname.match(/^\/(?:embed|shorts|live)\/([^/?]+)/)?.[1];
    if (
      ["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"].includes(hostname) &&
      videoId &&
      /^[\w-]{11}$/.test(videoId)
    ) {
      const thumbnailSize = focusVideoThumbnailFallback.value ? "hqdefault" : "maxresdefault";
      return `https://img.youtube.com/vi/${videoId}/${thumbnailSize}.jpg`;
    }
  } catch {
    return "";
  }
  return "";
});

const handleFocusVideoThumbnailError = () => {
  focusVideoThumbnailFallback.value = true;
};

const captureFocusVideoPoster = (event) => {
  const video = event.currentTarget;
  applyFocusVideoAudioToNative();
  if (!video.videoWidth || !video.videoHeight) return;
  focusVideoError.value = "";
  isFocusVideoPlaying.value = true;
  try {
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = Math.round(320 * (video.videoHeight / video.videoWidth));
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
    focusVideoPoster.value = canvas.toDataURL("image/jpeg", 0.78);
  } catch {
    focusVideoPoster.value = "";
  }
};

const sendFocusEmbedCommand = (command, args = []) => {
  focusBackgroundEmbedRef.value?.contentWindow?.postMessage(
    JSON.stringify({ event: "command", func: command, args }),
    "*",
  );
};

const requestHighestFocusVideoQuality = () => {
  if (focusVideoQualityTimeout) clearTimeout(focusVideoQualityTimeout);
  focusVideoQualityTimeout = setTimeout(() => {
    if (focusVideoEmbedUrl.value.includes("youtube-nocookie.com")) {
      sendFocusEmbedCommand("setPlaybackQuality", ["highres"]);
    }
    focusVideoQualityTimeout = null;
  }, 1200);
};

const syncFocusVideoEmbedAudio = (retry = false) => {
  if (focusVideoAudioSyncTimeout) {
    clearTimeout(focusVideoAudioSyncTimeout);
    focusVideoAudioSyncTimeout = null;
  }

  if (focusVideoEmbedUrl.value.includes("youtube-nocookie.com")) {
    sendFocusEmbedCommand(isFocusVideoMuted.value ? "mute" : "unMute");
    sendFocusEmbedCommand("setVolume", [isFocusVideoMuted.value ? 0 : focusVideoVolume.value]);
  } else if (focusVideoEmbedUrl.value.includes("player.vimeo.com")) {
    focusBackgroundEmbedRef.value?.contentWindow?.postMessage(
      JSON.stringify({ method: "setMuted", value: isFocusVideoMuted.value }),
      "*",
    );
    focusBackgroundEmbedRef.value?.contentWindow?.postMessage(
      JSON.stringify({ method: "setVolume", value: isFocusVideoMuted.value ? 0 : focusVideoVolume.value / 100 }),
      "*",
    );
  }

  if (retry && focusVideoAudioSyncAttempts < 4) {
    focusVideoAudioSyncAttempts += 1;
    focusVideoAudioSyncTimeout = setTimeout(() => {
      focusVideoAudioSyncTimeout = null;
      syncFocusVideoEmbedAudio(true);
    }, 700);
  } else if (!retry) {
    focusVideoAudioSyncAttempts = 0;
    focusVideoAudioSyncTimeout = setTimeout(() => {
      focusVideoAudioSyncTimeout = null;
      syncFocusVideoEmbedAudio(true);
    }, 350);
  } else {
    focusVideoAudioSyncAttempts = 0;
  }
};

const applyFocusVideoAudioToNative = () => {
  const video = focusBackgroundVideoRef.value;
  if (!video) return;
  video.volume = isFocusVideoMuted.value ? 0 : focusVideoVolume.value / 100;
  video.muted = isFocusVideoMuted.value;
};

const toggleFocusVideoMute = () => {
  isFocusVideoMuted.value = !isFocusVideoMuted.value;
  applyFocusVideoAudioToNative();
  syncFocusVideoEmbedAudio();
};

const setFocusVideoVolume = (event) => {
  focusVideoVolume.value = Number(event.target.value);
  if (focusVideoVolume.value > 0) isFocusVideoMuted.value = false;
  applyFocusVideoAudioToNative();
  syncFocusVideoEmbedAudio();
};

const finishFocusVideoIntro = () => {
  isFocusVideoIntroActive.value = false;
  if (focusVideoIntroTimeout) {
    clearTimeout(focusVideoIntroTimeout);
    focusVideoIntroTimeout = null;
  }
};

const handleFocusEmbedLoad = () => {
  requestHighestFocusVideoQuality();
  syncFocusVideoEmbedAudio();
  if (!focusVideoEmbedUrl.value.includes("youtube-nocookie.com")) return;

  finishFocusVideoIntro();
  isFocusVideoIntroActive.value = true;
  focusVideoIntroTimeout = setTimeout(finishFocusVideoIntro, 4400);
};

const toggleFocusBackgroundVideo = () => {
  if (!focusVideoUrl.value) return;

  const shouldPlay = !isFocusVideoPlaying.value;
  if (focusVideoEmbedUrl.value) {
    if (focusVideoEmbedUrl.value.includes("youtube-nocookie.com")) {
      sendFocusEmbedCommand(shouldPlay ? "playVideo" : "pauseVideo");
    } else {
      focusBackgroundEmbedRef.value?.contentWindow?.postMessage(
        JSON.stringify({ method: shouldPlay ? "play" : "pause" }),
        "*",
      );
    }
    isFocusVideoPlaying.value = shouldPlay;
    if (shouldPlay && isFocusVideoMuted.value) toggleFocusVideoMute();
    return;
  }

  const video = focusBackgroundVideoRef.value;
  if (!video) return;
  applyFocusVideoAudioToNative();
  if (shouldPlay) {
    video.play().catch((error) => {
      console.error("Could not play the focus background video:", error);
      focusVideoError.value = "The background video could not start. Check the video link and try again.";
    });
  } else {
    video.pause();
  }
};

const openFocusFullscreen = async (requestBrowserFullscreen = true) => {
  focusFullscreenError.value = "";
  focusPanelDrag = null;
  focusPanelZIndex = Math.max(
    1,
    ...Object.values(focusPanels.value).map((panel) => panel.z),
  );
  isFocusFullscreenOpen.value = true;
  localStorage.setItem(focusFullscreenOpenStorageKey, "true");
  await nextTick();

  const root = focusFullscreenRoot.value;
  if (root) {
    const margin = 20;
    for (const [panelId, panel] of Object.entries(focusPanels.value)) {
      if (!panel.open) continue;
      const element = root.querySelector(`[data-focus-panel="${panelId}"]`);
      if (!element) continue;
      const defaultPositions = {
        timer: { x: margin, y: margin },
        competitors: { x: root.clientWidth - element.getBoundingClientRect().width - margin, y: margin },
        video: { x: margin, y: root.clientHeight - element.getBoundingClientRect().height - margin - 76 },
        music: {
          x: root.clientWidth - element.getBoundingClientRect().width - margin,
          y: root.clientHeight - element.getBoundingClientRect().height - margin,
        },
      };
      const resolvedPosition = resolveFocusPanelPosition(
        panel,
        root,
        element,
        defaultPositions[panelId],
        margin,
      );
      updateFocusPanel(panelId, resolvedPosition, false);
      if (!Number.isFinite(panel.x) || !Number.isFinite(panel.y)) saveFocusPanels(panelId);
    }
  }

  if (
    !requestBrowserFullscreen ||
    !focusFullscreenRoot.value?.requestFullscreen ||
    !document.fullscreenEnabled
  ) return;
  try {
    await focusFullscreenRoot.value.requestFullscreen();
  } catch (error) {
    console.error("Could not enter browser fullscreen:", error);
    focusFullscreenError.value = "Immersive mode is open, but browser fullscreen could not be enabled.";
  }
};

const closeFocusFullscreen = async () => {
  isFocusFullscreenOpen.value = false;
  localStorage.setItem(focusFullscreenOpenStorageKey, "false");
  shouldRestoreFullscreenAfterVideoPicker.value = false;
  isFocusVideoFilePickerOpen.value = false;
  isFocusVideoPickerOpen.value = false;
  if (document.fullscreenElement === focusFullscreenRoot.value) {
    try {
      await document.exitFullscreen();
    } catch (error) {
      console.error("Could not exit browser fullscreen:", error);
    }
  }
};

const handleFocusFullscreenChange = () => {
  if (document.fullscreenElement === focusFullscreenRoot.value) {
    shouldRestoreFullscreenAfterVideoPicker.value = false;
    focusFullscreenError.value = "";
    return;
  }
  if (isFocusFullscreenOpen.value && document.fullscreenElement !== focusFullscreenRoot.value) {
    if (isFocusVideoFilePickerOpen.value) return;
    isFocusFullscreenOpen.value = false;
    localStorage.setItem(focusFullscreenOpenStorageKey, "false");
    isFocusVideoPickerOpen.value = false;
  }
};

const handleFocusFullscreenKeydown = (event) => {
  if (event.key === "Escape" && isFocusFullscreenOpen.value) {
    if (isFocusVideoPickerOpen.value) {
      isFocusVideoPickerOpen.value = false;
      return;
    }
    closeFocusFullscreen();
  }
};

const clearLocalFocusVideo = () => {
  if (localFocusVideoObjectUrl) {
    URL.revokeObjectURL(localFocusVideoObjectUrl);
    localFocusVideoObjectUrl = null;
  }
};

const openFocusVideoFilePicker = () => {
  if (!focusVideoInput.value) return;
  shouldRestoreFullscreenAfterVideoPicker.value =
    document.fullscreenElement === focusFullscreenRoot.value;
  isFocusVideoFilePickerOpen.value = true;
  focusVideoInput.value.click();
};

const finishFocusVideoFilePicker = async () => {
  isFocusVideoFilePickerOpen.value = false;
  if (!shouldRestoreFullscreenAfterVideoPicker.value || !isFocusFullscreenOpen.value) {
    shouldRestoreFullscreenAfterVideoPicker.value = false;
    return;
  }

  await restoreFocusBrowserFullscreen();
};

const restoreFocusBrowserFullscreen = async () => {
  if (!isFocusFullscreenOpen.value || document.fullscreenElement) {
    shouldRestoreFullscreenAfterVideoPicker.value = false;
    return;
  }
  const root = focusFullscreenRoot.value;
  if (!root?.requestFullscreen || !document.fullscreenEnabled) {
    focusFullscreenError.value = "The immersive session is open; browser fullscreen is not available.";
    return;
  }
  try {
    await root.requestFullscreen();
    shouldRestoreFullscreenAfterVideoPicker.value = false;
    focusFullscreenError.value = "";
  } catch (error) {
    console.error("Could not restore browser fullscreen after choosing a video:", error);
    focusFullscreenError.value = "The immersive session is still open. Select Return to fullscreen to continue.";
  }
};

const applyFocusVideoLink = () => {
  const link = focusVideoLink.value.trim();
  let parsedUrl;
  try {
    parsedUrl = new URL(link);
  } catch {
    focusVideoError.value = "Enter a valid MP4/WebM, YouTube, or Vimeo URL.";
    return;
  }
  if (!["http:", "https:"].includes(parsedUrl.protocol)) {
    focusVideoError.value = "Video links must use HTTP or HTTPS.";
    return;
  }

  clearLocalFocusVideo();
  focusVideoUrl.value = parsedUrl.href;
  focusVideoName.value = "";
  focusVideoLink.value = parsedUrl.href;
  focusVideoPoster.value = "";
  focusVideoThumbnailFallback.value = false;
  isFocusVideoPlaying.value = true;
  isFocusVideoMuted.value = false;
  focusVideoError.value = "";
  localStorage.setItem(focusVideoStorageKey, parsedUrl.href);
  isFocusVideoPickerOpen.value = false;
};

const handleFocusVideoFileChange = (event) => {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!file) {
    finishFocusVideoFilePicker();
    return;
  }
  if (file.type && !file.type.startsWith("video/")) {
    focusVideoError.value = "Choose a video file to use as the background.";
    finishFocusVideoFilePicker();
    return;
  }

  clearLocalFocusVideo();
  localFocusVideoObjectUrl = URL.createObjectURL(file);
  focusVideoUrl.value = localFocusVideoObjectUrl;
  focusVideoName.value = file.name;
  focusVideoLink.value = "";
  focusVideoPoster.value = "";
  focusVideoThumbnailFallback.value = false;
  isFocusVideoPlaying.value = true;
  isFocusVideoMuted.value = false;
  focusVideoError.value = "";
  localStorage.removeItem(focusVideoStorageKey);
  isFocusVideoPickerOpen.value = false;
  finishFocusVideoFilePicker();
};

const removeFocusVideo = () => {
  clearLocalFocusVideo();
  focusVideoUrl.value = "";
  focusVideoName.value = "";
  focusVideoLink.value = "";
  focusVideoPoster.value = "";
  focusVideoThumbnailFallback.value = false;
  isFocusVideoPlaying.value = false;
  isFocusVideoMuted.value = true;
  focusVideoError.value = "";
  localStorage.removeItem(focusVideoStorageKey);
};

const handleFocusVideoError = () => {
  isFocusVideoPlaying.value = false;
  focusVideoError.value = "This video could not be played. Try a direct MP4/WebM link, a YouTube or Vimeo link, or choose a local file.";
};

// Circle SVG stroke-dash calculations
const circleRadius = 78;
const circumference = 2 * Math.PI * circleRadius;
const timerProgressRatio = computed(() => {
  if (activeFocusTask.value?.completed) return 1;
  if (!totalTimerDuration.value) return 0;
  return Math.max(0, Math.min(1, timerSecondsRemaining.value / totalTimerDuration.value));
});
const strokeDashoffset = computed(() =>
  circumference * (1 - timerProgressRatio.value)
);
const timerDialAnimationKey = ref(0);
const isTimerDialAnimating = ref(false);
let timerDialAnimationTimeout = null;
const replayTimerDialAnimation = () => {
  timerDialAnimationKey.value += 1;
  isTimerDialAnimating.value = true;
  if (timerDialAnimationTimeout) clearTimeout(timerDialAnimationTimeout);
  timerDialAnimationTimeout = setTimeout(() => {
    isTimerDialAnimating.value = false;
    timerDialAnimationTimeout = null;
  }, 850);
};

// Current Focus (In One Go) & 10-Minute Grace Period State
const currentFocusSeconds = ref(0);
const currentFocusRecordedSeconds = ref(0);
const unrecordedCurrentFocusSeconds = computed(() =>
  Math.max(0, currentFocusSeconds.value - currentFocusRecordedSeconds.value)
);
const pausedAtTimestamp = ref(null);
const graceSecondsRemaining = ref(600); // 10 minutes = 600s
let graceTimerInterval = null;

// Formatter for Current Focus time
const formatCurrentFocus = (seconds) => {
  const s = Number(seconds) || 0;
  if (s < 60) {
    return `${s}s`;
  }
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const remSecs = s % 60;
  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  return `${mins}m ${remSecs}s`;
};

const getTaskStudiedSeconds = (taskId) => {
  const savedTimer = taskTimers.value[taskId] || {};
  if (typeof savedTimer.studiedSeconds === "number") return savedTimer.studiedSeconds;

  const total = Number(savedTimer.total);
  const remaining = Number(savedTimer.resumeRemaining);
  return Number.isFinite(total) && Number.isFinite(remaining)
    ? Math.max(0, total - remaining)
    : null;
};

// Formatter for Grace Period countdown (MM:SS)
const formatGraceRemaining = (seconds) => {
  const s = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(s / 60);
  const remSecs = s % 60;
  return `${String(mins).padStart(2, "0")}:${String(remSecs).padStart(2, "0")}`;
};

// Updates Recent Focus with current focus time (when paused, or when grace timer runs out)
const updateRecentFocusWithCurrent = (isFinal = false) => {
  if (currentFocusSeconds.value <= 0) return;
  const now = new Date();
  const timeStr = `Today, ${now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;
  const durSec = currentFocusSeconds.value;
  const durMin = Math.max(1, Math.round(durSec / 60));

  // If the top session was already for this current flow, update it in-place
  if (focusSessions.value.length > 0 && focusSessions.value[0]._isCurrentFlow) {
    focusSessions.value[0].durationSec = durSec;
    focusSessions.value[0].durationMin = durMin;
    focusSessions.value[0].dateStr = timeStr;
    focusSessions.value[0].title = activeFocusTask.value?.title || "Focus Session";
    if (isFinal) {
      delete focusSessions.value[0]._isCurrentFlow;
    }
  } else {
    focusSessions.value.unshift({
      id: Date.now(),
      title: activeFocusTask.value?.title || "Focus Session",
      durationSec: durSec,
      durationMin: durMin,
      dateStr: timeStr,
      _isCurrentFlow: !isFinal,
    });
  }
  saveTimersToStorage();
};

// Start 10-minute grace window when study is paused
const startGracePeriod = () => {
  if (graceTimerInterval) clearInterval(graceTimerInterval);
  if (!pausedAtTimestamp.value) {
    pausedAtTimestamp.value = Date.now();
  }

  const checkGrace = () => {
    if (!pausedAtTimestamp.value) return;
    const elapsed = Math.floor((Date.now() - pausedAtTimestamp.value) / 1000);
    const left = Math.max(0, 600 - elapsed);
    graceSecondsRemaining.value = left;

    if (left <= 0) {
      // 10 minutes exceeded! Grace timer ran out:
      clearInterval(graceTimerInterval);
      graceTimerInterval = null;

      // Finalize Recent Focus with the full unbroken focus achieved!
      updateRecentFocusWithCurrent(true);
      recordUnrecordedFocusTime();

      currentFocusSeconds.value = 0;
      currentFocusRecordedSeconds.value = 0;
      pausedAtTimestamp.value = null;
      graceSecondsRemaining.value = 600;
      saveTimersToStorage();
    }
  };

  checkGrace();
  graceTimerInterval = setInterval(checkGrace, 1000);
};

// Cancel grace window when study resumes
const stopGracePeriod = () => {
  if (graceTimerInterval) {
    clearInterval(graceTimerInterval);
    graceTimerInterval = null;
  }
  pausedAtTimestamp.value = null;
  graceSecondsRemaining.value = 600;
};

// Persist timer state to localStorage
const saveTimersToStorage = () => {
  if (activeFocusTask.value && activeFocusTask.value.id) {
    taskTimers.value[activeFocusTask.value.id] = {
      ...taskTimers.value[activeFocusTask.value.id],
      remaining: timerSecondsRemaining.value,
      total: totalTimerDuration.value,
      running: isTimerRunning.value,
      deadlineAt: isTimerRunning.value ? timerDeadlineAt : null,
      lastUpdatedAt: isTimerRunning.value ? timerLastUpdatedAt : null,
      sessionStartedAt: isTimerRunning.value ? timerSessionStartedAt : null,
      sessionId: isTimerRunning.value ? timerSessionId : null,
    };
  }
  if (isTimerRunning.value) lastTimerStorageAt = Date.now();
  localStorage.setItem(taskTimersStorageKey, JSON.stringify(taskTimers.value));
  localStorage.setItem(activeTaskStorageKey, JSON.stringify(activeFocusTask.value));
  localStorage.setItem(focusSessionsStorageKey, JSON.stringify(focusSessions.value));
  localStorage.setItem(
    currentFocusStorageKey,
    JSON.stringify({
      seconds: currentFocusSeconds.value,
      recordedSeconds: currentFocusRecordedSeconds.value,
      pausedAt: pausedAtTimestamp.value,
    })
  );
  saveTaskLists();
};

const syncTimerFromClock = () => {
  if (!timerDeadlineAt) return false;

  const now = Date.now();
  const elapsedSeconds = Math.floor((now - (timerLastUpdatedAt || now)) / 1000);
  if (elapsedSeconds > 0) {
    const countedSeconds = Math.min(elapsedSeconds, timerSecondsRemaining.value);
    currentFocusSeconds.value += countedSeconds;
    timerLastUpdatedAt += countedSeconds * 1000;
  }

  timerSecondsRemaining.value = Math.max(0, Math.ceil((timerDeadlineAt - now) / 1000));
  return timerSecondsRemaining.value <= 0;
};

const stopTimerInterval = () => {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
};

const flushTimerSession = () => {
  const taskId = activeFocusTask.value?.id;
  if (!taskId || !timerSessionStartedAt || !timerSessionId) return;

  const endedAt = Date.now();
  const durationSeconds = Math.floor((endedAt - timerSessionStartedAt) / 1000);
  const session = {
    client_session_id: timerSessionId,
    started_at: new Date(timerSessionStartedAt).toISOString(),
    ended_at: new Date(endedAt).toISOString(),
    study_date: localDateKey(new Date(timerSessionStartedAt)),
    duration_seconds: durationSeconds,
  };
  timerSessionStartedAt = null;
  timerSessionId = null;
  if (durationSeconds <= 0) return;

  const task = tasks.value.find((item) => item.id === taskId);
  axios.post(apiUrl(`/tasks/${taskId}/sessions`), session)
    .then((response) => {
      if (!response.data?.duplicate && task) {
        task.actual_duration_seconds = (Number(task.actual_duration_seconds) || 0) + durationSeconds;
        saveTaskLists();
      }
    })
    .catch((error) => console.error("Unable to save focus session:", error));
};

const stopRunningTimer = () => {
  const expired = syncTimerFromClock();
  flushTimerSession();
  stopTimerInterval();
  isTimerRunning.value = false;
  timerDeadlineAt = null;
  timerLastUpdatedAt = null;
  if (expired) completeEarly();
  return expired;
};

const runTimerTick = () => {
  if (!isTimerRunning.value) return;

  if (syncTimerFromClock()) {
    stopTimerInterval();
    isTimerRunning.value = false;
    timerDeadlineAt = null;
    timerLastUpdatedAt = null;
    completeEarly();
    return;
  }

  if (Date.now() - lastTimerStorageAt >= 5000) saveTimersToStorage();
};

const handleTimerVisibilityChange = () => {
  if (!isTimerRunning.value) return;
  runTimerTick();
  if (isTimerRunning.value) saveTimersToStorage();
};

const toggleTimer = () => {
  if (!hasActiveFocusTask.value) return;

  if (isTimerRunning.value) {
    // PAUSE STUDY:
    if (stopRunningTimer()) return;
    updateRecentFocusWithCurrent(false);
    startGracePeriod();
    saveTimersToStorage();
  } else {
    // RESUME STUDY:
    stopGracePeriod();
    const now = Date.now();
    timerDeadlineAt = now + timerSecondsRemaining.value * 1000;
    timerLastUpdatedAt = now;
    timerSessionStartedAt = now;
    timerSessionId = globalThis.crypto?.randomUUID?.() || `${user.value.id}-${activeFocusTask.value.id}-${now}-${Math.random().toString(36).slice(2)}`;
    isTimerRunning.value = true;
    lastTimerStorageAt = now;
    timerInterval = setInterval(runTimerTick, 1000);
    saveTimersToStorage();
  }
};

const completeEarly = () => {
  if (!hasActiveFocusTask.value || activeFocusTask.value.completed) return;

  if (isTimerRunning.value) syncTimerFromClock();
  flushTimerSession();
  clearInterval(timerInterval);
  timerInterval = null;
  isTimerRunning.value = false;
  timerDeadlineAt = null;
  timerLastUpdatedAt = null;
  const remainingBeforeCompletion = timerSecondsRemaining.value;

  timerSecondsRemaining.value = 0;

  // Finalize Recent Focus session
  updateRecentFocusWithCurrent(true);

  // Record only focus seconds not already credited by an earlier completed task.
  recordUnrecordedFocusTime();

  const match = tasks.value.find((t) => t.id === activeFocusTask.value.id);
  if (match) {
    const now = new Date();
    const timeStr = `Today, ${now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;
    match.completed = true;
    match.completed_time = timeStr;
    try {
      axios.post(apiUrl(`/tasks/${match.id}/toggle`), {
        completed: true,
      });
    } catch (e) {}
  }

  activeFocusTask.value.completed = true;
  activeFocusTask.value.completed_time = `Today, ${new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`;

  taskTimers.value[activeFocusTask.value.id] = {
    remaining: 0,
    total: totalTimerDuration.value,
    resumeRemaining: remainingBeforeCompletion,
    studiedSeconds: Math.max(0, totalTimerDuration.value - remainingBeforeCompletion),
  };

  // Provide 10-minute grace window so user can proceed to next task in the same flow session
  startGracePeriod();
  saveTimersToStorage();
};

const selectTaskForTimer = (task) => {
  if (task?.skipped) return;
  replayTimerDialAnimation();

  // If a timer is already running for current task, pause and preserve its current time
  if (isTimerRunning.value) {
    stopRunningTimer();
  }

  if (activeFocusTask.value && activeFocusTask.value.id) {
    taskTimers.value[activeFocusTask.value.id] = {
      ...taskTimers.value[activeFocusTask.value.id],
      remaining: timerSecondsRemaining.value,
      total: totalTimerDuration.value,
    };
  }

  const durMinutes = Number(task.duration_minutes) || 45;

  // Switch active task
  activeFocusTask.value = {
    id: task.id,
    title: task.title,
    tag: task.tag,
    durationMinutes: durMinutes,
    completed: Boolean(task.completed),
    completed_time: task.completed_time,
  };

  // Restore preserved timer or initialize full duration
  const preserved = taskTimers.value[task.id];
  const durSecs = durMinutes * 60;
  if (task.completed) {
    totalTimerDuration.value = preserved?.total || durSecs;
    timerSecondsRemaining.value = 0;
    taskTimers.value[task.id] = {
      ...preserved,
      remaining: 0,
      total: totalTimerDuration.value,
    };
  } else if (preserved && typeof preserved.remaining === "number") {
    totalTimerDuration.value = preserved.total || durSecs;
    timerSecondsRemaining.value = preserved.remaining;
  } else {
    totalTimerDuration.value = durSecs;
    timerSecondsRemaining.value = task.completed ? 0 : durSecs;
    taskTimers.value[task.id] = {
      remaining: timerSecondsRemaining.value,
      total: totalTimerDuration.value,
    };
  }

  saveTimersToStorage();
};

const handleTaskCardClick = (task) => {
  if (!task || task.skipped) return;

  if (activeFocusTask.value?.id === task.id) {
    if (isTimerRunning.value) toggleTimer();
    clearActiveFocusTask();
    return;
  }

  selectTaskForTimer(task);
};

const chooseTaskForEmptyTimer = () => {
  const nextTask =
    activeListTasks.value.find((task) => !task.completed) ||
    tasks.value.find((task) => !task.completed) ||
    tasks.value[0];
  if (nextTask) {
    selectTaskForTimer(nextTask);
    return;
  }
  openAddTaskModal();
};

const restartCompletedTask = (targetTask) => {
  const taskId = targetTask?.id || activeFocusTask.value?.id;
  if (!taskId) return;

  const foundTask = tasks.value.find((t) => t.id === taskId);
  const durationMin = Number(foundTask?.duration_minutes || targetTask?.duration_minutes || targetTask?.durationMinutes) || 45;

  if (foundTask) {
    foundTask.completed = false;
    foundTask.completed_time = null;
  }

  activeFocusTask.value = {
    id: taskId,
    title: foundTask?.title || targetTask.title,
    tag: foundTask?.tag || targetTask.tag,
    durationMinutes: durationMin,
    completed: false,
    completed_time: null,
  };

  const totalSecs = durationMin * 60;
  totalTimerDuration.value = totalSecs;
  timerSecondsRemaining.value = totalSecs;
  taskTimers.value[taskId] = {
    remaining: totalSecs,
    total: totalSecs,
  };
  saveTimersToStorage();

  if (isTimerRunning.value) {
    stopRunningTimer();
  }

  // Start the focus timer immediately
  toggleTimer();

  try {
    axios.post(apiUrl(`/tasks/${taskId}/toggle`), { completed: false });
  } catch (e) {}
};

const restartActiveTaskTimer = () => {
  const task = activeFocusTask.value;
  if (!task?.id || task.completed) return;

  if (isTimerRunning.value && stopRunningTimer()) return;

  stopGracePeriod();
  const totalSeconds = (Number(task.durationMinutes) || 45) * 60;
  totalTimerDuration.value = totalSeconds;
  timerSecondsRemaining.value = totalSeconds;
  taskTimers.value[task.id] = { remaining: totalSeconds, total: totalSeconds };
  replayTimerDialAnimation();
  toggleTimer();
};

const resumeCompletedTask = (targetTask) => {
  const taskId = targetTask?.id || activeFocusTask.value?.id;
  if (!taskId) return;
  const savedTimer = taskTimers.value[taskId];
  const remainingSecs = Number(savedTimer?.resumeRemaining);
  if (!Number.isFinite(remainingSecs) || remainingSecs <= 0) return;

  const foundTask = tasks.value.find((task) => task.id === taskId);
  if (foundTask) {
    foundTask.completed = false;
    foundTask.completed_time = null;
  }

  activeFocusTask.value = {
    id: taskId,
    title: foundTask?.title || targetTask?.title || activeFocusTask.value.title,
    tag: foundTask?.tag || targetTask?.tag || activeFocusTask.value.tag,
    durationMinutes:
      foundTask?.duration_minutes ||
      targetTask?.duration_minutes ||
      targetTask?.durationMinutes ||
      activeFocusTask.value.durationMinutes,
    completed: false,
    completed_time: null,
  };
  totalTimerDuration.value = Number(savedTimer.total) || totalTimerDuration.value;
  timerSecondsRemaining.value = Math.min(remainingSecs, totalTimerDuration.value);
  taskTimers.value[taskId] = {
    remaining: timerSecondsRemaining.value,
    total: totalTimerDuration.value,
  };
  saveTimersToStorage();

  if (isTimerRunning.value) {
    clearInterval(timerInterval);
    isTimerRunning.value = false;
  }
  toggleTimer();

  try {
    axios.post(apiUrl(`/tasks/${taskId}/toggle`), { completed: false });
  } catch (error) {
    console.error(`Task ${taskId} was resumed locally but could not be updated on the server:`, error);
  }
};

// Formats live remaining time for a task in the task list without seconds
const getTaskRemainingFormatted = (task) => {
  if (task.completed) return "Done";
  let secs;
  if (activeFocusTask.value && activeFocusTask.value.id === task.id) {
    secs = timerSecondsRemaining.value;
  } else if (taskTimers.value[task.id] && typeof taskTimers.value[task.id].remaining === "number") {
    secs = taskTimers.value[task.id].remaining;
  } else {
    secs = (Number(task.duration_minutes) || 45) * 60;
  }
  const hrs = Math.floor(secs / 3600);
  const mins = Math.floor((secs % 3600) / 60);
  if (hrs > 0) {
    return `${hrs}h ${String(mins).padStart(2, "0")}m`;
  }
  return `${mins}m`;
};

// Ambient Sounds with Squarish Card Design (Reference Match)
const ambientSounds = ref([
  { id: "river", name: "River", icon: "ti ti-ripple", audioUrl: "/ambience/river.mp3", animationUrl: "/ambience/animations/River.gif", isPlaying: false, volume: 50, isFavorite: false },
  { id: "waves", name: "Waves", icon: "ti ti-waves", audioUrl: "/ambience/waves.wav", animationUrl: "/ambience/animations/waves.gif", panRate: 0.07, isPlaying: false, volume: 50, isFavorite: false },
  { id: "campfire", name: "Campfire", icon: "ti ti-flame", audioUrl: "/ambience/campfire.mp3", animationUrl: "/ambience/animations/fire.gif", isPlaying: false, volume: 60, isFavorite: false },
  { id: "wind", name: "Wind", icon: "ti ti-wind", audioUrl: "/ambience/wind.mp3", panRate: 0.035, isPlaying: false, volume: 45, isFavorite: false },
  { id: "howling_wind", name: "Howling Wind", icon: "ti ti-tornado", audioUrl: "/ambience/howling-wind.mp3", panRate: 0.045, isPlaying: false, volume: 50, isFavorite: false },
  { id: "wind_trees", name: "Wind in Trees", icon: "ti ti-trees", audioUrl: "/ambience/wind-in-trees.mp3", panRate: 0.04, isPlaying: false, volume: 55, isFavorite: false },
  { id: "waterfall", name: "Waterfall", icon: "ti ti-droplet-half-2", audioUrl: "/ambience/waterfall.mp3", isPlaying: false, volume: 65, isFavorite: false },
  { id: "snow_walk", name: "Walk in Snow", icon: "ti ti-snowflake", audioUrl: "/ambience/walk-in-snow.mp3", isPlaying: false, volume: 40, isFavorite: false },
  { id: "leaves_walk", name: "Walk on Leaves", icon: "ti ti-leaf", audioUrl: "/ambience/walk-on-leaves.mp3", isPlaying: false, volume: 45, isFavorite: false },
  { id: "highway", name: "Highway", icon: "ti ti-road", audioUrl: "/ambience/highway.mp3", panRate: 0.06, isPlaying: false, volume: 50, isFavorite: false },
  { id: "rain", name: "Rain", icon: "ti ti-cloud-rain", audioUrl: "/ambience/light-rain.mp3", isPlaying: false, volume: 75, isFavorite: false },
  { id: "cafe", name: "Cafe", icon: "ti ti-coffee", audioUrl: "/ambience/cafe.mp3", isPlaying: false, volume: 65, isFavorite: false },
  { id: "fireplace", name: "Fireplace", icon: "ti ti-campfire", audioUrl: "/ambience/campfire.mp3", animationUrl: "/ambience/animations/fire.gif", isPlaying: false, volume: 80, isFavorite: false },
  { id: "night", name: "Night Sky", icon: "ti ti-moon-stars", isPlaying: false, volume: 50, isFavorite: false },
]);

const ambientFilter = ref("all");

const favoriteAmbientSounds = computed(() => ambientSounds.value.filter((sound) => sound.isFavorite));
const filteredAmbientSounds = computed(() =>
  ambientFilter.value === "favorites" ? favoriteAmbientSounds.value : ambientSounds.value
);

const activeAmbientSounds = computed(() => ambientSounds.value.filter((s) => s.isPlaying));

// ==========================================
// 1. PROCEDURAL WEB AUDIO SYNTHESIS FOR AMBIENCE
// ==========================================
let ambientAudioCtx = null;
let taskCompletionAudio = null;
const activeAmbientNodes = {};

const getOrCreateAudioContext = () => {
  if (!ambientAudioCtx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      ambientAudioCtx = new AudioCtx();
    }
  }
  if (ambientAudioCtx && ambientAudioCtx.state === "suspended") {
    ambientAudioCtx.resume();
  }
  return ambientAudioCtx;
};

const playTaskCompletionTick = () => {
  if (!taskCompletionAudio) {
    taskCompletionAudio = new Audio("/task-completion.mp3");
    taskCompletionAudio.volume = 0.6;
  }

  taskCompletionAudio.currentTime = 0;
  taskCompletionAudio.play().catch((error) => {
    console.error("Failed to play task completion sound:", error);
  });
};

const startAmbientSoundNode = (snd) => {
  const ctx = getOrCreateAudioContext();
  if (!ctx) return;

  stopAmbientSoundNode(snd.id);

  const gainNode = ctx.createGain();
  const targetGain = Math.max(0.001, ((snd.volume || 50) / 100) * (snd.audioUrl ? 0.75 : 0.28));
  gainNode.gain.setValueAtTime(targetGain, ctx.currentTime);

  if (snd.audioUrl) {
    const audio = new Audio(snd.audioUrl);
    audio.loop = true;
    audio.preload = "auto";
    const mediaSource = ctx.createMediaElementSource(audio);
    const panner = ctx.createStereoPanner();
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    lfo.frequency.setValueAtTime(snd.panRate || 0.04, ctx.currentTime);
    lfoGain.gain.setValueAtTime(0.78, ctx.currentTime);
    mediaSource.connect(gainNode);
    gainNode.connect(panner);
    panner.connect(ctx.destination);
    lfo.connect(lfoGain);
    lfoGain.connect(panner.pan);
    lfo.start();
    activeAmbientNodes[snd.id] = {
      source: mediaSource,
      gain: gainNode,
      audio,
      panner,
      lfo,
      lfoGain,
    };
    audio.play().catch((error) => {
      console.error(`Failed to play ambience "${snd.name}":`, error);
      snd.isPlaying = false;
      stopAmbientSoundNode(snd.id);
      saveAmbientState();
    });
    return;
  }

  gainNode.connect(ctx.destination);

  // Generate 4s loopable noise buffer
  const bufferSize = ctx.sampleRate * 4;
  const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
  const data = noiseBuffer.getChannelData(0);

  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < bufferSize; i++) {
    const white = Math.random() * 2 - 1;
    if (snd.id === "rain" || snd.id === "river" || snd.id === "waterfall") {
      b0 = 0.99886 * b0 + white * 0.0555179;
      b1 = 0.99332 * b1 + white * 0.0750759;
      b2 = 0.96900 * b2 + white * 0.1538520;
      b3 = 0.86650 * b3 + white * 0.3104856;
      b4 = 0.55000 * b4 + white * 0.5329522;
      b5 = -0.7616 * b5 - white * 0.0168980;
      data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.12;
      b6 = white * 0.115926;
    } else if (snd.id === "campfire" || snd.id === "fireplace") {
      const isCrackle = Math.random() < 0.0035;
      const crackle = isCrackle ? (Math.random() * 2 - 1) * 3 : 0;
      b0 = 0.96 * b0 + white * 0.04;
      data[i] = b0 * 0.35 + crackle;
    } else if (snd.id === "highway") {
      b0 = 0.985 * b0 + white * 0.015;
      data[i] = b0 * 0.7;
    } else {
      b0 = (b0 + (0.02 * white)) / 1.02;
      data[i] = b0 * 2.5;
    }
  }

  const noiseSource = ctx.createBufferSource();
  noiseSource.buffer = noiseBuffer;
  noiseSource.loop = true;

  const filter = ctx.createBiquadFilter();
  if (snd.id === "river" || snd.id === "waterfall") {
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(850, ctx.currentTime);
    filter.Q.setValueAtTime(1.1, ctx.currentTime);
  } else if (snd.id === "rain") {
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(1400, ctx.currentTime);
  } else if (snd.id === "wind" || snd.id === "howling_wind") {
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(450, ctx.currentTime);
  } else if (snd.id === "waves") {
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(520, ctx.currentTime);
    const lfo = ctx.createOscillator();
    lfo.frequency.setValueAtTime(0.12, ctx.currentTime);
    const lfoGain = ctx.createGain();
    lfoGain.gain.setValueAtTime(0.18, ctx.currentTime);
    lfo.connect(lfoGain);
    lfoGain.connect(gainNode.gain);
    lfo.start();
  } else if (snd.id === "highway") {
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(350, ctx.currentTime);
  } else {
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(900, ctx.currentTime);
  }

  noiseSource.connect(filter);
  filter.connect(gainNode);
  noiseSource.start();

  activeAmbientNodes[snd.id] = { source: noiseSource, gain: gainNode };
};

const stopAmbientSoundNode = (sndId) => {
  if (activeAmbientNodes[sndId]) {
    const node = activeAmbientNodes[sndId];
    try {
      if (node.audio) {
        node.audio.pause();
        node.audio.removeAttribute("src");
        node.audio.load();
      } else {
        node.source.stop();
      }
      node.lfo?.stop();
      node.source.disconnect();
      node.lfo?.disconnect();
      node.lfoGain?.disconnect();
      node.panner?.disconnect();
      node.gain.disconnect();
    } catch (e) {}
    delete activeAmbientNodes[sndId];
  }
};

const updateAmbientSoundVolume = (snd) => {
  if (activeAmbientNodes[snd.id] && ambientAudioCtx) {
    const targetGain = Math.max(0.001, ((snd.volume || 50) / 100) * (snd.audioUrl ? 0.75 : 0.28));
    activeAmbientNodes[snd.id].gain.gain.setValueAtTime(targetGain, ambientAudioCtx.currentTime);
  }
};

const toggleAmbientSound = (snd) => {
  snd.isPlaying = !snd.isPlaying;
  if (snd.isPlaying) {
    startAmbientSoundNode(snd);
  } else {
    stopAmbientSoundNode(snd.id);
  }
  saveAmbientState();
};

const toggleAmbientFavorite = (snd) => {
  snd.isFavorite = !snd.isFavorite;
  saveAmbientState();
};

const handleAmbientSliderInput = (snd) => {
  if (snd.volume > 0 && !snd.isPlaying) {
    snd.isPlaying = true;
    startAmbientSoundNode(snd);
  } else if (snd.volume === 0 && snd.isPlaying) {
    snd.isPlaying = false;
    stopAmbientSoundNode(snd.id);
  } else if (snd.isPlaying) {
    updateAmbientSoundVolume(snd);
  }
  saveAmbientState();
};

const muteAllAmbiences = () => {
  ambientSounds.value.forEach((s) => {
    s.isPlaying = false;
    stopAmbientSoundNode(s.id);
  });
  saveAmbientState();
};

const saveAmbientState = () => {
  localStorage.setItem(
    "focusflow_ambients",
    JSON.stringify(
      ambientSounds.value.map((s) => ({
        id: s.id,
        isPlaying: s.isPlaying,
        volume: s.volume,
        isFavorite: s.isFavorite,
      }))
    )
  );
};

// ==========================================
// 2. REAL AUDIO ENGINE FOR MUSIC & PLAYLISTS
// ==========================================
let musicAudioElement = null;
const isMusicPlaying = ref(false);
const currentTrackIndex = ref(0);
const musicVolume = ref(85);
const focusMusicLastVolume = ref(85);
const isMusicLoading = ref(false);
const musicError = ref(null);
const showAddTrackModal = ref(false);
const showVideoPlayer = ref(false);
const isYouTubeLive = ref(false);
const videoPlayerControlsVisible = ref(true);
const videoPlayerPosition = ref({ left: 24, top: 24 });
const videoPlayerWidth = ref(420);
const videoPlayerDrag = ref(null);
const videoPlayerResize = ref(null);
let videoPlayerControlsTimeout = null;
const videoPlayerResizeHandles = [
  { direction: "n", label: "top edge" },
  { direction: "s", label: "bottom edge" },
  { direction: "e", label: "right edge" },
  { direction: "w", label: "left edge" },
  { direction: "ne", label: "top-right corner" },
  { direction: "nw", label: "top-left corner" },
  { direction: "se", label: "bottom-right corner" },
  { direction: "sw", label: "bottom-left corner" },
];
const videoPlayerSizePresets = [
  { label: "XS", width: 320 },
  { label: "S", width: 420 },
  { label: "M", width: 560 },
  { label: "L", width: 720 },
  { label: "XL", width: 900 },
  { label: "XXL", width: 1080 },
];
const showMusicVolume = ref(false);
const nowPlayingTitle = ref("");
const nowPlayingArtist = ref("");
const isLiveVideo = computed(() =>
  isYouTubeLive.value ||
  String(currentTrack.value?.duration || "").toLowerCase() === "live" ||
  currentTrack.value?.isLive === true
);

const revealVideoPlayerControls = () => {
  videoPlayerControlsVisible.value = true;
  if (videoPlayerControlsTimeout) clearTimeout(videoPlayerControlsTimeout);

  const hideControls = () => {
    const controls = document.querySelector(".floating-video-controls");
    if (controls?.contains(document.activeElement)) {
      videoPlayerControlsTimeout = setTimeout(hideControls, 900);
      return;
    }
    videoPlayerControlsVisible.value = false;
    videoPlayerControlsTimeout = null;
  };
  videoPlayerControlsTimeout = setTimeout(hideControls, 900);
};

const getMaxVideoPlayerWidth = (top = videoPlayerPosition.value.top) => {
  const availableHeight = Math.max(180, window.innerHeight - top - 24);
  const widthForAvailableHeight = ((availableHeight - 64) * 16) / 9 + 20;
  return Math.max(180, Math.min(window.innerWidth - 24, widthForAvailableHeight));
};

const keepVideoPlayerInViewport = () => {
  if (!showVideoPlayer.value) return;

  const maxWidth = getMaxVideoPlayerWidth(12);
  const width = Math.min(videoPlayerWidth.value, maxWidth);
  const height = (width - 20) * (9 / 16) + 64;
  videoPlayerWidth.value = width;
  videoPlayerPosition.value = {
    left: Math.min(videoPlayerPosition.value.left, Math.max(0, window.innerWidth - width)),
    top: Math.min(videoPlayerPosition.value.top, Math.max(0, window.innerHeight - height - 12)),
  };
};

const setVideoPlayerSize = (presetWidth) => {
  const maxWidth = getMaxVideoPlayerWidth(12);
  const width = Math.min(presetWidth, maxWidth);
  const height = (width - 20) * (9 / 16) + 64;
  const right = videoPlayerPosition.value.left + videoPlayerWidth.value;

  videoPlayerWidth.value = width;
  videoPlayerPosition.value = {
    left: Math.min(Math.max(0, right - width), Math.max(0, window.innerWidth - width)),
    top: Math.min(videoPlayerPosition.value.top, Math.max(0, window.innerHeight - height - 12)),
  };
};

const closeVideoPlayer = () => {
  showVideoPlayer.value = false;
  videoPlayerControlsVisible.value = false;
  if (videoPlayerControlsTimeout) clearTimeout(videoPlayerControlsTimeout);
  videoPlayerControlsTimeout = null;
  videoPlayerDrag.value = null;
  videoPlayerResize.value = null;
};

const toggleVideoPlayer = () => {
  if (showVideoPlayer.value) {
    closeVideoPlayer();
    return;
  }

  const width = Math.min(420, getMaxVideoPlayerWidth(12));
  const height = (width - 20) * (9 / 16) + 64;
  videoPlayerWidth.value = width;
  videoPlayerPosition.value = {
    left: Math.max(12, window.innerWidth - width - 24),
    top: Math.max(12, window.innerHeight - height - 24),
  };
  showVideoPlayer.value = true;
  revealVideoPlayerControls();
};

const startVideoPlayerDrag = (event) => {
  if (
    event.button !== 0 ||
    (event.target.closest("button") && !event.target.closest(".floating-video-drag-handle"))
  ) return;

  const player = event.currentTarget.closest(".embedded-player-box.video-active-frame");
  if (!player) return;

  const bounds = player.getBoundingClientRect();
  videoPlayerDrag.value = {
    pointerId: event.pointerId,
    offsetX: event.clientX - bounds.left,
    offsetY: event.clientY - bounds.top,
  };
  event.currentTarget.setPointerCapture(event.pointerId);
};

const moveVideoPlayer = (event) => {
  const drag = videoPlayerDrag.value;
  if (!drag || drag.pointerId !== event.pointerId) return;

  const player = event.currentTarget.closest(".embedded-player-box.video-active-frame");
  if (!player) return;

  const bounds = player.getBoundingClientRect();
  videoPlayerPosition.value = {
    left: Math.min(
      Math.max(0, event.clientX - drag.offsetX),
      Math.max(0, window.innerWidth - bounds.width),
    ),
    top: Math.min(
      Math.max(0, event.clientY - drag.offsetY),
      Math.max(0, window.innerHeight - bounds.height),
    ),
  };
};

const finishVideoPlayerDrag = (event) => {
  if (videoPlayerDrag.value?.pointerId === event.pointerId) {
    videoPlayerDrag.value = null;
  }
};

const startVideoPlayerResize = (event, direction) => {
  if (event.button !== 0) return;

  videoPlayerResize.value = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    startWidth: videoPlayerWidth.value,
    startLeft: videoPlayerPosition.value.left,
    startTop: videoPlayerPosition.value.top,
    right: videoPlayerPosition.value.left + videoPlayerWidth.value,
    bottom: videoPlayerPosition.value.top + (videoPlayerWidth.value - 20) * (9 / 16) + 64,
    direction,
  };
  event.currentTarget.setPointerCapture(event.pointerId);
  event.preventDefault();
};

const moveVideoPlayerResize = (event) => {
  const resize = videoPlayerResize.value;
  if (!resize || resize.pointerId !== event.pointerId) return;

  const maxWidth = getMaxVideoPlayerWidth(12);
  const minWidth = Math.min(240, maxWidth);
  const direction = resize.direction;
  const deltaX = event.clientX - resize.startX;
  const deltaY = event.clientY - resize.startY;
  let widthDelta = 0;

  if (direction.includes("e")) widthDelta += deltaX;
  if (direction.includes("w")) widthDelta -= deltaX;
  if (direction.includes("s")) widthDelta += deltaY * (16 / 9);
  if (direction.includes("n")) widthDelta -= deltaY * (16 / 9);
  if (direction.length === 2) widthDelta /= 2;

  const width = Math.min(maxWidth, Math.max(minWidth, resize.startWidth + widthDelta));
  const height = (width - 20) * (9 / 16) + 64;
  const left = direction.includes("w") ? resize.right - width : resize.startLeft;
  const top = direction.includes("n") ? resize.bottom - height : resize.startTop;

  videoPlayerWidth.value = width;
  videoPlayerPosition.value = {
    left: Math.min(Math.max(0, left), Math.max(0, window.innerWidth - width)),
    top: Math.min(Math.max(0, top), Math.max(0, window.innerHeight - height - 12)),
  };
};

const finishVideoPlayerResize = (event) => {
  if (videoPlayerResize.value?.pointerId === event.pointerId) {
    videoPlayerResize.value = null;
  }
};

const resizeVideoPlayerByKeyboard = (event) => {
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
  event.preventDefault();

  const maxWidth = getMaxVideoPlayerWidth(12);
  const minWidth = Math.min(240, maxWidth);
  const step = event.shiftKey ? 48 : 24;
  const delta = event.key === "ArrowRight" ? step : -step;
  const width = Math.min(maxWidth, Math.max(minWidth, videoPlayerWidth.value + delta));
  const height = (width - 20) * (9 / 16) + 64;
  const right = videoPlayerPosition.value.left + videoPlayerWidth.value;

  videoPlayerWidth.value = width;
  videoPlayerPosition.value = {
    left: Math.min(Math.max(0, right - width), Math.max(0, window.innerWidth - width)),
    top: Math.min(videoPlayerPosition.value.top, Math.max(0, window.innerHeight - height - 12)),
  };
};

// Live Progress and Seeking State
const trackProgressPercent = ref(0);
const trackCurrentTimeStr = ref("00:00");
const trackDurationStr = ref("00:00");
let playbackTimerInterval = null;
let currentTrackElapsedSecs = 0;
let currentTrackDurationSecs = 0; // Unknown until the player reports the real duration

// Playback engine bookkeeping
let activeTrackId = null; // id of the track the engine is currently set up for
const ytLoadedTrackId = ref(null); // YouTube track whose iframe is mounted (kept mounted while paused)
let ytLastMessageAt = 0;
let ytVolumeSynced = false;
let ytLastEndedAt = 0;
let ytPlayCommandAt = 0;
const ytReloadCounter = ref(0); // bumps to force a fresh YouTube iframe

const formatSeconds = (secs) => {
  if (isNaN(secs) || secs < 0) return "00:00";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};

// New Link / Track Input Fields
const newTrackTitle = ref("");
const newTrackUrl = ref("");
const newTrackArtist = ref("");
const isAddingMusic = ref(false);

// Focus Playlist (NO predefined/hardcoded tracks; user-added only)
const playlist = ref([]);
const playlistTitle = ref("Focus Playlist");
const savedPlaylists = ref([]);
const activePlaylistId = ref("");
const defaultPlaylistId = "focusflow-default-playlist";
const isPlaylistMenuOpen = ref(false);
const playlistPickerRef = ref(null);
const playlistPickerButton = ref(null);

const currentTrack = computed(() => {
  if (!playlist.value.length) return null;
  const idx = Math.min(Math.max(0, currentTrackIndex.value), playlist.value.length - 1);
  return playlist.value[idx];
});
const activeSavedPlaylist = computed(() =>
  savedPlaylists.value.find((saved) => saved.id === activePlaylistId.value)
);
const isPlaylistExpanded = ref(false);
const isPlaylistTracksModalOpen = ref(false);

const closePlaylistMenuOnOutsideClick = (event) => {
  if (!playlistPickerRef.value?.contains(event.target)) {
    isPlaylistMenuOpen.value = false;
  }
};

const choosePlaylist = async (playlistId) => {
  selectPlaylist(playlistId);
  isPlaylistMenuOpen.value = false;
  await nextTick();
  playlistPickerButton.value?.focus();
};

const selectPlaylistTrack = (index) => {
  if (index === currentTrackIndex.value) {
    if (!isMusicPlaying.value) playCurrentAudio();
  } else {
    currentTrackIndex.value = index;
    playCurrentAudio(true);
  }
  isPlaylistTracksModalOpen.value = false;
};

const saveActivePlaylist = () => {
  const activePlaylist = savedPlaylists.value.find((saved) => saved.id === activePlaylistId.value);
  if (!activePlaylist) return;
  activePlaylist.title = playlistTitle.value;
  activePlaylist.tracks = playlist.value;
  activePlaylist.currentTrackIndex = currentTrackIndex.value;
};

const selectPlaylist = (playlistId) => {
  if (!playlistId || playlistId === activePlaylistId.value) return;
  const selectedPlaylist = savedPlaylists.value.find((saved) => saved.id === playlistId);
  if (!selectedPlaylist) return;

  pauseCurrentAudio();
  saveActivePlaylist();
  activePlaylistId.value = selectedPlaylist.id;
  playlistTitle.value = selectedPlaylist.title;
  playlist.value = selectedPlaylist.tracks;
  currentTrackIndex.value = Math.min(
    Math.max(0, selectedPlaylist.currentTrackIndex || 0),
    Math.max(0, playlist.value.length - 1)
  );
  activeTrackId = null;
  ytLoadedTrackId.value = null;
  resetTrackProgress();
  nowPlayingTitle.value = currentTrack.value?.title || "";
  nowPlayingArtist.value = currentTrack.value?.artist || "";
  saveMusicState();
};

const selectDefaultPlaylist = () => {
  let defaultPlaylist = savedPlaylists.value.find((saved) => saved.id === defaultPlaylistId);
  if (!defaultPlaylist) {
    defaultPlaylist = {
      id: defaultPlaylistId,
      title: "My Songs",
      tracks: [],
      currentTrackIndex: 0,
    };
    savedPlaylists.value.push(defaultPlaylist);
  }
  if (activePlaylistId.value !== defaultPlaylistId) {
    pauseCurrentAudio();
    saveActivePlaylist();
    activePlaylistId.value = defaultPlaylist.id;
    playlistTitle.value = defaultPlaylist.title;
    playlist.value = defaultPlaylist.tracks;
    currentTrackIndex.value = Math.min(
      Math.max(0, defaultPlaylist.currentTrackIndex || 0),
      Math.max(0, defaultPlaylist.tracks.length - 1)
    );
    activeTrackId = null;
    ytLoadedTrackId.value = null;
    resetTrackProgress();
    nowPlayingTitle.value = currentTrack.value?.title || "";
    nowPlayingArtist.value = currentTrack.value?.artist || "";
  }
  return defaultPlaylist;
};

// Helper: Detect type of track
const getTrackType = (trk) => {
  if (!trk || !trk.url) return "audio";
  const url = trk.url.toLowerCase();
  if (url.includes("youtube.com") || url.includes("youtu.be")) return "youtube";
  if (url.includes("spotify.com")) return "spotify";
  return "audio";
};
const isCurrentTrackSeekable = computed(() =>
  Boolean(currentTrack.value) &&
  getTrackType(currentTrack.value) !== "spotify" &&
  trackDurationStr.value !== "00:00" &&
  !isLiveVideo.value
);

const isYouTubeUrl = (rawUrl) => {
  try {
    const hostname = new URL(rawUrl).hostname.toLowerCase();
    return hostname === "youtu.be" || hostname.endsWith(".youtube.com") || hostname === "youtube.com";
  } catch {
    return false;
  }
};

// Robust YouTube URL Parser
const parseYouTubeUrl = (rawUrl) => {
  if (!rawUrl) return { videoId: null, playlistId: null };
  try {
    const parsedUrl = new URL(rawUrl.trim());
    const playlistId = parsedUrl.searchParams.get("list");
    const host = parsedUrl.hostname.toLowerCase();
    let videoId = null;

    if (host === "youtu.be") {
      videoId = parsedUrl.pathname.split("/").filter(Boolean)[0] || null;
    } else {
      videoId = parsedUrl.searchParams.get("v");
      if (!videoId) {
        const pathMatch = parsedUrl.pathname.match(/^\/(?:live|shorts|embed)\/([^/]+)/);
        videoId = pathMatch ? pathMatch[1] : null;
      }
    }

    return { videoId, playlistId };
  } catch {
    return { videoId: null, playlistId: null };
  }
};

const getYouTubeEmbedUrl = (url) => {
  if (!url) return "";
  const { videoId, playlistId } = parseYouTubeUrl(url);

  const originParam =
    typeof window !== "undefined" && /^https?:/.test(window.location.origin)
      ? `&origin=${encodeURIComponent(window.location.origin)}`
      : "";
  const baseParams = `autoplay=1&enablejsapi=1&playsinline=1&controls=0${originParam}`;

  // The app manages its own playlist (next / prev / auto-advance), so a single
  // video must be embedded on its own. Passing list= here would make YouTube
  // auto-advance inside the iframe and desync the UI from what is playing.
  if (videoId) {
    return `https://www.youtube-nocookie.com/embed/${videoId}?${baseParams}`;
  }
  if (playlistId && !videoId) {
    return `https://www.youtube-nocookie.com/embed/videoseries?list=${playlistId}&${baseParams}`;
  }
  return "";
};

const sendYouTubeCommand = (func, args = []) => {
  const iframe = document.querySelector(".youtube-embed");
  if (iframe && iframe.contentWindow) {
    try {
      iframe.contentWindow.postMessage(
        JSON.stringify({ event: "command", func: func, args: args }),
        "*"
      );
    } catch (e) {}
  }
};

// YouTube only sends time / state updates after it receives this handshake.
const requestYouTubeUpdates = () => {
  const iframe = document.querySelector(".youtube-embed");
  if (iframe && iframe.contentWindow) {
    try {
      iframe.contentWindow.postMessage(
        JSON.stringify({ event: "listening", id: 1, channel: "widget" }),
        "*"
      );
    } catch (e) {}
  }
};

const getSpotifyEmbedUrl = (url) => {
  if (!url) return "";
  if (url.includes("/embed/")) return url;
  return url.replace("open.spotify.com/", "open.spotify.com/embed/") + "?utm_source=generator&theme=0";
};

// Playback progress ticker for time bar
const startPlaybackProgress = () => {
  if (playbackTimerInterval) clearInterval(playbackTimerInterval);
  playbackTimerInterval = setInterval(() => {
    if (!isMusicPlaying.value || !currentTrack.value) return;

    const trkType = getTrackType(currentTrack.value);
    if (trkType === "youtube") {
      // Real time / duration arrive through the iframe's postMessage events.
      // Only estimate locally when the player has stopped reporting.
      if (Date.now() - ytLastMessageAt > 1500) {
        requestYouTubeUpdates();
        currentTrackElapsedSecs += 0.5;
      }
      if (currentTrackDurationSecs > 0) {
        if (currentTrackElapsedSecs >= currentTrackDurationSecs + 1 && Date.now() - ytLastMessageAt > 1500) {
          nextTrack();
          return;
        }
        trackProgressPercent.value = Math.min(100, (currentTrackElapsedSecs / currentTrackDurationSecs) * 100);
        trackDurationStr.value = formatSeconds(currentTrackDurationSecs);
      }
      trackCurrentTimeStr.value = formatSeconds(currentTrackElapsedSecs);
    } else if (trkType === "audio" && musicAudioElement) {
      if (musicAudioElement.duration && !isNaN(musicAudioElement.duration) && isFinite(musicAudioElement.duration)) {
        currentTrackDurationSecs = musicAudioElement.duration;
        currentTrackElapsedSecs = musicAudioElement.currentTime;
        trackProgressPercent.value = Math.min(100, (currentTrackElapsedSecs / currentTrackDurationSecs) * 100);
        trackCurrentTimeStr.value = formatSeconds(currentTrackElapsedSecs);
        trackDurationStr.value = formatSeconds(currentTrackDurationSecs);
      }
    }
  }, 500);
};

const stopPlaybackProgress = () => {
  if (playbackTimerInterval) {
    clearInterval(playbackTimerInterval);
    playbackTimerInterval = null;
  }
};

// Called when the YouTube iframe finishes loading
const handleYouTubeFrameLoad = () => {
  requestYouTubeUpdates();
  sendYouTubeCommand("setVolume", [musicVolume.value]);
};

// Listen to YouTube player postMessage events (only from YouTube iframes)
const handleYouTubeMessage = (event) => {
  if (!event.origin || !/^https:\/\/(www\.)?youtube(-nocookie)?\.com$/.test(event.origin)) return;
  const trk = currentTrack.value;
  if (!trk || getTrackType(trk) !== "youtube") return;

  try {
    const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
    if (!data) return;

    if (data.event === "onReady") {
      requestYouTubeUpdates();
      sendYouTubeCommand("setVolume", [musicVolume.value]);
      return;
    }

    if (data.event === "onError" || (data.event === "infoDelivery" && data.info && typeof data.info.errorCode === "number")) {
      const rawErrorCode = data.info?.errorCode ?? data.info ?? data.data?.errorCode ?? data.data;
      const errorCode = Number(rawErrorCode);
      if (errorCode === 153) {
        musicError.value = "YouTube blocked the player because the request is missing this site's referrer. Reload the page and try again.";
      } else if (errorCode === 101 || errorCode === 150) {
        musicError.value = "The video owner does not allow this video to play in embedded players. Open it on YouTube instead.";
      } else if (errorCode === 100) {
        musicError.value = "This YouTube video is private, removed, or unavailable.";
      } else {
        musicError.value = "This YouTube video can't be played in the embedded player.";
      }
      return;
    }

    if (data.info) {
      ytLastMessageAt = Date.now();

      const videoData = data.info.videoData;
      if (videoData && typeof videoData === "object") {
        if (typeof videoData.isLive === "boolean" || typeof videoData.isLiveContent === "boolean") {
          isYouTubeLive.value = Boolean(videoData.isLive || videoData.isLiveContent);
        }
        if (typeof videoData.title === "string" && videoData.title) {
          nowPlayingTitle.value = videoData.title;
          if (trk.title === "YouTube Track" || trk.title === "Audio Stream Track") {
            trk.title = videoData.title;
            if (trk.source === "Audio Stream") trk.source = "YouTube";
            saveMusicState();
          }
        }
        if (typeof videoData.author === "string" && videoData.author) {
          nowPlayingArtist.value = videoData.author;
          if (trk.artist === "Audio Stream") {
            trk.artist = videoData.author;
            saveMusicState();
          }
        }
      }

      if (typeof data.info.currentTime === "number") {
        currentTrackElapsedSecs = data.info.currentTime;
      }
      if (typeof data.info.duration === "number" && data.info.duration > 0) {
        currentTrackDurationSecs = data.info.duration;
      }
      if (currentTrackDurationSecs > 0) {
        trackProgressPercent.value = Math.min(100, (currentTrackElapsedSecs / currentTrackDurationSecs) * 100);
        trackDurationStr.value = formatSeconds(currentTrackDurationSecs);
      }
      trackCurrentTimeStr.value = formatSeconds(currentTrackElapsedSecs);

      if (!ytVolumeSynced) {
        ytVolumeSynced = true;
        sendYouTubeCommand("setVolume", [musicVolume.value]);
      }

      if (typeof data.info.playerState === "number") {
        const state = data.info.playerState;
        if (state === 0) {
          // Video ended -> auto advance (guard against duplicate "ended" events)
          if (Date.now() - ytLastEndedAt > 2000) {
            ytLastEndedAt = Date.now();
            nextTrack();
          }
        } else if (state === 1) {
          musicError.value = null;
          isMusicLoading.value = false;
          if (!isMusicPlaying.value) {
            isMusicPlaying.value = true;
            startPlaybackProgress();
            saveMusicState();
          }
        } else if (state === 3) {
          isMusicLoading.value = true;
        } else if (state === 2) {
          isMusicLoading.value = false;
          if (isMusicPlaying.value) {
            isMusicPlaying.value = false;
            stopPlaybackProgress();
            saveMusicState();
          }
        }
      }
    }
  } catch (e) {}
};

if (typeof window !== "undefined") {
  window.addEventListener("message", handleYouTubeMessage);
}

// Init HTML5 Audio Element
const initMusicAudio = () => {
  if (!musicAudioElement) {
    musicAudioElement = new Audio();
    musicAudioElement.volume = musicVolume.value / 100;
    musicAudioElement.preload = "auto";
    // Only loop when there is nothing else to advance to; otherwise "ended" -> next track
    musicAudioElement.loop = playlist.value.length <= 1;

    musicAudioElement.addEventListener("playing", () => {
      isMusicLoading.value = false;
      musicError.value = null;
    });

    musicAudioElement.addEventListener("canplay", () => {
      isMusicLoading.value = false;
    });

    musicAudioElement.addEventListener("ended", () => {
      if (playlist.value.length > 1 && !musicAudioElement.paused) {
        nextTrack();
      }
    });

    musicAudioElement.addEventListener("waiting", () => {
      isMusicLoading.value = true;
    });

    musicAudioElement.addEventListener("timeupdate", () => {
      if (musicAudioElement && musicAudioElement.duration && !isNaN(musicAudioElement.duration)) {
        const cur = musicAudioElement.currentTime;
        const dur = musicAudioElement.duration;
        currentTrackElapsedSecs = cur;
        currentTrackDurationSecs = dur;
        trackProgressPercent.value = (cur / dur) * 100;
        trackCurrentTimeStr.value = formatSeconds(cur);
        trackDurationStr.value = formatSeconds(dur);
      }
    });

    musicAudioElement.addEventListener("error", (e) => {
      console.warn("Audio stream error:", e);
      isMusicLoading.value = false;
      // Ignore the error fired when we deliberately clear the source
      if (musicAudioElement && musicAudioElement.getAttribute("src")) {
        musicError.value = "Couldn't load this audio. Check the link or try another track.";
        isMusicPlaying.value = false;
        stopPlaybackProgress();
      }
    });
  }
  return musicAudioElement;
};

const resetTrackProgress = () => {
  currentTrackElapsedSecs = 0;
  currentTrackDurationSecs = 0;
  trackProgressPercent.value = 0;
  trackCurrentTimeStr.value = "00:00";
  trackDurationStr.value = "00:00";
};

const stopAudioElement = () => {
  if (musicAudioElement) {
    musicAudioElement.pause();
  }
};

// forceRestart = true when the user explicitly picks / skips to a track
const playCurrentAudio = (forceRestart = false) => {
  const trk = currentTrack.value;
  if (!trk) return;

  const type = getTrackType(trk);
  const isNewTrack = forceRestart || activeTrackId !== trk.id;
  musicError.value = null;

  if (isNewTrack) {
    isYouTubeLive.value = String(trk.duration || "").toLowerCase() === "live" || trk.isLive === true;
    resetTrackProgress();
    ytVolumeSynced = false;
    ytLastMessageAt = 0;
    activeTrackId = trk.id;
    nowPlayingTitle.value = trk.title || "";
    nowPlayingArtist.value = trk.artist || "";
  }

  if (type === "youtube") {
    stopAudioElement();
    isMusicLoading.value = isNewTrack;

    if (!isNewTrack && ytLoadedTrackId.value === trk.id) {
      // Iframe is still mounted (paused) -> just resume where we left off
      ytPlayCommandAt = Date.now();
      sendYouTubeCommand("playVideo");
      sendYouTubeCommand("setVolume", [musicVolume.value]);
    } else {
      // (Re)mount the iframe; it autoplays on load. Changing the key forces a fresh embed.
      ytReloadCounter.value += 1;
      ytLoadedTrackId.value = trk.id;
    }

    isMusicPlaying.value = true;
    startPlaybackProgress();
    saveMusicState();
    return;
  }

  // Leaving YouTube -> unmount its iframe so it can't keep playing in the background
  ytLoadedTrackId.value = null;

  if (type === "spotify") {
    stopAudioElement();
    isMusicLoading.value = false;
    isMusicPlaying.value = true;
    startPlaybackProgress();
    saveMusicState();
    return;
  }

  // Direct Audio Track or Stream
  const audio = initMusicAudio();
  audio.volume = Math.max(0, Math.min(1, musicVolume.value / 100));
  audio.loop = playlist.value.length <= 1;

  if (isNewTrack) {
    audio.pause();
    audio.src = trk.url;
    audio.load();
  }

  isMusicLoading.value = isNewTrack;
  isMusicPlaying.value = true;
  startPlaybackProgress();

  const playPromise = audio.play();
  if (playPromise !== undefined) {
    playPromise
      .then(() => {
        isMusicLoading.value = false;
      })
      .catch((err) => {
        // AbortError just means a newer play()/load() superseded this one
        if (err && err.name === "AbortError") return;
        console.warn("Audio play error:", err);
        isMusicLoading.value = false;
        isMusicPlaying.value = false;
        stopPlaybackProgress();
        musicError.value =
          err && err.name === "NotAllowedError"
            ? "Your browser blocked autoplay. Press play to start the music."
            : "Couldn't play this audio. Check the link or try another track.";
        saveMusicState();
      });
  }

  saveMusicState();
};

const pauseCurrentAudio = () => {
  stopAudioElement();
  const trk = currentTrack.value;
  if (trk && getTrackType(trk) === "youtube") {
    sendYouTubeCommand("pauseVideo");
  }
  isMusicPlaying.value = false;
  isMusicLoading.value = false;
  stopPlaybackProgress();
  saveMusicState();
};

const toggleMusic = () => {
  if (isMusicPlaying.value) {
    pauseCurrentAudio();
  } else {
    playCurrentAudio();
  }
};

const playTrack = (idx) => {
  if (idx === currentTrackIndex.value && isMusicPlaying.value) {
    // Clicking the active track while it plays just pauses it
    pauseCurrentAudio();
    return;
  }
  const sameTrack = idx === currentTrackIndex.value;
  currentTrackIndex.value = idx;
  playCurrentAudio(!sameTrack);
};

const nextTrack = () => {
  if (!playlist.value.length) return;
  const trk = currentTrack.value;
  const { videoId, playlistId } = parseYouTubeUrl(trk?.url);
  if (
    trk &&
    getTrackType(trk) === "youtube" &&
    playlistId &&
    !videoId &&
    ytLoadedTrackId.value === trk.id
  ) {
    sendYouTubeCommand("nextVideo");
    return;
  }
  currentTrackIndex.value = (currentTrackIndex.value + 1) % playlist.value.length;
  playCurrentAudio(true);
};

const prevTrack = () => {
  if (!playlist.value.length) return;
  currentTrackIndex.value = (currentTrackIndex.value - 1 + playlist.value.length) % playlist.value.length;
  playCurrentAudio(true);
};

const handleSeek = (e) => {
  const trk = currentTrack.value;
  if (!trk || !isCurrentTrackSeekable.value || currentTrackDurationSecs <= 0) return;

  const type = getTrackType(trk);
  if (type !== "audio" && type !== "youtube") return;

  const val = Math.max(0, Math.min(100, Number(e.target.value)));
  const targetSecs = (val / 100) * currentTrackDurationSecs;
  trackProgressPercent.value = val;
  currentTrackElapsedSecs = targetSecs;
  trackCurrentTimeStr.value = formatSeconds(targetSecs);

  if (type === "audio" && musicAudioElement && Number.isFinite(musicAudioElement.duration)) {
    musicAudioElement.currentTime = targetSecs;
  }
  if (type === "youtube") {
    sendYouTubeCommand("seekTo", [targetSecs, true]);
  }
};

const skipForwardFiveSeconds = () => {
  const trk = currentTrack.value;
  if (!trk || !isMusicPlaying.value || !isCurrentTrackSeekable.value) return;

  const type = getTrackType(trk);
  if (type !== "audio" && type !== "youtube") return;

  const audioDuration = Number(musicAudioElement?.duration);
  const duration = type === "audio" && Number.isFinite(audioDuration) && audioDuration > 0
    ? audioDuration
    : currentTrackDurationSecs;
  if (!Number.isFinite(duration) || duration <= 0) return;

  const audioCurrentTime = Number(musicAudioElement?.currentTime);
  const elapsed = type === "audio" && Number.isFinite(audioCurrentTime)
    ? audioCurrentTime
    : currentTrackElapsedSecs;
  if (!Number.isFinite(elapsed)) return;

  const targetSecs = Math.min(duration, elapsed + 5);

  if (type === "audio") {
    if (!musicAudioElement) return;
    musicAudioElement.currentTime = targetSecs;
  } else {
    sendYouTubeCommand("seekTo", [targetSecs, true]);
  }

  currentTrackElapsedSecs = targetSecs;
  trackCurrentTimeStr.value = formatSeconds(targetSecs);
  trackProgressPercent.value = Math.min(100, (targetSecs / duration) * 100);
};

const handleMusicVolumeInput = () => {
  if (musicAudioElement) {
    musicAudioElement.volume = Math.max(0, Math.min(1, musicVolume.value / 100));
  }
  sendYouTubeCommand("setVolume", [musicVolume.value]);
};

const setFocusMusicVolume = (event) => {
  musicVolume.value = Number(event.target.value);
  if (musicVolume.value > 0) focusMusicLastVolume.value = musicVolume.value;
  handleMusicVolumeInput();
};

const toggleFocusMusicMute = () => {
  if (musicVolume.value > 0) {
    focusMusicLastVolume.value = musicVolume.value;
    musicVolume.value = 0;
  } else {
    musicVolume.value = focusMusicLastVolume.value || 85;
  }
  handleMusicVolumeInput();
};

const goToLive = () => {
  if (currentTrackDurationSecs <= 0) {
    requestYouTubeUpdates();
    return;
  }

  const liveEdgeSeconds = Math.max(0, currentTrackDurationSecs - 1);
  sendYouTubeCommand("seekTo", [liveEdgeSeconds, true]);
  currentTrackElapsedSecs = liveEdgeSeconds;
  trackCurrentTimeStr.value = formatSeconds(liveEdgeSeconds);
  trackProgressPercent.value = Math.min(100, (liveEdgeSeconds / currentTrackDurationSecs) * 100);
};

const toggleTrackFavorite = (trk) => {
  trk.isFavorite = !trk.isFavorite;
  saveMusicState();
};

const removeTrackFromPlaylist = (idx) => {
  playlist.value.splice(idx, 1);
  if (currentTrackIndex.value >= playlist.value.length) {
    currentTrackIndex.value = Math.max(0, playlist.value.length - 1);
  }
  if (playlist.value.length === 0) {
    pauseCurrentAudio();
    activeTrackId = null;
    ytLoadedTrackId.value = null;
    resetTrackProgress();
    nowPlayingTitle.value = "";
    nowPlayingArtist.value = "";
  } else if (isMusicPlaying.value) {
    playCurrentAudio();
  }
  saveMusicState();
};

const addMusicLink = async () => {
  if (!newTrackUrl.value.trim() && !newTrackTitle.value.trim()) return;

  const url = newTrackUrl.value.trim();
  musicError.value = null;
  isAddingMusic.value = true;

  try {
    const { playlistId, videoId } = parseYouTubeUrl(url);
    const isYouTube = isYouTubeUrl(url);

    // Case A: YouTube Playlist (extract and show ALL songs)
    if (playlistId && !videoId) {
      try {
        const res = await axios.get(apiUrl("/youtube/playlist"), {
          params: { playlist_id: playlistId },
        });
        if (res.data && res.data.tracks && res.data.tracks.length > 0) {
          const fetchedTracks = res.data.tracks;
          pauseCurrentAudio();
          saveActivePlaylist();
          const selectedTitle = newTrackTitle.value.trim() || res.data.title || "YouTube Playlist";
          const savedPlaylistId = `youtube-${playlistId}`;
          let savedPlaylist = savedPlaylists.value.find((saved) => saved.id === savedPlaylistId);
          if (savedPlaylist) {
            savedPlaylist.title = selectedTitle;
            savedPlaylist.tracks = fetchedTracks;
            savedPlaylist.currentTrackIndex = 0;
          } else {
            savedPlaylist = {
              id: savedPlaylistId,
              title: selectedTitle,
              tracks: fetchedTracks,
              currentTrackIndex: 0,
            };
            savedPlaylists.value.push(savedPlaylist);
          }
          activePlaylistId.value = savedPlaylist.id;
          playlistTitle.value = savedPlaylist.title;
          playlist.value = savedPlaylist.tracks;
          currentTrackIndex.value = 0;
          playCurrentAudio(true);
          newTrackTitle.value = "";
          newTrackUrl.value = "";
          newTrackArtist.value = "";
          showAddTrackModal.value = false;
          isAddingMusic.value = false;
          saveMusicState();
          return;
        }
      } catch (err) {
        console.warn("Backend YouTube playlist parser error:", err);
        musicError.value =
          err.response?.data?.error ||
          "Couldn't load this YouTube playlist. Check that the playlist is public and try again.";
      }

      musicError.value =
        musicError.value ||
        "Couldn't load this YouTube playlist. Check that the playlist is public and try again.";
      isAddingMusic.value = false;
      return;
    }

    // Case B: Single YouTube Video
    if (isYouTube && videoId) {
      let title = newTrackTitle.value.trim();
      let artist = newTrackArtist.value.trim() || "YouTube";
      let cover = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;

      try {
        const res = await axios.get(apiUrl(`/youtube/track?url=${encodeURIComponent(url)}`));
        if (res.data) {
          if (!title && res.data.title) title = res.data.title;
          if (res.data.artist) artist = res.data.artist;
          if (res.data.cover) cover = res.data.cover;
        }
      } catch (e) {}

      const newEntry = {
        id: `yt-${videoId}-${Date.now()}`,
        title: title || "YouTube Track",
        artist: artist,
        source: "YouTube",
        url: url,
        cover: cover,
        duration: "YouTube",
        tag: "YouTube",
        isFavorite: false,
      };

      const defaultPlaylist = selectDefaultPlaylist();
      defaultPlaylist.tracks.unshift(newEntry);
      playlist.value = defaultPlaylist.tracks;
      currentTrackIndex.value = 0;
      playCurrentAudio(true);
      newTrackTitle.value = "";
      newTrackUrl.value = "";
      newTrackArtist.value = "";
      showAddTrackModal.value = false;
      isAddingMusic.value = false;
      saveMusicState();
      return;
    }

    if (isYouTube) {
      musicError.value = "Couldn't identify a video or playlist in that YouTube link. Please check the URL.";
      isAddingMusic.value = false;
      return;
    }

    // Case C: Spotify or Audio Stream Link
    let detectedSource = "Audio Stream";
    if (url.includes("spotify.com")) detectedSource = "Spotify";

    const newEntry = {
      id: `track-${Date.now()}`,
      title: newTrackTitle.value.trim() || (detectedSource + " Track"),
      artist: newTrackArtist.value.trim() || detectedSource,
      source: detectedSource,
      url: url || "#",
      cover: "/forest_rain_cover.jpg",
      duration: detectedSource === "Spotify" ? "Spotify" : "Live",
      tag: detectedSource,
      isFavorite: false,
    };

    const defaultPlaylist = selectDefaultPlaylist();
    defaultPlaylist.tracks.unshift(newEntry);
    playlist.value = defaultPlaylist.tracks;
    currentTrackIndex.value = 0;
    playCurrentAudio(true);

    newTrackTitle.value = "";
    newTrackUrl.value = "";
    newTrackArtist.value = "";
    showAddTrackModal.value = false;
    isAddingMusic.value = false;
    saveMusicState();
  } catch (err) {
    console.error("Failed to add music link:", err);
    isAddingMusic.value = false;
  }
};

const saveMusicState = () => {
  saveActivePlaylist();
  localStorage.setItem("focusflow_playlists", JSON.stringify(savedPlaylists.value));
  localStorage.setItem("focusflow_active_playlist_id", activePlaylistId.value);
  localStorage.setItem("focusflow_playlist", JSON.stringify(playlist.value));
  localStorage.setItem("focusflow_playlist_title", playlistTitle.value);
  localStorage.setItem("focusflow_current_track_idx", JSON.stringify(currentTrackIndex.value));
  localStorage.setItem("focusflow_music_playing", JSON.stringify(isMusicPlaying.value));
};

// Stats
const stats = ref({
  streak_days: 3,
  focus_minutes_today: 0,
  focus_seconds_today: 0,
  focus_minutes_week: 1455,
  focus_seconds_week: 87300,
  stats_date: getTodayDateKey(),
});

const formatMinutesToHours = (minutes) => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hrs}h ${mins}m`;
};

// Logout
const handleLogout = () => {
  // The Authorization header is captured before the session is cleared so the
  // server can actually revoke the token - the Axios interceptor runs after
  // this synchronous block and would otherwise see an empty session.
  const headers = buildAuthHeaders() || undefined;
  axios.post(apiUrl("/auth/logout"), {}, { headers }).catch(() => {});
  clearSession();
  router.push("/");
};

const clearBrowserStorage = () => {
  const shouldClear = window.confirm(
    "Clear all FocusFlow data stored in this browser? This will sign you out and reset local preferences.",
  );
  if (!shouldClear) return;

  localStorage.clear();
  window.location.reload();
};

const closeNotificationPanelOnOutsideClick = (event) => {
  if (!notificationPanelRef.value?.contains(event.target)) {
    showNotificationPanel.value = false;
  }
};

onMounted(() => {
  replayTimerDialAnimation();
  document.addEventListener("visibilitychange", handleTimerVisibilityChange);
  window.addEventListener("focus", handleTimerVisibilityChange);
  document.addEventListener("click", closePlaylistMenuOnOutsideClick);
  document.addEventListener("click", closeNotificationPanelOnOutsideClick);
  document.addEventListener("click", closeTaskListMenuOnOutsideClick);
  document.addEventListener("fullscreenchange", handleFocusFullscreenChange);
  document.addEventListener("keydown", handleFocusFullscreenKeydown);
  document.addEventListener("scroll", positionTaskCalendarPopover, true);
  window.addEventListener("resize", keepVideoPlayerInViewport);
  window.addEventListener("resize", positionTaskCalendarPopover, { passive: true });

  // Restore legacy timer keys only for the original demo account.
  const savedTimers =
    localStorage.getItem(taskTimersStorageKey) ||
    (user.value.id === 1 ? localStorage.getItem("focusflow_task_timers") : null);
  if (savedTimers) {
    try {
      taskTimers.value = JSON.parse(savedTimers);
    } catch (error) {
      console.error("Failed to restore task timers:", error);
    }
  }

  const savedActiveTask =
    localStorage.getItem(activeTaskStorageKey) ||
    (user.value.id === 1 ? localStorage.getItem("focusflow_active_task") : null);
  if (savedActiveTask) {
    try {
      activeFocusTask.value = JSON.parse(savedActiveTask);
      const preserved = taskTimers.value[activeFocusTask.value.id];
      if (preserved && typeof preserved.remaining === "number") {
        totalTimerDuration.value = preserved.total || activeFocusTask.value.durationMinutes * 60;
        timerSecondsRemaining.value = preserved.remaining;
      }
    } catch (error) {
      console.error("Failed to restore the active focus task:", error);
    }
  }

  // Restore focus sessions
  const savedSessions = localStorage.getItem(focusSessionsStorageKey);
  if (savedSessions) {
    try {
      focusSessions.value = JSON.parse(savedSessions);
    } catch (e) {}
  }

  // Restore stats
  const savedStats = localStorage.getItem("focusflow_stats");
  if (savedStats) {
    try {
      stats.value = JSON.parse(savedStats);
    } catch (e) {}
  }

  // Restore Current Focus and check 10-minute grace period
  const savedCurrentFocus = localStorage.getItem(currentFocusStorageKey);
  if (savedCurrentFocus) {
    try {
      const parsed = JSON.parse(savedCurrentFocus);
      const secs = Number(parsed.seconds) || 0;
      currentFocusRecordedSeconds.value = Math.min(
        secs,
        Math.max(0, Number(parsed.recordedSeconds) || 0),
      );
      const pausedAt = parsed.pausedAt ? Number(parsed.pausedAt) : null;

      if (pausedAt) {
        const elapsedSincePause = Math.floor((Date.now() - pausedAt) / 1000);
        if (elapsedSincePause >= 600) {
          // 10 minutes expired while away! Reset focus
          currentFocusSeconds.value = 0;
          currentFocusRecordedSeconds.value = 0;
          pausedAtTimestamp.value = null;
          graceSecondsRemaining.value = 600;
        } else {
          // Still within grace period!
          currentFocusSeconds.value = secs;
          pausedAtTimestamp.value = pausedAt;
          graceSecondsRemaining.value = 600 - elapsedSincePause;
          startGracePeriod();
        }
      } else {
        currentFocusSeconds.value = secs;
      }
    } catch (e) {}
  }

  const restoredRunningTimer = taskTimers.value[activeFocusTask.value?.id];
  if (restoredRunningTimer?.running && Number.isFinite(Number(restoredRunningTimer.deadlineAt))) {
    isTimerRunning.value = true;
    timerDeadlineAt = Number(restoredRunningTimer.deadlineAt);
    timerLastUpdatedAt = Number(restoredRunningTimer.lastUpdatedAt) || Date.now();
    timerSessionStartedAt = Number(restoredRunningTimer.sessionStartedAt) || timerLastUpdatedAt;
    timerSessionId = restoredRunningTimer.sessionId || `${user.value.id}-${activeFocusTask.value.id}-${timerSessionStartedAt}`;
    lastTimerStorageAt = Date.now();
    runTimerTick();
    if (isTimerRunning.value) timerInterval = setInterval(runTimerTick, 1000);
  }

  // Restore ambient sounds state
  const savedAmbients = localStorage.getItem("focusflow_ambients");
  if (savedAmbients) {
    try {
      const parsed = JSON.parse(savedAmbients);
      parsed.forEach((saved) => {
        const found = ambientSounds.value.find((s) => s.id === saved.id);
        if (found) {
          found.isPlaying = Boolean(saved.isPlaying);
          if (typeof saved.volume === "number") found.volume = saved.volume;
          if (typeof saved.isFavorite === "boolean") found.isFavorite = saved.isFavorite;
          delete found.tag;
        }
      });
    } catch (e) {}
  }
  ambientFilter.value = ambientSounds.value.some((sound) => sound.isFavorite)
    ? "favorites"
    : "all";

  // Restore playlist and music state (remove any predefined playlists)
  const savedPlaylist = localStorage.getItem("focusflow_playlist");
  const savedPlaylistTitle = localStorage.getItem("focusflow_playlist_title");
  let savedActivePlaylistId = localStorage.getItem("focusflow_active_playlist_id");
  const filterSavedTracks = (tracks) =>
    tracks.filter(
      (track) =>
        track &&
        track.artist !== "Groove Salad (SomaFM)" &&
        track.artist !== "Deep Space One (SomaFM)" &&
        track.artist !== "Vaporwaves (SomaFM)" &&
        track.artist !== "Lush (SomaFM)"
    );
  const savedPlaylistsJson = localStorage.getItem("focusflow_playlists");
  if (savedPlaylistsJson) {
    try {
      const parsedPlaylists = JSON.parse(savedPlaylistsJson);
      if (Array.isArray(parsedPlaylists)) {
        savedPlaylists.value = parsedPlaylists
          .filter((saved) => saved && typeof saved.id === "string" && Array.isArray(saved.tracks))
          .map((saved) => ({
            ...saved,
            title: saved.title || "Untitled Playlist",
            tracks: filterSavedTracks(saved.tracks),
            currentTrackIndex: Number(saved.currentTrackIndex) || 0,
          }));
      }
    } catch (e) {
      savedPlaylists.value = [];
    }
  }

  const misplacedDefaultPlaylist = savedPlaylists.value.find(
    (saved) => saved.id === defaultPlaylistId && saved.title.trim().toLowerCase() !== "my songs"
  );
  if (misplacedDefaultPlaylist) {
    const legacyPlaylistId = "focusflow-legacy-imported-playlist";
    misplacedDefaultPlaylist.id = legacyPlaylistId;
    savedPlaylists.value.push({
      id: defaultPlaylistId,
      title: "My Songs",
      tracks: [],
      currentTrackIndex: 0,
    });
    if (savedActivePlaylistId === defaultPlaylistId) {
      savedActivePlaylistId = legacyPlaylistId;
    }
  }

  if (!savedPlaylists.value.length) {
    let legacyTracks = [];
    if (savedPlaylist) {
      try {
        const parsed = JSON.parse(savedPlaylist);
        if (Array.isArray(parsed)) legacyTracks = filterSavedTracks(parsed);
      } catch (e) {
        legacyTracks = [];
      }
    }
    const legacyTitle = savedPlaylistTitle?.trim();
    const isLegacyDefaultTitle =
      !legacyTitle || ["my songs", "focus playlist"].includes(legacyTitle.toLowerCase());
    if (legacyTracks.length && !isLegacyDefaultTitle) {
      const legacyPlaylistId = "focusflow-legacy-imported-playlist";
      savedPlaylists.value = [
        {
          id: legacyPlaylistId,
          title: legacyTitle,
          tracks: legacyTracks,
          currentTrackIndex: 0,
        },
        {
          id: defaultPlaylistId,
          title: "My Songs",
          tracks: [],
          currentTrackIndex: 0,
        },
      ];
      if (savedActivePlaylistId === defaultPlaylistId) {
        savedActivePlaylistId = legacyPlaylistId;
      }
    } else {
      savedPlaylists.value = [{
        id: defaultPlaylistId,
        title: "My Songs",
        tracks: legacyTracks,
        currentTrackIndex: 0,
      }];
    }
  }

  const activePlaylist =
    savedPlaylists.value.find((saved) => saved.id === savedActivePlaylistId) || savedPlaylists.value[0];
  activePlaylistId.value = activePlaylist.id;
  playlistTitle.value = activePlaylist.title;
  playlist.value = activePlaylist.tracks;
  const savedTrackIdx = localStorage.getItem("focusflow_current_track_idx");
  if (savedTrackIdx !== null && !localStorage.getItem("focusflow_playlists")) {
    try {
      activePlaylist.currentTrackIndex = Number(savedTrackIdx) || 0;
    } catch (e) {}
  }
  currentTrackIndex.value = Math.min(
    Math.max(0, activePlaylist.currentTrackIndex || 0),
    Math.max(0, playlist.value.length - 1)
  );
  nowPlayingTitle.value = currentTrack.value?.title || "";
  nowPlayingArtist.value = currentTrack.value?.artist || "";
  saveMusicState();
  saveTimersToStorage();

  updateClock();
  clockInterval = setInterval(updateClock, 1000);
  fetchTasks().then(() => {
    if (
      hasActiveFocusTask.value &&
      !tasks.value.some((task) => String(task.id) === String(activeFocusTask.value.id))
    ) {
      clearActiveFocusTask();
    }
  });
  fetchStats();
  if (localStorage.getItem(focusFullscreenOpenStorageKey) === "true") {
    openFocusFullscreen(false);
  }
});

onUnmounted(() => {
  document.removeEventListener("visibilitychange", handleTimerVisibilityChange);
  window.removeEventListener("focus", handleTimerVisibilityChange);
  document.removeEventListener("click", closePlaylistMenuOnOutsideClick);
  document.removeEventListener("click", closeNotificationPanelOnOutsideClick);
  document.removeEventListener("click", closeTaskListMenuOnOutsideClick);
  document.removeEventListener("fullscreenchange", handleFocusFullscreenChange);
  document.removeEventListener("keydown", handleFocusFullscreenKeydown);
  document.removeEventListener("scroll", positionTaskCalendarPopover, true);
  window.removeEventListener("resize", keepVideoPlayerInViewport);
  window.removeEventListener("resize", positionTaskCalendarPopover);
  stopPlaybackProgress();
  if (clockInterval) clearInterval(clockInterval);
  if (timerDialAnimationTimeout) clearTimeout(timerDialAnimationTimeout);
  if (videoPlayerControlsTimeout) clearTimeout(videoPlayerControlsTimeout);
  if (timerInterval) clearInterval(timerInterval);
  if (graceTimerInterval) clearInterval(graceTimerInterval);
  if (focusVideoQualityTimeout) clearTimeout(focusVideoQualityTimeout);
  if (focusVideoIntroTimeout) clearTimeout(focusVideoIntroTimeout);
  clearLocalFocusVideo();
  if (musicAudioElement) {
    musicAudioElement.pause();
    musicAudioElement.src = "";
    musicAudioElement = null;
  }
  Object.keys(activeAmbientNodes).forEach((id) => {
    stopAmbientSoundNode(id);
  });
});
</script>

<template>
  <div class="dashboard-layout">
    <!-- LEFT SIDEBAR -->
    <aside class="sidebar">
      <div class="sidebar-top">
        <!-- Logo -->
        <router-link class="logo-area" to="/" aria-label="FocusFlow home">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12c0-2.25.744-4.327 2-6l8 6z" />
              <path d="M12 2c2.5 3.5 3 7 1 10" />
            </svg>
          </div>
          <span class="logo-text">Focus Flow</span>
        </router-link>

        <!-- Navigation Links -->
        <nav class="nav-menu">
          <router-link
            v-for="item in navItems"
            :key="item.name"
            :to="item.to"
            class="nav-item"
            active-class="active"
            exact-active-class="active"
          >
            <i :class="item.icon"></i>
            <span>{{ item.name }}</span>
          </router-link>
        </nav>
      </div>

      <!-- Sidebar Bottom: Motivation Card -->
      <div class="sidebar-bottom">
        <div class="motivation-card">
          <div class="motivation-content">
            <p class="quote-text">"Small steps every day lead to big results."</p>
            <div class="quote-sprout">
              <i class="ti ti-leaf"></i>
            </div>
          </div>
        </div>
        <div class="sidebar-account-row">
          <button
            class="sidebar-account"
            type="button"
            @click="router.push('/profile')"
            :title="`Open ${user.username || 'account'} profile`"
          >
            <span class="user-avatar">
              {{ user.username ? user.username.charAt(0).toUpperCase() : 'A' }}
            </span>
            <span class="sidebar-account-details">
              <span class="sidebar-account-name">{{ user.username || 'Account' }}</span>
              <span class="sidebar-account-action">View profile</span>
            </span>
          </button>
          <button class="sidebar-logout-btn" type="button" @click="handleLogout" title="Log out" aria-label="Log out">
            <i class="ti ti-logout" aria-hidden="true"></i>
          </button>
        </div>
      </div>
    </aside>

    <!-- MAIN DASHBOARD CONTENT -->
    <div class="main-wrapper">
      <!-- TOP HEADER / BANNER -->
      <header class="dashboard-header">
        <div class="header-banner">
          <div class="banner-content">
            <div class="greeting-box">
              <h1 class="greeting-title">
                {{ greeting }}, {{ user.username }}!
                <button
                  :key="greetingWaveKey"
                  class="wave-emoji"
                  :class="{ 'is-waving': greetingWaveKey > 0 }"
                  type="button"
                  aria-label="Wave hello"
                  title="Wave hello"
                  @click.stop="waveGreeting"
                >👋</button>
              </h1>
              <p class="greeting-subtitle">Your focus today builds your tomorrow.</p>
            </div>

            <div class="header-right-tools">
              <div class="date-chip">
                <i class="ti ti-calendar-event" aria-hidden="true"></i>
                <span>{{ currentDate }}</span>
              </div>
              <div class="time-chip">
                <i class="ti ti-clock"></i>
                <span>{{ currentTime }}</span>
              </div>
              <div
                ref="notificationPanelRef"
                class="notification-area"
                @click.stop
                @keydown.esc.stop.prevent="showNotificationPanel = false"
              >
                <button
                  class="icon-chip notification-btn"
                  type="button"
                  title="Notifications"
                  aria-label="Notifications"
                  aria-haspopup="dialog"
                  :aria-expanded="showNotificationPanel"
                  aria-controls="notification-panel"
                  @click="showNotificationPanel = !showNotificationPanel"
                >
                  <i class="ti ti-bell" aria-hidden="true"></i>
                </button>
                <Transition name="notification-panel">
                  <section
                    v-if="showNotificationPanel"
                    id="notification-panel"
                    class="notification-panel"
                    role="dialog"
                    aria-labelledby="notification-panel-title"
                  >
                    <div class="notification-panel-header">
                      <div>
                        <h2 id="notification-panel-title">Notifications</h2>
                        <p>Updates from your focus workspace</p>
                      </div>
                      <button
                        class="notification-close-btn"
                        type="button"
                        aria-label="Close notifications"
                        @click="showNotificationPanel = false"
                      >
                        <i class="ti ti-x" aria-hidden="true"></i>
                      </button>
                    </div>
                    <div class="notification-empty-state">
                      <span class="notification-empty-icon">
                        <i class="ti ti-bell-off" aria-hidden="true"></i>
                      </span>
                      <strong>You're all caught up</strong>
                      <span>There are no new notifications right now.</span>
                    </div>
                  </section>
                </Transition>
              </div>
              <ThemeSwitcher />
              <button
                type="button"
                class="header-clear-storage-btn"
                title="Clear browser local storage"
                aria-label="Clear browser local storage"
                @click="clearBrowserStorage"
              >
                <i class="ti ti-database-x" aria-hidden="true"></i>
                <span>Clear Local Storage</span>
              </button>
              <button class="user-avatar mobile-account" type="button" @click="router.push('/profile')" title="Open profile" aria-label="Open profile">
                <span>{{ user.username ? user.username.charAt(0).toUpperCase() : 'A' }}</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- 3-COLUMN CONTENT GRID -->
      <main class="dashboard-grid">
        <!-- COLUMN 1: TODAY'S TASKS -->
        <section
          class="card tasks-card"
        >
          <div class="card-header">
            <div>
              <div class="title-with-icon">
                <div class="icon-badge purple">
                  <i class="ti ti-clipboard-check"></i>
                </div>
                <h2 class="card-title">Task Lists</h2>
                <span class="task-card-count">{{ taskLists.length }} {{ taskLists.length === 1 ? 'list' : 'lists' }}</span>
              </div>
              <p class="card-subtitle">Create separate lists and keep every task in its place.</p>
            </div>
            <div class="task-header-actions">
              <button
                ref="taskCalendarAnchorRef"
                type="button"
                class="task-date-calendar-toggle task-header-calendar-toggle"
                :aria-expanded="isTaskCalendarOpen"
                aria-haspopup="dialog"
                aria-controls="task-calendar-panel"
                :aria-label="`Choose task date. Current selection: ${selectedStudyDateLabel}`"
                :title="`Calendar · ${selectedStudyDateLabel}`"
                @click="toggleTaskCalendar"
              ><i class="ti ti-calendar-month" aria-hidden="true"></i></button>
              <button
                class="task-list-add-icon"
                type="button"
                aria-label="Create a new task list"
                title="Create a new task list"
                @click="openCreateTaskListModal"
              >
                <i class="ti ti-plus"></i>
                <span>New list</span>
              </button>
            </div>
          </div>

          <!-- Task list switcher -->
          <div class="task-list-manager">
            <div class="task-list-manager-heading">
              <div class="task-list-manager-label">
                <i class="ti ti-layout-list"></i>
                <span>Lists</span>
              </div>
              <span class="task-list-manager-count">{{ taskLists.length }} available</span>
            </div>
            <div class="task-list-switcher" @wheel="handleTaskListSwitcherWheel">
              <div
                v-for="list in taskLists"
                :key="list.id"
                class="task-list-tab-item"
                :class="{ 'is-dragging': draggedTaskListId === list.id }"
                :style="{
                  '--task-list-color': getTaskListColor(list.id),
                  '--task-list-foreground': getTaskListForeground(list.id),
                }"
                @dragover="reorderTaskList($event, list.id)"
                @drop.prevent="finishTaskListDrag"
              >
                <button
                  type="button"
                  class="task-list-tab"
                  draggable="true"
                  :class="{ active: activeTaskListId === list.id }"
                  :aria-pressed="activeTaskListId === list.id"
                  @click="selectTaskList(list.id)"
                  @dragstart="startTaskListDrag($event, list.id)"
                  @dragend="finishTaskListDrag"
                >
                  <i class="task-list-tab-icon" :class="`ti ${list.icon}`"></i>
                  <span>{{ list.name }}</span>
                  <span class="task-list-tab-count">{{ dateFilteredTaskListCount(list.id) }}</span>
                </button>
                <div class="task-list-actions-menu">
                  <button
                    type="button"
                    class="task-list-menu-trigger"
                    :aria-label="`Actions for ${list.name}`"
                    :aria-expanded="openTaskListMenu?.listId === list.id"
                    :title="`Actions for ${list.name}`"
                    @click.stop="toggleTaskListMenu($event, list)"
                  >
                    <i class="ti ti-dots-vertical" aria-hidden="true"></i>
                  </button>
                  <Teleport to="body">
                    <div
                      v-if="openTaskListMenu?.listId === list.id"
                      class="task-list-actions-dropdown"
                      role="menu"
                      :style="{ top: `${openTaskListMenu.top}px`, left: `${openTaskListMenu.left}px` }"
                    >
                      <button type="button" role="menuitem" @click="openEditTaskListModal(list)">
                        <i class="ti ti-pencil" aria-hidden="true"></i>
                        <span>Edit list</span>
                      </button>
                      <button
                        type="button"
                        role="menuitem"
                        class="delete-list-action"
                        :disabled="taskLists.length <= 1"
                        :title="taskLists.length <= 1 ? 'At least one task list must remain' : `Delete ${list.name}`"
                        @click="openTaskListMenu = null; taskListToDelete = list"
                      >
                        <i class="ti ti-trash" aria-hidden="true"></i>
                        <span>Delete list</span>
                      </button>
                    </div>
                  </Teleport>
                </div>
              </div>
            </div>
          </div>

          <Teleport to="body">
            <Transition name="task-calendar-popover">
              <section
                v-if="isTaskCalendarOpen"
                id="task-calendar-panel"
                ref="taskCalendarPanelRef"
                class="task-calendar-panel task-calendar-popover"
                role="dialog"
                aria-label="Task calendar"
                :style="taskCalendarPopoverStyle"
                @keydown.esc.stop.prevent="isTaskCalendarOpen = false"
              >
                <div class="task-calendar-heading">
                  <button type="button" class="task-date-step" aria-label="Previous month" @click="changeCalendarMonth(-1)">
                    <i class="ti ti-chevron-left" aria-hidden="true"></i>
                  </button>
                  <strong>{{ calendarMonthLabel }}</strong>
                  <button type="button" class="task-date-step" aria-label="Next month" @click="changeCalendarMonth(1)">
                    <i class="ti ti-chevron-right" aria-hidden="true"></i>
                  </button>
                  <button type="button" class="task-date-today" @click="chooseTaskDateFilter('Today'); isTaskCalendarOpen = false">Today</button>
                  <span v-if="calendarLoading" class="task-calendar-loading">Loading</span>
                </div>
                <div class="task-calendar-grid" role="grid" aria-label="Scheduled task dates">
                  <span v-for="day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']" :key="day" class="task-calendar-weekday">{{ day }}</span>
                  <button
                    v-for="day in calendarGridDays"
                    :key="day.key"
                    type="button"
                    class="task-calendar-day"
                    :class="{ 'outside-month': !day.inMonth, selected: day.isSelected, 'has-tasks': day.event?.total }"
                    :aria-label="`${day.key}${day.event?.total ? `, ${day.event.total} scheduled tasks` : ''}`"
                    :aria-pressed="day.isSelected"
                    @click="selectCalendarDay(day.key)"
                  >
                    <span>{{ day.number }}</span>
                    <small v-if="day.event?.total">{{ day.event.total }}</small>
                  </button>
                </div>
              </section>
            </Transition>
          </Teleport>

          <!-- Task filters and create action -->
          <div class="task-list-filter-row">
            <div class="filter-pills">
              <button
                class="pill"
                :class="{ active: taskFilter === 'All' }"
                @click="selectTaskFilter('All')"
              >
                All ({{ taskCounts.total }})
              </button>
              <button
                class="pill"
                :class="{ active: taskFilter === 'Pending' }"
                @click="selectTaskFilter('Pending')"
              >
                Pending ({{ taskCounts.pending }})
              </button>
              <button
                class="pill"
                :class="{ active: taskFilter === 'Completed' }"
                @click="selectTaskFilter('Completed')"
              >
                Completed ({{ taskCounts.completed }})
              </button>
              <div class="task-more-filter-menu" @keydown.esc.stop.prevent="taskFilterMenuOpen = false">
                <button
                  type="button"
                  class="task-more-filter-trigger"
                  :class="{ active: ['Skipped', 'High priority', 'Recurring'].includes(taskFilter) }"
                  :aria-expanded="taskFilterMenuOpen"
                  aria-label="More task filters"
                  title="More task filters"
                  @click.stop="taskFilterMenuOpen = !taskFilterMenuOpen"
                ><i class="ti ti-dots" aria-hidden="true"></i></button>
                <div v-if="taskFilterMenuOpen" class="task-more-filter-dropdown" role="menu" aria-label="More task filters">
                  <button
                    v-for="filter in ['Skipped', 'High priority', 'Recurring']"
                    :key="filter"
                    type="button"
                    role="menuitemradio"
                    :aria-checked="taskFilter === filter"
                    @click="selectTaskFilter(filter)"
                  >
                    <span>{{ filter }}</span>
                    <i v-if="taskFilter === filter" class="ti ti-check" aria-hidden="true"></i>
                  </button>
                </div>
              </div>
            </div>
            <button class="add-task-btn" @click="openAddTaskModal">
              <i class="ti ti-plus"></i>
              <span>Add Task</span>
            </button>
          </div>

          <div class="task-list-container">
            <div class="task-progress-panel">
              <div class="task-progress-heading">
                <div class="task-progress-summary">
                  <strong>Progress</strong>
                  <span class="task-progress-percent">{{ taskCompletionPercent }}%</span>
                </div>
              </div>
              <div
                class="task-overview-progress-track"
                role="progressbar"
                :aria-valuenow="taskCompletionPercent"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="`${taskCompletionPercent}% of tasks completed`"
              >
                <span :style="{ width: `${taskCompletionPercent}%` }"></span>
              </div>
            </div>

            <!-- Tasks List -->
            <div class="task-list">
            <div v-if="!filteredTasks.length" class="task-list-empty">
              <i class="ti ti-list-check"></i>
              <span>{{ taskFilter === 'All' ? 'This list is ready for your next task.' : `No ${taskFilter.toLowerCase()} tasks in this list.` }}</span>
            </div>
            <div
              v-for="task in filteredTasks"
              :key="task.id"
              class="task-row"
              :class="{
                'task-done': task.completed,
                'task-skipped': task.skipped,
                'task-focused': activeFocusTask && activeFocusTask.id === task.id,
              }"
              :style="{
                '--task-list-color': getTaskListColor(task.task_list_id),
                '--task-list-foreground': getTaskListForeground(task.task_list_id),
              }"
              @click="handleTaskCardClick(task)"
            >
              <div class="task-left">
                <span class="task-sequence-number" aria-hidden="true">
                  {{ getTaskListPosition(task) }}
                </span>
                <div
                  class="custom-checkbox"
                  :class="{ checked: task.completed }"
                  @click.stop="toggleTask(task)"
                  title="Mark Complete"
                >
                  <svg
                    v-if="task.completed"
                    class="task-checkbox-tick"
                    viewBox="0 0 16 16"
                    aria-hidden="true"
                  >
                    <path d="m3.25 8.25 3 3 6.5-6.5" />
                  </svg>
                </div>
                <div class="task-details">
                  <div class="task-name-line">
                    <span class="task-name" :class="{ 'strike-through': task.completed }">{{ task.title }}</span>
                    <i v-if="task.series_id" class="ti ti-repeat task-recurring-icon" title="Recurring task" aria-label="Recurring task"></i>
                    <span v-if="task.priority === 'high'" class="task-priority-high">High</span>
                  </div>
                  <span class="tag-pill">
                    {{ task.tag }}
                  </span>
                  <span class="task-date-meta">
                    <span v-if="task.scheduled_date">{{ formatTaskCalendarDate(task.scheduled_date) }}</span>
                    <span v-if="task.due_date" :class="{ 'task-overdue': task.due_date < getTodayDateKey() && !task.completed && !task.skipped }">
                      Due {{ formatTaskCalendarDate(task.due_date) }}
                    </span>
                    <span>{{ Number(task.duration_minutes) || 45 }} min</span>
                  </span>
                  <span v-if="task.notes" class="task-note-preview">{{ task.notes }}</span>
                </div>
              </div>

              <div class="task-right">
                <div class="task-status-column">
                <template v-if="task.skipped">
                  <div class="completed-meta">
                    <span class="status-check skipped-task-status">Skipped</span>
                    <span class="time-meta">Not completed</span>
                  </div>
                </template>
                <template v-else-if="task.completed">
                  <div class="completed-meta">
                    <span class="status-check">
                      <svg class="task-status-tick" viewBox="0 0 16 16" aria-hidden="true">
                        <path d="m3.25 8.25 3 3 6.5-6.5" />
                      </svg>
                      Completed
                    </span>
                    <span class="time-meta">{{ task.completed_time || 'Today' }}</span>
                    <span
                      v-if="getTaskStudiedSeconds(task.id) !== null"
                      class="task-studied-meta"
                    >
                      Studied {{ formatCurrentFocus(getTaskStudiedSeconds(task.id)) }}
                    </span>
                  </div>
                </template>
                <template v-else>
                  <div class="pending-meta" :class="{ 'live-active-timer': activeFocusTask && activeFocusTask.id === task.id }">
                    <i class="ti ti-clock"></i>
                    <span class="task-timer-text">{{ getTaskRemainingFormatted(task) }}</span>
                  </div>
                </template>
                <div class="task-progress-track" aria-hidden="true">
                  <span :style="{ width: `${getTaskProgressPercent(task)}%` }"></span>
                </div>
                </div>

                <!-- Action Buttons: Edit and Remove -->
                <div class="task-action-btns">
                  <button class="action-btn edit-btn" @click.stop="openEditTask(task)" title="Edit Task">
                    <i class="ti ti-edit"></i>
                  </button>
                  <button class="action-btn delete-btn" @click.stop="deleteTask(task)" title="Remove Task">
                    <i class="ti ti-trash"></i>
                  </button>
                </div>
              </div>
            </div>
            </div>
          </div>
        </section>

        <!-- COLUMN 2: CENTER FOCUS TIMER (FULL-WIDTH READY) -->
        <section class="card timer-card">
          <div class="timer-top-mode">
            <div class="mode-dropdown">
              <i class="ti ti-leaf"></i>
              <span>Focus Mode</span>
              <i class="ti ti-chevron-down arrow-down"></i>
            </div>
            <div class="timer-top-actions">
              <div class="timer-mode-tag">
                <span class="pulse-indicator" :class="{ running: isTimerRunning }"></span>
                <span>{{ isTimerRunning ? 'Session Active' : 'Ready' }}</span>
              </div>
              <button
                type="button"
                class="timer-fullscreen-btn"
                title="Open immersive focus"
                aria-label="Open immersive focus"
                @click="openFocusFullscreen"
              >
                <i class="ti ti-maximize" aria-hidden="true"></i>
                <span>Fullscreen</span>
              </button>
            </div>
          </div>

          <!-- Main Timer Display with Task Info and Controls -->
          <div
            class="timer-main-row"
            :class="{
              'task-is-completed': hasActiveFocusTask && activeFocusTask.completed,
              'timer-no-task-selected': !hasActiveFocusTask
            }"
          >
            <!-- Left: Circular Clock with an animated checkmark for completed tasks -->
            <div class="timer-dial-wrap">
              <div class="radial-timer-container" :class="{ 'timer-empty-dial': !hasActiveFocusTask }">
                <svg class="radial-svg" viewBox="0 0 180 180">
                  <circle
                    class="circle-bg"
                    cx="90"
                    cy="90"
                    :r="circleRadius"
                    stroke-width="8"
                  />
                  <circle
                    v-if="hasActiveFocusTask"
                    class="circle-progress"
                    :class="{ 'ring-load-animation': isTimerDialAnimating }"
                    :key="`${activeFocusTask.id}-${timerDialAnimationKey}`"
                    cx="90"
                    cy="90"
                    :r="circleRadius"
                    stroke-width="8"
                    :stroke-dasharray="circumference"
                    :stroke-dashoffset="strokeDashoffset"
                    :style="`--ring-circumference: ${circumference}px; --ring-target-offset: ${strokeDashoffset}px`"
                    stroke-linecap="round"
                  />
                  <circle
                    v-if="hasActiveFocusTask && !activeFocusTask.completed"
                    :key="`${activeFocusTask.id}-${timerDialAnimationKey}`"
                    class="circle-end-dot"
                    :class="{ 'ring-end-dot-animation': isTimerDialAnimating }"
                    cx="168"
                    cy="90"
                    r="6.5"
                    :style="`--ring-target-angle: ${timerProgressRatio * 360}deg`"
                    aria-hidden="true"
                  />
                </svg>

                <div class="radial-center-text">
                  <div v-if="!hasActiveFocusTask" class="timer-empty-center">
                    <i class="ti ti-target-arrow" aria-hidden="true"></i>
                    <span>READY</span>
                  </div>
                  <template v-else-if="activeFocusTask.completed">
                    <svg
                      :key="activeFocusTask.id"
                      class="completed-tick"
                      viewBox="0 0 24 24"
                      role="img"
                      aria-label="Task completed"
                    >
                      <path d="m5 12 4 4L19 6" />
                    </svg>
                    <span class="completed-ring-label">Completed</span>
                    <span
                      v-if="getTaskStudiedSeconds(activeFocusTask.id) !== null"
                      class="completed-study-label"
                    >
                      Studied {{ formatCurrentFocus(getTaskStudiedSeconds(activeFocusTask.id)) }}
                    </span>
                    <span class="completed-time-label">{{ activeFocusTask.completed_time || 'Done' }}</span>
                  </template>
                  <template v-else>
                    <span class="timer-digits">{{ timerFormatted }}</span>
                    <span class="timer-status-label">{{ isTimerRunning ? 'In Progress' : 'Remaining' }}</span>
                  </template>
                </div>
              </div>

            </div>

            <!-- Active task title and timer controls -->
            <div class="timer-side-controls">
              <div v-if="hasActiveFocusTask" class="active-task-info">
                <div class="task-status-row">
                  <span class="active-task-label">CURRENT TASK</span>
                  <span v-if="activeFocusTask.completed" class="completed-badge-pill">
                    <i class="ti ti-check"></i> Completed
                  </span>
                </div>
                <div class="active-task-title-row">
                  <h3 class="active-task-name" :class="{ 'task-name-completed': activeFocusTask.completed }">
                    {{ activeFocusTask.title }}
                  </h3>
                  <span class="tag-pill cyan">{{ activeFocusTask.tag }}</span>
                </div>
              </div>

              <!-- Controls: If completed, show Restart Focus / Switch Task -->
              <div
                v-if="hasActiveFocusTask && activeFocusTask.completed"
                class="timer-actions-vertical restart-only-actions"
                :class="{ 'resume-available': hasResumableCompletedTask }"
              >
                <button
                  v-if="hasResumableCompletedTask"
                  class="resume-task-btn"
                  @click="resumeCompletedTask(activeFocusTask)"
                >
                  <i class="ti ti-player-play"></i>
                  <span>Resume</span>
                </button>
                <button class="restart-task-btn" @click="restartCompletedTask(activeFocusTask)">
                  <i class="ti ti-reload"></i>
                  <span>Restart Focus</span>
                </button>
              </div>

              <!-- Controls: If not completed, show Pause/Start and Complete Early -->
              <div
                v-else-if="hasActiveFocusTask"
                class="timer-actions-vertical timer-actions-icon-row"
                role="group"
                aria-label="Active task controls"
              >
                <button
                  type="button"
                  class="timer-icon-action restart-icon-action"
                  aria-label="Restart focus timer"
                  title="Restart focus timer"
                  @click="restartActiveTaskTimer"
                >
                  <i class="ti ti-reload" aria-hidden="true"></i>
                </button>
                <button
                  type="button"
                  class="pause-btn timer-icon-action timer-label-action"
                  :aria-label="isTimerRunning ? 'Pause focus timer' : 'Start focus timer'"
                  :title="isTimerRunning ? 'Pause focus timer' : 'Start focus timer'"
                  @click="toggleTimer"
                >
                  <i :class="isTimerRunning ? 'ti ti-player-pause' : 'ti ti-player-play'"></i>
                  <span>{{ isTimerRunning ? 'Pause' : 'Play' }}</span>
                </button>
                <button
                  type="button"
                  class="complete-btn timer-icon-action"
                  aria-label="Complete task"
                  title="Complete task"
                  @click="completeEarly"
                >
                  <i class="ti ti-check" aria-hidden="true"></i>
                </button>
              </div>

              <div v-else class="timer-empty-content">
                <span class="active-task-label">NO TASK SELECTED</span>
                <h3>Your next focus starts here</h3>
                <p>Choose a task from your list or create one to begin a focus session.</p>
                <div class="timer-empty-actions">
                  <button class="timer-empty-primary" @click="chooseTaskForEmptyTimer">
                    <i :class="tasks.length ? 'ti ti-list-check' : 'ti ti-plus'"></i>
                    <span>{{ tasks.length ? 'Choose a task' : 'Add a task' }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Full Width Focus Details inside Focus Timer Card -->
          <div class="focus-details-card">
            <div class="focus-stats-quad">
              <!-- Stat 1: Current Focus (Study in One Go with 10-Minute Grace Period) -->
              <div
                class="metric-box current-focus-metric"
                :class="{
                  'in-flow': isTimerRunning,
                  'in-grace': !isTimerRunning && pausedAtTimestamp && graceSecondsRemaining > 0 && currentFocusSeconds > 0
                }"
              >
                <div class="metric-top">
                  <i class="ti ti-flame text-amber"></i>
                  <span class="metric-label">Current Focus</span>
                  <span v-if="isTimerRunning" class="live-flow-dot" title="Deep Focus In One Go"></span>
                </div>
                <div class="metric-body">
                  <span class="metric-big-time highlight-flame">{{ formatCurrentFocus(currentFocusSeconds) }}</span>
                  <div class="flow-status-sub">
                    <template v-if="isTimerRunning">
                      <span class="metric-sub text-teal"><i class="ti ti-bolt"></i> In One Go</span>
                    </template>
                    <template v-else-if="pausedAtTimestamp && graceSecondsRemaining > 0 && currentFocusSeconds > 0">
                      <span class="metric-sub text-amber grace-countdown" title="Focus resets if not resumed within 10 minutes">
                        <i class="ti ti-hourglass-empty"></i> Grace: {{ formatGraceRemaining(graceSecondsRemaining) }}
                      </span>
                    </template>
                    <template v-else-if="currentFocusSeconds > 0">
                      <span class="metric-sub text-slate">Paused</span>
                    </template>
                    <template v-else>
                      <span class="metric-sub">Study in one go</span>
                    </template>
                  </div>
                </div>
              </div>

              <!-- Stat 2: Today's Study Time -->
              <div class="metric-box">
                <div class="metric-top">
                  <i class="ti ti-calendar-stats text-teal"></i>
                  <span class="metric-label">Today's Study Time</span>
                </div>
                <div class="metric-body">
                  <span class="metric-big-time">{{ formatTotalStudyTime(totalStudySecondsToday) }}</span>
                  <span class="metric-sub">Today</span>
                </div>
              </div>

              <!-- Stat 3: Recent Focus (Time only, no subject) -->
              <div class="metric-box">
                <div class="metric-top">
                  <i class="ti ti-history text-indigo"></i>
                  <span class="metric-label">Recent Focus</span>
                </div>
                <div v-if="focusSessions.length > 0" class="metric-body">
                  <span class="metric-big-time">{{ formatSessionDuration(focusSessions[0]) }}</span>
                  <span class="metric-sub">{{ focusSessions[0].dateStr }}</span>
                </div>
                <div v-else class="metric-body">
                  <span class="metric-sub">No recent sessions</span>
                </div>
              </div>

              <!-- Stat 4: Best Focus (Time only, no subject) -->
              <div class="metric-box best-focus-metric" :class="{ 'live-record-box': bestFocusSession && bestFocusSession.isNewRecord }">
                <div class="metric-top">
                  <i class="ti ti-trophy text-amber"></i>
                  <span class="metric-label">Best Focus</span>
                  <span v-if="bestFocusSession && bestFocusSession.isNewRecord" class="live-record-tag">NEW RECORD! 🔥</span>
                </div>
                <div v-if="bestFocusSession" class="metric-body">
                  <span class="metric-big-time highlight-amber">{{ formatSessionDuration(bestFocusSession) }}</span>
                  <span class="metric-sub highlight-amber">
                    {{ bestFocusSession.isNewRecord ? 'Setting Record Live! ⚡' : 'Personal Best ⚡' }}
                  </span>
                </div>
                <div v-else class="metric-body">
                  <span class="metric-sub">Complete a session</span>
                </div>
              </div>

              <div class="metric-box">
                <div class="metric-top">
                  <i class="ti ti-chart-arrows-vertical text-green"></i>
                  <span class="metric-label">Total Study Time</span>
                </div>
                <div class="metric-body">
                  <span class="metric-big-time">{{ formatTotalStudyTime(totalStudySecondsThisWeek) }}</span>
                  <span class="metric-sub">This Week</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- COLUMN 3: AMBIENT SOUNDS & MUSIC -->
        <div class="column-right">
          <!-- Ambient Sounds Card (Squarish Design Matching Reference Image) -->
          <section class="card ambient-card">
            <div class="card-header-simple">
              <div class="title-with-icon">
                <i class="ti ti-headphones icon-teal"></i>
                <h3 class="card-title-sm">Ambient Soundscapes</h3>
              </div>
              <div class="ambient-header-actions">
                <button
                  class="mute-all-btn"
                  @click="muteAllAmbiences"
                  title="Mute all ambient sounds"
                  aria-label="Mute all ambient sounds"
                >
                  <i class="ti ti-volume-3" aria-hidden="true"></i>
                </button>
              </div>
            </div>

            <!-- Filter chips: All and Favorites -->
            <div class="ambient-filter-bar">
              <button
                class="ambient-pill"
                :class="{ active: ambientFilter === 'all' }"
                :aria-pressed="ambientFilter === 'all'"
                @click="ambientFilter = 'all'"
              >
                All ({{ ambientSounds.length }})
              </button>
              <button
                class="ambient-pill"
                :class="{ active: ambientFilter === 'favorites' }"
                :aria-pressed="ambientFilter === 'favorites'"
                @click="ambientFilter = 'favorites'"
              >
                <svg class="ambient-favorites-heart" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78Z" />
                </svg>
                Favorites ({{ favoriteAmbientSounds.length }})
              </button>
            </div>

            <!-- Reference Image Card Grid: Squarish cards with hatched pattern left block & volume slider on right -->
            <div class="ambient-ref-grid">
              <div
                v-for="snd in filteredAmbientSounds"
                :key="snd.id"
                class="amb-ref-card"
                :class="{ 'is-active': snd.isPlaying }"
                @click="toggleAmbientSound(snd)"
              >
                <!-- Left Square Block: Diagonal hatch pattern when idle, solid white with black icon when active -->
                <div
                  class="amb-hatch-block"
                  :class="[
                    `amb-tile-${snd.id}`,
                    { 'is-playing': snd.isPlaying, 'has-playing-animation': snd.isPlaying && snd.animationUrl }
                  ]"
                  :title="snd.isPlaying ? `Pause ${snd.name}` : `Play ${snd.name}`"
                >
                  <img
                    v-if="snd.isPlaying && snd.animationUrl"
                    :src="snd.animationUrl"
                    :alt="`${snd.name} animation`"
                    class="amb-playing-animation"
                    aria-hidden="true"
                  />
                  <svg
                    v-else-if="snd.id === 'waves'"
                    class="amb-block-icon waves-ambience-icon amb-icon-waves"
                    viewBox="0 0 32 32"
                    aria-hidden="true"
                  >
                    <path d="M3 11c3.25 0 3.25-4 6.5-4S12.75 11 16 11s3.25-4 6.5-4S25.75 11 29 11" />
                    <path d="M3 17c3.25 0 3.25-4 6.5-4S12.75 17 16 17s3.25-4 6.5-4S25.75 17 29 17" />
                    <path d="M3 23c3.25 0 3.25-4 6.5-4S12.75 23 16 23s3.25-4 6.5-4S25.75 23 29 23" />
                  </svg>
                  <i
                    v-else
                    :class="[snd.icon, 'amb-block-icon', `amb-icon-${snd.id}`]"
                  ></i>
                </div>

                <!-- Right Content Section: Title + Heart on top, Slider at bottom -->
                <div class="amb-content-block">
                  <div class="amb-top-row">
                    <span class="amb-title">{{ snd.name }}</span>
                    <button
                      class="amb-heart-btn"
                      :class="{ 'is-favorited': snd.isFavorite }"
                      @click.stop="toggleAmbientFavorite(snd)"
                      :aria-label="snd.isFavorite ? 'Remove favorite' : 'Add to favorites'"
                      :title="snd.isFavorite ? 'Remove favorite' : 'Add to favorites'"
                    >
                      <svg v-if="snd.isFavorite" class="amb-favorite-filled-heart" viewBox="0 0 24 24" aria-hidden="true">
                        <path fill="#ef4444" d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78Z" />
                      </svg>
                      <i v-else class="ti ti-heart" aria-hidden="true"></i>
                    </button>
                  </div>

                  <div class="amb-bottom-row">
                    <div class="amb-slider-wrap">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        v-model.number="snd.volume"
                        @input="handleAmbientSliderInput(snd)"
                        class="amb-track-slider"
                        @click.stop
                        :style="{
                          '--range-progress': `${snd.volume}%`,
                          background: snd.isPlaying
                            ? `linear-gradient(to right, #ffffff 0%, #ffffff ${snd.volume}%, rgba(255,255,255,0.18) ${snd.volume}%, rgba(255,255,255,0.18) 100%)`
                            : `linear-gradient(to right, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.35) ${snd.volume}%, rgba(255,255,255,0.1) ${snd.volume}%, rgba(255,255,255,0.1) 100%)`
                        }"
                      />
                    </div>
                    <span class="amb-vol-pct">{{ snd.volume }}%</span>
                  </div>
                </div>
              </div>
              <div
                v-if="ambientFilter === 'favorites' && favoriteAmbientSounds.length === 0"
                class="ambient-favorites-empty"
              >
                <i class="ti ti-heart-off" aria-hidden="true"></i>
                <span>No favorite sounds yet</span>
                <span>Tap a heart on a sound to add it here.</span>
              </div>
            </div>
          </section>

          <!-- MUSIC & PLAYLISTS SECTION (Matching Reference Image) -->
          <section class="card music-card ref-music-station">
            <!-- Header matching Reference Image -->
            <div class="music-ref-header">
              <div class="music-header-left">
                <div class="music-icon-pill">
                  <i class="ti ti-music"></i>
                </div>
                <div class="music-header-titles">
                  <h3 class="music-main-title">Music & Playlists</h3>
                  <span class="music-subtitle">Your perfect sound, anytime</span>
                </div>
              </div>

              <button class="music-add-link-btn" @click="showAddTrackModal = true">
                <i class="ti ti-plus"></i>
                <span>Add Link</span>
              </button>
            </div>

            <!-- HERO NOW PLAYING CARD (Exact Match to New Reference Design) -->
            <div class="hero-now-playing-box">
              <!-- TOP ROW: Artwork + Track Details + Top-Right Visualizer -->
              <div class="hero-top-row">
                <div class="hero-top-left">
                  <div class="hero-artwork-wrap">
                    <img
                      :src="currentTrack ? currentTrack.cover : '/forest_rain_cover.jpg'"
                      alt="Now Playing"
                      class="hero-artwork-img"
                    />
                  </div>
                  <div class="hero-meta-col">
                    <h4
                      class="hero-track-title"
                      :title="nowPlayingTitle || currentTrack?.title || 'Motivation'"
                    >
                      <span
                        class="hero-track-marquee"
                        :class="{ 'is-scrolling': (nowPlayingTitle || currentTrack?.title || 'Motivation').length > 36 }"
                      >
                        <span class="hero-track-marquee-track">
                          <span>{{ nowPlayingTitle || currentTrack?.title || 'Motivation' }}</span>
                          <span v-if="(nowPlayingTitle || currentTrack?.title || 'Motivation').length > 36" aria-hidden="true">
                            {{ nowPlayingTitle || currentTrack?.title || 'Motivation' }}
                          </span>
                        </span>
                      </span>
                    </h4>
                    <span class="hero-track-artist">{{ nowPlayingArtist || currentTrack?.artist || 'YouTube' }}</span>

                    <div class="hero-badge-row">
                      <!-- Source Pill (e.g. YouTube, Live Stream) -->
                      <span class="live-stream-pill">
                        <span class="live-waveform-mini">
                          <span class="lw-bar lw-1"></span>
                          <span class="lw-bar lw-2"></span>
                          <span class="lw-bar lw-3"></span>
                        </span>
                        <span>{{ currentTrack ? currentTrack.source : 'YouTube' }}</span>
                        <span class="live-green-pulse"></span>
                      </span>

                      <!-- Watch Video Toggle (Only for YouTube tracks) -->
                      <button
                        v-if="currentTrack && getTrackType(currentTrack) === 'youtube'"
                        type="button"
                        class="toggle-video-pill"
                        @click="toggleVideoPlayer"
                        :title="showVideoPlayer ? 'Hide Video' : 'Watch Video'"
                        :aria-label="showVideoPlayer ? 'Hide video' : 'Watch video'"
                        :aria-pressed="showVideoPlayer"
                      >
                        <svg
                          class="toggle-video-youtube-icon"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path d="M4.5 5.5h15A2.5 2.5 0 0 1 22 8v8a2.5 2.5 0 0 1-2.5 2.5h-15A2.5 2.5 0 0 1 2 16V8a2.5 2.5 0 0 1 2.5-2.5Z" fill="none" stroke="currentColor" stroke-width="1.8" />
                          <path d="m10 8.5 5.5 3.5-5.5 3.5v-7Z" fill="currentColor" />
                          <path d="M7 3.5 9 2M17 3.5 15 2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Top Right Mini Visualizer Bars -->
                <div class="hero-card-eq-bars" :class="{ 'is-eq-live': isMusicPlaying }">
                  <span class="hb hb-1"></span>
                  <span class="hb hb-2"></span>
                  <span class="hb hb-3"></span>
                </div>
              </div>

              <!-- BOTTOM ROW: Seeker on Left + Playback Controls on Right -->
              <div class="hero-bottom-row">
                <!-- Seeker Slider with Side Time Labels -->
                <div class="hero-seeker-container">
                  <span class="seeker-time-label">{{ trackCurrentTimeStr }}</span>
                  <div class="seeker-slider-wrap">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      :value="trackProgressPercent"
                      :disabled="!isCurrentTrackSeekable"
                      @input="handleSeek"
                      class="hero-seeker-slider"
                      :style="{
                        '--range-progress': `${trackProgressPercent}%`,
                        background: `linear-gradient(to right, var(--brand-accent) 0%, var(--brand-accent-hover) ${trackProgressPercent}%, rgba(255, 255, 255, 0.14) ${trackProgressPercent}%, rgba(255, 255, 255, 0.14) 100%)`
                      }"
                    />
                  </div>
                  <span class="seeker-time-label">{{ trackDurationStr }}</span>
                  <button
                    type="button"
                    class="hero-seek-forward-btn"
                    :disabled="!isCurrentTrackSeekable || !isMusicPlaying"
                    @click="skipForwardFiveSeconds"
                    aria-label="Forward 5 seconds"
                    title="Forward 5 seconds"
                  >
                    +5
                  </button>
                </div>

                <!-- Big Circular Controls Row -->
                <div class="hero-controls-row">
                  <button class="hero-skip-btn" @click="prevTrack" title="Previous Track">
                    <i class="ti ti-player-skip-back"></i>
                  </button>

                  <!-- BIG GLOWING PLAY/PAUSE BUTTON -->
                  <button class="hero-big-play-btn" @click="toggleMusic" :title="isMusicPlaying ? 'Pause' : 'Play'">
                    <i :class="isMusicPlaying ? 'ti ti-player-pause' : 'ti ti-player-play play-icon-offset'"></i>
                  </button>

                  <button class="hero-skip-btn" @click="nextTrack" title="Next Track">
                    <i class="ti ti-player-skip-forward"></i>
                  </button>

                  <div class="music-volume-control">
                    <button
                      type="button"
                      class="hero-skip-btn music-volume-button"
                      @click="showMusicVolume = !showMusicVolume"
                      :aria-expanded="showMusicVolume"
                      aria-label="Volume"
                      title="Volume"
                    >
                      <i class="ti ti-volume-2"></i>
                    </button>
                    <div v-if="showMusicVolume" class="music-volume-row">
                      <i class="ti ti-volume-2 music-vol-icon"></i>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        v-model.number="musicVolume"
                        @input="handleMusicVolumeInput"
                        class="music-volume-slider"
                        :style="{
                          '--range-progress': `${musicVolume}%`,
                          background: `linear-gradient(to right, var(--brand-accent) 0%, var(--brand-accent) ${musicVolume}%, rgba(255,255,255,0.1) ${musicVolume}%, rgba(255,255,255,0.1) 100%)`
                        }"
                        aria-label="Master Music Volume"
                      />
                      <span class="music-vol-val">{{ musicVolume }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <Teleport to="body">
              <div
                v-if="currentTrack && getTrackType(currentTrack) === 'youtube' && ytLoadedTrackId === currentTrack.id && getYouTubeEmbedUrl(currentTrack.url)"
                class="embedded-player-box"
                :class="{ 'video-active-frame': showVideoPlayer, 'audio-only-frame': !showVideoPlayer }"
                :style="showVideoPlayer ? {
                  left: `${videoPlayerPosition.left}px`,
                  top: `${videoPlayerPosition.top}px`,
                  width: `${videoPlayerWidth}px`,
                } : undefined"
                @pointerenter="revealVideoPlayerControls"
                @pointermove="revealVideoPlayerControls"
              >
                <div
                  v-if="showVideoPlayer"
                  class="floating-video-header"
                  @pointerdown="startVideoPlayerDrag"
                  @pointermove="moveVideoPlayer"
                  @pointerup="finishVideoPlayerDrag"
                  @pointercancel="finishVideoPlayerDrag"
                  @lostpointercapture="finishVideoPlayerDrag"
                >
                  <span class="floating-video-title">
                    <i class="ti ti-grip-vertical" aria-hidden="true"></i>
                    {{ nowPlayingTitle || currentTrack?.title || 'Now Playing' }}
                  </span>
                  <div class="floating-video-header-actions">
                    <button
                      type="button"
                      class="floating-video-drag-handle"
                      aria-label="Drag music player"
                      title="Drag music player"
                      @click.prevent
                    >
                      <i class="ti ti-grip-vertical" aria-hidden="true"></i>
                    </button>
                    <button
                      v-for="preset in videoPlayerSizePresets"
                      :key="preset.label"
                      type="button"
                      class="floating-video-size"
                      :aria-label="`Set video player size to ${preset.label}`"
                      :title="`${preset.label} video size`"
                      @pointerdown.stop
                      @click="setVideoPlayerSize(preset.width)"
                    >
                      {{ preset.label }}
                    </button>
                    <button
                      type="button"
                      class="floating-video-close"
                      aria-label="Close video player"
                      title="Close video"
                      @pointerdown.stop
                      @click="closeVideoPlayer"
                    >
                      <i class="ti ti-x" aria-hidden="true"></i>
                    </button>
                  </div>
                </div>
                <iframe
                  :key="ytReloadCounter"
                  :src="getYouTubeEmbedUrl(currentTrack.url)"
                  title="YouTube Focus Player"
                  class="embedded-iframe youtube-embed"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  referrerpolicy="strict-origin-when-cross-origin"
                  allowfullscreen
                ></iframe>
                <div
                  class="floating-video-controls"
                  :class="{ 'is-hidden': !videoPlayerControlsVisible }"
                  @pointerdown.stop
                  @focusin="revealVideoPlayerControls"
                  @focusout="revealVideoPlayerControls"
                >
                  <button
                    type="button"
                    class="floating-video-control-button"
                    :aria-label="isMusicPlaying ? 'Pause video' : 'Play video'"
                    :title="isMusicPlaying ? 'Pause' : 'Play'"
                    @click="toggleMusic"
                  >
                    <i :class="isMusicPlaying ? 'ti ti-player-pause' : 'ti ti-player-play'" aria-hidden="true"></i>
                  </button>
                  <button
                    v-if="isLiveVideo"
                    type="button"
                    class="floating-video-live-button"
                    aria-label="Jump to live"
                    title="Jump to live"
                    @click="goToLive"
                  >
                    <span aria-hidden="true"></span>
                    LIVE
                  </button>
                  <span class="floating-video-time">{{ trackCurrentTimeStr }}</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    :value="trackProgressPercent"
                    class="floating-video-seeker"
                    :style="{ '--range-progress': `${trackProgressPercent}%` }"
                    aria-label="Seek video"
                    @input="handleSeek"
                  />
                  <span class="floating-video-time">{{ trackDurationStr }}</span>
                  <i class="ti ti-volume-2 floating-video-volume-icon" aria-hidden="true"></i>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    v-model.number="musicVolume"
                    class="floating-video-volume"
                    :style="{ '--range-progress': `${musicVolume}%` }"
                    aria-label="Video volume"
                    @input="handleMusicVolumeInput"
                  />
                </div>
                <button
                  v-for="handle in videoPlayerResizeHandles"
                  :key="handle.direction"
                  type="button"
                  class="floating-video-resize"
                  :class="`resize-${handle.direction}`"
                  :aria-label="`Resize video player from ${handle.label}`"
                  :title="`Drag the ${handle.label} to resize; use left and right arrow keys`"
                  @pointerdown="startVideoPlayerResize($event, handle.direction)"
                  @pointermove="moveVideoPlayerResize"
                  @pointerup="finishVideoPlayerResize"
                  @pointercancel="finishVideoPlayerResize"
                  @lostpointercapture="finishVideoPlayerResize"
                  @keydown="resizeVideoPlayerByKeyboard"
                ></button>
              </div>
            </Teleport>

            <!-- Spotify Embedded Player (Active when Spotify track is selected & playing) -->
            <div v-if="currentTrack && getTrackType(currentTrack) === 'spotify' && isMusicPlaying" class="embedded-player-box spotify-active-frame">
              <iframe
                :src="getSpotifyEmbedUrl(currentTrack.url)"
                title="Spotify Focus Player"
                class="embedded-iframe spotify-embed"
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                loading="lazy"
              ></iframe>
            </div>

            <!-- FOCUS PLAYLIST SECTION (Exact Match to Reference Image) -->
            <div class="ref-playlist-section">
              <div
                class="ref-playlist-header"
                role="button"
                tabindex="0"
                :aria-expanded="isPlaylistExpanded"
                aria-controls="saved-playlist-tracks"
                @click="isPlaylistExpanded = !isPlaylistExpanded"
                @keydown.enter.prevent="isPlaylistExpanded = !isPlaylistExpanded"
                @keydown.space.prevent="isPlaylistExpanded = !isPlaylistExpanded"
              >
                <div class="ref-playlist-header-left">
                  <i class="ti ti-list ref-list-icon"></i>
                  <div class="ref-playlist-titles">
                    <div class="ref-playlist-title-row">
                      <span class="ref-playlist-title">{{ activeSavedPlaylist?.title || playlistTitle }}</span>
                      <span class="ref-tracks-badge">{{ playlist.length }}</span>
                      <div
                        ref="playlistPickerRef"
                        class="playlist-picker"
                        @click.stop
                        @keydown.stop
                        @keydown.esc.stop.prevent="isPlaylistMenuOpen = false"
                      >
                        <button
                          ref="playlistPickerButton"
                          type="button"
                          class="playlist-picker-trigger"
                          aria-label="Choose playlist"
                          aria-haspopup="listbox"
                          :aria-expanded="isPlaylistMenuOpen"
                          title="Choose playlist"
                          @click.stop="isPlaylistMenuOpen = !isPlaylistMenuOpen"
                        >
                          <i class="ti ti-dots" aria-hidden="true"></i>
                        </button>
                        <div
                          v-if="isPlaylistMenuOpen"
                          class="playlist-picker-menu"
                          role="listbox"
                          aria-label="Saved playlists"
                        >
                          <button
                            v-for="saved in savedPlaylists"
                            :key="saved.id"
                            type="button"
                            class="playlist-picker-option"
                            :class="{ 'is-selected': saved.id === activePlaylistId }"
                            role="option"
                            :aria-selected="saved.id === activePlaylistId"
                            @click="choosePlaylist(saved.id)"
                          >
                            <span class="playlist-picker-option-title">{{ saved.title }}</span>
                            <span class="playlist-picker-option-count">{{ saved.tracks.length }}</span>
                            <i
                              v-if="saved.id === activePlaylistId"
                              class="ti ti-check playlist-picker-check"
                              aria-hidden="true"
                            ></i>
                          </button>
                        </div>
                      </div>
                    </div>
                    <span class="ref-playlist-sub">{{ isPlaylistExpanded ? 'Click to hide songs' : 'Click to view songs' }}</span>
                  </div>
                </div>
                <div class="ref-playlist-header-right">
                  <button
                    type="button"
                    class="playlist-show-all-btn"
                    aria-label="Show all songs"
                    title="Show all songs"
                    @click.stop="isPlaylistTracksModalOpen = true"
                    @keydown.stop
                  >
                    <i class="ti ti-list" aria-hidden="true"></i>
                  </button>
                  <i
                    class="ti ti-chevron-down playlist-expand-icon"
                    :class="{ expanded: isPlaylistExpanded }"
                    aria-hidden="true"
                  ></i>
                </div>
              </div>

              <div v-if="isPlaylistExpanded" id="saved-playlist-tracks" class="ref-tracks-list">
                <div v-if="playlist.length === 0" class="empty-playlist-box">
                  <i class="ti ti-music-off empty-playlist-icon"></i>
                  <span class="empty-playlist-msg">No tracks in playlist yet</span>
                  <span class="empty-playlist-sub">Click <strong>+ Add Link</strong> above to paste a YouTube playlist or video!</span>
                </div>

                <div
                  v-for="(trk, idx) in playlist"
                  :key="trk.id"
                  class="ref-track-card"
                  :class="{ 'is-active-track': idx === currentTrackIndex }"
                  @click="playTrack(idx)"
                >
                  <div class="track-card-left">
                    <!-- Left Slot: Waveform when playing, bullet dot when idle -->
                    <div class="track-status-slot">
                      <div v-if="idx === currentTrackIndex && isMusicPlaying" class="row-playing-wave">
                        <span class="rw-bar rw-1"></span>
                        <span class="rw-bar rw-2"></span>
                        <span class="rw-bar rw-3"></span>
                      </div>
                      <span v-else-if="idx === currentTrackIndex" class="row-paused-dot"></span>
                      <span v-else class="row-idle-bullet"></span>
                    </div>

                    <img :src="trk.cover || '/forest_rain_cover.jpg'" alt="" class="track-card-thumb" />

                    <div class="track-card-info">
                      <span class="track-card-name">{{ trk.title }}</span>
                      <span class="track-card-source">{{ trk.source }} • {{ trk.artist }}</span>
                    </div>
                  </div>

                  <div class="track-card-right">
                    <!-- Now Playing Badge if active -->
                    <span v-if="idx === currentTrackIndex" class="now-playing-pill">
                      Now Playing
                    </span>
                    <span v-else class="row-idle-eq-icon">
                      <i class="ti ti-chart-bar font-small"></i>
                    </span>

                    <!-- Heart Favorite Button -->
                    <button
                      class="track-heart-btn"
                      :class="{ 'is-fav': trk.isFavorite }"
                      @click.stop="toggleTrackFavorite(trk)"
                      :aria-label="trk.isFavorite ? 'Remove from favorites' : 'Add to favorites'"
                      :title="trk.isFavorite ? 'Remove from favorites' : 'Add to favorites'"
                    >
                      <svg v-if="trk.isFavorite" class="track-heart-filled" viewBox="0 0 24 24" aria-hidden="true">
                        <path fill="#ef4444" d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78Z" />
                      </svg>
                      <i v-else class="ti ti-heart" aria-hidden="true"></i>
                    </button>

                    <button
                      type="button"
                      class="track-options-btn"
                      :aria-label="`Remove ${trk.title} from playlist`"
                      title="Remove from playlist"
                      @click.stop="removeTrackFromPlaylist(idx)"
                    >
                      <i class="ti ti-trash" aria-hidden="true"></i>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <Teleport to="body">
            <div
              v-if="isPlaylistTracksModalOpen"
              class="modal-overlay playlist-tracks-modal-overlay"
              role="presentation"
              @click.self="isPlaylistTracksModalOpen = false"
              @keydown.esc="isPlaylistTracksModalOpen = false"
            >
              <section
                class="modal-box playlist-tracks-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="playlist-tracks-modal-title"
              >
                <div class="modal-header">
                  <div>
                    <h3 id="playlist-tracks-modal-title">All songs</h3>
                    <p class="playlist-tracks-modal-subtitle">
                      {{ activeSavedPlaylist?.title || playlistTitle }} · {{ playlist.length }} songs
                    </p>
                  </div>
                  <button
                    type="button"
                    class="close-modal-btn"
                    aria-label="Close song list"
                    @click="isPlaylistTracksModalOpen = false"
                  >
                    <i class="ti ti-x" aria-hidden="true"></i>
                  </button>
                </div>
                <div v-if="playlist.length" class="playlist-tracks-modal-list">
                  <button
                    v-for="(track, index) in playlist"
                    :key="track.id"
                    type="button"
                    class="playlist-modal-track"
                    :class="{ 'is-current': index === currentTrackIndex }"
                    @click="selectPlaylistTrack(index)"
                  >
                    <img
                      :src="track.cover || '/forest_rain_cover.jpg'"
                      alt=""
                      class="playlist-modal-track-artwork"
                    />
                    <span class="playlist-modal-track-copy">
                      <span class="playlist-modal-track-title">{{ track.title }}</span>
                      <span class="playlist-modal-track-artist">{{ track.artist || track.source || 'Unknown artist' }}</span>
                    </span>
                    <span v-if="index === currentTrackIndex" class="playlist-modal-current">
                      <i class="ti ti-volume-2" aria-hidden="true"></i>
                      {{ isMusicPlaying ? 'Playing' : 'Selected' }}
                    </span>
                    <i v-else class="ti ti-player-play playlist-modal-play-icon" aria-hidden="true"></i>
                  </button>
                </div>
                <div v-else class="playlist-tracks-modal-empty">
                  <i class="ti ti-music-off" aria-hidden="true"></i>
                  <span>No songs in this playlist yet.</span>
                </div>
              </section>
            </div>
          </Teleport>
        </div>
      </main>

      <!-- Bottom page breathing room spacer -->
      <div class="bottom-page-spacer"></div>
    </div>

      <!-- ADD MUSIC LINK MODAL -->
      <div
        v-if="showAddTrackModal"
        class="modal-overlay music-link-modal-overlay"
        @click.self="showAddTrackModal = false"
        @keydown.esc="showAddTrackModal = false"
      >
        <div class="modal-box music-link-modal" role="dialog" aria-modal="true" aria-labelledby="music-link-modal-title">
          <div class="modal-header">
            <div>
              <h3 id="music-link-modal-title">Add a music link</h3>
              <p class="music-link-modal-subtitle">Playlist, video, or audio stream.</p>
            </div>
            <button
              class="close-modal-btn"
              type="button"
              aria-label="Close"
              :disabled="isAddingMusic"
              @click="showAddTrackModal = false"
            >
              <i class="ti ti-x"></i>
            </button>
          </div>

          <form @submit.prevent="addMusicLink" class="add-music-form">
            <p v-if="musicError" class="music-link-error" role="alert">{{ musicError }}</p>
            <div class="form-input-group">
              <label for="music-link-url">Link</label>
              <div class="input-with-icon">
                <i class="ti ti-link"></i>
                <input
                  id="music-link-url"
                  type="url"
                  v-model="newTrackUrl"
                  placeholder="Paste a playlist, video, or stream URL"
                  required
                  autofocus
                />
              </div>
            </div>

            <div class="form-row-duo">
              <div class="form-input-group flex-1">
                <label for="music-link-title">Title <span class="optional-label">Optional</span></label>
                <input
                  id="music-link-title"
                  type="text"
                  v-model="newTrackTitle"
                  placeholder="Track or playlist name"
                />
              </div>
              <div class="form-input-group flex-1">
                <label for="music-link-artist">Artist / channel <span class="optional-label">Optional</span></label>
                <input
                  id="music-link-artist"
                  type="text"
                  v-model="newTrackArtist"
                  placeholder="Name"
                />
              </div>
            </div>

            <div class="form-actions-right">
              <button
                type="button"
                class="btn-cancel-music"
                @click="showAddTrackModal = false"
                :disabled="isAddingMusic"
              >
                Cancel
              </button>
              <button type="submit" class="btn-save-music" :disabled="isAddingMusic">
                <i :class="isAddingMusic ? 'ti ti-loader spin-pulse' : 'ti ti-plus'"></i>
                <span>{{ isAddingMusic ? 'Adding...' : 'Add link' }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- CREATE TASK LIST MODAL -->
      <div
        v-if="showCreateTaskListModal"
        class="modal-overlay focus-dialog-overlay"
        @click.self="showCreateTaskListModal = false"
        @keydown.esc="showCreateTaskListModal = false"
      >
        <div
          class="modal-box focus-dialog focus-dialog--list"
          :style="{
            '--task-list-color': newTaskListColor,
            '--task-list-foreground': taskListForegroundForColor(newTaskListColor),
          }"
          role="dialog"
          aria-modal="true"
          aria-labelledby="task-list-modal-title"
        >
          <div class="modal-header">
            <div class="modal-title-block">
              <span class="modal-icon" aria-hidden="true">
                <i class="ti" :class="newTaskListIcon"></i>
              </span>
              <div>
                <h3 id="task-list-modal-title">{{ editingTaskListId ? 'Edit task list' : 'Create a task list' }}</h3>
                <p class="modal-subtitle">
                  {{ editingTaskListId
                    ? 'Update this list’s name, color, or icon.'
                    : 'Name it, pick a color, and choose an icon so it stands out in your workspace.' }}
                </p>
              </div>
            </div>
            <button class="close-modal-btn" type="button" aria-label="Close" @click="showCreateTaskListModal = false">
              <i class="ti ti-x"></i>
            </button>
          </div>
          <form @submit.prevent="createTaskList" class="task-form">
            <section class="form-section">
              <h4 class="form-section-title"><i class="ti ti-pencil" aria-hidden="true"></i> List details</h4>
              <div class="modal-group">
                <label for="task-list-name">List name <span class="required">*</span></label>
                <input
                  id="task-list-name"
                  v-model="newTaskListName"
                  type="text"
                  maxlength="32"
                  placeholder="e.g. Exam preparation"
                  required
                  autofocus
                />
              </div>
            </section>

            <section class="form-section">
              <h4 class="form-section-title"><i class="ti ti-palette" aria-hidden="true"></i> Appearance</h4>
              <div class="modal-group">
                <label>Color</label>
                <div class="task-list-color-options">
                  <button
                    v-for="color in taskListColors"
                    :key="color"
                    class="task-list-color-swatch"
                    :class="{ selected: newTaskListColor === color }"
                    :style="{ backgroundColor: color }"
                    type="button"
                    :aria-label="`Select ${color} list color`"
                    :aria-pressed="newTaskListColor === color"
                    @click="newTaskListColor = color"
                  ></button>
                  <label class="task-list-custom-color" title="Choose a custom color">
                    <i class="ti ti-color-picker"></i>
                    <input v-model="newTaskListColor" type="color" aria-label="Choose a custom list color" />
                  </label>
                </div>
              </div>

              <div class="modal-group">
                <label>Icon</label>
                <div class="task-list-icon-options">
                  <button
                    v-for="icon in taskListIcons"
                    :key="icon"
                    class="task-list-icon-option"
                    :class="{ selected: newTaskListIcon === icon }"
                    type="button"
                    :aria-label="`Select ${icon.replace('ti-', '').replaceAll('-', ' ')} icon`"
                    :aria-pressed="newTaskListIcon === icon"
                    @click="newTaskListIcon = icon"
                  >
                    <i class="ti" :class="icon"></i>
                  </button>
                </div>
              </div>
            </section>

            <section class="form-section task-list-preview-section">
              <h4 class="form-section-title"><i class="ti ti-eye" aria-hidden="true"></i> Preview</h4>
              <div class="task-list-preview-stage">
                <span class="task-list-preview-chip" :style="{ backgroundColor: newTaskListColor }">
                  <i class="ti" :class="newTaskListIcon"></i>
                  <span>{{ newTaskListName.trim() || 'Your list' }}</span>
                  <span class="task-list-tab-count">
                    {{ editingTaskListId ? activeListTaskCount(editingTaskListId) : 0 }}
                  </span>
                </span>
                <p class="task-list-preview-hint">This is how the list will appear above your tasks.</p>
              </div>
            </section>

            <div class="modal-actions">
              <button type="button" class="cancel-btn" @click="showCreateTaskListModal = false; editingTaskListId = null">Cancel</button>
              <button type="submit" class="save-task-btn">
                <i :class="editingTaskListId ? 'ti ti-check' : 'ti ti-plus'" aria-hidden="true"></i>
                {{ editingTaskListId ? 'Save changes' : 'Create list' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- ADD TASK MODAL -->
    <div
      v-if="taskListToDelete"
      class="modal-overlay"
      @click.self="taskListToDelete = null"
      @keydown.esc="taskListToDelete = null"
    >
      <div
        class="modal-box task-list-modal task-list-delete-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-task-list-title"
      >
        <div class="modal-header">
          <div>
            <h3 id="delete-task-list-title">Delete “{{ taskListToDelete.name }}”?</h3>
            <p class="task-list-modal-subtitle">
              This list and all tasks in it will be deleted permanently.
            </p>
          </div>
          <button
            class="close-modal-btn"
            type="button"
            aria-label="Cancel"
            @click="taskListToDelete = null"
          >
            <i class="ti ti-x"></i>
          </button>
        </div>
        <div class="modal-actions">
          <button type="button" class="cancel-btn" @click="taskListToDelete = null">Keep list</button>
          <button type="button" class="delete-task-list-confirm-btn" @click="confirmDeleteTaskList">
            <i class="ti ti-trash" aria-hidden="true"></i>
            <span>Delete list</span>
          </button>
        </div>
      </div>
    </div>

            <div v-if="showAddTaskModal" class="modal-overlay focus-dialog-overlay" @click.self="showAddTaskModal = false">
      <div class="modal-box task-schedule-modal focus-dialog" role="dialog" aria-modal="true" aria-labelledby="add-task-title">
        <div class="modal-header">
          <div class="modal-title-block">
            <span class="modal-icon"><i class="ti ti-target" aria-hidden="true"></i></span>
            <div>
              <h3 id="add-task-title">Add New Focus Task</h3>
              <p class="modal-subtitle">Capture what you'll work on, when, and how often.</p>
            </div>
          </div>
          <button class="close-modal-btn" type="button" @click="showAddTaskModal = false" aria-label="Close">
            <i class="ti ti-x" aria-hidden="true"></i>
          </button>
        </div>
        <form @submit.prevent="addNewTask" class="task-form">
          <section class="form-section">
            <h4 class="form-section-title"><i class="ti ti-pencil" aria-hidden="true"></i> Task details</h4>
            <div class="modal-group">
              <label>Task Title <span class="required">*</span></label>
              <input type="text" v-model="newTaskTitle" placeholder="e.g. Organic Chemistry Revisions" required />
            </div>
            <div class="modal-group-row">
              <div class="modal-group">
                <label>Tag</label>
                <input type="text" v-model="newTaskTag" placeholder="Study" />
              </div>
              <div class="modal-group">
                <label>Duration (min)</label>
                <input type="number" v-model="newTaskMinutes" min="5" max="300" />
              </div>
            </div>
          </section>

          <section class="form-section">
            <h4 class="form-section-title"><i class="ti ti-folder" aria-hidden="true"></i> Organization</h4>
            <div class="modal-group-row">
              <div class="modal-group">
                <label>Task List</label>
                <select v-model="newTaskSchedule.task_list_id">
                  <option v-for="list in taskLists" :key="list.id" :value="list.id">{{ list.name }}</option>
                </select>
              </div>
              <div class="modal-group">
                <label>Priority</label>
                <div class="priority-segmented" role="radiogroup" aria-label="Priority">
                  <button
                    v-for="p in ['low', 'medium', 'high']"
                    :key="p"
                    type="button"
                    class="priority-seg"
                    :class="{ active: newTaskSchedule.priority === p }"
                    :aria-pressed="newTaskSchedule.priority === p"
                    @click="newTaskSchedule.priority = p"
                  >{{ p }}</button>
                </div>
              </div>
            </div>
          </section>

          <section class="form-section">
            <h4 class="form-section-title"><i class="ti ti-calendar" aria-hidden="true"></i> Schedule</h4>
            <div class="modal-group-row">
              <div class="modal-group">
                <label>Scheduled Date</label>
                <input type="date" v-model="newTaskSchedule.scheduled_date" @change="newTaskSchedule.start_date = newTaskSchedule.scheduled_date" />
              </div>
              <div class="modal-group">
                <label>Due Date <span class="optional-label">Optional</span></label>
                <input type="date" v-model="newTaskSchedule.due_date" />
              </div>
            </div>
            <div class="modal-group">
              <label>Notes <span class="optional-label">Optional</span></label>
              <textarea v-model="newTaskSchedule.notes" placeholder="Instructions or reminders" maxlength="5000" rows="3"></textarea>
            </div>
          </section>

          <details class="task-schedule-advanced" open>
            <summary><i class="ti ti-repeat" aria-hidden="true"></i> Repeat schedule</summary>
            <div class="schedule-options-grid">
              <div class="modal-group">
                <label>Repeat</label>
                <select v-model="newTaskSchedule.recurrence.frequency">
                  <option value="none">Does not repeat</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="custom">Custom interval</option>
                </select>
              </div>
              <div class="modal-group" v-if="newTaskSchedule.recurrence.frequency !== 'none'">
                <label>{{ newTaskSchedule.recurrence.frequency === 'monthly' ? 'Every N months' : newTaskSchedule.recurrence.frequency === 'weekly' ? 'Every N weeks' : 'Every N days' }}</label>
                <input type="number" v-model.number="newTaskSchedule.recurrence.interval" min="1" max="366" />
              </div>
              <div class="modal-group" v-if="newTaskSchedule.recurrence.frequency === 'custom'">
                <label>Interval Unit</label>
                <select v-model="newTaskSchedule.recurrence.unit">
                  <option value="days">Days</option>
                  <option value="weeks">Weeks</option>
                  <option value="months">Months</option>
                </select>
              </div>
              <div class="modal-group" v-if="newTaskSchedule.recurrence.frequency === 'monthly'">
                <label>Day of Month</label>
                <input type="number" v-model.number="newTaskSchedule.recurrence.day_of_month" min="1" max="31" />
              </div>
            </div>
            <div
              v-if="newTaskSchedule.recurrence.frequency === 'weekly' || (newTaskSchedule.recurrence.frequency === 'custom' && newTaskSchedule.recurrence.unit === 'weeks')"
              class="recurrence-weekdays"
              role="group"
              aria-label="Repeat weekdays"
            >
              <button
                v-for="day in recurrenceWeekdays"
                :key="day.value"
                type="button"
                :class="{ selected: newTaskSchedule.recurrence.weekdays.includes(day.value) }"
                :aria-pressed="newTaskSchedule.recurrence.weekdays.includes(day.value)"
                :title="day.title"
                @click="toggleRecurrenceWeekday(newTaskSchedule, day.value)"
              >{{ day.label }}</button>
            </div>
            <div class="modal-group-row" v-if="newTaskSchedule.recurrence.frequency !== 'none'">
              <div class="modal-group">
                <label>Start Date</label>
                <input type="date" v-model="newTaskSchedule.start_date" required />
              </div>
              <div class="modal-group">
                <label>Ends</label>
                <select v-model="newTaskSchedule.recurrence.end_condition">
                  <option value="never">Never</option>
                  <option value="date">On date</option>
                  <option value="count">After occurrences</option>
                </select>
              </div>
              <div class="modal-group" v-if="newTaskSchedule.recurrence.end_condition === 'date'">
                <label>End Date</label>
                <input type="date" v-model="newTaskSchedule.recurrence.end_date" :min="newTaskSchedule.start_date" required />
              </div>
              <div class="modal-group" v-if="newTaskSchedule.recurrence.end_condition === 'count'">
                <label>Occurrences</label>
                <input type="number" v-model.number="newTaskSchedule.recurrence.occurrence_count" min="1" max="10000" required />
              </div>
            </div>
            <p class="recurrence-preview">{{ recurrenceSummary(newTaskSchedule.recurrence) }}</p>
          </details>
          <p v-if="taskFormError" class="task-form-error" role="alert">{{ taskFormError }}</p>
          <div class="modal-actions">
            <button type="button" class="cancel-btn" @click="showAddTaskModal = false">Cancel</button>
            <button type="submit" class="save-task-btn"><i class="ti ti-check" aria-hidden="true"></i> Create Task</button>
          </div>
        </form>
      </div>
    </div>


    <!-- EDIT TASK MODAL -->
    <div v-if="showEditTaskModal" class="modal-overlay focus-dialog-overlay" @click.self="showEditTaskModal = false">
      <div class="modal-box task-schedule-modal focus-dialog" role="dialog" aria-modal="true" aria-labelledby="edit-task-title">
        <div class="modal-header">
          <div class="modal-title-block">
            <span class="modal-icon"><i class="ti ti-pencil" aria-hidden="true"></i></span>
            <div>
              <h3 id="edit-task-title">Edit focus task</h3>
              <p class="modal-subtitle">Update what you'll work on, when, and how often.</p>
            </div>
          </div>
          <button class="close-modal-btn" type="button" @click="showEditTaskModal = false" aria-label="Close">
            <i class="ti ti-x" aria-hidden="true"></i>
          </button>
        </div>
        <form @submit.prevent="saveEditedTask" class="task-form">
          <section class="form-section">
            <h4 class="form-section-title"><i class="ti ti-pencil" aria-hidden="true"></i> Task details</h4>
            <div class="modal-group">
              <label>Task Title <span class="required">*</span></label>
              <input type="text" v-model="editTaskTitle" placeholder="Task Title" required />
            </div>
            <div class="modal-group-row">
              <div class="modal-group">
                <label>Tag</label>
                <input type="text" v-model="editTaskTag" placeholder="Study" />
              </div>
              <div class="modal-group">
                <label>Duration (min)</label>
                <input type="number" v-model="editTaskMinutes" min="5" max="300" />
              </div>
            </div>
          </section>

          <section class="form-section">
            <h4 class="form-section-title"><i class="ti ti-folder" aria-hidden="true"></i> Organization</h4>
            <div class="modal-group-row">
              <div class="modal-group">
                <label>Task List</label>
                <select v-model="editTaskSchedule.task_list_id">
                  <option v-for="list in taskLists" :key="list.id" :value="list.id">{{ list.name }}</option>
                </select>
              </div>
              <div class="modal-group">
                <label>Priority</label>
                <div class="priority-segmented" role="radiogroup" aria-label="Priority">
                  <button
                    v-for="p in ['low', 'medium', 'high']"
                    :key="p"
                    type="button"
                    class="priority-seg"
                    :class="{ active: editTaskSchedule.priority === p }"
                    :aria-pressed="editTaskSchedule.priority === p"
                    @click="editTaskSchedule.priority = p"
                  >{{ p }}</button>
                </div>
              </div>
            </div>
          </section>

          <section class="form-section">
            <h4 class="form-section-title"><i class="ti ti-calendar" aria-hidden="true"></i> Schedule</h4>
            <div class="modal-group-row">
              <div class="modal-group">
                <label>Scheduled Date</label>
                <input type="date" v-model="editTaskSchedule.scheduled_date" />
              </div>
              <div class="modal-group">
                <label>Due Date <span class="optional-label">Optional</span></label>
                <input type="date" v-model="editTaskSchedule.due_date" />
              </div>
            </div>
            <div class="modal-group">
              <label>Notes <span class="optional-label">Optional</span></label>
              <textarea v-model="editTaskSchedule.notes" placeholder="Instructions or reminders" maxlength="5000" rows="3"></textarea>
            </div>
          </section>

          <details class="task-schedule-advanced" :open="Boolean(tasks.find(task => task.id === editingTaskId)?.series_id)">
            <summary><i class="ti ti-repeat" aria-hidden="true"></i> Repeat schedule</summary>
            <div class="modal-group" v-if="tasks.find(task => task.id === editingTaskId)?.series_id">
              <label>Apply changes to</label>
              <select v-model="editTaskScope">
                <option value="this">This occurrence only</option>
                <option value="future">This and future occurrences</option>
                <option value="series">Entire series</option>
              </select>
            </div>
            <div class="schedule-options-grid">
              <div class="modal-group">
                <label>Repeat</label>
                <select
                  :value="editTaskSchedule.recurrence.frequency"
                  @change="setEditRecurrenceFrequency($event.target.value)"
                >
                  <option
                    v-if="!tasks.find(task => task.id === editingTaskId)?.series_id"
                    value="none"
                  >Does not repeat</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="custom">Custom interval</option>
                </select>
              </div>
              <div class="modal-group" v-if="editTaskSchedule.recurrence.frequency !== 'none'">
                <label>{{ editTaskSchedule.recurrence.frequency === 'monthly' ? 'Every N months' : editTaskSchedule.recurrence.frequency === 'weekly' ? 'Every N weeks' : 'Every N days' }}</label>
                <input type="number" v-model.number="editTaskSchedule.recurrence.interval" min="1" max="366" />
              </div>
              <div class="modal-group" v-if="editTaskSchedule.recurrence.frequency === 'custom'">
                <label>Interval Unit</label>
                <select v-model="editTaskSchedule.recurrence.unit">
                  <option value="days">Days</option>
                  <option value="weeks">Weeks</option>
                  <option value="months">Months</option>
                </select>
              </div>
              <div class="modal-group" v-if="editTaskSchedule.recurrence.frequency === 'monthly'">
                <label>Day of Month</label>
                <input type="number" v-model.number="editTaskSchedule.recurrence.day_of_month" min="1" max="31" />
              </div>
            </div>
            <div
              v-if="editTaskSchedule.recurrence.frequency === 'weekly' || (editTaskSchedule.recurrence.frequency === 'custom' && editTaskSchedule.recurrence.unit === 'weeks')"
              class="recurrence-weekdays"
              role="group"
              aria-label="Repeat weekdays"
            >
              <button
                v-for="day in recurrenceWeekdays"
                :key="day.value"
                type="button"
                :class="{ selected: editTaskSchedule.recurrence.weekdays.includes(day.value) }"
                :aria-pressed="editTaskSchedule.recurrence.weekdays.includes(day.value)"
                :title="day.title"
                @click="toggleRecurrenceWeekday(editTaskSchedule, day.value)"
              >{{ day.label }}</button>
            </div>
            <div class="modal-group-row" v-if="editTaskSchedule.recurrence.frequency !== 'none'">
              <div class="modal-group">
                <label>Series Start Date</label>
                <input type="date" v-model="editTaskSchedule.start_date" required />
              </div>
              <div class="modal-group">
                <label>Ends</label>
                <select v-model="editTaskSchedule.recurrence.end_condition">
                  <option value="never">Never</option>
                  <option value="date">On date</option>
                  <option value="count">After occurrences</option>
                </select>
              </div>
              <div class="modal-group" v-if="editTaskSchedule.recurrence.end_condition === 'date'">
                <label>End Date</label>
                <input type="date" v-model="editTaskSchedule.recurrence.end_date" :min="editTaskSchedule.start_date" required />
              </div>
              <div class="modal-group" v-if="editTaskSchedule.recurrence.end_condition === 'count'">
                <label>Occurrences</label>
                <input type="number" v-model.number="editTaskSchedule.recurrence.occurrence_count" min="1" max="10000" required />
              </div>
            </div>
            <p class="recurrence-preview">{{ recurrenceSummary(editTaskSchedule.recurrence) }}</p>
          </details>
          <p v-if="taskFormError" class="task-form-error" role="alert">{{ taskFormError }}</p>
          <div class="modal-actions">
            <button type="button" class="cancel-btn" @click="showEditTaskModal = false">Cancel</button>
            <button type="submit" class="save-task-btn"><i class="ti ti-check" aria-hidden="true"></i> Save changes</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showDeleteTaskModal" class="modal-overlay" @click.self="showDeleteTaskModal = false">
      <div class="modal-box task-delete-modal">
        <div class="modal-header">
          <h3>{{ taskBeingDeleted?.series_id ? 'Remove recurring task' : 'Remove task' }}</h3>
          <button type="button" class="close-modal-btn" aria-label="Close" @click="showDeleteTaskModal = false">
            <i class="ti ti-x" aria-hidden="true"></i>
          </button>
        </div>
        <p class="task-delete-copy">
          {{ taskBeingDeleted?.series_id
            ? `Choose what to remove for “${taskBeingDeleted.title}”.`
            : `Remove “${taskBeingDeleted?.title}”? Completed history is preserved.` }}
        </p>
        <div v-if="taskBeingDeleted?.series_id" class="modal-group">
          <label>Apply to</label>
          <select v-model="taskDeleteScope">
            <option value="this">Skip this occurrence only</option>
            <option value="future">Stop this and future occurrences</option>
            <option value="series">Stop the entire series</option>
          </select>
        </div>
        <p v-if="taskFormError" class="task-form-error" role="alert">{{ taskFormError }}</p>
        <div class="modal-actions">
          <button type="button" class="cancel-btn" @click="showDeleteTaskModal = false">Cancel</button>
          <button type="button" class="delete-task-list-confirm-btn" @click="confirmDeleteTask">
            <i class="ti ti-trash" aria-hidden="true"></i>
            <span>{{ taskDeleteScope === 'this' && taskBeingDeleted?.series_id ? 'Skip occurrence' : 'Remove task' }}</span>
          </button>
        </div>
      </div>
    </div>

  </div>

  <Teleport to="body">
    <section
      v-if="isFocusFullscreenOpen"
      ref="focusFullscreenRoot"
      class="focus-immersive"
      role="dialog"
      aria-modal="true"
      aria-label="Immersive focus session"
      tabindex="-1"
    >
      <iframe
        v-if="focusVideoEmbedUrl"
        :key="focusVideoEmbedUrl"
        ref="focusBackgroundEmbedRef"
        class="focus-immersive-background-video focus-immersive-background-embed"
        :class="{ 'is-intro': isFocusVideoIntroActive }"
        :src="focusVideoEmbedUrl"
        title="Ambient background video"
        allow="autoplay; encrypted-media; picture-in-picture"
        referrerpolicy="strict-origin-when-cross-origin"
        @load="handleFocusEmbedLoad"
      ></iframe>
      <video
        v-else-if="focusVideoUrl"
        :key="focusVideoUrl"
        ref="focusBackgroundVideoRef"
        class="focus-immersive-background-video"
        :src="focusVideoUrl"
        autoplay
        :muted="isFocusVideoMuted"
        loop
        playsinline
        aria-hidden="true"
        @error="handleFocusVideoError"
        @loadeddata="captureFocusVideoPoster"
        @loadedmetadata="applyFocusVideoAudioToNative"
        @play="isFocusVideoPlaying = true"
        @pause="isFocusVideoPlaying = false"
      ></video>
      <div
        v-if="isFocusVideoIntroActive"
        class="focus-immersive-video-reveal"
        aria-hidden="true"
        @animationend="finishFocusVideoIntro"
      ></div>
      <div class="focus-immersive-backdrop" aria-hidden="true"></div>
      <div
        v-if="focusVideoEmbedUrl && !isFocusVideoPlaying"
        class="focus-video-paused-cover"
        aria-hidden="true"
      ></div>

      <button
        type="button"
        class="focus-immersive-close"
        aria-label="Exit immersive focus"
        title="Exit fullscreen (Esc)"
        @click="closeFocusFullscreen"
      >
        <i class="ti ti-minimize" aria-hidden="true"></i>
      </button>

      <div v-if="focusFullscreenError" class="focus-immersive-notice" role="status">
        <span>{{ focusFullscreenError }}</span>
        <button
          v-if="shouldRestoreFullscreenAfterVideoPicker"
          type="button"
          @click="restoreFocusBrowserFullscreen"
        >
          Return to fullscreen
        </button>
      </div>
      <p v-if="focusVideoError" class="focus-immersive-notice video-error" role="alert">
        {{ focusVideoError }}
      </p>

      <nav class="focus-immersive-dock" aria-label="Focus panels">
        <button
          type="button"
          :class="{ active: focusPanels.timer.open }"
          :aria-pressed="focusPanels.timer.open"
          aria-label="Open focus timer panel"
          title="Focus timer"
          @click="openFocusPanel('timer')"
        >
          <i class="ti ti-focus-2" aria-hidden="true"></i>
        </button>
        <button
          type="button"
          :class="{ active: focusPanels.competitors.open }"
          :aria-pressed="focusPanels.competitors.open"
          aria-label="Open competitors panel"
          title="Study with others"
          @click="openFocusPanel('competitors')"
        >
          <i class="ti ti-users" aria-hidden="true"></i>
        </button>
        <button
          type="button"
          :class="{ active: focusPanels.video.open }"
          :aria-pressed="focusPanels.video.open"
          aria-label="Open background video panel"
          title="Background video"
          @click="openFocusPanel('video')"
        >
          <i class="ti ti-movie" aria-hidden="true"></i>
        </button>
        <button
          type="button"
          :class="{ active: focusPanels.music.open }"
          :aria-pressed="focusPanels.music.open"
          aria-label="Open music player panel"
          title="Music player"
          @click="openFocusPanel('music')"
        >
          <i class="ti ti-music" aria-hidden="true"></i>
        </button>
      </nav>

      <div
        v-if="focusPanels.timer.open"
        class="focus-immersive-panel focus-immersive-panel-timer"
        data-focus-panel="timer"
        :style="focusPanelPositionStyle('timer')"
        @pointerdown="startFocusPanelDrag($event, 'timer')"
        @pointermove="moveFocusPanel($event, 'timer')"
        @pointerup="finishFocusPanelDrag($event, 'timer')"
        @pointercancel="finishFocusPanelDrag($event, 'timer')"
        @lostpointercapture="finishFocusPanelDrag($event, 'timer')"
      >
        <section class="focus-immersive-card focus-immersive-timer">
          <div class="focus-panel-header">
            <span class="focus-panel-heading">
              <i class="ti ti-focus-2" aria-hidden="true"></i>
              Focus timer
              <span class="focus-immersive-live" :class="{ running: isTimerRunning }">
                <span></span>{{ isTimerRunning ? "Focusing" : "Paused" }}
              </span>
            </span>
            <div class="focus-panel-actions">
              <button type="button" aria-label="Close focus timer panel" title="Close panel" @click="closeFocusPanel('timer')">
                <i class="ti ti-x" aria-hidden="true"></i>
              </button>
              <button
                type="button"
                :aria-pressed="focusPanels.timer.pinned"
                :aria-label="focusPanels.timer.pinned ? 'Unpin focus timer panel' : 'Pin focus timer panel'"
                :title="focusPanels.timer.pinned ? 'Unpin panel' : 'Pin panel'"
                @click="toggleFocusPanelPin('timer')"
              >
                <i :class="focusPanels.timer.pinned ? 'ti ti-pin-filled' : 'ti ti-pin'" aria-hidden="true"></i>
              </button>
            </div>
          </div>
          <h1>{{ hasActiveFocusTask ? activeFocusTask.title : "No task selected" }}</h1>
          <p class="focus-immersive-task-meta">
            {{ hasActiveFocusTask ? activeFocusTask.tag || "Focus session" : "Choose a task from your dashboard to begin." }}
          </p>
          <div class="focus-immersive-countdown">
            {{ hasActiveFocusTask ? timerFormatted : "00:00:00" }}
          </div>
          <div class="focus-immersive-progress" aria-hidden="true">
            <span :style="{ width: `${timerProgressRatio * 100}%` }"></span>
          </div>
          <div class="focus-immersive-timer-actions">
            <button
              v-if="hasActiveFocusTask && !activeFocusTask.completed"
              type="button"
              class="focus-immersive-action primary"
              @click="toggleTimer"
            >
              <i :class="isTimerRunning ? 'ti ti-player-pause' : 'ti ti-player-play'" aria-hidden="true"></i>
              {{ isTimerRunning ? "Pause" : "Start focus" }}
            </button>
            <button
              v-else-if="hasActiveFocusTask"
              type="button"
              class="focus-immersive-action primary"
              @click="restartCompletedTask(activeFocusTask)"
            >
              <i class="ti ti-reload" aria-hidden="true"></i>
              Restart
            </button>
            <button
              v-if="hasResumableCompletedTask"
              type="button"
              class="focus-immersive-action secondary"
              @click="resumeCompletedTask(activeFocusTask)"
            >
              <i class="ti ti-player-play" aria-hidden="true"></i>
              Resume
            </button>
            <span v-if="!hasActiveFocusTask" class="focus-immersive-hint">Select a task on the dashboard to start.</span>
            <button
              v-if="hasActiveFocusTask && !activeFocusTask.completed"
              type="button"
              class="focus-immersive-action secondary"
              @click="completeEarly"
            >
              <i class="ti ti-check" aria-hidden="true"></i>
              Finish
            </button>
          </div>
        </section>
      </div>

      <div
        v-if="focusPanels.competitors.open"
        class="focus-immersive-panel focus-immersive-panel-competitors"
        data-focus-panel="competitors"
        :style="focusPanelPositionStyle('competitors')"
        @pointerdown="startFocusPanelDrag($event, 'competitors')"
        @pointermove="moveFocusPanel($event, 'competitors')"
        @pointerup="finishFocusPanelDrag($event, 'competitors')"
        @pointercancel="finishFocusPanelDrag($event, 'competitors')"
        @lostpointercapture="finishFocusPanelDrag($event, 'competitors')"
      >
        <section class="focus-immersive-card focus-immersive-competitors" aria-label="Competitors studying">
          <div class="focus-panel-header">
            <span class="focus-panel-heading">
              <i class="ti ti-users" aria-hidden="true"></i>
              Study with others
              <i class="ti ti-world" aria-hidden="true"></i>
            </span>
            <div class="focus-panel-actions">
              <button type="button" aria-label="Close competitors panel" title="Close panel" @click="closeFocusPanel('competitors')">
                <i class="ti ti-x" aria-hidden="true"></i>
              </button>
              <button
                type="button"
                :aria-pressed="focusPanels.competitors.pinned"
                :aria-label="focusPanels.competitors.pinned ? 'Unpin competitors panel' : 'Pin competitors panel'"
                :title="focusPanels.competitors.pinned ? 'Unpin panel' : 'Pin panel'"
                @click="toggleFocusPanelPin('competitors')"
              >
                <i :class="focusPanels.competitors.pinned ? 'ti ti-pin-filled' : 'ti ti-pin'" aria-hidden="true"></i>
              </button>
            </div>
          </div>
          <div class="focus-immersive-competitors-empty">
            <i class="ti ti-users-group" aria-hidden="true"></i>
            <p>Study competitors will appear here.</p>
            <span>Connects to Competitive mode when it becomes available.</span>
          </div>
        </section>
      </div>

      <div
        v-if="focusPanels.video.open"
        class="focus-immersive-panel focus-immersive-panel-video"
        data-focus-panel="video"
        :style="focusPanelPositionStyle('video')"
        @pointerdown="startFocusPanelDrag($event, 'video')"
        @pointermove="moveFocusPanel($event, 'video')"
        @pointerup="finishFocusPanelDrag($event, 'video')"
        @pointercancel="finishFocusPanelDrag($event, 'video')"
        @lostpointercapture="finishFocusPanelDrag($event, 'video')"
      >
        <section class="focus-immersive-card focus-immersive-video-card">
          <div class="focus-panel-header">
            <span>
              <i class="ti ti-movie" aria-hidden="true"></i>
              Background video
              <button
                type="button"
                class="focus-panel-drag-handle"
                aria-label="Drag background video panel"
                title="Drag background video panel"
                @click.prevent
              >
                <i class="ti ti-grip-vertical" aria-hidden="true"></i>
              </button>
            </span>
            <div class="focus-panel-actions">
              <button type="button" aria-label="Close background video panel" title="Close panel" @click="closeFocusPanel('video')">
                <i class="ti ti-x" aria-hidden="true"></i>
              </button>
              <button
                type="button"
                :aria-pressed="focusPanels.video.pinned"
                :aria-label="focusPanels.video.pinned ? 'Unpin background video panel' : 'Pin background video panel'"
                :title="focusPanels.video.pinned ? 'Unpin panel' : 'Pin panel'"
                @click="toggleFocusPanelPin('video')"
              >
                <i :class="focusPanels.video.pinned ? 'ti ti-pin-filled' : 'ti ti-pin'" aria-hidden="true"></i>
              </button>
            </div>
          </div>
          <div class="focus-video-preview">
            <img
              v-if="focusVideoThumbnailUrl"
              :src="focusVideoThumbnailUrl"
              alt=""
              draggable="false"
              @dragstart.prevent
              @error="handleFocusVideoThumbnailError"
            />
            <div v-else class="focus-video-placeholder">
              <i class="ti ti-movie" aria-hidden="true"></i>
            </div>
          </div>
          <div class="focus-video-details">
            <strong :title="focusVideoDisplayName">{{ focusVideoDisplayName }}</strong>
            <span>{{ focusVideoUrl ? "Ambient video" : "Choose a video for your session" }}</span>
          </div>
          <div class="focus-video-controls">
            <input
              class="focus-video-volume-slider"
              type="range"
              min="0"
              max="100"
              :value="focusVideoVolume"
              :disabled="!focusVideoUrl || isFocusVideoMuted"
              :aria-label="`Background video volume ${focusVideoVolume} percent`"
              @input="setFocusVideoVolume"
            />
            <button
              type="button"
              class="focus-immersive-icon-button focus-video-play-toggle"
              :disabled="!focusVideoUrl"
              :aria-label="isFocusVideoPlaying ? 'Pause background video' : 'Play background video'"
              :title="isFocusVideoPlaying ? 'Pause background video' : 'Play background video'"
              @click="toggleFocusBackgroundVideo"
            >
              <i :class="isFocusVideoPlaying ? 'ti ti-player-pause' : 'ti ti-player-play'" aria-hidden="true"></i>
            </button>
            <button
              type="button"
              class="focus-immersive-icon-button"
              :disabled="!focusVideoUrl"
              :aria-label="isFocusVideoMuted ? 'Unmute background video' : 'Mute background video'"
              :title="isFocusVideoMuted ? 'Unmute background video' : 'Mute background video'"
              @click="toggleFocusVideoMute"
            >
              <i :class="isFocusVideoMuted ? 'ti ti-volume-off' : 'ti ti-volume'" aria-hidden="true"></i>
            </button>
          </div>
          <button
            type="button"
            class="focus-immersive-icon-button"
            :aria-expanded="isFocusVideoPickerOpen"
            aria-label="Change background video"
            title="Change background video"
            @click="isFocusVideoPickerOpen = !isFocusVideoPickerOpen"
          >
            <i class="ti ti-switch-horizontal" aria-hidden="true"></i>
          </button>

          <div v-if="isFocusVideoPickerOpen" class="focus-video-picker" @click.stop>
            <div class="focus-video-picker-heading">
              <strong>Change background video</strong>
              <button type="button" aria-label="Close video picker" @click="isFocusVideoPickerOpen = false">
                <i class="ti ti-x" aria-hidden="true"></i>
              </button>
            </div>
            <form class="focus-video-link-form" @submit.prevent="applyFocusVideoLink">
              <label for="focus-video-link">Video link (MP4/WebM, YouTube, or Vimeo)</label>
              <div>
                <input
                  id="focus-video-link"
                  v-model="focusVideoLink"
                  type="url"
                  placeholder="https://youtu.be/VIDEO_ID or https://example.com/video.mp4"
                  autocomplete="url"
                />
                <button type="submit">Use link</button>
              </div>
            </form>
            <div class="focus-video-picker-actions">
              <button type="button" @click="openFocusVideoFilePicker">
                <i class="ti ti-upload" aria-hidden="true"></i>
                Choose local video
              </button>
              <button v-if="focusVideoUrl" type="button" class="remove-video-action" @click="removeFocusVideo">
                Remove video
              </button>
            </div>
            <input
              ref="focusVideoInput"
              class="focus-video-file-input"
              type="file"
              accept="video/*"
              @change="handleFocusVideoFileChange"
              @cancel="finishFocusVideoFilePicker"
            />
          </div>
        </section>
      </div>

      <div
        v-if="focusPanels.music.open"
        class="focus-immersive-panel focus-immersive-panel-music"
        data-focus-panel="music"
        :style="focusPanelPositionStyle('music')"
        @pointerdown="startFocusPanelDrag($event, 'music')"
        @pointermove="moveFocusPanel($event, 'music')"
        @pointerup="finishFocusPanelDrag($event, 'music')"
        @pointercancel="finishFocusPanelDrag($event, 'music')"
        @lostpointercapture="finishFocusPanelDrag($event, 'music')"
      >
        <section class="focus-immersive-card focus-immersive-music" aria-label="Music player">
          <div class="focus-music-panel-header">
            <span class="focus-panel-title">
              <i class="ti ti-music" aria-hidden="true"></i>
              Music player
              <button
                type="button"
                class="focus-panel-drag-handle"
                aria-label="Drag music player panel"
                title="Drag music player panel"
                @click.prevent
              >
                <i class="ti ti-grip-vertical" aria-hidden="true"></i>
              </button>
            </span>
            <div class="focus-panel-actions">
              <button type="button" aria-label="Close music player panel" title="Close panel" @click="closeFocusPanel('music')">
                <i class="ti ti-x" aria-hidden="true"></i>
              </button>
              <button
                type="button"
                :aria-pressed="focusPanels.music.pinned"
                :aria-label="focusPanels.music.pinned ? 'Unpin music player panel' : 'Pin music player panel'"
                :title="focusPanels.music.pinned ? 'Unpin panel' : 'Pin panel'"
                @click="toggleFocusPanelPin('music')"
              >
                <i :class="focusPanels.music.pinned ? 'ti ti-pin-filled' : 'ti ti-pin'" aria-hidden="true"></i>
              </button>
            </div>
          </div>
          <div class="focus-music-panel-content">
            <img
              v-if="currentTrack?.cover"
              class="focus-music-cover"
              :src="currentTrack.cover"
              alt=""
              draggable="false"
              @dragstart.prevent
            />
            <div v-else class="focus-music-cover-placeholder">
              <i class="ti ti-music" aria-hidden="true"></i>
            </div>
            <div class="focus-music-main">
              <span class="focus-immersive-eyebrow">{{ currentTrack ? playlistTitle : "No playlist selected" }}</span>
              <strong :title="currentTrack?.title || 'No track selected'">
                {{ currentTrack?.title || "No track selected" }}
              </strong>
              <input
                type="range"
                min="0"
                max="100"
                :value="trackProgressPercent"
                :disabled="!currentTrack"
                aria-label="Music playback position"
                @input="handleSeek"
              />
            </div>
            <div class="focus-music-controls">
              <input
                class="focus-music-volume-slider"
                type="range"
                min="0"
                max="100"
                :value="musicVolume"
                :disabled="!currentTrack"
                :aria-label="`Music volume ${musicVolume} percent`"
                @input="setFocusMusicVolume"
              />
              <button
                type="button"
                class="focus-music-volume-toggle"
                :disabled="!currentTrack"
                :aria-label="musicVolume === 0 ? 'Unmute music' : 'Mute music'"
                :title="musicVolume === 0 ? 'Unmute music' : 'Mute music'"
                @click="toggleFocusMusicMute"
              >
                <i :class="musicVolume === 0 ? 'ti ti-volume-off' : 'ti ti-volume'" aria-hidden="true"></i>
              </button>
              <button type="button" :disabled="!playlist.length" aria-label="Previous track" title="Previous track" @click="prevTrack">
                <i class="ti ti-player-skip-back" aria-hidden="true"></i>
              </button>
              <button
                type="button"
                class="focus-music-play"
                :disabled="!currentTrack"
                :aria-label="isMusicPlaying ? 'Pause music' : 'Play music'"
                :title="isMusicPlaying ? 'Pause music' : 'Play music'"
                @click="toggleMusic"
              >
                <i :class="isMusicPlaying ? 'ti ti-player-pause' : 'ti ti-player-play'" aria-hidden="true"></i>
              </button>
              <button type="button" :disabled="!playlist.length" aria-label="Next track" title="Next track" @click="nextTrack">
                <i class="ti ti-player-skip-forward" aria-hidden="true"></i>
              </button>
            </div>
          </div>
        </section>
      </div>
    </section>
  </Teleport>
</template>

<style scoped>
@property --dashboard-motivation-glow-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

@property --task-card-glow-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

/* GENERAL DASHBOARD LAYOUT WITH DARK VORTEX PATTERN */
.dashboard-layout {
  display: flex;
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  background-color: #05070e;
  background-image:
    radial-gradient(circle at 50% 30%, rgba(45, 212, 191, 0.08) 0%, rgba(8, 12, 26, 0.85) 60%, #05070e 100%),
    url('/tunnel_bg_dark.jpg');
  background-position: center center;
  background-repeat: no-repeat;
  background-size: cover;
  background-attachment: fixed;
  color: #f1f5f9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  position: relative;
}

/* SIDEBAR STYLING (FIXED & NON-SCROLLING, NEVER CUTS OFF BOTTOM CARD) */
.sidebar {
  width: 248px;
  height: 100vh;
  position: sticky;
  top: 0;
  background: rgba(9, 13, 25, 0.88);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 20px 14px 14px;
  flex-shrink: 0;
  z-index: 10;
  overflow: hidden;
  box-sizing: border-box;
}

.sidebar-top {
  display: flex;
  flex-direction: column;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 13px;
  min-height: 96px;
  box-sizing: border-box;
  padding: 0 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  text-decoration: none;
}

.logo-icon {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  color: #2dd4bf;
  filter: drop-shadow(0 0 12px rgba(45, 212, 191, 0.26));
}

.logo-icon svg {
  display: block;
  width: 100%;
  height: 100%;
}

.logo-text {
  font-size: 20px;
  font-weight: 750;
  letter-spacing: -0.025em;
  color: #ffffff;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  width: 100%;
  min-height: 50px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  border: 1px solid transparent;
  border-radius: 13px;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
  text-align: left;
  text-decoration: none;
}

.nav-item i {
  width: 24px;
  flex: 0 0 24px;
  text-align: center;
  font-size: 23px;
}

.nav-item:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(148, 163, 184, 0.12);
  transform: translateX(2px);
}

.nav-item.active {
  background: rgba(45, 212, 191, 0.12);
  border: 1px solid rgba(45, 212, 191, 0.2);
  color: #5eead4;
  box-shadow: inset 3px 0 #2dd4bf, 0 6px 16px rgba(0, 0, 0, 0.12);
}

.nav-item:focus-visible {
  outline: 2px solid rgba(94, 234, 212, 0.8);
  outline-offset: 2px;
}

.sidebar-bottom {
  position: relative;
  isolation: isolate;
  margin-top: auto;
  flex-shrink: 0;
  padding-bottom: 2px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-bottom::before {
  content: '';
  position: absolute;
  inset: 18% -8px;
  z-index: -1;
  border-radius: 24px;
  background: radial-gradient(ellipse, rgba(45, 212, 191, 0.42), rgba(56, 189, 248, 0.18) 45%, transparent 72%);
  filter: blur(20px);
  pointer-events: none;
}

.motivation-card {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  height: 105px;
  border: 1px solid rgba(45, 212, 191, 0.22);
  background:
    radial-gradient(ellipse at 100% 100%, rgba(45, 212, 191, 0.2), transparent 58%),
    radial-gradient(ellipse at 0% 0%, rgba(99, 102, 241, 0.15), transparent 62%),
    linear-gradient(145deg, rgba(19, 31, 54, 0.98), rgba(8, 15, 31, 0.98));
  box-shadow: 0 0 22px rgba(45, 212, 191, 0.16), inset 0 1px rgba(255, 255, 255, 0.05);
}

.motivation-card::before {
  position: absolute;
  z-index: 1;
  inset: 0;
  padding: 1px;
  border-radius: inherit;
  background: conic-gradient(
    from var(--dashboard-motivation-glow-angle),
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
  animation: dashboard-motivation-glow-travel 4s linear infinite;
}

@keyframes dashboard-motivation-glow-travel {
  to {
    --dashboard-motivation-glow-angle: 360deg;
  }
}

.motivation-card .motivation-content {
  z-index: 2;
}

@media (prefers-reduced-motion: reduce) {
  .motivation-card::before {
    animation: none;
  }
}

.sidebar-account {
  min-width: 0;
  min-height: 68px;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.76);
  color: #e2e8f0;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.sidebar-account:hover {
  border-color: rgba(45, 212, 191, 0.32);
  background: rgba(20, 32, 52, 0.92);
  box-shadow: 0 0 16px rgba(45, 212, 191, 0.1);
}

.sidebar-account .user-avatar {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  box-sizing: border-box;
  font-size: 15px;
}

.sidebar-account-details {
  min-width: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
}

.sidebar-account-name {
  overflow: hidden;
  color: #f1f5f9;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-account-action {
  color: #94a3b8;
  font-size: 11px;
}

.sidebar-account-row {
  display: flex;
  align-items: stretch;
  gap: 7px;
}

.sidebar-logout-btn {
  width: 42px;
  flex: 0 0 42px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.76);
  color: #94a3b8;
  font-size: 17px;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.sidebar-logout-btn:hover {
  border-color: rgba(251, 113, 133, 0.35);
  background: rgba(244, 63, 94, 0.12);
  color: #fda4af;
}

.motivation-content {
  position: relative;
  height: 100%;
  box-sizing: border-box;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.quote-text {
  font-size: 12px;
  line-height: 1.45;
  font-weight: 500;
  color: #e2e8f0;
  margin: 0;
}

.quote-sprout {
  align-self: flex-end;
  color: #2dd4bf;
  font-size: 15px;
}

/* MAIN WRAPPER (ONLY SCROLLABLE PAGE AREA WITH COMFORTABLE BOTTOM PADDING) */
.main-wrapper {
  flex: 1;
  min-width: 0;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px 28px 60px;
  gap: 20px;
  box-sizing: border-box;
}

.bottom-page-spacer {
  height: 30px;
  flex-shrink: 0;
}

/* HEADER BANNER */
.header-banner {
  position: relative;
  border-radius: 18px;
  overflow: visible;
  min-height: 96px;
  border: 1px solid rgba(148, 163, 184, 0.13);
  background:
    radial-gradient(ellipse at 0% 0%, rgba(45, 212, 191, 0.12), transparent 48%),
    radial-gradient(ellipse at 100% 100%, rgba(99, 102, 241, 0.1), transparent 50%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(8, 13, 27, 0.98));
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.18), inset 0 1px rgba(255, 255, 255, 0.035);
}

.banner-content {
  min-height: 96px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 16px 24px;
}

.greeting-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #ffffff;
  margin: 0;
}

.wave-emoji {
  display: inline-block;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  line-height: 1;
  vertical-align: baseline;
  cursor: pointer;
  transform-origin: 70% 75%;
}

.wave-emoji:focus-visible {
  outline: 2px solid #2dd4bf;
  outline-offset: 3px;
  border-radius: 4px;
}

.wave-emoji.is-waving {
  animation: greeting-wave 800ms ease-in-out;
}

.wave-emoji:hover {
  filter: brightness(1.08);
}

@keyframes greeting-wave {
  0%, 100% { transform: rotate(0deg); }
  15% { transform: rotate(18deg); }
  30% { transform: rotate(-10deg); }
  45% { transform: rotate(18deg); }
  60% { transform: rotate(-4deg); }
  75% { transform: rotate(10deg); }
}

@media (prefers-reduced-motion: reduce) {
  .wave-emoji.is-waving {
    animation: none;
  }
}

.greeting-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin: 4px 0 0;
}

.header-right-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.date-chip,
.time-chip {
  min-height: 42px;
  box-sizing: border-box;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.82), rgba(8, 13, 27, 0.76));
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 13px;
  padding: 0 13px;
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.035);
}

.date-chip i {
  color: #5eead4;
  font-size: 17px;
}

.time-chip i {
  color: #a5b4fc;
  font-size: 17px;
}

.time-chip span {
  font-variant-numeric: tabular-nums;
}

.icon-chip {
  position: relative;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(8, 13, 27, 0.78));
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 13px;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a5f3fc;
  font-size: 19px;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.notification-btn:hover {
  color: #ffffff;
  border-color: rgba(56, 189, 248, 0.55);
  background: linear-gradient(145deg, rgba(14, 116, 144, 0.32), rgba(15, 23, 42, 0.94));
  box-shadow: 0 0 18px rgba(34, 211, 238, 0.12);
  transform: translateY(-1px);
}

.notification-btn:focus-visible {
  outline: 2px solid rgba(94, 234, 212, 0.8);
  outline-offset: 3px;
}

.notification-area {
  position: relative;
  flex: 0 0 auto;
}

.notification-panel {
  position: absolute;
  z-index: 30;
  top: calc(100% + 12px);
  right: 0;
  width: min(340px, calc(100vw - 32px));
  padding: 16px;
  box-sizing: border-box;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 15px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.98), rgba(8, 13, 27, 0.99));
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.48), inset 0 1px rgba(255, 255, 255, 0.04);
  color: #e2e8f0;
}

.notification-panel::before {
  position: absolute;
  top: -6px;
  right: 17px;
  width: 10px;
  height: 10px;
  content: "";
  transform: rotate(45deg);
  background: #0f172a;
  border-top: 1px solid rgba(148, 163, 184, 0.22);
  border-left: 1px solid rgba(148, 163, 184, 0.22);
}

.notification-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.notification-panel-header h2 {
  margin: 0;
  color: #f8fafc;
  font-size: 15px;
  font-weight: 700;
}

.notification-panel-header p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 11px;
}

.notification-close-btn {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: #94a3b8;
  cursor: pointer;
}

.notification-close-btn:hover {
  background: rgba(255, 255, 255, 0.09);
  color: #fff;
}

.notification-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  padding: 27px 8px 16px;
  text-align: center;
}

.notification-empty-icon {
  display: grid;
  width: 42px;
  height: 42px;
  margin-bottom: 3px;
  place-items: center;
  border: 1px solid rgba(45, 212, 191, 0.2);
  border-radius: 13px;
  background: rgba(45, 212, 191, 0.08);
  color: #5eead4;
  font-size: 19px;
}

.notification-empty-state strong {
  color: #e2e8f0;
  font-size: 13px;
}

.notification-empty-state > span:last-child {
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.45;
}

.notification-panel-enter-active,
.notification-panel-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
  transform-origin: top right;
}

.notification-panel-enter-from,
.notification-panel-leave-to {
  opacity: 0;
  transform: translateY(-5px) scale(0.98);
}

.user-avatar {
  border: 1px solid rgba(186, 230, 253, 0.45);
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0284c7, #38bdf8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.user-avatar:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.48);
}

.mobile-account {
  display: none;
}

/* 3-COLUMN CONTENT GRID (RESTRICTED HEIGHT & ALIGN TOP) */
.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.95fr) minmax(0, 0.95fr);
  gap: 20px;
  align-items: start;
  min-width: 0;
}

.dashboard-grid > *,
.column-right {
  min-width: 0;
}

/* GENERIC CARD (ENHANCED VISIBILITY & CONTRAST) */
.card {
  background: rgba(13, 18, 34, 0.88);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 16px 36px -8px rgba(0, 0, 0, 0.65), 0 0 20px rgba(45, 212, 191, 0.04);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.card:hover {
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 20px 42px -6px rgba(0, 0, 0, 0.75), 0 0 24px rgba(45, 212, 191, 0.07);
}

/* COLUMN 1: TASKS (MATCHING HEIGHT TO TIMER CARD) */
.tasks-card {
  display: flex;
  flex-direction: column;
  height: 565px;
  max-height: 565px;
  box-sizing: border-box;
}

.task-progress-panel {
  flex: 0 0 auto;
  margin: 0 12px 12px 2px;
  padding: 9px 10px;
  border: 1px solid var(--mono-border);
  border-radius: 11px;
  background: color-mix(in srgb, var(--brand-accent) 4%, var(--mono-panel));
}

.task-progress-heading,
.task-progress-summary {
  display: flex;
  min-width: 0;
  align-items: center;
}

.task-progress-heading {
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 7px;
}

.task-progress-summary {
  gap: 7px;
}

.task-progress-summary > strong {
  color: var(--mono-text);
  font-size: 11px;
  font-weight: 750;
}

.task-progress-percent {
  padding: 2px 5px;
  border: 1px solid var(--brand-accent-border);
  border-radius: 5px;
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
  font-size: 9px;
  font-weight: 800;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.task-overview-progress-track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--mono-hover);
}

.task-overview-progress-track > span {
  display: block;
  width: 0;
  height: 100%;
  border-radius: inherit;
  background: var(--brand-accent);
  transition: width 260ms ease;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-badge {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.icon-badge.purple {
  background: rgba(147, 51, 234, 0.15);
  color: #c084fc;
}

.card-title {
  font-size: 16.5px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.task-card-count {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border: 1px solid var(--brand-accent-border);
  border-radius: 999px;
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

.card-subtitle {
  font-size: 12px;
  color: #64748b;
  margin: 4px 0 0;
}

.add-task-btn {
  background: rgba(45, 212, 191, 0.12);
  border: 1px solid rgba(45, 212, 191, 0.35);
  color: #2dd4bf;
  border-radius: 10px;
  padding: 6px 12px;
  font-size: 12.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-task-btn:hover {
  background: rgba(45, 212, 191, 0.2);
}

.task-date-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 0 0 10px;
  min-width: 0;
}

.task-date-controls {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.task-date-step,
.task-date-today,
.task-date-filter,
.task-date-picker-label {
  min-height: 30px;
  box-sizing: border-box;
  border: 1px solid var(--mono-border);
  border-radius: 8px;
  background: var(--mono-surface);
  color: var(--mono-text);
  font: inherit;
  font-size: 11px;
}

.task-date-step {
  display: grid;
  width: 30px;
  flex: 0 0 30px;
  place-items: center;
  padding: 0;
}

.task-date-step:hover,
.task-date-today:hover,
.task-date-picker-label:hover {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
}

.task-date-picker-label {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 170px;
  padding: 0 9px;
  color: var(--brand-accent-strong);
  font-weight: 700;
  white-space: nowrap;
}

.task-date-picker-label input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
}

.task-date-today {
  padding: 0 9px;
}

.task-date-filter {
  max-width: 116px;
  padding: 0 8px;
}

.task-date-calendar-toggle {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  place-items: center;
  border: 1px solid var(--mono-border);
  border-radius: 8px;
  background: var(--mono-surface);
  color: var(--mono-muted);
}

.task-date-calendar-toggle[aria-expanded="true"] {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.task-calendar-panel {
  width: 100%;
  box-sizing: border-box;
  margin: -2px 0 12px;
  padding: 10px;
  border: 1px solid var(--mono-border);
  border-radius: 10px;
  background: var(--mono-inset);
}

.task-calendar-panel.task-calendar-popover {
  position: fixed;
  z-index: 1200;
  width: min(320px, calc(100vw - 16px));
  max-height: min(80vh, 460px);
  margin: 0;
  overflow-y: auto;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
  transform-origin: top right;
}

.task-calendar-popover-enter-active,
.task-calendar-popover-leave-active {
  transition: opacity 140ms ease, transform 140ms ease;
}

.task-calendar-popover-enter-from,
.task-calendar-popover-leave-to {
  opacity: 0;
  transform: translateY(-5px) scale(0.98);
}

.task-calendar-heading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--mono-text);
  font-size: 12px;
}

.task-calendar-loading {
  color: var(--mono-muted);
  font-size: 10px;
}

.task-calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 3px;
}

.task-calendar-weekday {
  padding: 3px 0;
  color: var(--mono-muted);
  font-size: 9px;
  font-weight: 700;
  text-align: center;
}

.task-calendar-day {
  display: flex;
  min-width: 0;
  min-height: 34px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  padding: 2px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: var(--mono-text);
  font-size: 10px;
}

.task-calendar-day.outside-month {
  color: var(--mono-subtle);
}

.task-calendar-day.has-tasks small {
  color: var(--brand-accent-strong);
  font-size: 8px;
  font-weight: 800;
}

.task-calendar-day.selected {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
  font-weight: 800;
}

.task-list-filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 16px;
}

.filter-pills {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.pill {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 5px 12px;
  font-size: 12px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pill.active {
  background: rgba(45, 212, 191, 0.14);
  border-color: rgba(45, 212, 191, 0.45);
  color: #2dd4bf;
  font-weight: 600;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 11px;
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding: 0 12px 0 0;
  scroll-padding-block: 0;
  border: 0;
  border-radius: 14px;
  background: transparent;
}

.task-list-container {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  max-height: none;
  box-sizing: border-box;
  overflow: hidden;
  margin-top: 10px;
  padding: 12px 0 12px 12px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.2);
}

.task-row {
  isolation: isolate;
  flex: 0 0 auto;
  min-height: 76px;
  box-sizing: border-box;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 15px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
  position: relative;
  overflow: hidden;
  box-shadow: none;
}

.task-row::before {
  display: none;
  position: absolute;
  z-index: 0;
  inset: 0;
  padding: 1px;
  border-radius: inherit;
  background: conic-gradient(
    from var(--task-card-glow-angle),
    transparent 0deg 270deg,
    color-mix(in srgb, var(--task-list-color) 42%, transparent) 294deg,
    color-mix(in srgb, var(--task-list-color) 96%, white) 316deg,
    color-mix(in srgb, var(--task-list-color) 58%, #38bdf8) 332deg,
    transparent 350deg 360deg
  );
  content: "";
  pointer-events: none;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  mask-composite: exclude;
  animation: task-card-glow-travel 4s linear infinite;
}

.task-row.task-focused::before {
  display: block;
}

.task-row > * {
  position: relative;
  z-index: 1;
}

@keyframes task-card-glow-travel {
  to {
    --task-card-glow-angle: 360deg;
  }
}

@media (prefers-reduced-motion: reduce) {
  .task-row::before {
    animation: none;
  }
}

.task-row:hover {
  background: rgba(25, 34, 62, 0.95);
  border-color: rgba(148, 163, 184, 0.24);
  box-shadow: 0 5px 14px rgba(0, 0, 0, 0.3);
}

/* Focused task selection */
.task-row.task-focused {
  background: color-mix(in srgb, var(--task-list-color) 8%, rgba(18, 24, 46, 0.95));
  border-color: color-mix(in srgb, var(--task-list-color) 38%, rgba(255, 255, 255, 0.12));
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
}

.task-row.task-done.task-focused {
  background: color-mix(in srgb, var(--task-list-color) 12%, rgba(18, 24, 46, 0.98));
  border-color: color-mix(in srgb, var(--task-list-color) 48%, rgba(255, 255, 255, 0.12));
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
}

.task-row.task-done {
  opacity: 0.65;
}

.task-row.task-done.task-focused {
  opacity: 1;
}

.task-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.task-sequence-number {
  display: inline-flex;
  width: 24px;
  height: 22px;
  flex: 0 0 24px;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  border: 1px solid var(--mono-border);
  border-radius: 6px;
  background: var(--mono-panel);
  color: var(--mono-text);
  font-size: 11px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
  line-height: 1;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}

.custom-checkbox {
  width: 22px;
  height: 22px;
  border-radius: 7px;
  border: 1.5px solid #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 13.5px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.custom-checkbox.checked {
  background: var(--task-list-color);
  border-color: var(--task-list-color);
  color: #090c17;
}

.task-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.task-name-line {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.task-name-line .task-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-recurring-icon {
  flex: 0 0 auto;
  color: var(--brand-accent-strong);
  font-size: 12px;
}

.task-priority-high {
  flex: 0 0 auto;
  padding: 2px 5px;
  border-radius: 5px;
  background: rgba(239, 68, 68, 0.12);
  color: #f87171;
  font-size: 9px;
  font-weight: 750;
  text-transform: uppercase;
}

.task-date-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--mono-muted);
  font-size: 10px;
  line-height: 1.2;
}

.task-overdue {
  color: #dc2626;
  font-weight: 700;
}

.task-name {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  line-height: 1.35;
  transition: color 0.2s;
}

.task-focused .task-name {
  color: #ffffff;
  font-weight: 700;
}

.task-name.strike-through {
  text-decoration: line-through;
  color: #64748b;
}

.task-focused .task-name.strike-through {
  color: #ffffff;
  text-decoration: none;
}

.task-row.task-done.task-focused .time-meta {
  color: #e2e8f0;
}

.tag-pill {
  align-self: flex-start;
  font-size: 11.5px;
  color: #818cf8;
  background: rgba(99, 102, 241, 0.12);
  padding: 3px 9px;
  border-radius: 6px;
  transition: all 0.2s;
}

.tag-pill.cyan-glow {
  color: var(--task-list-color);
  background: color-mix(in srgb, var(--task-list-color) 20%, transparent);
  box-shadow: 0 0 8px color-mix(in srgb, var(--task-list-color) 35%, transparent);
}

.task-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.pending-meta {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
  padding: 3px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  transition: color 0.18s ease, border-color 0.18s ease;
}

.pending-meta.live-active-timer {
  color: var(--task-list-color);
  border: 1px solid color-mix(in srgb, var(--task-list-color) 60%, transparent);
  font-weight: 700;
}

.pending-meta.live-active-timer i {
  color: var(--task-list-color);
}

@keyframes spinPulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.22); filter: drop-shadow(0 0 4px #2dd4bf); }
  100% { transform: scale(1); }
}

.spin-pulse {
  animation: spinPulse 1.6s ease-in-out infinite;
}

.completed-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding-right: 2px;
}

.status-check {
  font-size: 12px;
  font-weight: 600;
  color: var(--task-list-color);
  display: flex;
  align-items: center;
  gap: 4px;
}

.skipped-task-status {
  color: var(--mono-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.time-meta {
  font-size: 11px;
  color: #64748b;
}

.task-studied-meta {
  font-size: 11px;
  font-weight: 700;
  color: #2dd4bf;
}

/* ACTION BUTTONS: EDIT & DELETE */
.task-action-btns {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 2px;
  padding-left: 8px;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

.action-btn {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 15.5px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.action-btn.edit-btn:hover {
  box-shadow: 0 2px 10px rgba(56, 189, 248, 0.3);
  transform: translateY(-1.5px);
}

.action-btn.edit-btn {
  background: rgba(56, 189, 248, 0.18);
  border-color: rgba(56, 189, 248, 0.45);
  color: #38bdf8;
}

.action-btn.delete-btn:hover {
  box-shadow: 0 2px 10px rgba(244, 63, 94, 0.3);
  transform: translateY(-1.5px);
}

.action-btn.delete-btn {
  background: rgba(244, 63, 94, 0.18);
  border-color: rgba(244, 63, 94, 0.45);
  color: #fb7185;
}

/* Task list switcher */
.task-list-manager {
  margin-bottom: 14px;
  padding: 11px 12px 12px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 13px;
  background: linear-gradient(120deg, rgba(15, 23, 42, 0.42), rgba(255, 255, 255, 0.025));
}

.task-list-manager-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 9px;
}

.task-list-manager-label {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.task-list-manager-label i {
  color: #2dd4bf;
  font-size: 14px;
}

.task-list-switcher {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 58px;
  margin: -5px -8px -8px;
  padding: 8px 8px 9px;
  box-sizing: border-box;
  overflow-x: auto;
  overflow-y: hidden;
}

.task-list-tab {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  box-sizing: border-box;
  white-space: nowrap;
  padding: 4px 12px;
  border: 1px solid rgba(148, 163, 184, 0.13);
  border-radius: 9px;
  background: rgba(15, 23, 42, 0.52);
  color: #aab7c9;
  font: inherit;
  font-size: 11.5px;
  cursor: pointer;
  transition: filter 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.task-list-tab {
  color: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.13);
}

.task-list-tab-item {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  min-width: 0;
  margin: 0;
}

.task-list-tab-item.is-dragging {
  opacity: 0.55;
}

.task-list-tab-item .task-list-tab {
  cursor: grab;
  min-width: 0;
  padding-inline: 9px 34px;
  border-radius: 9px;
  border-color: color-mix(in srgb, var(--task-list-color) 48%, transparent);
  background: color-mix(in srgb, var(--task-list-color) 13%, rgba(15, 23, 42, 0.52));
}

.task-list-tab:hover {
  border-color: color-mix(in srgb, var(--task-list-color) 78%, transparent);
  background: color-mix(in srgb, var(--task-list-color) 24%, rgba(15, 23, 42, 0.52));
  filter: none;
}

.task-list-tab.active {
  border-color: color-mix(in srgb, var(--task-list-color) 82%, transparent);
  background: color-mix(in srgb, var(--task-list-color) 25%, rgba(15, 23, 42, 0.52));
  color: color-mix(in srgb, var(--task-list-color) 75%, white);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--task-list-color) 35%, transparent), 0 3px 10px rgba(0, 0, 0, 0.16);
}

.task-list-menu-trigger {
  position: absolute;
  top: 50%;
  right: 5px;
  z-index: 2;
  display: grid;
  width: 20px;
  height: 20px;
  box-sizing: border-box;
  place-items: center;
  padding: 0;
  border: 1px solid var(--task-list-color);
  border-radius: 6px;
  background: var(--mono-panel);
  color: var(--mono-text);
  cursor: pointer;
  box-shadow: 0 0 0 2px var(--mono-panel);
  transform: translateY(-50%);
  transition: color 0.16s ease, background-color 0.16s ease, transform 0.16s ease;
}

.task-list-menu-trigger i {
  font-size: 12px;
  line-height: 1;
}

.task-list-menu-trigger:hover,
.task-list-menu-trigger[aria-expanded="true"] {
  border-color: var(--task-list-color);
  background: var(--task-list-color);
  color: var(--task-list-foreground);
  transform: translateY(-50%);
}

.task-list-actions-dropdown {
  position: fixed;
  z-index: 1000;
  display: grid;
  min-width: 136px;
  padding: 5px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 10px;
  background: #111827;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.32);
}

.task-list-actions-dropdown button {
  display: flex;
  min-height: 34px;
  align-items: center;
  gap: 9px;
  padding: 0 9px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #e2e8f0;
  font: inherit;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}

.task-list-actions-dropdown button:hover:not(:disabled) {
  background: rgba(148, 163, 184, 0.13);
}

.task-list-actions-dropdown button.delete-list-action {
  color: #fb7185;
}

.task-list-actions-dropdown button.delete-list-action:hover:not(:disabled) {
  background: rgba(244, 63, 94, 0.14);
}

.task-list-actions-dropdown button:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}

.task-list-tab-icon {
  font-size: 14px;
}

.task-list-tab-count {
  display: inline-grid;
  min-width: 18px;
  height: 22px;
  place-items: center;
  padding: 0 4px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--task-list-color) 26%, rgba(0, 0, 0, 0.2));
  color: #ffffff;
  font-size: 10px;
}

.task-list-add-icon {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  place-items: center;
  border: 1px solid rgba(45, 212, 191, 0.35);
  border-radius: 8px;
  background: rgba(45, 212, 191, 0.12);
  color: #2dd4bf;
  font: inherit;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.task-list-add-icon:hover {
  border-color: rgba(45, 212, 191, 0.65);
  background: rgba(45, 212, 191, 0.22);
  transform: translateY(-1px);
}

.task-list-add-icon i {
  font-size: 16px;
}

.task-list-modal {
  width: min(460px, calc(100vw - 32px));
  max-width: 460px;
  max-height: calc(100vh - 32px);
  box-sizing: border-box;
  overflow-y: auto;
}

.task-list-modal-subtitle {
  margin: 5px 0 0;
  color: #8492a8;
  font-size: 12px;
}

.delete-task-list-confirm-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 10px 15px;
  border: 1px solid rgba(244, 63, 94, 0.4);
  border-radius: 9px;
  background: rgba(244, 63, 94, 0.15);
  color: #fda4af;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease;
}

.delete-task-list-confirm-btn:hover {
  border-color: rgba(244, 63, 94, 0.7);
  background: rgba(244, 63, 94, 0.24);
}

.task-list-color-options,
.task-list-icon-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.task-list-color-swatch,
.task-list-custom-color,
.task-list-icon-option {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 2px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.task-list-color-swatch:hover,
.task-list-custom-color:hover,
.task-list-icon-option:hover {
  transform: translateY(-2px);
}

.task-list-color-swatch.selected {
  border-color: #ffffff;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.2);
}

.task-list-custom-color {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: linear-gradient(135deg, #f43f5e, #8b5cf6, #38bdf8, #22c55e, #eab308);
  color: #ffffff;
  font-size: 16px;
}

.task-list-custom-color input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.task-list-icon-option {
  border-color: rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.035);
  color: #aab7c9;
  font-size: 17px;
}

.task-list-icon-option.selected {
  border-color: var(--task-list-color);
  background: color-mix(in srgb, var(--task-list-color) 18%, transparent);
  color: var(--task-list-color);
  box-shadow: 0 0 12px color-mix(in srgb, var(--task-list-color) 20%, transparent);
}

.task-list-preview-label {
  margin: 3px 0 8px;
  color: #64748b;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.11em;
}

.task-list-preview {
  display: flex;
  min-height: 40px;
  align-items: center;
}

.task-list-preview-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  padding: 6px 10px;
  border-radius: 9px;
  color: var(--task-list-foreground, #ffffff);
  font-size: 11.5px;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.16);
}

.task-list-preview-chip > span:nth-child(2) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-list-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-height: 74px;
  padding: 14px;
  border: 1px dashed rgba(148, 163, 184, 0.16);
  border-radius: 11px;
  color: #7c8ba1;
  font-size: 12px;
  text-align: center;
}

.task-list-empty i {
  color: var(--task-list-color);
  font-size: 17px;
}

/* COLUMN 2: CENTER TIMER (RESTRICTED COMPACT SPREAD) */
.timer-card {
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  gap: 14px;
  height: 565px;
  max-height: 565px;
  box-sizing: border-box;
}

.timer-top-mode {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.timer-top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.timer-fullscreen-btn {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--mono-border);
  border-radius: 9px;
  background: var(--mono-surface);
  color: var(--mono-muted);
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
}

.timer-fullscreen-btn:hover {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.timer-fullscreen-btn i {
  font-size: 14px;
}

.mode-dropdown {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 6px 12px;
  font-size: 12.5px;
  color: #2dd4bf;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.arrow-down {
  color: #64748b;
  font-size: 12px;
}

.timer-mode-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #94a3b8;
}

.pulse-indicator {
  width: 7px;
  height: 7px;
  border-radius: 8px;
  background: #64748b;
}

.pulse-indicator.running {
  background: #2dd4bf;
  box-shadow: 0 0 8px #2dd4bf;
}

/* SIDE-BY-SIDE TIMER ROW: LEFT CLOCK, RIGHT CONTROLS */
.timer-main-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 10px 4px 6px;
}

.timer-dial-wrap {
  position: relative;
  isolation: isolate;
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  align-self: center;
  overflow: visible;
}

.radial-timer-container {
  position: relative;
  width: 170px;
  height: 170px;
  flex-shrink: 0;
}

.timer-empty-dial::before {
  position: absolute;
  inset: 12%;
  border-radius: 50%;
  background: var(--brand-accent);
  content: "";
  filter: blur(32px);
  opacity: 0.08;
  pointer-events: none;
}

.radial-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.circle-bg {
  fill: none;
  stroke: rgba(255, 255, 255, 0.06);
}

.timer-empty-dial .circle-bg {
  stroke: var(--brand-accent);
  stroke-dasharray: 3 8;
  stroke-opacity: 0.3;
}

.circle-progress {
  fill: none;
  stroke: #2dd4bf;
  transition: stroke-dashoffset 0.8s ease;
  filter: drop-shadow(0 0 8px rgba(45, 212, 191, 0.45));
}

.circle-end-dot {
  fill: var(--brand-accent);
  stroke: var(--mono-panel);
  stroke-width: 2;
  filter: drop-shadow(0 0 5px var(--brand-accent-glow));
  transform: rotate(var(--ring-target-angle));
  transform-box: view-box;
  transform-origin: 90px 90px;
  transition: transform 350ms ease;
}

.ring-load-animation {
  animation: timer-ring-draw 850ms ease-out forwards;
}

.ring-end-dot-animation {
  animation: timer-ring-dot-draw 850ms ease-out forwards;
}

@keyframes timer-ring-draw {
  from {
    stroke-dashoffset: var(--ring-circumference);
  }
  to {
    stroke-dashoffset: var(--ring-target-offset);
  }
}

@keyframes timer-ring-dot-draw {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(var(--ring-target-angle));
  }
}

.radial-center-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.timer-empty-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  color: var(--brand-accent);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.timer-empty-center i {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--brand-accent) 35%, transparent);
  border-radius: 50%;
  background: color-mix(in srgb, var(--brand-accent) 10%, transparent);
  font-size: 21px;
  box-shadow: 0 0 24px color-mix(in srgb, var(--brand-accent) 18%, transparent);
}

.timer-digits {
  display: inline-block;
  min-height: 1em;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #ffffff;
  font-variant-numeric: tabular-nums;
}

.timer-status-label {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

/* RIGHT SIDE CONTROLS & TASK INFO */
.timer-side-controls {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 14px;
}

.timer-empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 440px;
  text-align: center;
}

.timer-empty-content h3 {
  margin: 0;
  color: #fff;
  font-size: 17px;
  font-weight: 750;
  letter-spacing: -0.02em;
}

.timer-empty-content p {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.timer-empty-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.timer-empty-primary {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
  padding: 0 13px;
  border: 1px solid var(--brand-accent);
  background: var(--brand-accent);
  color: #081018;
}

.timer-empty-primary:hover {
  transform: translateY(-1px);
  filter: brightness(1.08);
}

.active-task-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
}

.active-task-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #64748b;
}

.active-task-name {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  line-height: 1.3;
}

.active-task-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: nowrap;
  width: max-content;
  max-width: 100%;
  gap: 8px;
}

.active-task-title-row .active-task-name {
  min-width: 0;
  overflow-wrap: anywhere;
}

.active-task-title-row .tag-pill {
  align-self: auto;
  flex: 0 0 auto;
}

.timer-actions-vertical {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  width: min(100%, 320px);
  max-width: 100%;
}

.pause-btn {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  min-height: 56px;
  padding: 10px 12px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pause-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.complete-btn {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  background: #2dd4bf;
  border: none;
  border-radius: 10px;
  min-height: 56px;
  padding: 10px 12px;
  color: #090c17;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(45, 212, 191, 0.3);
  transition: all 0.2s ease;
}

.complete-btn:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.timer-actions-vertical.timer-actions-icon-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: min(100%, 166px);
  max-width: 100%;
}

.timer-actions-icon-row .timer-icon-action {
  display: grid;
  flex: 0 0 34px;
  place-items: center;
  width: 34px;
  height: 34px;
  min-height: 34px;
  box-sizing: border-box;
  padding: 0;
  border-radius: 12px;
  font-size: 22px;
  line-height: 1;
  gap: 0;
  transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.timer-actions-icon-row .timer-icon-action i {
  font-size: 22px;
  line-height: 1;
}

.timer-actions-icon-row .timer-label-action {
  display: inline-flex;
  flex: 0 0 82px;
  width: 82px;
  min-width: 82px;
  padding: 0 7px;
  gap: 7px;
  font-size: 13px;
}

.restart-icon-action {
  border: 1px solid var(--mono-border);
  background: var(--mono-surface);
  color: var(--mono-muted);
  cursor: pointer;
}

.restart-icon-action:hover {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.pause-btn.timer-icon-action {
  border: 1px solid var(--brand-accent-border);
  border-radius: 18px;
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.pause-btn.timer-icon-action:hover {
  border-color: var(--brand-accent);
  background: var(--brand-accent);
  color: var(--brand-accent-ink);
  transform: translateY(-1px);
}

.complete-btn.timer-icon-action {
  border: 1px solid transparent;
  background: var(--brand-accent);
  color: var(--brand-accent-ink);
  box-shadow: 0 4px 15px var(--brand-accent-glow);
}

.complete-btn.timer-icon-action:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.timer-actions-icon-row .timer-icon-action:focus-visible {
  outline: 2px solid var(--brand-accent-strong);
  outline-offset: 2px;
}

/* COMPLETED TASK CONTROLS */
.completed-tick {
  width: 40px;
  height: 40px;
  overflow: visible;
  color: var(--brand-accent-strong);
}

.completed-tick path {
  fill: none;
  stroke: currentColor;
  stroke-width: 2.8;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 24;
  stroke-dashoffset: 24;
  animation: completed-tick-draw 460ms cubic-bezier(0.22, 1, 0.36, 1) 80ms forwards;
}

@keyframes completed-tick-draw {
  to {
    stroke-dashoffset: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ring-load-animation {
    animation: none;
  }

  .ring-end-dot-animation {
    animation: none;
  }

  .completed-tick path {
    animation: none;
    stroke-dashoffset: 0;
  }
}

.completed-ring-label {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.completed-time-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 3px;
}

.completed-study-label {
  font-size: 12px;
  font-weight: 700;
  color: #2dd4bf;
  margin-top: 3px;
}

.task-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.completed-badge-pill {
  font-size: 10.5px;
  font-weight: 700;
  color: #2dd4bf;
  background: rgba(45, 212, 191, 0.15);
  border: 1px solid rgba(45, 212, 191, 0.4);
  border-radius: 999px;
  padding: 2px 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.task-name-completed {
  color: #94a3b8 !important;
  text-decoration: line-through;
}

.restart-task-btn {
  flex: 1;
  width: 100%;
  background: rgba(45, 212, 191, 0.12);
  border: 1px solid rgba(45, 212, 191, 0.35);
  border-radius: 14px;
  padding: 13px 22px;
  color: #2dd4bf;
  font-size: 14.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.timer-actions-vertical.restart-only-actions {
  display: flex;
  align-self: center;
  justify-content: center;
  width: min(100%, 320px);
}

.timer-actions-vertical.restart-only-actions.resume-available {
  display: flex;
  width: fit-content;
  max-width: 100%;
  gap: 8px;
}

.resume-task-btn {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(45, 212, 191, 0.35);
  border-radius: 14px;
  padding: 13px 16px;
  background: rgba(45, 212, 191, 0.12);
  color: #2dd4bf;
  font-size: 14.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.resume-task-btn:hover {
  border-color: #2dd4bf;
  background: #2dd4bf;
  color: #090c17;
  box-shadow: 0 4px 16px rgba(45, 212, 191, 0.4);
  transform: translateY(-1px);
}

.restart-only-actions.resume-available .restart-task-btn {
  flex: initial;
  width: 100%;
  margin-inline: 0;
  padding-inline: 12px;
  font-size: 13px;
}

.restart-only-actions .restart-task-btn {
  flex: 0 1 180px;
  width: min(100%, 180px);
  box-sizing: border-box;
  margin-inline: auto;
}

.timer-actions-vertical.restart-only-actions .resume-task-btn,
.timer-actions-vertical.restart-only-actions .restart-task-btn {
  height: 34px;
  min-height: 34px;
  box-sizing: border-box;
  padding: 0 10px;
  border-radius: 18px;
  font-size: 13px;
  gap: 6px;
}

.timer-actions-vertical.restart-only-actions.resume-available .resume-task-btn,
.timer-actions-vertical.restart-only-actions.resume-available .restart-task-btn {
  flex: 0 1 auto;
  width: auto;
  min-width: 0;
  white-space: nowrap;
}

.restart-task-btn:hover {
  background: #2dd4bf;
  color: #090c17;
  box-shadow: 0 4px 16px rgba(45, 212, 191, 0.4);
  transform: translateY(-1px);
}

/* FULL-WIDTH FOCUS DETAILS CARD INSIDE TIMER */
.focus-details-card {
  width: 100%;
  box-sizing: border-box;
  background: rgba(10, 14, 28, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: inset 0 0 16px rgba(0, 0, 0, 0.4);
}

.focus-stats-quad {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-box {
  background: rgba(18, 24, 46, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.metric-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.metric-top i {
  font-size: 14px;
}

.metric-label {
  font-size: 10.5px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.metric-body {
  display: flex;
  flex-direction: column;
  margin-top: 2px;
}

.metric-big-time {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
}

.metric-sub {
  font-size: 10.5px;
  color: #64748b;
  margin-top: 1px;
}

.highlight-amber {
  color: #fbbf24;
}

.highlight-flame {
  color: #fbbf24;
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.35);
  font-variant-numeric: tabular-nums;
}

.current-focus-metric {
  transition: all 0.3s ease;
}

.current-focus-metric.in-flow {
  border-color: rgba(245, 158, 11, 0.4);
  box-shadow: 0 0 16px rgba(245, 158, 11, 0.15), inset 0 0 10px rgba(245, 158, 11, 0.05);
}

.current-focus-metric.in-grace {
  border-color: rgba(251, 146, 60, 0.45);
  background: rgba(30, 22, 14, 0.88);
}

.live-flow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 8px #f59e0b;
  margin-left: auto;
  animation: flowBlink 1.4s infinite ease-in-out;
}

@keyframes flowBlink {
  0%, 100% { opacity: 0.4; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.3); }
}

.flow-status-sub {
  display: flex;
  align-items: center;
  gap: 4px;
}

.grace-countdown {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 700;
  color: #fb923c !important;
  animation: gracePulse 2s infinite ease-in-out;
}

@keyframes gracePulse {
  0%, 100% { opacity: 0.85; }
  50% { opacity: 1; text-shadow: 0 0 6px rgba(251, 146, 60, 0.6); }
}

.live-record-box {
  border-color: rgba(251, 191, 36, 0.5) !important;
  background: rgba(36, 26, 12, 0.88) !important;
  box-shadow: 0 0 20px rgba(251, 191, 36, 0.25) !important;
  animation: liveRecordPulse 2s infinite alternate ease-in-out;
}

@keyframes liveRecordPulse {
  0% {
    box-shadow: 0 0 14px rgba(251, 191, 36, 0.2);
    border-color: rgba(251, 191, 36, 0.4);
  }
  100% {
    box-shadow: 0 0 26px rgba(251, 191, 36, 0.5);
    border-color: #fbbf24;
  }
}

.live-record-tag {
  font-size: 9px;
  font-weight: 800;
  color: #090c17;
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
  padding: 1px 6px;
  border-radius: 6px;
  margin-left: auto;
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
  animation: tagFlash 1.2s infinite ease-in-out;
}

@keyframes tagFlash {
  0%, 100% { opacity: 0.85; transform: scale(0.96); }
  50% { opacity: 1; transform: scale(1.04); }
}

.text-cyan { color: #2dd4bf; }
.text-teal { color: #2dd4bf; }
.text-green { color: #34d399; }
.text-indigo { color: #818cf8; }
.text-amber { color: #f59e0b; }
.text-slate { color: #94a3b8; }

/* COLUMN 3: AMBIENT & MUSIC */
.column-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.card-header-simple {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.card-title-sm {
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.icon-teal { color: #2dd4bf; }
.icon-indigo { color: #818cf8; }

.more-link {
  font-size: 11px;
  color: #64748b;
  text-decoration: none;
}

.more-link:hover {
  color: #94a3b8;
}

/* Ambient Soundscapes: Reference Image Squarish Cards */
.ambient-card {
  padding: 18px 20px;
}

.ambient-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ambient-filter-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.ambient-pill {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 9px;
  padding: 6px 13px;
  font-size: 12.5px;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.ambient-pill:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.ambient-pill.active {
  background: var(--brand-accent-soft);
  border-color: var(--brand-accent-border);
  color: var(--brand-accent-strong);
  font-weight: 600;
}

.ambient-favorites-heart {
  width: 13px;
  height: 13px;
  flex: 0 0 13px;
  fill: #dc2626;
}

.ambient-pill .active-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2dd4bf;
  box-shadow: 0 0 6px #2dd4bf;
}

.mute-all-btn {
  background: rgba(244, 63, 94, 0.12);
  border: 1px solid rgba(244, 63, 94, 0.35);
  color: #fb7185;
  width: 34px;
  height: 34px;
  padding: 0;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.mute-all-btn:hover {
  background: rgba(244, 63, 94, 0.25);
  color: #ffffff;
}

.mute-all-btn i {
  color: #ef4444;
  font-size: 15px;
}

/* 2-Column Grid of Squarish Cards (Matching Reference Image) */
.ambient-ref-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  column-gap: 16px;
  width: 96%;
  margin-inline: auto;
  align-content: start;
  max-height: 310px;
  overflow-y: auto;
  padding-right: 4px;
}

.ambient-favorites-empty {
  grid-column: 1 / -1;
  min-height: 128px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #94a3b8;
  background: rgba(14, 20, 38, 0.52);
  border: 1px dashed rgba(148, 163, 184, 0.18);
  border-radius: 10px;
  text-align: center;
}

.ambient-favorites-empty > i {
  margin-bottom: 2px;
  color: #818cf8;
  font-size: 20px;
}

.ambient-favorites-empty > span:first-of-type {
  color: #e2e8f0;
  font-size: 12.5px;
  font-weight: 600;
}

.ambient-favorites-empty > span:last-of-type {
  color: #64748b;
  font-size: 11px;
}

/* Individual Reference Card */
.amb-ref-card {
  display: flex;
  align-items: stretch;
  height: 74px;
  background: rgba(12, 16, 28, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.22s ease;
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
}

.amb-ref-card:hover {
  border-color: rgba(255, 255, 255, 0.22);
  background: rgba(16, 22, 38, 0.98);
  transform: translateY(-1px);
}

.amb-ref-card.is-active {
  border-color: rgba(255, 255, 255, 0.45);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6), 0 0 12px rgba(255, 255, 255, 0.06);
}

/* Left Square Block: Diagonal Hatch Idle / Solid White Active (Reference Match) */
.amb-hatch-block {
  position: relative;
  width: 72px;
  min-width: 72px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: repeating-linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.06),
    rgba(255, 255, 255, 0.06) 1.5px,
    transparent 1.5px,
    transparent 6.5px
  );
  border-right: 1px solid rgba(255, 255, 255, 0.09);
  color: rgba(255, 255, 255, 0.45);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.amb-hatch-block::before,
.amb-hatch-block::after {
  position: absolute;
  z-index: 0;
  content: "";
  pointer-events: none;
  opacity: 0;
}

.amb-hatch-block.is-playing::before,
.amb-hatch-block.is-playing::after {
  opacity: 1;
}

.amb-hatch-block.is-playing .amb-block-icon {
  position: relative;
  z-index: 1;
}

.amb-ref-card:hover .amb-hatch-block {
  color: rgba(255, 255, 255, 0.7);
}

.amb-block-icon {
  font-size: 25px;
  transform-origin: center;
  transition: transform 0.2s ease, filter 0.2s ease, color 0.2s ease;
}

.amb-playing-animation {
  position: relative;
  z-index: 1;
  width: 32px;
  height: 32px;
  object-fit: contain;
  pointer-events: none;
}

.waves-ambience-icon {
  width: 28px;
  height: 28px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.amb-hatch-block:hover .amb-block-icon {
  transform: scale(1.15);
}

.amb-tile-waterfall.is-playing::before {
  right: -12px;
  bottom: 10px;
  left: -12px;
  height: 17px;
  border-top: 1px solid rgba(56, 189, 248, 0.6);
  border-radius: 50%;
  box-shadow: 0 -5px 0 -4px rgba(56, 189, 248, 0.48), 0 5px 0 -4px rgba(56, 189, 248, 0.35);
  animation: ambience-water-current 3.2s ease-in-out infinite;
}

.amb-tile-waves.is-playing .amb-icon-waves path {
  stroke-dasharray: 18 8;
  animation: ambience-wave-drift 2.8s linear infinite;
}

.amb-tile-waves.is-playing .amb-icon-waves path:nth-child(2) {
  animation-delay: -0.9s;
}

.amb-tile-waves.is-playing .amb-icon-waves path:nth-child(3) {
  animation-delay: -1.8s;
}

.amb-tile-waterfall.is-playing::after,
.amb-tile-rain.is-playing::before {
  top: -10px;
  right: 14px;
  width: 1px;
  height: 100%;
  background: repeating-linear-gradient(to bottom, transparent 0 8px, rgba(56, 189, 248, 0.72) 9px 12px, transparent 13px 21px);
  box-shadow: -13px 8px 0 -0.2px rgba(56, 189, 248, 0.5), 13px -6px 0 -0.2px rgba(56, 189, 248, 0.42);
  animation: ambience-rain-fall 0.9s linear infinite;
}

.amb-tile-rain.is-playing::after {
  top: -16px;
  right: 28px;
  width: 1px;
  height: 100%;
  background: repeating-linear-gradient(to bottom, transparent 0 12px, rgba(56, 189, 248, 0.48) 13px 16px, transparent 17px 27px);
  animation: ambience-rain-fall 1.25s linear -0.4s infinite;
}

.amb-tile-wind.is-playing::before,
.amb-tile-howling_wind.is-playing::before,
.amb-tile-wind_trees.is-playing::before {
  top: 23px;
  left: -32px;
  width: 38px;
  height: 7px;
  border-top: 1px solid rgba(148, 163, 184, 0.72);
  border-radius: 50%;
  box-shadow: 0 5px 0 -1px rgba(148, 163, 184, 0.45);
  animation: ambience-wind-gust 2.4s ease-out infinite;
}

.amb-tile-wind.is-playing::after,
.amb-tile-howling_wind.is-playing::after,
.amb-tile-wind_trees.is-playing::after {
  top: 42px;
  left: -38px;
  width: 30px;
  height: 5px;
  border-top: 1px solid rgba(148, 163, 184, 0.52);
  border-radius: 50%;
  animation: ambience-wind-gust 3.1s ease-out -1.2s infinite;
}

.amb-tile-howling_wind.is-playing::before,
.amb-tile-howling_wind.is-playing::after {
  animation-duration: 1.35s;
}

.amb-tile-wind_trees.is-playing .amb-block-icon {
  animation: ambience-tree-sway 4.2s ease-in-out infinite;
}

.amb-tile-snow_walk.is-playing::before,
.amb-tile-leaves_walk.is-playing::before {
  top: -8px;
  left: 14px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(226, 232, 240, 0.9);
  box-shadow: 17px 12px 0 -1px rgba(226, 232, 240, 0.78), 34px -3px 0 -1px rgba(226, 232, 240, 0.65);
  animation: ambience-particles-drift 2.8s linear infinite;
}

.amb-tile-snow_walk.is-playing::after,
.amb-tile-leaves_walk.is-playing::after {
  top: -14px;
  left: 31px;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: rgba(226, 232, 240, 0.7);
  box-shadow: 16px 20px 0 rgba(226, 232, 240, 0.5);
  animation: ambience-particles-drift 3.6s linear -1.4s infinite;
}

.amb-tile-leaves_walk.is-playing::before,
.amb-tile-leaves_walk.is-playing::after {
  background: rgba(163, 190, 93, 0.86);
  border-radius: 80% 10% 80% 10%;
}

.amb-tile-highway.is-playing::before {
  top: 14px;
  bottom: 14px;
  left: -70%;
  width: 45%;
  background: linear-gradient(90deg, transparent, rgba(251, 191, 36, 0.05), rgba(251, 191, 36, 0.76), transparent);
  filter: blur(1px);
  animation: ambience-headlight-pass 2.1s ease-in-out infinite;
}

.amb-tile-highway.is-playing::after {
  top: 39px;
  left: -50%;
  width: 38%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(248, 113, 113, 0.65), transparent);
  animation: ambience-headlight-pass 2.8s ease-in-out -1.2s infinite;
}

.amb-tile-cafe.is-playing::before,
.amb-tile-cafe.is-playing::after {
  bottom: 32px;
  width: 7px;
  height: 18px;
  border-left: 1px solid rgba(203, 213, 225, 0.78);
  border-radius: 50%;
  filter: blur(0.4px);
  animation: ambience-steam-rise 2.4s ease-out infinite;
}

.amb-tile-cafe.is-playing::before {
  left: 23px;
}

.amb-tile-cafe.is-playing::after {
  left: 38px;
  animation-delay: -1.15s;
}

.amb-tile-night.is-playing::before,
.amb-tile-night.is-playing::after {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: rgba(250, 204, 21, 0.92);
  box-shadow: 0 0 6px rgba(250, 204, 21, 0.65);
  animation: ambience-star-twinkle 2.2s ease-in-out infinite;
}

.amb-tile-night.is-playing::before {
  top: 17px;
  left: 14px;
}

.amb-tile-night.is-playing::after {
  top: 43px;
  right: 13px;
  width: 2px;
  height: 2px;
  animation-delay: -1.1s;
}

@keyframes ambience-water-current {
  0%, 100% { transform: translateX(-4px) scaleX(0.94); opacity: 0.35; }
  50% { transform: translateX(5px) scaleX(1.05); opacity: 0.8; }
}

@keyframes ambience-wave-drift {
  to { stroke-dashoffset: -52; }
}

@keyframes ambience-rain-fall {
  from { transform: translateY(-16px); }
  to { transform: translateY(16px); }
}

@keyframes ambience-wind-gust {
  0% { transform: translateX(0) scaleX(0.55); opacity: 0; }
  25% { opacity: 0.8; }
  100% { transform: translateX(100px) scaleX(1.2); opacity: 0; }
}

@keyframes ambience-tree-sway {
  0%, 100% { transform: rotate(-2deg); }
  50% { transform: rotate(2deg); }
}

@keyframes ambience-particles-drift {
  from { transform: translateY(-8px) translateX(0) rotate(0); opacity: 0; }
  15% { opacity: 0.85; }
  to { transform: translateY(84px) translateX(8px) rotate(100deg); opacity: 0; }
}

@keyframes ambience-headlight-pass {
  0% { transform: translateX(0); opacity: 0; }
  20% { opacity: 0.8; }
  70%, 100% { transform: translateX(190%); opacity: 0; }
}

@keyframes ambience-steam-rise {
  0% { transform: translateY(8px) scaleY(0.5); opacity: 0; }
  30% { opacity: 0.65; }
  100% { transform: translateY(-17px) scaleY(1.2); opacity: 0; }
}

@keyframes ambience-star-twinkle {
  0%, 100% { transform: scale(0.65); opacity: 0.25; }
  50% { transform: scale(1.35); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .amb-hatch-block.is-playing::before,
  .amb-hatch-block.is-playing::after,
  .amb-playing-animation,
  .amb-tile-waves.is-playing .amb-icon-waves path,
  .amb-tile-wind_trees.is-playing .amb-block-icon,
  .amb-tile-campfire.is-playing .amb-block-icon {
    animation: none;
  }
}

/* ACTIVE STATE: Changes to Solid White with Crisp Black Icon */
.amb-ref-card.is-active .amb-hatch-block {
  background: #ffffff !important;
  color: #000000 !important;
  border-right: 1px solid #ffffff;
  box-shadow: inset 0 0 4px rgba(0, 0, 0, 0.15);
}

.amb-ref-card.is-active .amb-hatch-block.has-playing-animation {
  background: #ffffff !important;
  border-right-color: #ffffff;
  box-shadow: inset 0 0 4px rgba(0, 0, 0, 0.15);
  color: #000000;
}

.amb-ref-card.is-active .amb-block-icon {
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.2));
}

/* Right Content Section */
.amb-content-block {
  flex: 1;
  min-width: 0;
  padding: 9px 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.amb-top-row {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.amb-title {
  position: absolute;
  top: 50%;
  left: 0;
  right: 30px;
  transform: translateY(-50%);
  box-sizing: border-box;
  font-size: 13.5px;
  font-weight: 700;
  color: #ffffff;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
  letter-spacing: -0.01em;
  transition: color 0.15s;
}

.amb-title:hover {
  color: #2dd4bf;
}

.amb-heart-btn {
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  padding: 0;
  color: #64748b;
  font-size: 15px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
}

.amb-heart-btn:hover {
  color: #f43f5e;
  background: rgba(244, 63, 94, 0.1);
  border-color: rgba(244, 63, 94, 0.18);
}

.amb-heart-btn.is-favorited {
  color: #ef4444;
}

.amb-heart-btn > svg,
.amb-heart-btn.is-favorited > svg {
  width: 15px;
  height: 15px;
}

.amb-heart-btn.is-favorited > svg {
  fill: #ef4444;
}

/* Bottom Row with Built-In Minimalist Slider */
.amb-bottom-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.amb-slider-wrap {
  flex: 1;
  display: flex;
  align-items: center;
}

.amb-track-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 2px;
  outline: none;
  transition: all 0.15s ease;
}

.amb-track-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.75);
  transition: transform 0.15s;
}

.amb-track-slider::-webkit-slider-thumb:hover {
  transform: scale(1.35);
}

.amb-effect-tag {
  font-size: 10.5px;
  font-weight: 600;
  color: #94a3b8;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.swell-wave-icon {
  width: 13px;
  height: 7px;
  color: #2dd4bf;
}

.amb-vol-pct {
  font-size: 10.5px;
  font-weight: 600;
  color: #64748b;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* ===================================================
   MUSIC PLAYER: COMPACT SLEEK DESIGN
   Restricted size, responsive controls, rich playlist rows
=================================================== */
.ref-music-station {
  flex: 1;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  padding: 16px 18px;
  background: rgba(11, 16, 30, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
}

/* Top Header */
.music-ref-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.music-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.music-icon-pill {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: rgba(99, 102, 241, 0.16);
  border: 1px solid rgba(99, 102, 241, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #818cf8;
  font-size: 18px;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.25);
  flex-shrink: 0;
}

.music-header-titles {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.music-link-error {
  margin: 0;
  color: #fca5a5;
  font-size: 12px;
  line-height: 1.4;
}

.music-main-title {
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.01em;
}

.music-subtitle {
  font-size: 11.5px;
  color: #64748b;
  font-weight: 500;
}

/* "+ Add Link" Button */
.music-add-link-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #ffffff;
  border-radius: 999px;
  padding: 6px 15px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.22s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.music-add-link-btn:hover {
  background: rgba(99, 102, 241, 0.3);
  border-color: rgba(99, 102, 241, 0.6);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.45);
}

.preset-chip {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #cbd5e1;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.18s ease;
}

.preset-chip:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.4);
  color: #ffffff;
}

.add-music-form {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.form-input-group label {
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
  display: block;
}

.optional-label {
  margin-left: 3px;
  color: #64748b;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-icon i {
  position: absolute;
  left: 12px;
  color: #818cf8;
  font-size: 16px;
}

.input-with-icon input {
  padding-left: 36px !important;
}

.form-input-group input {
  background: rgba(8, 12, 24, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: #ffffff;
  outline: none;
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.form-input-group input:focus {
  border-color: #818cf8;
}

.form-row-duo {
  display: flex;
  gap: 10px;
}

.form-actions-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
}

.btn-cancel-music {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 14px;
  cursor: pointer;
}

.btn-cancel-music:hover {
  color: #ffffff;
}

.btn-save-music {
  background: #6366f1;
  border: none;
  border-radius: 10px;
  padding: 9px 18px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.4);
}

.btn-save-music:hover {
  background: #4f46e5;
  transform: translateY(-1px);
}

/* ===================================================
   HERO NOW PLAYING CARD (Exact Match to New Reference Image)
=================================================== */
.hero-now-playing-box {
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  background: rgba(12, 17, 34, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 16px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
  position: relative;
  overflow: hidden;
}

/* TOP ROW */
.hero-top-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
  min-width: 0;
}

.hero-top-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.hero-artwork-wrap {
  display: grid;
  width: 80px;
  height: 80px;
  min-width: 80px;
  flex: 0 0 80px;
  place-items: center;
  overflow: hidden;
  border: 1px solid var(--mono-border);
  border-radius: 14px;
  background: var(--mono-surface);
}

.hero-artwork-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-meta-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.hero-track-title {
  position: relative;
  display: block;
  width: 100%;
  min-width: 0;
  height: 14px;
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  overflow: hidden;
  letter-spacing: -0.015em;
  line-height: 14px;
  mask-image: linear-gradient(to right, #000 92%, transparent);
}

.hero-track-marquee {
  display: block;
  width: 100%;
  height: 100%;
  white-space: nowrap;
  overflow: hidden;
}

.hero-track-marquee.is-scrolling {
  position: absolute;
  top: 0;
  left: 0;
}

.hero-track-marquee-track {
  display: flex;
  width: max-content;
  white-space: nowrap;
}

.hero-track-marquee.is-scrolling .hero-track-marquee-track {
  animation: heroTrackTitleScroll 24s linear infinite;
}

.hero-track-marquee-track > span {
  flex: 0 0 auto;
  padding-right: 2.5rem;
}

.hero-track-title:hover .hero-track-marquee.is-scrolling .hero-track-marquee-track {
  animation-play-state: paused;
}

@keyframes heroTrackTitleScroll {
  to {
    transform: translateX(-50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-track-title {
    mask-image: none;
  }

  .hero-track-marquee.is-scrolling .hero-track-marquee-track {
    animation: none;
  }

  .hero-track-marquee.is-scrolling .hero-track-marquee-track > span + span {
    display: none;
  }
}

.hero-track-artist {
  font-size: 12.5px;
  color: #94a3b8;
  margin-top: 2px;
  margin-bottom: 6px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Badges Row */
.hero-badge-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* Green Live Stream / Source Pill */
.live-stream-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #34d399;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.live-waveform-mini {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 9px;
}

.lw-bar {
  width: 2px;
  background: #34d399;
  border-radius: 1px;
}

.lw-1 { height: 4px; animation: eqBounce 0.8s infinite alternate ease-in-out; }
.lw-2 { height: 9px; animation: eqBounce 0.6s infinite alternate ease-in-out; }
.lw-3 { height: 6px; animation: eqBounce 0.7s infinite alternate ease-in-out; }

.live-green-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 6px #34d399;
  animation: dotBlink 1.4s infinite ease-in-out;
}

/* Red Watch Video Pill */
.toggle-video-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 999px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #f87171;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-video-youtube-icon {
  width: 18px;
  height: 18px;
  color: #ff0000;
  flex-shrink: 0;
}

.toggle-video-pill i {
  font-size: 14px;
  color: #f87171;
  flex-shrink: 0;
}

.toggle-video-label {
  display: flex;
  flex-direction: column;
  line-height: 1.05;
  font-size: 9.5px;
  font-weight: 700;
  text-align: left;
}

.toggle-video-pill:hover {
  background: rgba(239, 68, 68, 0.25);
  color: #ffffff;
  border-color: rgba(239, 68, 68, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
}

.toggle-video-pill:hover i {
  color: #ffffff;
}

/* Top Right Visualizer Bars (3 Vertical Rounded Bars in Image) */
.hero-card-eq-bars {
  display: flex;
  align-items: flex-end;
  gap: 2.5px;
  height: 14px;
  padding-top: 2px;
}

.hb {
  width: 2.5px;
  background: var(--brand-accent);
  border-radius: 1.5px;
  opacity: 0.65;
  height: 7px;
  transition: height 0.2s, opacity 0.2s;
}

.hero-card-eq-bars.is-eq-live .hb {
  opacity: 1;
}

.hero-card-eq-bars.is-eq-live .hb-1 { animation: eqHeroBounce 0.8s infinite alternate ease-in-out; }
.hero-card-eq-bars.is-eq-live .hb-2 { animation: eqHeroBounce 0.5s infinite alternate ease-in-out; }
.hero-card-eq-bars.is-eq-live .hb-3 { animation: eqHeroBounce 0.9s infinite alternate ease-in-out; }

@keyframes eqHeroBounce {
  from {
    height: 3px;
  }
  to {
    height: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-card-eq-bars.is-eq-live .hb {
    animation: none;
    height: 9px;
  }
}

/* BOTTOM ROW (Seeker on Left, Controls on Right) */
.hero-bottom-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

/* Seeker Container (Time - Slider - Time) */
.hero-seeker-container {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1 1 auto;
  min-width: 0;
}

.seeker-time-label {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.hero-seek-forward-btn {
  display: inline-flex;
  width: 28px;
  height: 24px;
  flex: 0 0 28px;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid rgba(129, 140, 248, 0.35);
  border-radius: 7px;
  background: rgba(91, 106, 240, 0.14);
  color: #c7d2fe;
  font: inherit;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.hero-seek-forward-btn:hover {
  border-color: rgba(129, 140, 248, 0.7);
  background: rgba(91, 106, 240, 0.28);
  color: #ffffff;
}

.hero-seek-forward-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.seeker-slider-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
}

.hero-seeker-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 2px;
  outline: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.hero-seeker-slider:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.hero-seeker-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 0 8px #ffffff, 0 0 14px rgba(99, 102, 241, 0.8);
  cursor: pointer;
  transition: transform 0.15s ease;
}

.hero-seeker-slider::-webkit-slider-thumb:hover {
  transform: scale(1.25);
}

/* Circular Playback Controls Row */
.hero-controls-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 5px;
  flex-shrink: 0;
}

.music-volume-control {
  position: relative;
}

.music-volume-button i {
  font-size: 16px;
}

.music-volume-row {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 210px;
  max-width: calc(100vw - 24px);
  box-sizing: border-box;
  padding: 8px 12px;
  background: rgba(14, 20, 38, 0.96);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.hero-skip-btn {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.hero-skip-btn i {
  font-size: 16px;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-skip-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  transform: scale(1.08);
}

.hero-skip-btn:hover i {
  color: #ffffff;
}

/* GLOWING PLAY/PAUSE BUTTON (Proportional Size) */
.hero-big-play-btn {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  border-radius: 50%;
  background: #5b6af0;
  border: 1.5px solid rgba(255, 255, 255, 0.28);
  color: #ffffff;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 0 20px rgba(91, 106, 240, 0.65), 0 3px 12px rgba(0, 0, 0, 0.4);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-big-play-btn i {
  font-size: 20px;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.play-icon-offset {
  margin-left: 2px;
}

.hero-big-play-btn:hover {
  transform: scale(1.08);
  box-shadow: 0 0 28px rgba(91, 106, 240, 0.85), 0 6px 18px rgba(0, 0, 0, 0.5);
  border-color: #ffffff;
}

/* EMBEDDED PLAYER CONTAINER (FIXES BLACK SQUARE COMPLETELY) */
.embedded-player-box.audio-only-frame {
  position: absolute !important;
  left: -9999px !important;
  top: -9999px !important;
  width: 320px !important;
  height: 180px !important;
  opacity: 0.001 !important;
  pointer-events: none !important;
}

.embedded-player-box.video-active-frame {
  position: fixed;
  z-index: 10000;
  width: 420px;
  max-width: calc(100vw - 24px);
  box-sizing: border-box;
  padding: 10px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.14);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.65);
  background: #000000;
  animation: slidePanelDown 0.25s ease-out;
}

.floating-video-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 34px;
  margin-bottom: 8px;
  color: #cbd5e1;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.floating-video-header:active {
  cursor: grabbing;
}

.floating-video-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.floating-video-title i {
  flex: 0 0 auto;
  color: #94a3b8;
  font-size: 15px;
}

.floating-video-header-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 3px;
}

.floating-video-drag-handle {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 7px;
  background: rgba(148, 163, 184, 0.14);
  color: #e2e8f0;
  cursor: grab;
  touch-action: none;
}

.floating-video-drag-handle:active {
  cursor: grabbing;
}

.floating-video-size {
  min-width: 25px;
  height: 24px;
  padding: 0 4px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.1);
  color: #cbd5e1;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
}

.floating-video-size:hover,
.floating-video-size:focus-visible {
  border-color: var(--brand-accent);
  background: color-mix(in srgb, var(--brand-accent) 18%, transparent);
  color: #ffffff;
  outline: none;
}

.floating-video-close {
  display: grid;
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  place-items: center;
  padding: 0;
  color: #cbd5e1;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  cursor: pointer;
}

.floating-video-close:hover {
  color: #ffffff;
  background: rgba(239, 68, 68, 0.72);
  border-color: rgba(248, 113, 113, 0.8);
}

.embedded-player-box.video-active-frame iframe {
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 9;
  border: none;
  display: block;
  border-radius: 8px;
}

.embedded-player-box.video-active-frame .youtube-embed {
  pointer-events: none;
}

.floating-video-controls {
  position: absolute;
  z-index: 2;
  right: 22px;
  bottom: 20px;
  left: 22px;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  background: rgba(8, 10, 16, 0.88);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.36);
  color: #f8fafc;
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
  transition: opacity 140ms ease, transform 140ms ease;
}

.floating-video-controls.is-hidden {
  opacity: 0;
  pointer-events: none;
  transform: translateY(6px);
}

.floating-video-control-button {
  display: grid;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  place-items: center;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  cursor: pointer;
}

.floating-video-control-button:hover,
.floating-video-control-button:focus-visible {
  border-color: var(--brand-accent);
  background: var(--brand-accent);
  color: var(--brand-accent-ink);
}

.floating-video-time {
  flex: 0 0 auto;
  color: #e2e8f0;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.floating-video-live-button {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  border: 1px solid rgba(248, 113, 113, 0.45);
  border-radius: 6px;
  background: rgba(127, 29, 29, 0.35);
  color: #fecaca;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.04em;
  cursor: pointer;
}

.floating-video-live-button > span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.75);
}

.floating-video-live-button:hover,
.floating-video-live-button:focus-visible {
  border-color: #f87171;
  background: rgba(153, 27, 27, 0.55);
  color: #ffffff;
  outline: none;
}

.floating-video-seeker,
.floating-video-volume {
  height: 4px;
  min-width: 0;
  margin: 0;
  border: 0;
  border-radius: 999px;
  outline: none;
  appearance: none;
  background: linear-gradient(
    to right,
    var(--brand-accent) 0%,
    var(--brand-accent) var(--range-progress),
    rgba(255, 255, 255, 0.28) var(--range-progress),
    rgba(255, 255, 255, 0.28) 100%
  );
  cursor: pointer;
}

.floating-video-seeker {
  flex: 1 1 auto;
}

.floating-video-volume {
  flex: 0 1 76px;
}

.floating-video-seeker::-webkit-slider-thumb,
.floating-video-volume::-webkit-slider-thumb {
  width: 11px;
  height: 11px;
  border: 0;
  border-radius: 50%;
  appearance: none;
  background: var(--brand-accent);
}

.floating-video-seeker::-moz-range-thumb,
.floating-video-volume::-moz-range-thumb {
  width: 11px;
  height: 11px;
  border: 0;
  border-radius: 50%;
  background: var(--brand-accent);
}

.floating-video-volume-icon {
  flex: 0 0 auto;
  color: #cbd5e1;
  font-size: 15px;
}

.floating-video-resize {
  position: absolute;
  z-index: 3;
  display: block;
  min-width: 0;
  min-height: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  touch-action: none;
}

.floating-video-resize.resize-n,
.floating-video-resize.resize-s {
  left: 18px;
  right: 18px;
  height: 8px;
  cursor: ns-resize;
}

.floating-video-resize.resize-n {
  top: 0;
}

.floating-video-resize.resize-s {
  bottom: 0;
}

.floating-video-resize.resize-e,
.floating-video-resize.resize-w {
  top: 18px;
  bottom: 18px;
  width: 8px;
  cursor: ew-resize;
}

.floating-video-resize.resize-e {
  right: 0;
}

.floating-video-resize.resize-w {
  left: 0;
}

.floating-video-resize.resize-ne,
.floating-video-resize.resize-nw,
.floating-video-resize.resize-se,
.floating-video-resize.resize-sw {
  width: 18px;
  height: 18px;
}

.floating-video-resize.resize-ne {
  top: 0;
  right: 0;
  cursor: nesw-resize;
}

.floating-video-resize.resize-nw {
  top: 0;
  left: 0;
  cursor: nwse-resize;
}

.floating-video-resize.resize-se {
  right: 0;
  bottom: 0;
  cursor: nwse-resize;
}

.floating-video-resize.resize-sw {
  bottom: 0;
  left: 0;
  cursor: nesw-resize;
}

.floating-video-resize:focus-visible {
  outline: 2px solid var(--brand-accent);
  outline-offset: -3px;
}

.embedded-player-box.spotify-active-frame {
  width: 100%;
  margin: 0 0 14px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
}

.embedded-player-box.spotify-active-frame iframe {
  width: 100%;
  height: 152px;
  border: none;
  display: block;
}

/* ===================================================
   FOCUS PLAYLIST SECTION (Exact Match to Mockup)
=================================================== */
.ref-playlist-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  box-sizing: border-box;
  padding: 8px;
  overflow: hidden;
  border: 1px solid var(--mono-border);
  border-radius: 18px;
  background: var(--mono-inset);
}

.ref-playlist-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
  box-sizing: border-box;
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(22, 30, 51, 0.86), rgba(14, 20, 37, 0.76));
  cursor: pointer;
  transition: border-color 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

.ref-playlist-header:hover,
.ref-playlist-header[aria-expanded="true"] {
  border-color: rgba(129, 140, 248, 0.42);
  background: linear-gradient(135deg, rgba(30, 39, 66, 0.94), rgba(17, 24, 44, 0.9));
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2), 0 0 18px rgba(99, 102, 241, 0.08);
}

.ref-playlist-header:focus-visible {
  outline: 2px solid #818cf8;
  outline-offset: 2px;
}

.ref-playlist-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.ref-list-icon {
  font-size: 17px;
  color: #818cf8;
}

.ref-playlist-titles {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.ref-playlist-title-row {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  width: 100%;
}

.ref-playlist-title {
  display: block;
  min-width: 0;
  max-width: min(320px, 55vw);
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-expand-icon {
  flex: 0 0 auto;
  color: #94a3b8;
  font-size: 13px;
  transition: transform 160ms ease, color 160ms ease;
}

.playlist-expand-icon.expanded {
  transform: rotate(180deg);
  color: #c7d2fe;
}

.playlist-picker {
  position: relative;
  width: fit-content;
  flex: 0 0 auto;
}

.playlist-picker-trigger {
  display: grid;
  width: 27px;
  height: 27px;
  place-items: center;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: #94a3b8;
  font-size: 15px;
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease, border-color 160ms ease;
}

.playlist-picker-trigger:hover,
.playlist-picker-trigger[aria-expanded="true"] {
  color: #e0e7ff;
  background: rgba(129, 140, 248, 0.12);
  border-color: rgba(129, 140, 248, 0.25);
}

.playlist-picker-trigger:focus-visible,
.playlist-picker-option:focus-visible {
  outline: 2px solid #818cf8;
  outline-offset: 2px;
}

.playlist-picker-menu {
  position: absolute;
  z-index: 40;
  top: calc(100% + 7px);
  left: 0;
  width: min(320px, calc(100vw - 48px));
  max-height: min(280px, 50vh);
  padding: 5px;
  overflow-y: auto;
  background: #101729;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 11px;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.48), 0 2px 8px rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(16px);
  animation: playlist-menu-enter 140ms ease-out;
}

.playlist-picker-option {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  min-height: 38px;
  padding: 8px 10px;
  color: #cbd5e1;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease;
}

.playlist-picker-option:hover {
  color: #ffffff;
  background: rgba(148, 163, 184, 0.1);
}

.playlist-picker-option.is-selected {
  color: #e0e7ff;
  background: rgba(99, 102, 241, 0.16);
}

.playlist-picker-option-title {
  flex: 0 1 auto;
  min-width: 0;
  max-width: calc(100% - 54px);
  overflow: hidden;
  font-size: 12.5px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-picker-option-count {
  flex: 0 0 auto;
  margin-right: auto;
  padding: 2px 7px;
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 5px;
  font-size: 10px;
  font-weight: 700;
}

.playlist-picker-option.is-selected .playlist-picker-option-count {
  color: #c7d2fe;
  background: rgba(129, 140, 248, 0.18);
}

.playlist-picker-check {
  flex: 0 0 auto;
  margin-left: auto;
  color: #a5b4fc;
  font-size: 14px;
}

@keyframes playlist-menu-enter {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .playlist-picker-menu {
    animation: none;
  }
}

.ref-playlist-sub {
  font-size: 11.5px;
  color: #64748b;
  font-weight: 500;
}

.ref-tracks-badge {
  font-size: 11px;
  font-weight: 700;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.14);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 6px;
  padding: 4px 11px;
}

.ref-playlist-header-right {
  display: flex;
  align-items: center;
  gap: 7px;
  flex: 0 0 auto;
}

.playlist-show-all-btn {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;
  padding: 0;
  border: 1px solid var(--mono-border);
  border-radius: 7px;
  background: var(--mono-surface);
  color: var(--mono-muted);
  cursor: pointer;
  transition: color 150ms ease, background-color 150ms ease, border-color 150ms ease,
    transform 100ms ease;
}

.playlist-show-all-btn:hover {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.playlist-show-all-btn i {
  color: inherit;
  font-size: 15px;
}

.playlist-tracks-modal-overlay {
  z-index: 1400;
}

.playlist-tracks-modal {
  display: flex;
  width: min(620px, calc(100vw - 32px));
  max-width: 620px;
  max-height: min(720px, calc(100vh - 32px));
  flex-direction: column;
  overflow: hidden;
  padding: 20px;
  border: 1px solid var(--mono-border);
  background: var(--mono-panel);
  color: var(--mono-text);
}

.playlist-tracks-modal .modal-header {
  flex: 0 0 auto;
  margin-bottom: 14px;
}

.playlist-tracks-modal .modal-header h3 {
  color: var(--mono-text);
}

.playlist-tracks-modal .close-modal-btn {
  color: var(--mono-muted);
}

.playlist-tracks-modal-subtitle {
  margin: 5px 0 0;
  color: var(--mono-muted);
  font-size: 12px;
}

.playlist-tracks-modal-list {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 7px;
  overflow-y: auto;
  padding: 2px 3px 2px 0;
}

.playlist-modal-track {
  display: flex;
  min-height: 58px;
  align-items: center;
  gap: 11px;
  padding: 7px 10px;
  border: 1px solid var(--mono-border);
  border-radius: 10px;
  background: var(--mono-surface);
  color: var(--mono-text);
  text-align: left;
  cursor: pointer;
  transition: border-color 150ms ease, background-color 150ms ease, transform 100ms ease;
}

.playlist-modal-track:hover,
.playlist-modal-track.is-current {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
}

.playlist-modal-track-artwork {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  border: 1px solid var(--mono-border);
  border-radius: 7px;
  background: var(--mono-panel);
  object-fit: cover;
}

.playlist-modal-track-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.playlist-modal-track-title,
.playlist-modal-track-artist {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-modal-track-title {
  color: var(--mono-text);
  font-size: 13px;
  font-weight: 700;
}

.playlist-modal-track-artist {
  color: var(--mono-muted);
  font-size: 11px;
}

.playlist-modal-current {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 5px;
  color: var(--brand-accent-strong);
  font-size: 10px;
  font-weight: 700;
}

.playlist-modal-current i,
.playlist-modal-play-icon {
  color: var(--brand-accent-strong);
  font-size: 15px;
}

.playlist-modal-play-icon {
  flex: 0 0 auto;
  margin: 0 5px;
  opacity: 0.7;
}

.playlist-tracks-modal-empty {
  display: flex;
  min-height: 150px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--mono-muted);
  font-size: 13px;
}

.playlist-tracks-modal-empty i {
  color: var(--mono-muted);
  font-size: 26px;
}

/* Playlist List */
.ref-tracks-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}

/* Individual Playlist Track Row */
.ref-track-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  box-sizing: border-box;
  padding: 8px 12px;
  background: rgba(14, 20, 38, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ref-track-card:hover {
  background: rgba(20, 28, 54, 0.85);
  border-color: rgba(255, 255, 255, 0.14);
  transform: translateY(-1px);
}

/* Active Track Highlight */
.ref-track-card.is-active-track {
  background: linear-gradient(90deg, rgba(30, 42, 85, 0.55) 0%, rgba(18, 26, 52, 0.6) 100%);
  border: 1.5px solid rgba(99, 102, 241, 0.65);
  box-shadow: 0 0 18px rgba(99, 102, 241, 0.18);
}

/* Track Left Meta */
.track-card-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.track-status-slot {
  width: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.row-playing-wave {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 10px;
}

.rw-bar {
  width: 2px;
  background: #818cf8;
  border-radius: 1px;
}

.rw-1 { height: 5px; animation: eqBounce 0.7s infinite alternate ease-in-out; }
.rw-2 { height: 10px; animation: eqBounce 0.5s infinite alternate ease-in-out; }
.rw-3 { height: 7px; animation: eqBounce 0.85s infinite alternate ease-in-out; }

.row-paused-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #818cf8;
}

.row-idle-bullet {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
}

.track-card-thumb {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.track-card-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 1px;
}

.track-card-name {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-card-source {
  font-size: 11px;
  color: #818cf8;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Track Right Meta */
.track-card-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.now-playing-pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.24);
  border: 1px solid rgba(99, 102, 241, 0.45);
  color: #a5b4fc;
  font-size: 10.5px;
  font-weight: 700;
}

.row-idle-eq-icon {
  color: #64748b;
  font-size: 14px;
}

.track-heart-btn {
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #64748b;
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, transform 0.15s;
}

.track-heart-btn:hover {
  color: #f43f5e;
  background: rgba(244, 63, 94, 0.1);
  border-color: rgba(244, 63, 94, 0.18);
}

.track-heart-btn.is-fav {
  color: #ef4444;
}

.track-heart-filled {
  width: 16px;
  height: 16px;
  fill: #ef4444;
}

.track-heart-btn i {
  display: block;
  line-height: 1;
}

.track-options-btn {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  background: rgba(244, 63, 94, 0.04);
  border: 1px solid transparent;
  border-radius: 7px;
  color: #64748b;
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s;
}

.track-options-btn:hover {
  color: #fb7185;
  background: rgba(244, 63, 94, 0.12);
  border-color: rgba(244, 63, 94, 0.2);
}

.music-vol-icon {
  flex: 0 0 auto;
  font-size: 15px;
  color: #818cf8;
}

.music-volume-slider {
  flex: 1;
  min-width: 0;
  -webkit-appearance: none;
  appearance: none;
  height: 5px;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.music-volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #818cf8;
  box-shadow: 0 0 8px rgba(129, 140, 248, 0.8);
  cursor: pointer;
  transition: transform 0.15s;
}

.music-volume-slider::-webkit-slider-thumb:hover {
  transform: scale(1.3);
}

.music-vol-val {
  flex: 0 0 34px;
  font-size: 11px;
  font-weight: 700;
  color: #818cf8;
  min-width: 0;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* BOTTOM STATS ROW */
.stats-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-card {
  background: rgba(13, 18, 34, 0.88);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 12px 28px -6px rgba(0, 0, 0, 0.6);
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.stat-card:hover {
  border-color: rgba(255, 255, 255, 0.18);
  transform: translateY(-1px);
}

.stat-icon-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.stat-badge {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.stat-badge.blue { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
.stat-badge.purple { background: rgba(147, 51, 234, 0.15); color: #c084fc; }
.stat-badge.orange { background: rgba(249, 115, 22, 0.15); color: #fb923c; }
.stat-badge.green { background: rgba(45, 212, 191, 0.15); color: #2dd4bf; }

.stat-name {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
}

.progress-details {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-ratio {
  font-size: 12px;
  color: #cbd5e1;
  white-space: nowrap;
}

.progress-bar-container {
  flex: 1;
  height: 5px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #2dd4bf;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.progress-pct-label {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.stat-big-val {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
}

.stat-sub-label {
  font-size: 11px;
  color: #64748b;
}

.stat-sub-label.orange-sub {
  color: #fb923c;
  font-weight: 500;
}

.mini-bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  margin-left: auto;
}

.chart-bar {
  width: 4px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
}

.chart-bar.active {
  background: #2dd4bf;
  box-shadow: 0 0 6px rgba(45, 212, 191, 0.5);
}

.header-clear-storage-btn {
  display: inline-flex;
  min-height: 42px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid rgba(251, 113, 133, 0.42);
  border-radius: 13px;
  background: rgba(24, 32, 51, 0.72);
  color: #fda4af;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}

.header-clear-storage-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(251, 113, 133, 0.72);
  background: #2b1b2a;
}

.header-clear-storage-btn:focus-visible {
  outline: 2px solid #fda4af;
  outline-offset: 3px;
}

.header-clear-storage-btn i {
  font-size: 15px;
}

/* MODAL STYLES */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #0f1322;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 24px;
  width: 100%;
  max-width: 420px;
}

.task-schedule-modal {
  width: min(560px, calc(100vw - 28px));
  max-width: 560px;
  max-height: calc(100vh - 28px);
  overflow-y: auto;
}

.music-link-modal {
  width: min(520px, calc(100vw - 32px));
  max-width: 520px;
  max-height: calc(100vh - 32px);
  box-sizing: border-box;
  overflow-y: auto;
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.6), 0 0 32px rgba(99, 102, 241, 0.12);
}

.music-link-modal-subtitle {
  margin: 5px 0 0;
  color: #8492a8;
  font-size: 12px;
}

.music-link-modal .form-actions-right {
  margin-top: 8px;
}

.music-link-modal .close-modal-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.close-modal-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 18px;
}

.task-form {
  padding: 20px 26px 24px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-section {
  padding: 16px 18px;
  margin-bottom: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #5eead4;
}

.form-section-title i {
  font-size: 14px;
}

.modal-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.modal-group label {
  font-size: 12px;
  color: #cbd5e1;
}

.modal-group :is(input, select, textarea) {
  box-sizing: border-box;
  width: 100%;
  background: rgba(8, 10, 18, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 10px 12px;
  color: #ffffff;
  font-size: 13px;
  outline: none;
}

.modal-group :is(input, select, textarea):focus {
  border-color: #2dd4bf;
}

.modal-group select {
  min-height: 39px;
}

.modal-group textarea {
  min-height: 74px;
  resize: vertical;
}

.task-schedule-advanced {
  margin: 4px 0 14px;
  padding: 10px 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.025);
}

.task-schedule-advanced summary {
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.task-schedule-advanced[open] summary {
  margin-bottom: 12px;
  color: var(--brand-accent-strong);
}

.schedule-options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
  gap: 0 12px;
}

.recurrence-weekdays {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 12px;
}

.recurrence-weekdays button {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.04);
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
}

.recurrence-weekdays button.selected {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

.recurrence-preview {
  margin: 0 0 4px;
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.4;
}

.task-form-error {
  margin: 0 0 12px;
  color: #fca5a5;
  font-size: 12px;
}

.modal-group-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
  gap: 12px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.05);
  border: none;
  color: #94a3b8;
  padding: 9px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}

.save-task-btn {
  background: #2dd4bf;
  border: none;
  color: #090c17;
  font-weight: 700;
  padding: 9px 18px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}

/* FOCUS DIALOGS — add task, edit task, add list */
.focus-dialog-overlay {
  background: rgba(4, 6, 16, 0.72);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  padding: 16px;
  animation: addTaskOverlayIn 0.2s ease-out;
}

@keyframes addTaskOverlayIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.focus-dialog {
  width: min(640px, calc(100vw - 32px));
  max-width: 640px;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  padding: 0;
  border-color: rgba(45, 212, 191, 0.22);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6), 0 0 32px rgba(45, 212, 191, 0.12);
  animation: addTaskBoxIn 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
}

@keyframes addTaskBoxIn {
  from { opacity: 0; transform: translateY(12px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.focus-dialog .modal-header {
  margin-bottom: 0;
  padding: 24px 26px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: linear-gradient(180deg, rgba(45, 212, 191, 0.08), transparent);
}

.focus-dialog .modal-title-block {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.focus-dialog .modal-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  background: linear-gradient(135deg, rgba(45, 212, 191, 0.25), rgba(99, 102, 241, 0.25));
  color: #5eead4;
  font-size: 21px;
  flex-shrink: 0;
  box-shadow: 0 6px 18px rgba(45, 212, 191, 0.2);
}

.focus-dialog .modal-header h3 {
  font-size: 18px;
  letter-spacing: -0.01em;
}

.focus-dialog .modal-subtitle {
  margin: 3px 0 0;
  font-size: 12.5px;
  color: #94a3b8;
  line-height: 1.4;
}

.focus-dialog .close-modal-btn {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}

.focus-dialog .close-modal-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  transform: rotate(90deg);
}

.focus-dialog .task-form {
  padding: 20px 26px 24px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.focus-dialog .form-section {
  padding: 16px 18px;
  margin-bottom: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
}

.focus-dialog .form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #5eead4;
}

.focus-dialog .form-section-title i {
  font-size: 14px;
}

.focus-dialog .modal-group {
  margin-bottom: 12px;
}

.focus-dialog .modal-group label {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.focus-dialog .required {
  color: #f87171;
  font-weight: 700;
}

.focus-dialog .optional-label {
  font-size: 10.5px;
  color: #64748b;
  font-weight: 500;
}

.focus-dialog .modal-group :is(input, select, textarea) {
  border-radius: 11px;
  padding: 10px 13px;
  font-size: 13.5px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
  font-family: inherit;
}

.focus-dialog .modal-group :is(input, select, textarea)::placeholder {
  color: #475569;
}

.focus-dialog .modal-group :is(input, select, textarea):hover {
  border-color: rgba(255, 255, 255, 0.18);
}

.focus-dialog .modal-group :is(input, select, textarea):focus {
  border-color: #2dd4bf;
  box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.18);
  background: rgba(8, 10, 18, 0.9);
}

.focus-dialog .modal-group select {
  min-height: 40px;
  cursor: pointer;
}

.focus-dialog .modal-group textarea {
  min-height: 84px;
  resize: vertical;
  line-height: 1.5;
}

.focus-dialog .priority-segmented {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  padding: 4px;
  background: rgba(8, 10, 18, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 11px;
}

.focus-dialog .priority-seg {
  border: none;
  background: transparent;
  color: #94a3b8;
  padding: 8px 6px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 600;
  text-transform: capitalize;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.focus-dialog .priority-seg:hover {
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
}

.focus-dialog .priority-seg.active {
  background: linear-gradient(135deg, #2dd4bf, #5eead4);
  color: #090c17;
  box-shadow: 0 4px 12px rgba(45, 212, 191, 0.3);
}

.focus-dialog .task-schedule-advanced {
  margin: 4px 0 14px;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
  transition: border-color 0.15s ease;
}

.focus-dialog .task-schedule-advanced:hover {
  border-color: rgba(45, 212, 191, 0.25);
}

.focus-dialog .task-schedule-advanced summary {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  list-style: none;
}

.focus-dialog .task-schedule-advanced summary::-webkit-details-marker {
  display: none;
}

.focus-dialog .task-schedule-advanced summary::before {
  content: "\25B8";
  color: #5eead4;
  font-size: 12px;
  transition: transform 0.15s ease;
}

.focus-dialog .task-schedule-advanced[open] summary::before {
  transform: rotate(90deg);
}

.focus-dialog .task-schedule-advanced[open] summary {
  margin-bottom: 14px;
  color: var(--brand-accent-strong, #5eead4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 12px;
}

.focus-dialog .modal-group-row {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.focus-dialog .modal-actions {
  margin-top: 18px;
  padding: 16px 0 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  bottom: 0;
  background: color-mix(in srgb, #0f1322 92%, transparent);
}

.focus-dialog .cancel-btn {
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  padding: 10px 18px;
  border-radius: 11px;
  font-size: 13.5px;
  font-weight: 600;
  transition: background 0.15s ease, color 0.15s ease;
}

.focus-dialog .cancel-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.focus-dialog .save-task-btn {
  background: linear-gradient(135deg, #2dd4bf, #5eead4);
  padding: 10px 20px;
  border-radius: 11px;
  font-size: 13.5px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 8px 22px rgba(45, 212, 191, 0.35);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.focus-dialog .save-task-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 26px rgba(45, 212, 191, 0.45);
}

.focus-dialog .save-task-btn:active {
  transform: translateY(0);
}

.focus-dialog--list .modal-actions {
  position: static;
  background: transparent;
}

.focus-dialog--list {
  width: min(540px, calc(100vw - 32px));
  max-width: 540px;
  border-color: color-mix(in srgb, var(--task-list-color, #2dd4bf) 38%, rgba(255, 255, 255, 0.12));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6), 0 0 28px color-mix(in srgb, var(--task-list-color, #2dd4bf) 22%, transparent);
}

.focus-dialog--list .modal-header {
  background: linear-gradient(180deg, color-mix(in srgb, var(--task-list-color) 18%, transparent), transparent);
}

.focus-dialog--list .modal-icon {
  background: linear-gradient(135deg, color-mix(in srgb, var(--task-list-color) 42%, transparent), rgba(99, 102, 241, 0.22));
  color: var(--task-list-color);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--task-list-color) 28%, transparent);
}

.focus-dialog--list .form-section-title {
  color: var(--task-list-color);
}

.focus-dialog .task-list-color-options,
.focus-dialog .task-list-icon-options {
  gap: 8px;
}

.focus-dialog .task-list-color-swatch,
.focus-dialog .task-list-custom-color,
.focus-dialog .task-list-icon-option {
  width: 38px;
  height: 38px;
  border-radius: 11px;
}

.focus-dialog .task-list-color-swatch.selected {
  border-color: #ffffff;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--task-list-color) 55%, transparent);
}

.focus-dialog .task-list-preview-section {
  margin-bottom: 0;
}

.focus-dialog .task-list-preview-stage {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 14px;
  border-radius: 12px;
  background:
    radial-gradient(ellipse at 0% 0%, color-mix(in srgb, var(--task-list-color) 22%, transparent), transparent 58%),
    rgba(8, 10, 18, 0.45);
  border: 1px dashed color-mix(in srgb, var(--task-list-color) 32%, rgba(255, 255, 255, 0.08));
}

.focus-dialog .task-list-preview-chip {
  padding: 8px 12px;
  border-radius: 11px;
  font-size: 13px;
  box-shadow: 0 10px 22px color-mix(in srgb, var(--task-list-color) 28%, transparent), inset 0 0 0 1px rgba(255, 255, 255, 0.18);
}

.focus-dialog .task-list-preview-hint {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.4;
}


/* RESPONSIVE */
@media (max-width: 1280px) {
  .dashboard-grid {
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  }
  .column-right {
    grid-column: span 2;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }
  .quote-banner-card {
    grid-column: span 2;
  }
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 860px) {
  .sidebar {
    display: none;
  }
  .timer-card {
    height: auto;
    max-height: none;
  }
  .mobile-account {
    display: flex;
  }
  .banner-content {
    padding: 18px 20px;
  }
  .header-right-tools {
    gap: 8px;
  }
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .column-right {
    grid-column: span 1;
    grid-template-columns: minmax(0, 1fr);
  }
  .quote-banner-card {
    grid-column: span 1;
  }
}

@media (max-width: 560px) {
  .column-right {
    width: 100%;
    min-width: 0;
  }

  .task-list-filter-row {
    gap: 6px;
  }

  .task-date-toolbar {
    gap: 5px;
  }

  .task-date-picker-label {
    max-width: 140px;
  }

  .task-date-today {
    padding: 0 7px;
  }

  .task-date-filter {
    max-width: 100px;
    padding-inline: 5px;
    font-size: 10px;
  }

  .filter-pills {
    flex: 1;
    flex-wrap: nowrap;
    gap: 4px;
    overflow-x: auto;
  }

  .filter-pills .pill {
    flex: 0 0 auto;
    padding: 4px 6px;
    font-size: 10px;
  }

  .task-list-filter-row .add-task-btn {
    flex: 0 0 auto;
    padding: 6px 7px;
    font-size: 10.5px;
    white-space: nowrap;
  }

  .header-right-tools {
    gap: 6px;
  }

  .date-chip,
  .time-chip {
    min-height: 40px;
    gap: 6px;
    padding: 0 9px;
    font-size: 12px;
  }

  .date-chip {
    flex: 0 1 auto;
  }

  .date-chip i,
  .time-chip i {
    font-size: 16px;
  }

  .notification-btn {
    width: 40px;
    height: 40px;
  }

  .tasks-card {
    padding: 16px;
  }

  .timer-card {
    height: auto;
    max-height: none;
    min-width: 0;
    padding: 16px;
    gap: 14px;
  }

  .timer-main-row {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    flex-direction: column;
    gap: 16px;
    padding: 4px 0 0;
  }

  .radial-timer-container {
    width: min(170px, 52vw);
    height: min(170px, 52vw);
  }

  .timer-side-controls,
  .active-task-info,
  .task-status-row {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }

  .timer-side-controls {
    flex: none;
    gap: 12px;
    align-items: center;
  }

  .active-task-info {
    align-items: center;
    text-align: center;
  }

  .task-status-row {
    justify-content: center;
  }

  .task-status-row {
    flex-wrap: wrap;
    gap: 6px;
  }

  .active-task-name {
    max-width: 100%;
    overflow-wrap: anywhere;
  }

  .timer-actions-vertical {
    display: grid;
    align-self: center;
    width: min(100%, 320px);
    max-width: 100%;
    min-width: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .pause-btn,
  .complete-btn,
  .restart-task-btn {
    min-width: 0;
    padding: 10px 8px;
    font-size: 12px;
    gap: 6px;
  }

  .restart-task-btn {
    grid-column: 1 / -1;
  }

  .focus-details-card {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    padding: 12px;
  }

  .focus-stats-quad {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .metric-box {
    min-width: 0;
    padding: 10px 9px;
  }

  .metric-top {
    min-width: 0;
    flex-wrap: wrap;
  }

  .metric-label {
    min-width: 0;
  }

  .header-banner,
  .banner-content {
    min-height: 0;
  }

  .banner-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
  }

  .greeting-title {
    font-size: 20px;
  }

  .greeting-subtitle {
    font-size: 12px;
  }

  .header-right-tools {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .date-chip {
    flex: 1 1 140px;
  }

  .task-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
    padding: 12px;
    flex: 0 0 auto;
  }

  .task-left,
  .task-right {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }

  .task-left {
    gap: 10px;
  }

  .task-details {
    flex: 1;
    min-width: 0;
  }

  .task-name {
    overflow-wrap: anywhere;
  }

  .task-right {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }

  .pending-meta {
    justify-self: start;
    white-space: nowrap;
  }

  .completed-meta {
    min-width: 0;
    align-items: flex-start;
    justify-content: center;
  }

  .time-meta {
    white-space: nowrap;
  }

  .task-action-btns {
    gap: 5px;
    margin-left: 0;
    padding-left: 8px;
  }

  .ambient-card,
  .ref-music-station {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    padding: 14px;
  }

  .ambient-ref-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 14px;
    max-height: 300px;
    padding-right: 3px;
  }

  .amb-ref-card {
    min-width: 0;
    height: 72px;
  }

  .amb-hatch-block {
    width: 50px;
    min-width: 50px;
  }

  .amb-block-icon {
    font-size: 21px;
  }

  .amb-content-block {
    padding: 7px 6px;
  }

  .amb-top-row {
    gap: 2px;
  }

  .amb-title {
    font-size: 11.5px;
  }

  .amb-heart-btn {
    flex-basis: 22px;
    width: 22px;
    height: 22px;
    font-size: 13px;
  }

  .amb-bottom-row {
    gap: 4px;
  }

  .amb-vol-pct {
    font-size: 9px;
  }

  .amb-content-block {
    min-width: 0;
    padding: 8px 10px;
  }

  .amb-bottom-row {
    min-width: 0;
    gap: 8px;
  }

  .amb-slider-wrap {
    min-width: 0;
  }

  .music-ref-header {
    min-width: 0;
    gap: 8px;
  }

  .music-header-left {
    min-width: 0;
    flex: 1;
    gap: 8px;
  }

  .music-icon-pill {
    width: 34px;
    height: 34px;
    flex-basis: 34px;
  }

  .music-header-titles {
    min-width: 0;
    flex: 1;
  }

  .music-main-title {
    font-size: 14px;
  }

  .music-subtitle {
    font-size: 10.5px;
    line-height: 1.25;
  }

  .music-add-link-btn {
    flex: 0 0 auto;
    gap: 4px;
    padding: 6px 9px;
    font-size: 11px;
  }

  .hero-now-playing-box {
    padding: 12px;
    gap: 12px;
  }

  .hero-top-row {
    gap: 8px;
  }

  .hero-top-left {
    gap: 10px;
  }

  .hero-artwork-wrap {
    width: 64px;
    height: 64px;
    min-width: 64px;
    flex-basis: 64px;
    border-radius: 10px;
  }

  .hero-bottom-row {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }

  .hero-seeker-container {
    width: auto;
    min-width: 0;
    flex: 1 1 auto;
    gap: 5px;
  }

  .hero-seek-forward-btn {
    width: 26px;
    flex-basis: 26px;
  }

  .hero-seeker-slider {
    min-width: 0;
  }

  .hero-controls-row {
    width: auto;
    flex: 0 0 auto;
    justify-content: flex-end;
    gap: 4px;
  }

  .hero-skip-btn {
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
  }

  .hero-big-play-btn {
    width: 34px;
    height: 34px;
    flex: 0 0 34px;
  }

  .ref-playlist-section,
  .ref-playlist-header,
  .ref-playlist-header-left,
  .ref-playlist-titles {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }

  .ref-playlist-header {
    gap: 6px;
  }

  .ref-playlist-header-left {
    flex: 1;
    gap: 6px;
  }

  .ref-playlist-titles {
    flex: 1;
  }

  .playlist-picker {
    width: auto;
    min-width: auto;
  }

  .ref-tracks-badge {
    flex: 0 0 auto;
    padding: 4px 7px;
    font-size: 10px;
  }

  .ref-tracks-list,
  .ref-track-card {
    min-width: 0;
    box-sizing: border-box;
  }

  .action-btn {
    width: 32px;
    height: 32px;
  }
}

@media (min-width: 861px) and (max-width: 1280px) {
  .dashboard-grid {
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  }

  .tasks-card {
    height: 610px;
    max-height: 610px;
  }

  .timer-card {
    height: auto;
    min-height: 610px;
    max-height: none;
  }

  .radial-timer-container {
    width: 200px;
    height: 200px;
  }

  .timer-digits {
    font-size: 29px;
  }

  .column-right {
    grid-column: span 2;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }

  .ambient-card {
    padding: 15px;
  }

  .ambient-ref-grid {
    gap: 8px 14px;
    max-height: 230px;
  }

}

@media (min-width: 1281px) {
  .main-wrapper {
    padding-bottom: 24px;
  }

  .bottom-page-spacer {
    height: 0;
  }

  .dashboard-grid {
    flex: 1 1 0;
    min-height: 0;
    align-items: stretch;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.2fr) minmax(320px, 1fr);
  }

  .tasks-card,
  .timer-card {
    height: auto;
    min-height: 0;
    max-height: none;
  }

  .radial-timer-container {
    width: 216px;
    height: 216px;
  }

  .timer-digits {
    font-size: 30px;
  }

  .timer-status-label {
    font-size: 12px;
  }

  .active-task-name {
    font-size: 17px;
  }

  .timer-side-controls {
    gap: 16px;
  }

  .timer-actions-vertical {
    gap: 8px;
  }

  .pause-btn,
  .complete-btn {
    min-height: 64px;
    padding-right: 8px;
    padding-left: 8px;
    font-size: 13px;
  }

  .column-right {
    grid-column: auto;
    align-self: stretch;
    min-height: 0;
  }

  .column-right > .ambient-card,
  .column-right > .ref-music-station {
    flex: 1 1 0;
    min-height: 0;
  }

  .ambient-card {
    display: flex;
    flex-direction: column;
    padding: 15px;
  }

  .ambient-ref-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    flex: 1;
    min-height: 0;
    gap: 8px 16px;
    max-height: none;
  }

  .amb-ref-card {
    height: 64px;
  }

  .amb-hatch-block {
    width: 48px;
    min-width: 48px;
  }

  .amb-block-icon {
    font-size: 20px;
  }

  .amb-content-block {
    padding: 6px 5px;
  }

  .amb-top-row {
    gap: 2px;
  }

  .amb-title {
    font-size: 11px;
  }

  .amb-heart-btn {
    flex-basis: 22px;
    width: 22px;
    height: 22px;
    font-size: 13px;
  }

  .amb-bottom-row {
    gap: 4px;
  }

  .amb-vol-pct {
    font-size: 9px;
  }

  .ref-playlist-section {
    flex: 1 1 0;
    min-height: 69px;
  }

  .ref-playlist-header {
    flex: 0 0 auto;
    padding: 8px 10px;
  }

  .ref-tracks-list {
    flex: 1 1 auto;
    min-height: 0;
    max-height: 120px;
  }

  .ref-music-station {
    padding: 9px;
  }

  .music-ref-header {
    margin-bottom: 8px;
  }

  .music-icon-pill {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
    font-size: 15px;
  }

  .music-main-title {
    font-size: 13px;
  }

  .music-subtitle {
    font-size: 9.5px;
  }

  .music-add-link-btn {
    padding: 6px 8px;
    font-size: 10px;
  }

  .hero-now-playing-box {
    flex: 0 0 auto;
    padding: 10px;
    gap: 8px;
    margin-bottom: 8px;
    border-radius: 14px;
  }

  .hero-top-row {
    gap: 8px;
  }

  .hero-top-left {
    gap: 9px;
  }

  .hero-meta-col {
    gap: 0;
  }

  .hero-track-artist {
    margin-top: 0;
    margin-bottom: 2px;
    font-size: 11px;
  }

  .hero-badge-row {
    flex-wrap: nowrap;
    gap: 4px;
  }

  .live-stream-pill {
    gap: 4px;
    padding: 3px 7px;
    font-size: 10px;
  }

  .toggle-video-pill {
    width: 26px;
    height: 26px;
    flex: 0 0 26px;
  }

  .hero-artwork-wrap {
    width: 56px;
    height: 56px;
    min-width: 56px;
    flex-basis: 56px;
    border-radius: 9px;
  }

  .hero-bottom-row {
    flex-direction: row;
    align-items: center;
    gap: 6px;
  }

  .hero-seeker-container {
    width: auto;
    min-width: 0;
    flex: 1 1 auto;
    gap: 4px;
  }

  .hero-controls-row {
    width: auto;
    flex: 0 0 auto;
    justify-content: flex-end;
    gap: 3px;
  }

  .hero-skip-btn {
    width: 26px;
    height: 26px;
    flex-basis: 26px;
  }

  .hero-big-play-btn {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
  }

}

@media (min-width: 561px) {
  .timer-main-row {
    flex-direction: column;
    justify-content: flex-start;
    gap: 12px;
  }

  .radial-timer-container {
    align-self: center;
  }

  .timer-side-controls {
    align-self: stretch;
    width: 100%;
    flex: none;
    align-items: center;
    gap: 12px;
  }

  .active-task-info {
    align-items: center;
    text-align: center;
  }

  .task-status-row {
    justify-content: center;
  }

  .timer-actions-vertical {
    align-self: center;
  }
}

@media (max-width: 340px) {
  .hero-seeker-container > .seeker-time-label:last-of-type {
    display: none;
  }

  .hero-controls-row {
    gap: 2px;
  }

  .hero-skip-btn {
    width: 24px;
    height: 24px;
    flex-basis: 24px;
  }

  .hero-skip-btn i {
    font-size: 13px;
  }

  .hero-big-play-btn {
    width: 30px;
    height: 30px;
    flex-basis: 30px;
  }

  .hero-big-play-btn i {
    font-size: 16px;
  }

  .seeker-time-label {
    font-size: 9px;
  }

  .hero-seek-forward-btn {
    width: 23px;
    height: 22px;
    flex-basis: 23px;
    font-size: 9px;
  }

  .ambient-ref-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .amb-ref-card {
    height: 72px;
  }

  .amb-hatch-block {
    width: 60px;
    min-width: 60px;
  }

  .amb-content-block {
    padding: 8px 10px;
  }

  .amb-title {
    font-size: 12.5px;
  }

  .amb-heart-btn {
    flex-basis: 28px;
    width: 28px;
    height: 28px;
  }

  .amb-bottom-row {
    gap: 8px;
  }

  .amb-vol-pct {
    font-size: 10.5px;
  }
}

/* EMPTY PLAYLIST STATE */
.empty-playlist-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 28px 16px;
  text-align: center;
}

.empty-playlist-icon {
  font-size: 32px;
  color: #475569;
  opacity: 0.6;
}

.empty-playlist-msg {
  font-size: 14px;
  font-weight: 600;
  color: #94a3b8;
}

.empty-playlist-sub {
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
}

.focus-immersive {
  position: fixed;
  z-index: 1600;
  inset: 0;
  display: flex;
  min-width: 0;
  min-height: 100vh;
  min-height: 100dvh;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
  padding: clamp(18px, 3vw, 42px);
  overflow: hidden;
  background:
    radial-gradient(ellipse at 49% 38%, rgba(32, 86, 78, 0.28), transparent 54%),
    radial-gradient(ellipse at 85% 75%, rgba(40, 67, 73, 0.18), transparent 42%),
    #080d12;
  color: #f8fafc;
  isolation: isolate;
}

.focus-immersive:fullscreen {
  width: 100vw;
  height: 100vh;
  min-height: 0;
  border: 0;
}

.focus-immersive-background-video,
.focus-immersive-backdrop {
  position: absolute;
  z-index: -2;
  inset: 0;
  width: 100%;
  height: 100%;
}

.focus-immersive-background-video {
  object-fit: cover;
  background: radial-gradient(ellipse at 50% 40%, #243b3b 0%, #111b20 48%, #080d12 100%);
}

.focus-immersive-background-embed {
  border: 0;
  pointer-events: none;
  transform: scale(1);
  filter: none;
  transition: transform 4.2s cubic-bezier(0.2, 0.7, 0.2, 1), filter 1.1s ease;
}

.focus-immersive-background-embed.is-intro {
  transform: scale(1.055);
  filter: blur(5px) brightness(0.45);
}

.focus-immersive-video-reveal {
  position: absolute;
  z-index: 0;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse at center, rgba(7, 13, 17, 0.92), rgba(7, 13, 17, 0.99)),
    #080d12;
  animation: focus-video-curtain-reveal 4.2s cubic-bezier(0.22, 0.7, 0.25, 1) forwards;
}

@keyframes focus-video-curtain-reveal {
  0% {
    opacity: 1;
    clip-path: inset(0 0 0 0);
  }

  48% {
    opacity: 0.96;
    clip-path: inset(0 0 0 0);
  }

  100% {
    opacity: 0;
    clip-path: inset(50% 0 50% 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .focus-immersive-background-embed,
  .focus-immersive-background-embed.is-intro {
    transform: none;
    filter: none;
    transition: none;
  }

  .focus-immersive-video-reveal {
    animation-duration: 1ms;
  }
}

.focus-immersive-backdrop {
  z-index: -1;
  background:
    linear-gradient(180deg, rgba(5, 10, 13, 0.56), rgba(5, 10, 13, 0.18) 42%, rgba(5, 10, 13, 0.62)),
    radial-gradient(ellipse at 49% 38%, rgba(18, 40, 39, 0.12), rgba(4, 10, 13, 0.48));
  backdrop-filter: saturate(0.8);
}

.focus-video-paused-cover {
  position: absolute;
  z-index: 0;
  inset: 0;
  pointer-events: none;
  background: rgba(5, 10, 13, 0.42);
  backdrop-filter: blur(2px);
}

.focus-immersive-close {
  position: absolute;
  z-index: 1000;
  top: clamp(12px, 2vw, 24px);
  right: clamp(12px, 2vw, 24px);
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 12px;
  background: rgba(8, 14, 17, 0.62);
  color: #f8fafc;
  font-size: 18px;
  cursor: pointer;
  backdrop-filter: blur(12px);
  transition: background 150ms ease, border-color 150ms ease;
}

.focus-immersive-close:hover {
  border-color: rgba(255, 255, 255, 0.48);
  background: rgba(8, 14, 17, 0.86);
}

.focus-immersive-notice {
  position: absolute;
  z-index: 1001;
  top: 18px;
  left: 50%;
  max-width: min(520px, calc(100vw - 100px));
  margin: 0;
  padding: 10px 14px;
  transform: translateX(-50%);
  border: 1px solid rgba(251, 191, 36, 0.35);
  border-radius: 10px;
  background: rgba(69, 39, 6, 0.88);
  color: #fef3c7;
  font-size: 12px;
  text-align: center;
  backdrop-filter: blur(12px);
}

.focus-immersive-notice button {
  flex: 0 0 auto;
  padding: 6px 9px;
  border: 1px solid rgba(253, 230, 138, 0.55);
  border-radius: 7px;
  background: rgba(120, 73, 8, 0.72);
  color: #fffbeb;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.focus-immersive-notice button:hover {
  background: rgba(146, 92, 12, 0.9);
}

.focus-immersive-notice.video-error {
  top: auto;
  bottom: 16px;
  border-color: rgba(248, 113, 113, 0.38);
  background: rgba(69, 10, 10, 0.9);
  color: #fee2e2;
}

.focus-immersive-panel {
  position: absolute;
  z-index: 2;
  display: flex;
  width: min(520px, calc(100vw - 36px));
  max-height: calc(100dvh - 20px);
  flex-direction: column;
}

.focus-immersive-panel-timer {
  top: 20px;
  left: 20px;
}

.focus-immersive-panel-competitors {
  top: 20px;
  right: 20px;
}

.focus-immersive-panel-video {
  bottom: 92px;
  left: 20px;
}

.focus-immersive-panel-music {
  right: 20px;
  bottom: 20px;
}

.focus-immersive-panel .focus-immersive-card {
  width: 100%;
}

.focus-immersive-panel {
  cursor: grab;
  touch-action: auto;
  user-select: none;
}

.focus-immersive-panel:active {
  cursor: grabbing;
}

.focus-panel-header,
.focus-music-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.focus-panel-header {
  margin: 0 0 10px;
}

.focus-panel-title,
.focus-panel-header > span {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 7px;
  color: #e2e8f0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.focus-panel-heading {
  gap: 7px;
}

.focus-panel-heading > .focus-immersive-live {
  margin-left: 4px;
  text-transform: none;
}

.focus-panel-heading > .focus-immersive-live > span {
  display: inline-block;
}

.focus-panel-heading > .ti-world {
  margin-left: 2px;
}

.focus-panel-title > i,
.focus-panel-header > span > i {
  flex: 0 0 auto;
  color: var(--brand-accent);
  font-size: 15px;
}

.focus-panel-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.focus-music-panel-header {
  margin-bottom: 14px;
}

.focus-panel-actions button {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 7px;
  background: rgba(30, 41, 59, 0.9);
  color: #f8fafc;
  font-size: 14px;
  cursor: pointer;
}

.focus-panel-actions button.focus-panel-drag-handle {
  cursor: grab;
  touch-action: none;
}

.focus-panel-actions button.focus-panel-drag-handle:active {
  cursor: grabbing;
}

.focus-panel-drag-handle {
  display: grid;
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  place-items: center;
  margin-left: 3px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 7px;
  background: rgba(30, 41, 59, 0.9);
  color: #f8fafc;
  cursor: grab;
  touch-action: none;
}

.focus-panel-drag-handle:active {
  cursor: grabbing;
}

.focus-panel-actions button:hover,
.focus-panel-actions button[aria-pressed="true"] {
  border-color: var(--brand-accent);
  background: var(--brand-accent);
  color: var(--brand-accent-ink);
}

.focus-immersive-dock {
  position: absolute;
  z-index: 1000;
  bottom: clamp(14px, 2.5vw, 28px);
  left: clamp(14px, 2.5vw, 28px);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 14px;
  background: rgba(8, 14, 17, 0.94);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(16px);
}

.focus-immersive-dock button {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 10px;
  background: rgba(30, 41, 59, 0.94);
  color: #f8fafc;
  font-size: 18px;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease, color 150ms ease, transform 150ms ease;
}

.focus-immersive-dock button:hover {
  transform: translateY(-2px);
  border-color: var(--brand-accent);
  color: var(--brand-accent-strong);
}

.focus-immersive-dock button.active {
  border-color: var(--brand-accent);
  background: var(--brand-accent);
  color: var(--brand-accent-ink);
}

.focus-immersive-card {
  box-sizing: border-box;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 18px;
  background: rgba(9, 16, 19, 0.7);
  box-shadow: 0 14px 44px rgba(0, 0, 0, 0.24);
  color: #f8fafc;
  backdrop-filter: blur(18px) saturate(1.1);
}

.focus-immersive-timer {
  width: min(430px, calc(100vw - 100px));
  padding: 20px 22px;
}

.focus-immersive-card-heading {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.focus-immersive-eyebrow {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 7px;
  color: rgba(226, 232, 240, 0.72);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  line-height: 1.3;
}

.focus-immersive-eyebrow i {
  color: var(--brand-accent);
  font-size: 14px;
}

.focus-immersive-live {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  color: #cbd5e1;
  font-size: 10px;
  font-weight: 700;
}

.focus-immersive-live > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94a3b8;
}

.focus-immersive-live.running > span {
  background: #34d399;
  box-shadow: 0 0 10px rgba(52, 211, 153, 0.75);
  animation: focus-live-pulse 1.7s ease-in-out infinite;
}

.focus-immersive-timer h1 {
  display: -webkit-box;
  margin: 16px 0 4px;
  overflow: hidden;
  color: #f8fafc;
  font-size: clamp(18px, 2vw, 24px);
  font-weight: 700;
  line-height: 1.3;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.focus-immersive-task-meta {
  margin: 0;
  color: rgba(226, 232, 240, 0.7);
  font-size: 12px;
}

.focus-immersive-countdown {
  margin-top: 14px;
  color: #ffffff;
  font-size: clamp(36px, 5vw, 54px);
  font-variant-numeric: tabular-nums;
  font-weight: 650;
  letter-spacing: -0.05em;
  line-height: 1;
  text-shadow: 0 2px 24px rgba(0, 0, 0, 0.42);
}

.focus-immersive-progress {
  height: 4px;
  margin-top: 14px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
}

.focus-immersive-progress > span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--brand-accent);
  box-shadow: 0 0 12px var(--brand-accent);
  transition: width 300ms linear;
}

.focus-immersive-timer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}

.focus-immersive-action {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 9px;
  font: inherit;
  font-size: 11px;
  font-weight: 750;
  cursor: pointer;
  transition: filter 150ms ease, background-color 150ms ease;
}

.focus-immersive-action:hover {
  filter: brightness(1.1);
}

.focus-immersive-action.primary {
  background: var(--brand-accent);
  color: #08201b;
}

.focus-immersive-action.secondary {
  border-color: rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.08);
  color: #f8fafc;
}

.focus-immersive-hint {
  color: rgba(226, 232, 240, 0.64);
  font-size: 11px;
}

.focus-immersive-competitors {
  width: min(330px, calc(100vw - 100px));
  min-height: 182px;
  padding: 18px;
}

.focus-immersive-competitors > .focus-immersive-card-heading > i {
  color: rgba(226, 232, 240, 0.65);
  font-size: 17px;
}

.focus-immersive-competitors-empty {
  display: flex;
  min-height: 120px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 0 2px;
  text-align: center;
}

.focus-immersive-competitors-empty > i {
  color: rgba(226, 232, 240, 0.5);
  font-size: 25px;
}

.focus-immersive-competitors-empty p {
  margin: 8px 0 3px;
  color: #f1f5f9;
  font-size: 12px;
  font-weight: 700;
}

.focus-immersive-competitors-empty span {
  max-width: 230px;
  color: rgba(226, 232, 240, 0.62);
  font-size: 10px;
  line-height: 1.5;
}

.focus-immersive-video-card {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  width: min(520px, calc(100vw - 40px));
  min-height: 88px;
  align-items: center;
  gap: 12px;
  padding: 10px;
}

.focus-immersive-video-card > .focus-panel-header {
  flex: 0 0 100%;
  margin: 0;
}

.focus-video-preview {
  display: grid;
  width: 112px;
  height: 64px;
  flex: 0 0 112px;
  overflow: hidden;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.17);
  border-radius: 10px;
  background: linear-gradient(135deg, #183b3b, #101820 65%, #252c32);
}

.focus-video-preview img {
  width: 100%;
  height: 100%;
  border: 0;
  object-fit: cover;
}

.focus-video-placeholder {
  display: grid;
  width: 100%;
  height: 100%;
  place-items: center;
  color: rgba(226, 232, 240, 0.68);
  font-size: 22px;
}

.focus-video-details,
.focus-music-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.focus-video-details strong,
.focus-music-main strong {
  overflow: hidden;
  color: #f8fafc;
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-video-details > span:last-child {
  overflow: hidden;
  color: rgba(226, 232, 240, 0.64);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-immersive-icon-button,
.focus-music-controls button {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.08);
  color: #f8fafc;
  font-size: 15px;
  cursor: pointer;
  transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
}

.focus-immersive-icon-button:hover,
.focus-music-controls button:not(:disabled):hover {
  border-color: var(--brand-accent);
  background: rgba(255, 255, 255, 0.14);
  color: var(--brand-accent);
}

.focus-immersive-icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.focus-immersive-icon-button.focus-video-play-toggle {
  background: var(--brand-accent);
  color: #08201b;
}

.focus-immersive-icon-button.focus-video-play-toggle:hover:not(:disabled) {
  filter: brightness(1.12);
}

.focus-video-controls {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 5px;
}

.focus-video-volume-slider {
  width: 62px;
  height: 4px;
  margin: 0;
  accent-color: var(--brand-accent);
  cursor: pointer;
}

.focus-video-volume-slider:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.focus-video-picker {
  position: absolute;
  z-index: 5;
  bottom: calc(100% + 10px);
  left: 0;
  width: min(360px, calc(100vw - 40px));
  box-sizing: border-box;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 14px;
  background: rgba(9, 16, 19, 0.94);
  box-shadow: 0 16px 44px rgba(0, 0, 0, 0.36);
  backdrop-filter: blur(22px);
}

.focus-video-picker-heading,
.focus-video-link-form > div,
.focus-video-picker-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.focus-video-picker-heading {
  justify-content: space-between;
  margin-bottom: 12px;
}

.focus-video-picker-heading strong {
  color: #f8fafc;
  font-size: 12px;
}

.focus-video-picker-heading button {
  display: grid;
  width: 27px;
  height: 27px;
  place-items: center;
  border: 0;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
  cursor: pointer;
}

.focus-video-link-form label {
  display: block;
  margin-bottom: 6px;
  color: rgba(226, 232, 240, 0.72);
  font-size: 10px;
  font-weight: 700;
}

.focus-video-link-form input {
  width: 0;
  min-width: 0;
  min-height: 36px;
  flex: 1;
  box-sizing: border-box;
  padding: 0 9px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  outline: none;
  background: rgba(255, 255, 255, 0.07);
  color: #f8fafc;
  font: inherit;
  font-size: 11px;
}

.focus-video-link-form input:focus {
  border-color: var(--brand-accent);
}

.focus-video-link-form > div > button,
.focus-video-picker-actions > button {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.17);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.09);
  color: #f8fafc;
  font: inherit;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
}

.focus-video-link-form > div > button {
  border-color: transparent;
  background: var(--brand-accent);
  color: #08201b;
}

.focus-video-picker-actions {
  justify-content: space-between;
  margin-top: 10px;
}

.focus-video-picker-actions > button.remove-video-action {
  border-color: rgba(248, 113, 113, 0.3);
  color: #fecaca;
}

.focus-video-file-input {
  display: none;
}

.focus-immersive-music {
  display: flex;
  width: 100%;
  min-height: 88px;
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
  padding: 14px;
}

.focus-immersive-panel-music {
  overflow-y: auto;
}

.focus-music-panel-content {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
}

.focus-music-cover,
.focus-music-cover-placeholder {
  width: 56px;
  height: 56px;
  flex: 0 0 56px;
  border: 1px solid rgba(255, 255, 255, 0.17);
  border-radius: 9px;
  object-fit: cover;
}

.focus-music-cover {
  -webkit-user-drag: none;
  user-select: none;
}

.focus-music-cover-placeholder {
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(226, 232, 240, 0.68);
  font-size: 20px;
}

.focus-music-main > input[type="range"] {
  width: 100%;
  height: 3px;
  margin: 5px 0 0;
  accent-color: var(--brand-accent);
  cursor: pointer;
}

.focus-music-main > input[type="range"]:disabled {
  cursor: default;
  opacity: 0.45;
}

.focus-music-main {
  min-width: 120px;
}

.focus-music-controls {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 5px;
}

.focus-music-volume-slider {
  width: 54px;
  height: 4px;
  margin: 0;
  accent-color: var(--brand-accent);
  cursor: pointer;
}

.focus-music-volume-slider:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.focus-music-controls button.focus-music-volume-toggle {
  width: 28px;
  height: 28px;
  flex-basis: 28px;
  font-size: 13px;
}

.focus-music-controls button {
  width: 31px;
  height: 31px;
  flex-basis: 31px;
  border-radius: 50%;
  font-size: 13px;
}

.focus-music-controls button.focus-music-play {
  width: 38px;
  height: 38px;
  flex-basis: 38px;
  border-color: var(--brand-accent);
  background: var(--brand-accent);
  color: #08201b;
  font-size: 16px;
}

.focus-music-controls button:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

@keyframes focus-live-pulse {
  50% {
    opacity: 0.45;
    transform: scale(0.82);
  }
}

@media (max-width: 760px) {
  .focus-immersive {
    padding: 14px;
  }

  .focus-immersive-competitors {
    min-height: 0;
    padding: 12px 16px;
  }

  .focus-immersive-competitors-empty {
    min-height: 76px;
  }

  .focus-immersive-dock {
    gap: 6px;
    padding: 6px;
  }

  .focus-immersive-dock button {
    width: 38px;
    height: 38px;
  }

  .focus-video-picker {
    bottom: calc(100% + 8px);
  }
}

@media (max-width: 420px) {
  .focus-immersive-timer {
    padding: 16px;
  }

  .focus-immersive-countdown {
    font-size: 40px;
  }

  .focus-video-preview {
    width: 82px;
    height: 54px;
    flex-basis: 82px;
  }

  .focus-video-controls {
    gap: 3px;
  }

  .focus-video-controls .focus-immersive-icon-button {
    width: 30px;
    height: 30px;
    flex-basis: 30px;
  }

  .focus-video-volume-slider {
    width: 42px;
  }

  .focus-music-cover,
  .focus-music-cover-placeholder {
    width: 44px;
    height: 44px;
    flex-basis: 44px;
  }

  .focus-immersive-music {
    gap: 10px;
    padding: 10px;
  }

  .focus-music-panel-content {
    flex-wrap: wrap;
    gap: 8px;
  }

  .focus-music-main {
    min-width: 100px;
    flex: 1 1 120px;
  }

  .focus-music-controls {
    margin-left: auto;
  }

  .focus-music-controls {
    gap: 2px;
  }

  .focus-music-volume-slider {
    width: 40px;
  }

  .focus-music-controls button.focus-music-volume-toggle {
    width: 25px;
    height: 25px;
    flex-basis: 25px;
  }

  .focus-music-controls button {
    width: 27px;
    height: 27px;
    flex-basis: 27px;
  }

  .focus-music-controls button.focus-music-play {
    width: 33px;
    height: 33px;
    flex-basis: 33px;
  }
}

/* SPIN PULSE ANIMATION FOR LOADER */
.spin-pulse {
  animation: spinPulse 1s linear infinite;
}

@keyframes spinPulse {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}


</style>
