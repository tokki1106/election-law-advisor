import { writable } from 'svelte/store';
import { browser } from '$app/environment';

function getInitialTheme(): 'light' | 'dark' {
  if (!browser) return 'light';
  const saved = localStorage.getItem('theme');
  if (saved === 'dark' || saved === 'light') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export const theme = writable<'light' | 'dark'>(getInitialTheme());

export function toggleTheme() {
  theme.update(t => {
    const next = t === 'light' ? 'dark' : 'light';
    if (browser) {
      localStorage.setItem('theme', next);
      document.documentElement.setAttribute('data-theme', next);
    }
    return next;
  });
}

export function initTheme() {
  if (!browser) return;
  const t = getInitialTheme();
  document.documentElement.setAttribute('data-theme', t);
  theme.set(t);
}
