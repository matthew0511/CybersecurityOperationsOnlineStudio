'use strict';
// Runs before styles load so every page uses the saved appearance on first paint.
(() => {
  const key = 'studio:theme';
  const valid = value => ['light', 'dark', 'system'].includes(value);
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try { const saved = localStorage.getItem(key); if (valid(saved)) preference = saved; } catch {}
  const apply = () => {
    const resolved = preference === 'system' ? (system.matches ? 'dark' : 'light') : preference;
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
    document.querySelectorAll('[data-appearance-select]').forEach(select => { select.value = preference; });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = resolved === 'dark' ? '#0c1c28' : '#f3f6f8';
    window.dispatchEvent(new CustomEvent('studio:appearance', {detail: {preference, resolved}}));
  };
  const set = value => {
    preference = valid(value) ? value : 'system';
    try { localStorage.setItem(key, preference); } catch {}
    apply();
  };
  window.StudioAppearance = {set, get: () => preference};
  apply();
  system.addEventListener('change', () => { if (preference === 'system') apply(); });
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) {
      preference = valid(event.newValue) ? event.newValue : 'system';
      apply();
    }
  });
  document.addEventListener('DOMContentLoaded', () => {
    const host = document.querySelector('.auth-card') || document.querySelector('.doc-header') || document.querySelector('.invitation-main');
    if (!host) return;
    const label = document.createElement('label');
    label.className = 'appearance-control';
    label.append(document.createTextNode('Appearance'));
    const select = document.createElement('select');
    select.dataset.appearanceSelect = '';
    select.setAttribute('aria-label', 'Appearance');
    for (const [value, text] of [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']]) select.add(new Option(text, value));
    select.value = preference;
    select.addEventListener('change', () => set(select.value));
    label.append(select);
    host.prepend(label);
  });
})();
