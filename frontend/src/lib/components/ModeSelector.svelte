<script lang="ts">
  let { onSelect }: {
    onSelect: (mode: string) => void;
  } = $props();
</script>

<div class="mode-selector">
  <div class="heading">
    <h2 class="title">어떤 도움이 필요하세요?</h2>
    <p class="subtitle">사용자 유형에 맞는 맞춤 답변을 드립니다</p>
  </div>
  <div class="cards">
    <button class="card" onclick={() => onSelect('citizen')}>
      <span class="icon">&#x1F464;</span>
      <span class="label">일반 시민</span>
      <span class="desc">선거 관련 행동이 합법인지 궁금해요</span>
    </button>
    <button class="card" onclick={() => onSelect('candidate')}>
      <span class="icon">&#x1F3DB;</span>
      <span class="label">후보자 &middot; 선거운동원</span>
      <span class="desc">선거운동 중 법적 리스크를 확인하고 싶어요</span>
    </button>
  </div>
</div>

<style>
  .mode-selector {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 40px;
  }

  .heading {
    text-align: center;
  }

  .title {
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.02em;
  }

  .subtitle {
    margin-top: 8px;
    font-size: 14px;
    color: var(--text-muted);
  }

  .cards {
    display: flex;
    gap: 20px;
  }

  .card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 32px 28px;
    border: 2px solid var(--border);
    border-radius: 12px;
    background: white;
    width: 240px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .card:hover {
    border-color: var(--accent);
    box-shadow: 0 2px 12px rgba(218, 119, 86, 0.12);
  }

  .icon {
    font-size: 36px;
  }

  .label {
    font-size: 16px;
    font-weight: 600;
  }

  .desc {
    font-size: 13px;
    color: var(--text-muted);
    text-align: center;
    line-height: 1.5;
  }
</style>
