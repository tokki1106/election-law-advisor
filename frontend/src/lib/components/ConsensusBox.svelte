<script lang="ts">
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

  const NEC_REPORT_URL = 'https://nec.go.kr/site/nec/01/10101020000002020040704.jsp';
</script>

<div class="consensus-box">
  <div class="header">
    <span class="title">종합 판단</span>
    <span class="badge" style:background="{badge.color}20" style:color={badge.color}>
      {badge.icon} {badge.label}
    </span>
  </div>
  <div class="content">{content}</div>
  {#if citedArticles.length > 0}
    <div class="cited">
      <span class="cited-label">근거 조문:</span>
      {#each citedArticles as article}
        <span class="tag">{article}</span>
      {/each}
    </div>
  {/if}
  {#if riskLevel === 'danger'}
    <a class="report-btn" href={NEC_REPORT_URL} target="_blank" rel="noopener noreferrer">
      선거 위반 신고하기
    </a>
  {/if}
</div>

<style>
  .consensus-box {
    border: 2px solid var(--consensus-border);
    background: var(--consensus-bg);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 8px;
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .title {
    font-weight: 700;
    font-size: 15px;
  }

  .badge {
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
  }

  .content {
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .cited {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: 12px;
  }

  .cited-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
  }

  .tag {
    display: inline-block;
    padding: 2px 8px;
    background: rgba(218, 119, 86, 0.1);
    border-radius: 4px;
    font-size: 12px;
    color: var(--accent);
  }

  .report-btn {
    display: inline-block;
    margin-top: 12px;
    padding: 8px 16px;
    background: var(--danger);
    color: white;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    transition: opacity 0.2s;
  }

  .report-btn:hover {
    opacity: 0.9;
  }
</style>
