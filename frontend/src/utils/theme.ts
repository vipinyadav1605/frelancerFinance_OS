const THEME_KEY = "ffos_theme";

export type Theme = "light" | "dark";

export function getStoredTheme(): Theme {
  return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
}

export function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
}

/** Call once at app startup, before first paint, to avoid a flash of the wrong theme. */
export function initTheme() {
  applyTheme(getStoredTheme());
}
