<script lang="ts">
  import { renderMarkdown } from '$lib/markdown';

  let { content, riskLevel, citedArticles }: {
    content: string;
    riskLevel: string;
    citedArticles: string[];
  } = $props();

  const badge = $derived(
    riskLevel === 'safe'
      ? { color: 'var(--safe)', icon: '\uD83D\uDFE2', label: '안전' }
      : riskLevel === 'caution'
        ? { color: 'var(--caution)', icon: '\uD83D\uDFE1', label: '주의' }
        : { color: 'var(--danger)', icon: '\uD83D\uDD34', label: '위반가능' }
  );

  const renderedContent = $derived(renderMarkdown(content));

  const NEC_REPORT_URL = 'https://nec.go.kr/site/nec/01/10101020000002020040704.jsp';
</script>

<div class="consensus-box">
  <div class="header">
    <span class="title">종합 판단</span>
    <span class="badge" style:background="{badge.color}14" style:color={badge.color} style:border="1.5px solid {badge.color}40">
      {badge.icon} {badge.label}
    </span>
  </div>
  <div class="content markdown-body">{@html renderedContent}</div>
  {#if citedArticles.length > 0}
    <div class="cited">
      <span class="cited-label">근거 조문</span>
      {#each citedArticles as article}
        <span class="tag">{article}</span>
      {/each}
    </div>
  {/if}
  {#if riskLevel === 'danger'}
    <a class="report-btn" href={NEC_REPORT_URL} target="_blank" rel="noopener noreferrer">
      🚨 중앙선관위에 위반행위 신고
    </a>
  {/if}
</div>

<style>
  .consensus-box {
    border: 2px solid var(--consensus-border);
    background: var(--consensus-bg);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 8px;
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .title {
    font-weight: 700;
    font-size: 15px;
    letter-spacing: -0.01em;
  }

  .badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
  }

  .content {
    font-size: 14px;
    line-height: 1.75;
    word-break: keep-all;
    overflow-wrap: break-word;
  }

  .cited {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid rgba(218, 119, 86, 0.15);
  }

  .cited-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    margin-right: 4px;
  }

  .tag {
    display: inline-block;
    padding: 3px 10px;
    background: rgba(218, 119, 86, 0.08);
    border-radius: 6px;
    font-size: 12px;
    color: var(--accent);
    font-weight: 500;
  }

  .report-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 16px;
    padding: 10px 20px;
    background: var(--danger);
    color: white;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    transition: opacity 0.2s, transform 0.1s;
  }

  .report-btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
  }
</style>
