<script setup>
// Sidebar for the Analyse page: brand mark, primary navigation, quote and profile card.
const navItems = [
  { key: "environment", label: "Study Environment", icon: "dot" },
  { key: "analyse", label: "Analyse", icon: "chart" },
  { key: "settings", label: "Settings", icon: "dot" },
];

const activeItem = "analyse";
</script>

<template>
  <aside class="sidebar">
    <router-link to="/" class="brand">
      <span class="brand-ring">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
          <circle cx="12" cy="12" r="7.5" />
        </svg>
      </span>
      <span class="brand-name">Focus Flow</span>
    </router-link>

    <nav class="nav">
      <button
        v-for="item in navItems"
        :key="item.key"
        type="button"
        class="nav-item"
        :class="{ active: item.key === activeItem }"
      >
        <svg
          v-if="item.icon === 'chart'"
          class="nav-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <line x1="6" y1="20" x2="6" y2="11" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="18" y1="20" x2="18" y2="15" />
        </svg>
        <span v-else class="nav-dot"></span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="quote-box">
        <p class="quote-text">Small steps every day lead to big results.</p>
      </div>

      <div class="profile-card">
        <span class="avatar">M</span>
        <div class="profile-info">
          <span class="profile-name">Manoj</span>
          <button type="button" class="profile-link">View profile</button>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 250px;
  flex-shrink: 0;
  background: #1f1f1f;
  border-right: 1px solid rgba(255, 255, 255, 0.07);
  padding: 24px 18px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  padding: 4px 6px 0;
  margin-bottom: 32px;
}

.brand-ring {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #00ff9d;
  border: 1px solid rgba(0, 255, 157, 0.35);
  background: rgba(0, 255, 157, 0.08);
}

.brand-ring svg {
  width: 18px;
  height: 18px;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #ffffff;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 14px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: #a0a0a0;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #e5e5e5;
}

.nav-item.active {
  background: rgba(0, 255, 157, 0.08);
  border-color: rgba(0, 255, 157, 0.45);
  color: #00ff9d;
}

.nav-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  margin: 0 6px;
  flex-shrink: 0;
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
}

.sidebar-footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.quote-box {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 14px 16px;
}

.quote-text {
  margin: 0;
  font-size: 12.5px;
  font-style: italic;
  line-height: 1.5;
  color: #a0a0a0;
}

.profile-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 12px 14px;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(0, 255, 157, 0.14);
  border: 1px solid rgba(0, 255, 157, 0.3);
  color: #00ff9d;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.profile-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.profile-name {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.profile-link {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  font-size: 12px;
  color: #a0a0a0;
  text-align: left;
  cursor: pointer;
  transition: color 0.2s ease;
}

.profile-link:hover {
  color: #00ff9d;
}

@media (max-width: 1024px) {
  .sidebar {
    width: 100%;
    height: auto;
    position: static;
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    padding: 16px 20px;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  }

  .brand {
    margin-bottom: 0;
    padding: 0;
  }

  .nav {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
  }

  .nav-item {
    width: auto;
  }

  .sidebar-footer {
    display: none;
  }
}
</style>
