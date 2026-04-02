<script lang="ts">
  import { theme, toggleTheme } from '$lib/stores/theme';
</script>

<button class="toggle" onclick={toggleTheme} title={$theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}>
  <span class="track" class:dark={$theme === 'dark'}>
    <span class="thumb">
      {$theme === 'light' ? '☀️' : '🌙'}
    </span>
  </span>
</button>

<style>
  .toggle {
    display: flex;
    align-items: center;
    padding: 0;
  }

  .track {
    display: flex;
    align-items: center;
    width: 52px;
    height: 28px;
    border-radius: 14px;
    background: var(--border);
    padding: 2px;
    transition: background 0.25s;
    position: relative;
  }

  .track.dark {
    background: #4A4A52;
  }

  .thumb {
    width: 24px;
    height: 24px;
    border-radius: 12px;
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 3px var(--shadow);
  }

  .track.dark .thumb {
    transform: translateX(24px);
  }
</style>
