// Applies design tokens from a ULI theme to CSS custom properties.
// Backend logic is untouched by theming; only presentation changes.

export function applyTheme(theme: any): void {
  const root = document.documentElement;
  if (!theme?.tokens) return;
  const { color = {}, typography = {}, radius = {}, shadow = {}, border = {}, blur = {}, layout = {} } = theme.tokens;

  const vars: Record<string, string | undefined> = {
    "--color-bg": color.bg,
    "--color-bg-gradient": color.bgGradient,
    "--color-surface": color.surface,
    "--color-surface-solid": color.surfaceSolid,
    "--color-surface-hover": color.surfaceHover,
    "--color-text": color.text,
    "--color-muted": color.muted,
    "--color-accent": color.accent,
    "--color-accent-soft": color.accentSoft,
    "--color-border": color.border,
    "--color-danger": color.danger,
    "--color-success": color.success,
    "--color-warning": color.warning,
    "--font-family": typography.fontFamily,
    "--font-mono": typography.fontFamilyMono,
    "--font-size": typography.fontSizeBase,
    "--font-size-sm": typography.fontSizeSmall,
    "--font-size-heading": typography.fontSizeHeading,
    "--line-height": typography.lineHeight,
    "--border-width": border.width,
    "--radius-sm": radius.sm,
    "--radius-md": radius.md,
    "--radius-lg": radius.lg,
    "--radius-pill": radius.pill,
    "--shadow-sm": shadow.sm,
    "--shadow-md": shadow.md,
    "--shadow-glow": shadow.glow,
    "--blur": blur.glass,
    "--sidebar-width": layout.sidebarWidth,
    "--canvas-grid": layout.canvasGrid,
  };

  for (const [key, value] of Object.entries(vars)) {
    if (value) root.style.setProperty(key, value);
  }
  root.dataset.themeMode = theme.mode ?? "dark";
}
