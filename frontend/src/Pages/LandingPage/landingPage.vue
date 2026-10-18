<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

// Ambient Sound Interactive State
const isAmbientOn = ref(true);
const isPlaying = ref(true);
const activePreset = ref("deep-focus");
const soundLevels = ref({
  rain: 70,
  forest: 50,
  wind: 30,
  lofi: 40,
});

// Feature Cards Data
const features = [
  {
    iconType: "clock",
    title: "Focus timer",
    description: "Pomodoro, short and long breaks, or fully custom sessions.",
    badgeBg: "rgba(99, 102, 241, 0.18)",
    badgeColor: "#a5b4fc",
  },
  {
    iconType: "headphones",
    title: "Study environment",
    description: "Ambient sounds and lo-fi playlists to help you settle in.",
    badgeBg: "rgba(20, 184, 166, 0.18)",
    badgeColor: "#5eead4",
  },
  {
    iconType: "donut",
    title: "Progress tracking",
    description: "Streaks, weekly goals, and a breakdown of where your time goes.",
    badgeBg: "rgba(245, 158, 11, 0.18)",
    badgeColor: "#fcd34d",
  },
];

// Heatmap Orange Color Scale (0: faint background cell, 1: lightest peach -> 10: darkest deep burnt orange)
const heatmapColors = [
  "rgba(255, 255, 255, 0.04)", // 0: background empty cell
  "#fff7ed", // 1: D (Lightest soft cream-orange)
  "#ffedd5", // 2: I (Pale peach-orange)
  "#fed7aa", // 3: S (Light warm peach)
  "#fdba74", // 4: C (Soft sunburst orange)
  "#fb923c", // 5: I (Bright orange)
  "#f97316", // 6: P (Vivid electric orange)
  "#ea580c", // 7: L (Intense fire orange)
  "#c2410c", // 8: I (Deep reddish rust)
  "#9a3412", // 9: N (Dark crimson orange)
  "#7c2d12", // 10: E (Darkest deep burnt amber)
];

// Weekday row labels
const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// Month column labels (spaced across 33 columns for DISCIPLINE)
const months = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

// Heatmap Matrix spelling out "DISCIPLINE" in the middle 3 rows (Rows 2, 3, 4)
const heatmapMatrix = ref([
  // Mon (Row 0) - Background
  [0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0],
  // Tue (Row 1) - Background
  [0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0],
  // Wed (Row 2) - Top of 3-row DISCIPLINE: D(1)  I(2)  S(3)  C(4)  I(5)  P(6)  L(7)  I(8)  N(9)  E(10)
  [1, 1, 0,  0,  2,  0,  3, 3, 3,  0,  4, 4, 4,  0,  5,  0,  6, 6, 6,  0,  7, 0, 0,  0,  8,  0,  9, 0, 9,  0,  10, 10, 10],
  // Thu (Row 3) - Middle of 3-row DISCIPLINE
  [1, 0, 1,  0,  2,  0,  0, 3, 0,  0,  4, 0, 0,  0,  5,  0,  6, 6, 6,  0,  7, 0, 0,  0,  8,  0,  9, 9, 9,  0,  10, 10, 0],
  // Fri (Row 4) - Bottom of 3-row DISCIPLINE
  [1, 1, 0,  0,  2,  0,  3, 3, 3,  0,  4, 4, 4,  0,  5,  0,  6, 0, 0,  0,  7, 7, 7,  0,  8,  0,  9, 0, 9,  0,  10, 10, 10],
  // Sat (Row 5) - Background
  [0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0],
  // Sun (Row 6) - Background
  [0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0,  0,  0,  0,  0, 0, 0,  0,  0, 0, 0],
]);

// Handlers
function handleLogin() {
  router.push("/login");
}

function handleSignup() {
  router.push("/signup");
}
</script>

<template>
  <div class="landing-page">
    <!-- Navbar -->
    <header class="navbar">
      <div class="content-wrap navbar-inner">
        <div class="brand">
          <div class="brand-icon-wrap">
            <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 12c-2-2.5-4-4-6-4A4 4 0 1 0 2 12a4 4 0 0 0 4 4c2 0 4-1.5 6-4zm0 0c2 2.5 4 4 6 4a4 4 0 1 0 4-4 4 4 0 0 0-4-4c-2 0-4 1.5-6 4z"/>
            </svg>
          </div>
          <span class="brand-name">FocusFlow</span>
        </div>
        <div class="navbar-actions">
          <button class="btn btn-ghost" @click="handleLogin">Log in</button>
          <button class="btn btn-primary" @click="handleSignup">Sign up</button>
        </div>
      </div>
    </header>

    <!-- Main Content Container -->
    <main class="main-content">
      <!-- Background Ambient Glow -->
      <div class="ambient-glow"></div>

      <!-- Hero Section -->
      <section class="hero content-wrap">
        <div class="hero-badge">
          <svg class="badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2l2.4 5.4 5.6 1.1-4 4.3 1.1 5.7L12 15.6 7 18.5l1.1-5.7-4-4.3 5.6-1.1L12 2z"/>
          </svg>
          <span>Built for deep focus</span>
        </div>

        <h1 class="hero-title">
          Build your <span class="gradient-text">perfect</span> study session
        </h1>

        <p class="hero-subtitle">
          Timers, ambient sound, and progress tracking, all in one calm
          workspace designed to help you focus.
        </p>

        <div class="hero-actions">
          <button class="btn btn-primary btn-lg" @click="handleSignup">
            Get started free
            <svg class="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
          <button class="btn btn-secondary btn-lg">
            <div class="play-icon-wrap">
              <svg class="play-icon" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            </div>
            See how it works
          </button>
        </div>
      </section>

      <!-- Feature Cards Grid (3 Columns) -->
      <section class="feature-grid content-wrap">
        <div v-for="feature in features" :key="feature.title" class="feature-card">
          <div class="feature-icon-box" :style="{ backgroundColor: feature.badgeBg, color: feature.badgeColor }">
            <!-- Clock Icon -->
            <svg v-if="feature.iconType === 'clock'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            <!-- Headphones Icon -->
            <svg v-else-if="feature.iconType === 'headphones'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 18v-6a9 9 0 0 1 18 0v6"/>
              <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>
            </svg>
            <!-- Donut/Progress Icon -->
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>
              <path d="M22 12A10 10 0 0 0 12 2v10z"/>
            </svg>
          </div>
          <div class="feature-text">
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-description">{{ feature.description }}</p>
          </div>
        </div>
      </section>

      <!-- Split Section 1: Heatmap + Text -->
      <section class="split-section content-wrap">
        <!-- Heatmap Card -->
        <div class="heatmap-card">
          <div class="heatmap-header">
            <span class="heatmap-title">248 sessions this year</span>
            <div class="heatmap-legend">
              <span class="legend-text">Less</span>
              <div class="legend-swatches">
                <span
                  v-for="(color, i) in heatmapColors.slice(1)"
                  :key="i"
                  class="legend-swatch"
                  :style="{ background: color }"
                ></span>
              </div>
              <span class="legend-text">More</span>
            </div>
          </div>

          <!-- Grid + Labels Container -->
          <div class="heatmap-body">
            <!-- Day Row Labels -->
            <div class="day-labels">
              <span v-for="day in weekDays" :key="day" class="day-label">{{ day }}</span>
            </div>

            <div class="grid-and-months">
              <!-- Heatmap Grid (7 rows, 32 cols for wide stretchy layout) -->
              <div class="heatmap-grid">
                <template v-for="(row, rIndex) in heatmapMatrix" :key="rIndex">
                  <span
                    v-for="(val, cIndex) in row"
                    :key="`${rIndex}-${cIndex}`"
                    class="heatmap-cell"
                    :style="{ background: heatmapColors[val] }"
                  ></span>
                </template>
              </div>

              <!-- Month Column Labels -->
              <div class="month-labels">
                <span v-for="month in months" :key="month" class="month-label">{{ month }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Text Column -->
        <div class="split-text">
          <h2 class="split-title">See your consistency, not just your minutes</h2>
          <p class="split-description">
            A GitHub-style history of every day you showed up to focus. Darker
            squares mean deeper sessions, so you can spot patterns, catch slumps
            early, and see the full picture of how you actually study over weeks
            and months.
          </p>
        </div>
      </section>

      <!-- Split Section 2: Text + Streak Ring Card -->
      <section class="split-section content-wrap">
        <!-- Text Column -->
        <div class="split-text">
          <h2 class="split-title">Streaks keep you coming back</h2>
          <p class="split-description">
            Every focus session adds to your streak. Miss a day and it resets,
            so showing up daily is what compounds your progress.
          </p>
        </div>

        <!-- Streak Card -->
        <div class="streak-card">
          <div class="streak-card-inner">
            <!-- Left Side: Circular Ring Gauge -->
            <div class="streak-ring-col">
              <div class="streak-ring-div">
                <div class="streak-ring-inner">
                  <span class="ring-flame">🔥</span>
                  <span class="ring-number">12</span>
                  <span class="ring-label">days</span>
                </div>
              </div>
            </div>

            <!-- Vertical Divider -->
            <div class="streak-divider"></div>

            <!-- Right Side: Milestone Progress Timeline -->
            <div class="streak-milestones-col">
              <!-- 1 Day: Beginner -->
              <div class="milestone-item">
                <div class="milestone-badge badge-green">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M7 20h10M12 20v-8M12 12A6 6 0 0 1 6 6c3 0 6 2 6 6M12 12a6 6 0 0 0 6-6c-3 0-6 2-6 6"/>
                  </svg>
                </div>
                <div class="milestone-text">
                  <span class="m-title">1 day</span>
                  <span class="m-subtitle text-gray">Beginner</span>
                </div>
              </div>

              <div class="milestone-connector dot-green"></div>

              <!-- 20 Days: Focus Warrior -->
              <div class="milestone-item">
                <div class="milestone-badge badge-blue">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                </div>
                <div class="milestone-text">
                  <span class="m-title">20 days</span>
                  <span class="m-subtitle text-gray">Focus Warrior</span>
                </div>
              </div>

              <div class="milestone-connector dot-blue"></div>

              <!-- 80 Days: Knowledge Beast -->
              <div class="milestone-item">
                <div class="milestone-badge badge-purple">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
                    <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>
                  </svg>
                </div>
                <div class="milestone-text">
                  <span class="m-title">80 days</span>
                  <span class="m-subtitle text-gray">Knowledge Beast</span>
                </div>
              </div>

              <div class="milestone-connector dot-purple"></div>

              <!-- 180 Days: Kitaab Paglu -->
              <div class="milestone-item">
                <div class="milestone-badge badge-orange">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="9" cy="12" r="1"/>
                    <circle cx="15" cy="12" r="1"/>
                    <path d="M8 20v2h8v-2M12 2a7 7 0 0 0-7 7c0 3 1.6 5.5 3 7.5h8c1.4-2 3-4.5 3-7.5a7 7 0 0 0-7-7z"/>
                  </svg>
                </div>
                <div class="milestone-text">
                  <span class="m-title">180 days</span>
                  <span class="m-subtitle text-orange">Kitaab Paglu</span>
                </div>
              </div>

              <div class="milestone-connector dot-yellow"></div>

              <!-- 365+ Days: Padhaku Maharaj -->
              <div class="milestone-item">
                <div class="milestone-badge badge-yellow">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 4l3 12h14l3-12-6 7-4-7-4 7-6-7zM5 20h14v2H5z"/>
                  </svg>
                </div>
                <div class="milestone-text">
                  <span class="m-title">365+ days</span>
                  <span class="m-subtitle text-yellow">Padhaku Maharaj</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Split Section 3: Ambient Sound Feature Section (After Streaks) -->
      <section class="split-section content-wrap ambient-section">
        <!-- Left Side: Extracted Ambient Sounds Card Image -->
        <div class="ambient-card-wrap">
          <img src="/ambient_card.png" alt="Ambient Sounds UI" class="ambient-card-img" />
        </div>

        <!-- Right Side: Heading & Feature Highlights -->
        <div class="ambient-text-col">
          <div class="ambient-headphone-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 18v-6a9 9 0 0 1 18 0v6"/>
              <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>
            </svg>
          </div>

          <h2 class="ambient-heading">
            The right sounds.<br />
            The right mindset.
          </h2>

          <div class="ambient-features-list">
            <!-- Feature 1 -->
            <div class="ambient-feat-item">
              <div class="ambient-feat-header">
                <svg class="ambient-feat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M2 10v4M6 6v12M10 3v18M14 8v8M18 5v14M22 10v4"/>
                </svg>
                <span class="ambient-feat-title">Curated sounds</span>
              </div>
              <p class="ambient-feat-desc">High quality ambient tracks</p>
            </div>

            <!-- Feature 2 -->
            <div class="ambient-feat-item">
              <div class="ambient-feat-header">
                <svg class="ambient-feat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>
                  <line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>
                  <line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>
                  <line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>
                </svg>
                <span class="ambient-feat-title">Mix & match</span>
              </div>
              <p class="ambient-feat-desc">Create your perfect soundscape</p>
            </div>

            <!-- Feature 3 -->
            <div class="ambient-feat-item">
              <div class="ambient-feat-header">
                <svg class="ambient-feat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
                <span class="ambient-feat-title">Focus timer sync</span>
              </div>
              <p class="ambient-feat-desc">Sounds fade with your sessions</p>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <div class="content-wrap footer-inner">
        <span class="copyright">© 2025 FocusFlow. All rights reserved.</span>
        <nav class="footer-nav">
          <a href="#" class="footer-link">Privacy</a>
          <a href="#" class="footer-link">Terms</a>
          <a href="#" class="footer-link">Help</a>
          <a href="#" class="footer-link">Contact</a>
        </nav>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* Main Layout & Dark Theme Setup */
.landing-page {
  background: #080811;
  color: #f1f5f9;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow-x: hidden;
}

/* Expanded container width to stretch horizontally across wide screens */
.content-wrap {
  max-width: 1440px;
  width: 92%;
  margin: 0 auto;
  padding-left: 32px;
  padding-right: 32px;
  box-sizing: border-box;
}

/* Navbar Styling */
.navbar {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  z-index: 10;
  background: rgba(8, 8, 17, 0.85);
  backdrop-filter: blur(12px);
}

.navbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 76px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.45);
}

.brand-icon {
  width: 22px;
  height: 22px;
  color: #ffffff;
}

.brand-name {
  font-weight: 700;
  font-size: 20px;
  letter-spacing: -0.02em;
  color: #ffffff;
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* Buttons */
.btn {
  font-size: 14px;
  font-weight: 500;
  padding: 9px 20px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.btn-primary {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.38);
}

.btn-primary:hover {
  background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
  box-shadow: 0 6px 24px rgba(79, 70, 229, 0.55);
  transform: translateY(-1px);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-lg {
  padding: 14px 28px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
}

.btn-arrow {
  width: 18px;
  height: 18px;
}

.play-icon-wrap {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.play-icon {
  width: 10px;
  height: 10px;
  margin-left: 1px;
}

/* Ambient Background Glow */
.main-content {
  position: relative;
  flex: 1;
  padding-bottom: 80px;
}

.ambient-glow {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 450px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, rgba(168, 85, 247, 0.09) 45%, transparent 70%);
  filter: blur(70px);
  pointer-events: none;
  z-index: 0;
}

/* Hero Section */
.hero {
  text-align: center;
  padding-top: 72px;
  padding-bottom: 64px;
  position: relative;
  z-index: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(165, 180, 252, 0.25);
  color: #c7d2fe;
  font-size: 14px;
  font-weight: 500;
  padding: 7px 18px;
  border-radius: 24px;
  margin-bottom: 28px;
}

.badge-icon {
  width: 15px;
  height: 15px;
  color: #a5b4fc;
}

.hero-title {
  font-size: 54px;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin: 0 0 18px;
  line-height: 1.15;
  color: #ffffff;
}

.gradient-text {
  background: linear-gradient(135deg, #a78bfa 0%, #818cf8 60%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  color: #94a3b8;
  font-size: 18px;
  margin: 0 auto 36px;
  max-width: 620px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 18px;
  justify-content: center;
}

/* Feature Cards Grid (3 Columns, Spacious) */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 28px;
  margin-bottom: 72px;
  position: relative;
  z-index: 1;
}

.feature-card {
  background: rgba(18, 18, 30, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 28px 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.25s ease;
}

.feature-card:hover {
  border-color: rgba(99, 102, 241, 0.35);
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
}

.feature-icon-box {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feature-icon-box svg {
  width: 24px;
  height: 24px;
}

.feature-title {
  font-size: 17px;
  font-weight: 600;
  margin: 0 0 4px;
  color: #ffffff;
}

.feature-description {
  color: #94a3b8;
  font-size: 13.5px;
  margin: 0;
  line-height: 1.5;
}

/* Split Section Layout (Wide & Stretchy) */
.split-section {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 60px;
  align-items: center;
  margin-bottom: 72px;
  position: relative;
  z-index: 1;
}

.split-title {
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0 0 14px;
  color: #ffffff;
  line-height: 1.3;
}

.split-description {
  color: #94a3b8;
  font-size: 16px;
  margin: 0;
  line-height: 1.65;
}

/* Heatmap Card (Stretches across full card width) */
.heatmap-card {
  background: rgba(18, 18, 30, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  padding: 28px 32px;
}

.heatmap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}

.heatmap-title {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legend-text {
  font-size: 12px;
  color: #64748b;
}

.legend-swatches {
  display: flex;
  gap: 5px;
}

.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.heatmap-body {
  display: flex;
  gap: 16px;
}

.day-labels {
  display: grid;
  grid-template-rows: repeat(7, 26px);
  gap: 7px;
  font-size: 11px;
  color: #64748b;
  align-items: center;
}

.grid-and-months {
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}

.heatmap-grid {
  display: grid;
  grid-template-columns: repeat(33, 1fr);
  grid-template-rows: repeat(7, 22px);
  gap: 5px;
  width: 100%;
}

.heatmap-cell {
  width: 100%;
  height: 22px;
  border-radius: 3px;
  transition: transform 0.15s ease;
}

.heatmap-cell:hover {
  transform: scale(1.2);
}

.month-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  padding-left: 2px;
  padding-right: 2px;
}

/* Streak Card Layout */
.streak-card {
  background: rgba(14, 15, 29, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 32px 36px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
}

.streak-card-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Left Side Ring Div */
.streak-ring-col {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
}

.streak-ring-div {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: conic-gradient(#6366f1 0deg 250deg, rgba(255, 255, 255, 0.08) 250deg 360deg);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 24px rgba(99, 102, 241, 0.25);
}

.streak-ring-inner {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: #0b0c16;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring-flame {
  font-size: 20px;
  margin-bottom: 2px;
}

.ring-number {
  font-size: 36px;
  font-weight: 800;
  color: #ffffff;
  line-height: 1;
}

.ring-label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
}

/* Vertical Divider */
.streak-divider {
  width: 1px;
  height: 310px;
  background: rgba(255, 255, 255, 0.08);
  margin: 0 28px;
}

/* Right Side Milestones Track */
.streak-milestones-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.milestone-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.milestone-badge {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.milestone-badge svg {
  width: 20px;
  height: 20px;
}

.badge-green {
  border: 1.5px solid #84cc16;
  background: rgba(132, 204, 22, 0.12);
  color: #84cc16;
}

.badge-blue {
  border: 1.5px solid #3b82f6;
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
}

.badge-purple {
  border: 1.5px solid #a855f7;
  background: rgba(168, 85, 247, 0.12);
  color: #c084fc;
}

.badge-orange {
  border: 1.5px solid #f97316;
  background: rgba(249, 115, 22, 0.12);
  color: #fb923c;
}

.badge-yellow {
  border: 1.5px solid #eab308;
  background: rgba(234, 179, 8, 0.12);
  color: #fde047;
}

.milestone-text {
  display: flex;
  flex-direction: column;
}

.m-title {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
}

.m-subtitle {
  font-size: 13px;
  margin-top: 1px;
}

.text-gray {
  color: #94a3b8;
}

.text-orange {
  color: #f97316;
  font-weight: 600;
}

.text-yellow {
  color: #eab308;
  font-weight: 600;
}

.milestone-connector {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  margin-left: 18.5px;
  margin-top: 4px;
  margin-bottom: 4px;
}

.dot-green { background: #84cc16; box-shadow: 0 0 6px rgba(132, 204, 22, 0.6); }
.dot-blue { background: #3b82f6; box-shadow: 0 0 6px rgba(59, 130, 246, 0.6); }
.dot-purple { background: #a855f7; box-shadow: 0 0 6px rgba(168, 85, 247, 0.6); }
.dot-yellow { background: #eab308; box-shadow: 0 0 6px rgba(234, 179, 8, 0.6); }

/* Ambient Sound Section Styling */
.ambient-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 52px;
  align-items: center;
}

.ambient-card-wrap {
  width: 100%;
  display: flex;
  justify-content: center;
}

.ambient-card-img {
  width: 100%;
  max-width: 480px;
  height: auto;
  border-radius: 18px;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: block;
}

.ambient-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.ambient-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ambient-header-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ambient-header-icon svg {
  width: 22px;
  height: 22px;
}

.ambient-card-title {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.ambient-card-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin: 2px 0 0;
}

/* Toggle Pill */
.ambient-toggle-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.toggle-pill {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px;
  box-sizing: border-box;
  transition: background 0.25s ease;
}

.toggle-pill.toggle-active {
  background: #6366f1;
}

.toggle-circle {
  display: block;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  transition: transform 0.25s ease;
}

.toggle-pill.toggle-active .toggle-circle {
  transform: translateX(20px);
}

.toggle-label {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
}

/* Now Playing Banner Box */
.now-playing-box {
  background: rgba(8, 8, 17, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 24px;
}

.track-cover-wrap {
  width: 64px;
  height: 64px;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
}

.track-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.track-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.track-title {
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.track-genre {
  font-size: 12.5px;
  color: #a5b4fc;
  margin-top: 2px;
}

.track-timeline {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  font-size: 11px;
  color: #64748b;
}

.track-slider-track {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  position: relative;
}

.track-slider-fill {
  height: 100%;
  background: #818cf8;
  border-radius: 2px;
}

.track-slider-knob {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 0 6px rgba(129, 140, 248, 0.8);
}

.track-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ctrl-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.ctrl-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
}

.play-pause-btn {
  width: 40px;
  height: 40px;
  background: #6366f1;
  color: #ffffff;
}

.play-pause-btn:hover {
  background: #4f46e5;
  color: #ffffff;
  transform: scale(1.05);
}

.ctrl-btn svg {
  width: 16px;
  height: 16px;
}

.play-pause-btn svg {
  width: 18px;
  height: 18px;
}

.wave-btn {
  background: rgba(99, 102, 241, 0.12);
  color: #818cf8;
}

/* Mix your environment */
.section-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 14px;
}

.sound-slider-row {
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(8, 8, 17, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 10px 16px;
  margin-bottom: 10px;
}

.sound-icon-box {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sound-icon-box svg {
  width: 20px;
  height: 20px;
}

.icon-rain { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.icon-forest { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.icon-wind { background: rgba(20, 184, 166, 0.15); color: #2dd4bf; }
.icon-lofi { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

.sound-meta {
  width: 100px;
  display: flex;
  flex-direction: column;
}

.sound-name {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.sound-tag {
  font-size: 11px;
  color: #64748b;
}

.sound-slider-wrap {
  flex: 1;
  display: flex;
  align-items: center;
}

.sound-range-input {
  width: 100%;
  accent-color: #818cf8;
  cursor: pointer;
}

.sound-value {
  font-size: 12.5px;
  color: #94a3b8;
  width: 40px;
  text-align: right;
}

.sound-mute-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  width: 34px;
  height: 34px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sound-mute-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.sound-mute-btn svg {
  width: 16px;
  height: 16px;
}

/* Presets */
.presets-section {
  margin-top: 20px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.preset-pill {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 10px 14px;
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.preset-pill:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.preset-pill.active {
  background: rgba(99, 102, 241, 0.18);
  border-color: #6366f1;
  color: #a5b4fc;
}

.preset-icon {
  width: 16px;
  height: 16px;
}

.text-emerald { color: #34d399; }
.text-amber { color: #fbbf24; }

/* Ambient Right Side Column */
.ambient-text-col {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.ambient-headphone-badge {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(165, 180, 252, 0.2);
  color: #a5b4fc;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
}

.ambient-headphone-badge svg {
  width: 28px;
  height: 28px;
}

.ambient-heading {
  font-size: 38px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #ffffff;
  line-height: 1.15;
  margin: 0 0 36px;
}

.ambient-features-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  width: 100%;
}

.ambient-feat-item {
  display: flex;
  flex-direction: column;
}

.ambient-feat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.ambient-feat-icon {
  width: 18px;
  height: 18px;
  color: #a5b4fc;
}

.ambient-feat-title {
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
}

.ambient-feat-desc {
  font-size: 12.5px;
  color: #94a3b8;
  margin: 0;
  line-height: 1.4;
}

/* Footer */
.footer {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(8, 8, 17, 0.9);
  padding: 28px 0;
  margin-top: auto;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: #64748b;
}

.footer-nav {
  display: flex;
  gap: 28px;
}

.footer-link {
  color: #64748b;
  text-decoration: none;
  transition: color 0.2s ease;
}

.footer-link:hover {
  color: #94a3b8;
}

/* Responsive Adjustments */
@media (max-width: 1024px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }
  .split-section {
    grid-template-columns: 1fr;
  }
  .hero-title {
    font-size: 38px;
  }
}
</style>
tyle>
