<script lang="ts">
  import type { ChatTurn } from '$lib/stores/chat';

  let { turns, activeTurnIndex, onSelect }: {
    turns: ChatTurn[];
    activeTurnIndex: number;
    onSelect: (index: number) => void;
  } = $props();
</script>

{#if turns.length > 1}
  <div class="navigator">
    {#each turns as turn, i}
      <button
        class="nav-dot"
        class:active={activeTurnIndex === i}
        onclick={() => onSelect(i)}
        title={turn.question}
      >
        <span class="dot"></span>
        <span class="nav-label">{turn.question.length > 20 ? turn.question.slice(0, 20) + '...' : turn.question}</span>
      </button>
    {/each}
  </div>
{/if}

<style>
  .navigator {
    position: fixed;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    flex-direction: column;
    gap: 4px;
    z-index: 50;
  }

  .nav-dot {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px 4px 4px;
    border-radius: 12px;
    flex-direction: row-reverse;
    transition: background 0.15s;
  }

  .nav-dot:hover {
    background: var(--hover);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--border);
    flex-shrink: 0;
    transition: all 0.2s;
  }

  .nav-dot.active .dot {
    background: var(--accent);
    width: 10px;
    height: 10px;
  }

  .nav-label {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
    max-width: 0;
    overflow: hidden;
    opacity: 0;
    transition: max-width 0.2s, opacity 0.2s;
  }

  .nav-dot:hover .nav-label {
    max-width: 160px;
    opacity: 1;
  }

  .nav-dot.active .nav-label {
    color: var(--accent);
  }
</style>
