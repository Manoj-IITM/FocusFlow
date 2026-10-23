<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import {
  accentColor,
  accentPresets,
  setAccentColor,
  setThemeMode,
  themeMode,
} from "../theme.js";

const route = useRoute();
const isLightMode = computed(() => themeMode.value === "light");
const isAccentPickerOpen = ref(false);
</script>

<template>
  <div
    class="site-theme-switcher"
    :class="{ 'site-theme-switcher--dashboard': route.name === 'dashboard' }"
    role="group"
    aria-label="Color theme"
  >
    <button
      type="button"
      :class="{ active: !isLightMode }"
      :aria-pressed="!isLightMode"
      aria-label="Switch to dark mode"
      @click="setThemeMode('dark')"
    >
      <i class="ti ti-moon" aria-hidden="true"></i>
      <span>Dark</span>
    </button>
    <button
      type="button"
      :class="{ active: isLightMode }"
      :aria-pressed="isLightMode"
      aria-label="Switch to light mode"
      @click="setThemeMode('light')"
    >
      <i class="ti ti-sun" aria-hidden="true"></i>
      <span>Light</span>
    </button>
    <button
      type="button"
      class="accent-picker-toggle"
      :aria-expanded="isAccentPickerOpen"
      aria-label="Choose accent color"
      @click="isAccentPickerOpen = !isAccentPickerOpen"
    >
      <i class="ti ti-palette" aria-hidden="true"></i>
    </button>
    <section
      v-if="isAccentPickerOpen"
      class="accent-picker-panel"
      aria-label="Website accent color"
    >
      <div class="accent-picker-heading">Accent color</div>
      <div class="accent-picker-presets" role="group" aria-label="Preset accent colors">
        <button
          v-for="preset in accentPresets"
          :key="preset.color"
          type="button"
          class="accent-picker-swatch"
          :class="{ selected: accentColor.toLowerCase() === preset.color }"
          :style="{ '--swatch-color': preset.color }"
          :aria-label="`${preset.name} accent`"
          :aria-pressed="accentColor.toLowerCase() === preset.color"
          :title="preset.name"
          @click="setAccentColor(preset.color)"
        >
          <i v-if="accentColor.toLowerCase() === preset.color" class="ti ti-check" aria-hidden="true"></i>
        </button>
      </div>
      <label class="accent-picker-custom">
        <span>Custom color</span>
        <input
          type="color"
          :value="accentColor"
          aria-label="Choose a custom accent color"
          @input="setAccentColor($event.target.value)"
        />
      </label>
    </section>
  </div>
</template>

<style>
.site-theme-switcher {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 980;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 4px;
  border: 1px solid var(--mono-border);
  border-radius: 8px;
  background: var(--mono-panel);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}

.site-theme-switcher--dashboard {
  position: relative;
  right: auto;
  bottom: auto;
  z-index: 980;
  box-shadow: none;
}

.site-theme-switcher button {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 11px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--mono-muted);
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition: color 150ms ease, background-color 150ms ease, border-color 150ms ease, transform 100ms ease;
}

.site-theme-switcher .accent-picker-toggle {
  width: 34px;
  padding: 0;
}

.accent-picker-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  width: 228px;
  padding: 14px;
  border: 1px solid var(--mono-border);
  border-radius: 8px;
  background: var(--mono-panel);
  color: var(--mono-text);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.24);
}

.site-theme-switcher--dashboard .accent-picker-panel {
  top: calc(100% + 10px);
  bottom: auto;
  z-index: 981;
}

.accent-picker-heading {
  margin-bottom: 11px;
  color: var(--mono-text);
  font-size: 12px;
  font-weight: 700;
}

.accent-picker-presets {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.site-theme-switcher .accent-picker-swatch {
  display: grid;
  width: 26px;
  height: 26px;
  min-height: 26px;
  place-items: center;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 5px;
  background: var(--swatch-color);
  color: #ffffff;
}

.site-theme-switcher .accent-picker-swatch.selected {
  border-color: var(--mono-text);
  box-shadow: 0 0 0 2px var(--swatch-color);
}

.accent-picker-swatch i {
  font-size: 14px;
}

.accent-picker-custom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--mono-border);
  color: var(--mono-muted);
  font-size: 12px;
  font-weight: 600;
}

.accent-picker-custom input {
  width: 36px;
  height: 28px;
  padding: 2px;
  border: 1px solid var(--mono-border);
  border-radius: 5px;
  background: var(--mono-surface);
  cursor: pointer;
}

.site-theme-switcher button i {
  color: inherit !important;
  font-size: 14px;
}

.site-theme-switcher button.active {
  border-color: var(--brand-accent-border);
  background: var(--brand-accent-soft);
  color: var(--brand-accent-strong);
}

html[data-theme="dark"] .site-theme-switcher button.active i {
  color: #ffffff !important;
}

.site-theme-switcher button:hover:not(.active) {
  background: var(--mono-hover);
  color: var(--mono-text);
}

.site-theme-switcher button:focus-visible {
  outline: 2px solid var(--brand-accent);
  outline-offset: 2px;
}

@media (max-width: 560px) {
  .site-theme-switcher {
    right: 12px;
    bottom: 12px;
  }

  .site-theme-switcher--dashboard {
    right: calc(12px + 160px + 8px);
    bottom: 12px;
  }

  .site-theme-switcher button {
    min-height: 30px;
    padding-inline: 9px;
  }

  .site-theme-switcher .accent-picker-toggle {
    width: 30px;
    padding: 0;
  }
}

@media (max-width: 420px) {
  .site-theme-switcher--dashboard {
    right: 12px;
    bottom: 64px;
  }
}
</style>
