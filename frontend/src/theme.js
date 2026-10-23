import { ref } from "vue";

const themeStorageKey = "focusflow_theme";
const accentStorageKey = "focusflow_accent";
const supportedThemes = new Set(["dark", "light"]);
const accentPattern = /^#[\da-f]{6}$/i;
export const defaultAccentColor = "#14b8a6";
export const accentPresets = [
  { name: "Teal", color: defaultAccentColor },
  { name: "Blue", color: "#3b82f6" },
  { name: "Violet", color: "#8b5cf6" },
  { name: "Rose", color: "#f43f5e" },
  { name: "Amber", color: "#f59e0b" },
  { name: "Green", color: "#22c55e" },
];

export const themeMode = ref("dark");
export const accentColor = ref(defaultAccentColor);

const applyAccentColor = (color) => {
  accentColor.value = color;
  const root = document.documentElement;
  const channels = color.slice(1).match(/.{2}/g).map((channel) => parseInt(channel, 16));
  const luminance = channels
    .map((channel) => {
      const normalized = channel / 255;
      return normalized <= 0.04045
        ? normalized / 12.92
        : ((normalized + 0.055) / 1.055) ** 2.4;
    })
    .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
  const darkMode = themeMode.value === "dark";

  root.style.setProperty("--brand-accent", color);
  root.style.setProperty(
    "--brand-accent-strong",
    darkMode
      ? `color-mix(in srgb, ${color} 62%, white)`
      : `color-mix(in srgb, ${color} 72%, #0f172a)`
  );
  root.style.setProperty(
    "--brand-accent-hover",
    darkMode
      ? `color-mix(in srgb, ${color} 78%, white)`
      : `color-mix(in srgb, ${color} 84%, white)`
  );
  root.style.setProperty("--brand-accent-soft", `color-mix(in srgb, ${color} 14%, transparent)`);
  root.style.setProperty("--brand-accent-border", `color-mix(in srgb, ${color} 42%, transparent)`);
  root.style.setProperty(
    "--brand-accent-ink",
    luminance > 0.42 ? "#0f172a" : "#ffffff"
  );
  root.style.setProperty(
    "--brand-accent-glow",
    `color-mix(in srgb, ${color} 26%, transparent)`
  );
};

const applyTheme = (mode) => {
  themeMode.value = mode;
  document.documentElement.dataset.theme = mode;
  applyAccentColor(accentColor.value);
};

export const initializeTheme = () => {
  let savedTheme = null;
  let savedAccent = null;
  try {
    savedTheme = localStorage.getItem(themeStorageKey);
    savedAccent = localStorage.getItem(accentStorageKey);
  } catch (error) {
    console.error("Unable to read saved appearance preferences:", error);
  }

  accentColor.value = accentPattern.test(savedAccent || "")
    ? savedAccent
    : defaultAccentColor;
  applyTheme(supportedThemes.has(savedTheme) ? savedTheme : "dark");
};

export const setThemeMode = (mode) => {
  if (!supportedThemes.has(mode)) {
    throw new Error(`Unsupported theme: ${mode}`);
  }

  applyTheme(mode);
  try {
    localStorage.setItem(themeStorageKey, mode);
  } catch (error) {
    console.error("Unable to save the theme preference:", error);
  }
};

export const setAccentColor = (color) => {
  if (!accentPattern.test(color)) {
    throw new Error(`Unsupported accent color: ${color}`);
  }

  applyAccentColor(color);
  try {
    localStorage.setItem(accentStorageKey, color);
  } catch (error) {
    console.error("Unable to save the accent color preference:", error);
  }
};
