<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";

// Feature data — each pairs a text block with a visual that shows on the sticky side.
const features = [
  {
    kicker: "Focus timer",
    title: "Sessions that fit the way you study",
    description:
      "Pomodoro, short and long breaks, or fully custom intervals. Start a session and let FocusFlow keep you on track until the bell rings.",
    accent: "#818cf8",
    visualType: "timer",
  },
  {
    kicker: "Study environment",
    title: "The right sounds for the right mindset",
    description:
      "Rain, forest, wind and lo-fi — mix them into your own soundscape and let the ambience fade in and out with your focus sessions.",
    accent: "#2dd4bf",
    visualType: "ambient",
  },
  {
    kicker: "Progress tracking",
    title: "See your consistency, not just your minutes",
    description:
      "Streaks, weekly goals and a heatmap of every day you showed up. Spot patterns, catch slumps and watch your discipline compound.",
    accent: "#fbbf24",
    visualType: "progress",
  },
];

const activeIndex = ref(0);
let observer = null;

onMounted(() => {
  const blocks = document.querySelectorAll("[data-feature-block]");
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          activeIndex.value = Number(entry.target.dataset.featureIndex);
        }
      });
    },
    { threshold: 0.55, rootMargin: "-20% 0px -20% 0px" }
  );
  blocks.forEach((b) => observer.observe(b));
});

onBeforeUnmount(() => {
  if (observer) observer.disconnect();
});
</script>

<template>
  <section class="feature-scroll content-wrap">
    <div class="fs-grid">
      <!-- Sticky visual panel: crossfades between feature visuals -->
      <div class="fs-visual-col">
        <div class="fs-visual-sticky">
          <div
            v-for="(f, i) in features"
            :key="i"
            class="fs-visual"
            :class="{ active: i === activeIndex }"
          >
            <!-- Timer mockup -->
            <div v-if="f.visualType === 'timer'" class="mock mock-timer">
              <div class="mock-timer-ring">
                <div class="mock-timer-inner">
                  <span class="mock-timer-time">25:00</span>
                  <span class="mock-timer-label">Focus</span>
                </div>
              </div>
              <div class="mock-timer-modes">
                <span class="mock-mode active-mode">Pomodoro</span>
                <span class="mock-mode">Short break</span>
                <span class="mock-mode">Long break</span>
              </div>
            </div>

            <!-- Ambient mockup (uses real screenshot) -->
            <div v-else-if="f.visualType === 'ambient'" class="mock mock-ambient">
              <img src="/ambient_card.png" alt="Ambient sounds interface" />
            </div>

            <!-- Progress mockup: mini heatmap -->
            <div v-else class="mock mock-progress">
              <div class="mock-progress-head">
                <span class="mp-title">248 sessions</span>
                <span class="mp-streak">🔥 12 days</span>
              </div>
              <div class="mock-heatmap">
                <span
                  v-for="(c, i) in [
                    0,0,3,0,5,0,0,2,4,0,6,3,0,0,5,7,0,2,0,4,6,0,0,3,5,8,0,2,0,0,4,6,
                    0,2,5,0,0,3,6,0,7,0,0,4,0,2,5,7,0,3,6,0,0,5,8,0,2,0,4,7,0,0,3,
                    3,0,0,6,2,0,5,7,0,0,4,6,0,2,5,0,8,3,0,0,6,0,4,7,0,2,5,0,3,6,8,
                    0,5,0,2,7,4,0,0,6,3,0,5,8,0,2,0,4,7,0,0,3,6,0,5,0,2,8,4,0,0,6,
                    2,0,4,6,0,0,5,3,8,0,2,7,0,4,0,6,0,0,3,5,8,0,2,0,7,4,0,0,6,3,0,
                    0,3,6,0,2,5,8,0,0,4,7,0,2,0,5,6,0,3,8,0,0,2,4,7,0,5,0,0,6,3,8,
                  ]"
                  :key="i"
                  class="mp-cell"
                  :style="{
                    background:
                      c === 0
                        ? 'rgba(255,255,255,0.05)'
                        : [
                            '#fff7ed','#ffedd5','#fed7aa','#fdba74','#fb923c',
                            '#f97316','#ea580c','#c2410c','#9a3412','#7c2d12',
                          ][c - 1],
                  }"
                ></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Scrolling text column -->
      <div class="fs-text-col">
        <div
          v-for="(f, i) in features"
          :key="i"
          class="fs-text-block"
          :data-feature-index="i"
          data-feature-block
          :class="{ active: i === activeIndex }"
        >
          <span class="fs-kicker" :style="{ color: f.accent }">{{ f.kicker }}</span>
          <h3 class="fs-title">{{ f.title }}</h3>
          <p class="fs-desc">{{ f.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.feature-scroll {
  margin-bottom: 72px;
  position: relative;
  z-index: 1;
}

.fs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: start;
}

/* Sticky visual column */
.fs-visual-col {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  align-items: center;
}

.fs-visual-sticky {
  position: relative;
  width: 100%;
  height: 460px;
}

.fs-visual {
  position: absolute;
  inset: 0;
  opacity: 0;
  transform: scale(0.96);
  transition: opacity 0.6s ease, transform 0.6s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fs-visual.active {
  opacity: 1;
  transform: scale(1);
}

/* Shared mockup frame */
.mock {
  width: 100%;
  max-width: 460px;
  background: rgba(18, 18, 30, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
  overflow: hidden;
}

/* Timer mockup */
.mock-timer {
  padding: 48px 40px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 36px;
}

.mock-timer-ring {
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: conic-gradient(#818cf8 0deg 270deg, rgba(255,255,255,0.08) 270deg 360deg);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 36px rgba(99, 102, 241, 0.3);
}

.mock-timer-inner {
  width: 208px;
  height: 208px;
  border-radius: 50%;
  background: #0b0c16;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.mock-timer-time {
  font-size: 48px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.mock-timer-label {
  font-size: 14px;
  color: #94a3b8;
  margin-top: 6px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.mock-timer-modes {
  display: flex;
  gap: 8px;
}

.mock-mode {
  font-size: 12.5px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 8px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.04);
}

.mock-mode.active-mode {
  background: rgba(99, 102, 241, 0.18);
  color: #a5b4fc;
}

/* Ambient mockup */
.mock-ambient {
  padding: 0;
}

.mock-ambient img {
  width: 100%;
  height: auto;
  display: block;
}

/* Progress mockup */
.mock-progress {
  padding: 28px 30px 30px;
}

.mock-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.mp-title {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.mp-streak {
  font-size: 13px;
  font-weight: 600;
  color: #fb923c;
}

.mock-heatmap {
  display: grid;
  grid-template-columns: repeat(31, 1fr);
  gap: 4px;
}

.mp-cell {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 3px;
}

/* Scrolling text column */
.fs-text-col {
  display: flex;
  flex-direction: column;
}

.fs-text-block {
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  opacity: 0.4;
  transition: opacity 0.5s ease;
}

.fs-text-block.active {
  opacity: 1;
}

.fs-kicker {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-bottom: 16px;
}

.fs-title {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #ffffff;
  line-height: 1.25;
  margin: 0 0 18px;
}

.fs-desc {
  font-size: 17px;
  color: #94a3b8;
  line-height: 1.65;
  margin: 0;
  max-width: 440px;
}

/* Responsive */
@media (max-width: 1024px) {
  .fs-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
  .fs-visual-col {
    position: relative;
    height: auto;
    margin-bottom: 0;
  }
  .fs-visual-sticky {
    height: 320px;
  }
  .fs-text-block {
    height: auto;
    padding: 48px 0;
    opacity: 1;
  }
  .fs-title {
    font-size: 26px;
  }
}
</style>
