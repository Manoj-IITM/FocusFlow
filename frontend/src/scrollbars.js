const TRACK_SIZE = 6;
const FIXED_THUMB_LENGTH = 34;
const OVERFLOW_VALUES = new Set(["auto", "scroll", "overlay"]);

let layer;
let modalLayer;
let observer;
let resizeObserver;
let refreshFrame = 0;
let updateFrame = 0;
let started = false;
const scrollbars = new Map();
const observedElements = new Set();

const getRootScroller = () => document.scrollingElement || document.documentElement;

const isRootScroller = (element) => element === getRootScroller();

const getScrollbarLayer = (element) =>
  element.closest?.(".modal-overlay") && modalLayer ? modalLayer : layer;

const getAxisMetrics = (element, axis) => {
  const root = isRootScroller(element);
  const isVertical = axis === "y";
  const clientLength = root
    ? (isVertical ? document.documentElement.clientHeight : document.documentElement.clientWidth)
    : (isVertical ? element.clientHeight : element.clientWidth);
  const scrollLength = root
    ? (isVertical
      ? Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0)
      : Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0))
    : (isVertical ? element.scrollHeight : element.scrollWidth);
  const position = isVertical ? element.scrollTop : element.scrollLeft;

  return {
    root,
    clientLength,
    scrollLength,
    maxScroll: Math.max(0, scrollLength - clientLength),
    position: Math.max(0, Math.min(Math.max(0, scrollLength - clientLength), position || 0)),
  };
};

const hasScrollableOverflow = (element, axis) => {
  const { clientLength, scrollLength } = getAxisMetrics(element, axis);
  if (scrollLength <= clientLength + 1) return false;
  if (isRootScroller(element)) return true;

  const style = getComputedStyle(element);
  const overflow = axis === "y" ? style.overflowY : style.overflowX;
  return OVERFLOW_VALUES.has(overflow);
};

const createTrack = (element, axis) => {
  const track = document.createElement("div");
  const thumb = document.createElement("div");
  const vertical = axis === "y";

  track.className = `app-scrollbar-track app-scrollbar-track-${axis}`;
  track.dataset.scrollbarAxis = axis;
  thumb.className = "app-scrollbar-thumb";
  thumb.setAttribute("role", "scrollbar");
  thumb.setAttribute("aria-orientation", vertical ? "vertical" : "horizontal");
  thumb.setAttribute("aria-label", vertical ? "Vertical scrollbar" : "Horizontal scrollbar");
  thumb.setAttribute("aria-valuemin", "0");
  thumb.tabIndex = 0;
  track.append(thumb);

  const state = { element, axis, track, thumb, dragging: null };
  track.addEventListener("pointerdown", (event) => beginDrag(state, event));
  track.addEventListener("pointermove", (event) => moveDrag(state, event));
  track.addEventListener("pointerup", (event) => endDrag(state, event));
  track.addEventListener("pointercancel", (event) => endDrag(state, event));
  track.addEventListener("lostpointercapture", () => { state.dragging = null; });
  thumb.addEventListener("keydown", (event) => handleKey(state, event));

  getScrollbarLayer(element).append(track);
  return state;
};

const getPointerPosition = (state, event) => state.axis === "y" ? event.clientY : event.clientX;

const setScrollPosition = (state, value) => {
  if (state.axis === "y") state.element.scrollTop = value;
  else state.element.scrollLeft = value;
};

const beginDrag = (state, event) => {
  if (event.button !== 0) return;
  const metrics = getAxisMetrics(state.element, state.axis);
  if (!metrics.maxScroll) return;

  event.preventDefault();
  const vertical = state.axis === "y";
  const bounds = state.track.getBoundingClientRect();
  const trackStart = vertical ? bounds.top : bounds.left;
  const thumbStart = Number.parseFloat(state.thumb.style[vertical ? "top" : "left"]) || 0;
  const thumbLength = vertical ? state.thumb.offsetHeight : state.thumb.offsetWidth;
  const pointerPosition = getPointerPosition(state, event);
  const wasThumb = event.target === state.thumb;
  const pointerOffset = wasThumb
    ? pointerPosition - trackStart - thumbStart
    : thumbLength / 2;

  state.dragging = { pointerOffset };
  state.track.setPointerCapture?.(event.pointerId);
  if (!wasThumb) moveDrag(state, event);
};

const moveDrag = (state, event) => {
  if (!state.dragging) return;
  const metrics = getAxisMetrics(state.element, state.axis);
  const vertical = state.axis === "y";
  const trackLength = vertical ? state.track.clientHeight : state.track.clientWidth;
  const thumbLength = vertical ? state.thumb.offsetHeight : state.thumb.offsetWidth;
  const travel = Math.max(0, trackLength - thumbLength);
  if (!travel || !metrics.maxScroll) return;

  const bounds = state.track.getBoundingClientRect();
  const trackStart = vertical ? bounds.top : bounds.left;
  const desiredThumbPosition = getPointerPosition(state, event) - trackStart - state.dragging.pointerOffset;
  const ratio = Math.max(0, Math.min(1, desiredThumbPosition / travel));
  setScrollPosition(state, ratio * metrics.maxScroll);
  updateScrollbar(state);
};

const endDrag = (state, event) => {
  if (!state.dragging) return;
  state.dragging = null;
  if (state.track.hasPointerCapture?.(event.pointerId)) {
    state.track.releasePointerCapture(event.pointerId);
  }
};

const handleKey = (state, event) => {
  const metrics = getAxisMetrics(state.element, state.axis);
  if (!metrics.maxScroll) return;

  const page = Math.max(1, metrics.clientLength * 0.9);
  let nextPosition;
  if (state.axis === "y") {
    if (event.key === "ArrowDown") nextPosition = metrics.position + 40;
    else if (event.key === "ArrowUp") nextPosition = metrics.position - 40;
    else if (event.key === "PageDown") nextPosition = metrics.position + page;
    else if (event.key === "PageUp") nextPosition = metrics.position - page;
    else if (event.key === "Home") nextPosition = 0;
    else if (event.key === "End") nextPosition = metrics.maxScroll;
  } else {
    if (event.key === "ArrowRight") nextPosition = metrics.position + 40;
    else if (event.key === "ArrowLeft") nextPosition = metrics.position - 40;
    else if (event.key === "PageDown") nextPosition = metrics.position + page;
    else if (event.key === "PageUp") nextPosition = metrics.position - page;
    else if (event.key === "Home") nextPosition = 0;
    else if (event.key === "End") nextPosition = metrics.maxScroll;
  }

  if (nextPosition === undefined) return;
  event.preventDefault();
  setScrollPosition(state, Math.max(0, Math.min(metrics.maxScroll, nextPosition)));
  updateScrollbar(state);
};

const positionTrack = (state) => {
  const { element, axis } = state;
  const vertical = axis === "y";
  const root = isRootScroller(element);
  const bounds = root
    ? { left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight }
    : element.getBoundingClientRect();
  const clientLeft = root ? 0 : element.clientLeft;
  const clientTop = root ? 0 : element.clientTop;
  const clientWidth = root ? document.documentElement.clientWidth : element.clientWidth;
  const clientHeight = root ? document.documentElement.clientHeight : element.clientHeight;
  const style = root ? null : getComputedStyle(element);
  const borderRight = root ? 0 : Number.parseFloat(style.borderRightWidth) || 0;
  const borderBottom = root ? 0 : Number.parseFloat(style.borderBottomWidth) || 0;

  if (vertical) {
    const nativeGutter = root
      ? Math.max(0, window.innerWidth - document.documentElement.clientWidth)
      : Math.max(0, element.offsetWidth - element.clientWidth - clientLeft - borderRight);
    const innerRight = bounds.left + clientLeft + clientWidth;
    const trackWidth = nativeGutter > 0 ? Math.min(TRACK_SIZE, nativeGutter) : TRACK_SIZE;
    const x = nativeGutter > 0 ? innerRight : innerRight - trackWidth;
    state.track.style.left = `${x}px`;
    state.track.style.top = `${bounds.top + clientTop}px`;
    state.track.style.width = `${trackWidth}px`;
    state.track.style.height = `${clientHeight}px`;
  } else {
    const nativeGutter = root
      ? Math.max(0, window.innerHeight - document.documentElement.clientHeight)
      : Math.max(0, element.offsetHeight - element.clientHeight - clientTop - borderBottom);
    const innerBottom = bounds.top + clientTop + clientHeight;
    const trackHeight = nativeGutter > 0 ? Math.min(TRACK_SIZE, nativeGutter) : TRACK_SIZE;
    const y = nativeGutter > 0 ? innerBottom : innerBottom - trackHeight;
    state.track.style.left = `${bounds.left + clientLeft}px`;
    state.track.style.top = `${y}px`;
    state.track.style.width = `${clientWidth}px`;
    state.track.style.height = `${trackHeight}px`;
  }
};

const updateScrollbar = (state) => {
  const { element, axis, track, thumb } = state;
  if (!element.isConnected || !hasScrollableOverflow(element, axis)) {
    track.hidden = true;
    return;
  }

  const metrics = getAxisMetrics(element, axis);
  const vertical = axis === "y";
  const rect = element.getBoundingClientRect();
  if (!metrics.root && (rect.width <= 0 || rect.height <= 0)) {
    track.hidden = true;
    return;
  }
  track.hidden = false;
  positionTrack(state);

  const trackLength = vertical ? track.clientHeight : track.clientWidth;
  if (trackLength <= 0) {
    track.hidden = true;
    return;
  }
  const thumbLength = Math.min(trackLength, FIXED_THUMB_LENGTH);
  const travel = Math.max(0, trackLength - thumbLength);
  const thumbPosition = metrics.maxScroll ? travel * (metrics.position / metrics.maxScroll) : 0;

  if (vertical) {
    thumb.style.width = "100%";
    thumb.style.height = `${thumbLength}px`;
    thumb.style.left = "0";
    thumb.style.top = `${thumbPosition}px`;
  } else {
    thumb.style.width = `${thumbLength}px`;
    thumb.style.height = "100%";
    thumb.style.top = "0";
    thumb.style.left = `${thumbPosition}px`;
  }

  thumb.setAttribute("aria-valuemax", String(Math.round(metrics.maxScroll)));
  thumb.setAttribute("aria-valuenow", String(Math.round(metrics.position)));
};

const syncObservedElements = (elements) => {
  if (!resizeObserver) return;
  for (const element of observedElements) {
    if (!element.isConnected || !elements.has(element)) {
      resizeObserver.unobserve(element);
      observedElements.delete(element);
    }
  }
  for (const element of elements) {
    if (!observedElements.has(element)) {
      resizeObserver.observe(element);
      observedElements.add(element);
    }
  }
};

const refreshScrollbars = () => {
  refreshFrame = 0;
  if (!layer || !document.body) return;

  const elements = new Set([getRootScroller()]);
  const observationTargets = new Set([getRootScroller(), document.body]);
  document.body.querySelectorAll("*").forEach((element) => {
    if (!element.closest(".app-scrollbar-layer")) elements.add(element);
  });

  for (const element of elements) {
    let style;
    if (!isRootScroller(element)) style = getComputedStyle(element);
    if (
      isRootScroller(element) ||
      OVERFLOW_VALUES.has(style?.overflowY) ||
      OVERFLOW_VALUES.has(style?.overflowX)
    ) observationTargets.add(element);

    for (const axis of ["y", "x"]) {
      const key = `${axis}:${element === getRootScroller() ? "root" : getElementKey(element)}`;
      let state = scrollbars.get(key);
      if (hasScrollableOverflow(element, axis)) {
        if (!state) {
          state = createTrack(element, axis);
          scrollbars.set(key, state);
        } else {
          const ownerLayer = getScrollbarLayer(element);
          if (state.track.parentElement !== ownerLayer) ownerLayer.append(state.track);
        }
        updateScrollbar(state);
      } else if (state) {
        state.track.hidden = true;
      }
    }
  }
  for (const [key, state] of scrollbars) {
    if (!state.element.isConnected) {
      state.track.remove();
      scrollbars.delete(key);
    }
  }
  syncObservedElements(observationTargets);
};

const elementKeys = new WeakMap();
let nextElementKey = 1;
const getElementKey = (element) => {
  let key = elementKeys.get(element);
  if (!key) {
    key = nextElementKey++;
    elementKeys.set(element, key);
  }
  return key;
};

const scheduleRefresh = () => {
  if (!refreshFrame) refreshFrame = requestAnimationFrame(refreshScrollbars);
};

const updateAllScrollbars = () => {
  updateFrame = 0;
  for (const state of scrollbars.values()) updateScrollbar(state);
};

const scheduleUpdate = () => {
  if (!updateFrame) updateFrame = requestAnimationFrame(updateAllScrollbars);
};

export const initializeCustomScrollbars = () => {
  if (started || typeof window === "undefined" || !document.body) return;
  started = true;

  layer = document.createElement("div");
  layer.className = "app-scrollbar-layer";
  layer.setAttribute("aria-label", "Custom scrollbars");
  document.documentElement.append(layer);

  modalLayer = document.createElement("div");
  modalLayer.className = "app-scrollbar-layer app-scrollbar-modal-layer";
  modalLayer.setAttribute("aria-label", "Modal custom scrollbars");
  document.documentElement.append(modalLayer);

  document.documentElement.classList.add("app-custom-scrollbars-active");

  if ("ResizeObserver" in window) {
    resizeObserver = new ResizeObserver(scheduleRefresh);
    resizeObserver.observe(document.documentElement);
    resizeObserver.observe(document.body);
  }
  if ("MutationObserver" in window) {
    observer = new MutationObserver((records) => {
      if (records.some((record) => !record.target.closest?.(".app-scrollbar-layer"))) scheduleRefresh();
    });
    observer.observe(document.body, {
      attributes: true,
      childList: true,
      characterData: true,
      subtree: true,
    });
  }

  document.addEventListener("scroll", scheduleUpdate, true);
  window.addEventListener("resize", scheduleRefresh, { passive: true });
  window.addEventListener("orientationchange", scheduleRefresh, { passive: true });
  window.addEventListener("load", scheduleRefresh, { once: true });
  scheduleRefresh();
};
