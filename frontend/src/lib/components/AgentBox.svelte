<script lang="ts">
  import { renderMarkdown } from '$lib/markdown';

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

  const renderedContent = $derived(renderMarkdown(content));
</script>

<div class="agent-box" style:background={config.bgVar}>
  <div class="header">
    <span class="icon">{config.icon}</span>
    <span class="label">{config.label}</span>
    {#if isActive}
      <span class="pulse-dot"></span>
    {/if}
  </div>
  <div class="content markdown-body">
    {#if !content && isActive}
      <span class="analyzing">분석 중...</span>
    {:else}
      {@html renderedContent}
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
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: -0.01em;
    flex-shrink: 0;
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
    line-height: 1.75;
    word-break: keep-all;
    overflow-wrap: break-word;
    max-height: 400px;
    overflow-y: auto;
    flex: 1;
  }

  .analyzing {
    color: var(--text-muted);
    font-style: italic;
  }

  .cited {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid rgba(128, 128, 128, 0.12);
    flex-shrink: 0;
  }

  .tag {
    display: inline-block;
    padding: 3px 10px;
    background: rgba(128, 128, 128, 0.08);
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
  }
</style>
