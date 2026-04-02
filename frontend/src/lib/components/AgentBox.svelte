<script lang="ts">
  let { type, content, isActive, citedArticles }: {
    type: 'conservative' | 'liberal';
    content: string;
    isActive: boolean;
    citedArticles: string[];
  } = $props();

  const config = $derived(
    type === 'conservative'
      ? { icon: '\u2696\uFE0F', label: '보수적 해석', bgVar: 'var(--conservative-bg)' }
      : { icon: '\uD83D\uDD4A\uFE0F', label: '관용적 해석', bgVar: 'var(--liberal-bg)' }
  );
</script>

<div class="agent-box" style:background={config.bgVar}>
  <div class="header">
    <span class="icon">{config.icon}</span>
    <span class="label">{config.label}</span>
    {#if isActive}
      <span class="pulse-dot"></span>
    {/if}
  </div>
  <div class="content">
    {#if !content && isActive}
      <span class="analyzing">분석 중...</span>
    {:else}
      {content}
    {/if}
  </div>
  {#if citedArticles.length > 0}
    <div class="cited">
      {#each citedArticles as article}
        <span class="tag">{article}</span>
      {/each}
    </div>
  {/if}
</div>

<style>
  .agent-box {
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 8px;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 10px;
    font-weight: 600;
    font-size: 14px;
  }

  .icon {
    font-size: 18px;
  }

  .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.2s ease-in-out infinite;
    margin-left: 4px;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
  }

  .content {
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .analyzing {
    color: var(--text-muted);
    font-style: italic;
  }

  .cited {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }

  .tag {
    display: inline-block;
    padding: 2px 8px;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 4px;
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
