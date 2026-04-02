<script lang="ts">
  import { submitFeedback } from '$lib/api';

  let { conversationId, userQuestion, botResponse, riskLevel, onFeedback }: {
    conversationId: string;
    userQuestion: string;
    botResponse: string;
    riskLevel: string;
    onFeedback: (rating: 'up' | 'down') => void;
  } = $props();

  let submitted = $state(false);

  async function handleClick(rating: 'up' | 'down') {
    if (submitted) return;
    submitted = true;
    await submitFeedback({
      conversation_id: conversationId,
      user_question: userQuestion,
      bot_response: botResponse,
      risk_level: riskLevel || null,
      rating,
    });
    onFeedback(rating);
  }
</script>

<div class="feedback">
  {#if submitted}
    <span class="thanks">감사합니다!</span>
  {:else}
    <span class="prompt">이 답변이 도움이 되었나요?</span>
    <button class="fb-btn" onclick={() => handleClick('up')}>&#x1F44D;</button>
    <button class="fb-btn" onclick={() => handleClick('down')}>&#x1F44E;</button>
  {/if}
</div>

<style>
  .feedback {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
    font-size: 13px;
  }

  .prompt {
    color: var(--text-muted);
  }

  .fb-btn {
    font-size: 18px;
    padding: 4px 8px;
    border-radius: 6px;
    transition: background 0.15s;
  }

  .fb-btn:hover {
    background: var(--hover);
  }

  .thanks {
    color: var(--safe);
    font-weight: 500;
  }
</style>
