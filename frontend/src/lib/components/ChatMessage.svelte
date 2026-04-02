<script lang="ts">
  import AgentBox from './AgentBox.svelte';
  import ConsensusBox from './ConsensusBox.svelte';
  import FeedbackButtons from './FeedbackButtons.svelte';
  import type { ChatTurn } from '$lib/stores/chat';

  let { turn, conversationId, conservativeActive, liberalActive, turnIndex }: {
    turn: ChatTurn;
    conversationId: string;
    conservativeActive: boolean;
    liberalActive: boolean;
    turnIndex?: number;
  } = $props();
</script>

<div class="chat-message" id={turnIndex !== undefined ? `turn-${turnIndex}` : undefined}>
  <div class="user-question">
    <span class="q-icon">&#x1F4AC;</span>
    <span class="q-text">{turn.question}</span>
  </div>

  <div class="agents-row">
    <div class="agent-col">
      <AgentBox
        type="conservative"
        content={turn.conservative}
        isActive={conservativeActive}
        citedArticles={turn.conservativeCited}
      />
    </div>
    <div class="agent-col">
      <AgentBox
        type="liberal"
        content={turn.liberal}
        isActive={liberalActive}
        citedArticles={turn.liberalCited}
      />
    </div>
  </div>

  {#if turn.consensus}
    <ConsensusBox
      content={turn.consensus}
      riskLevel={turn.riskLevel}
      citedArticles={turn.consensusCited}
    />
  {/if}

  {#if turn.requestFeedback && turn.feedbackGiven === null}
    <FeedbackButtons
      {conversationId}
      userQuestion={turn.question}
      botResponse={turn.consensus}
      riskLevel={turn.riskLevel}
      onFeedback={(rating) => { turn.feedbackGiven = rating; }}
    />
  {/if}
</div>

<style>
  .chat-message {
    margin-bottom: 24px;
    scroll-margin-top: 16px;
  }

  .user-question {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    background: var(--bg-elevated);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 12px;
    border: 1px solid var(--border);
  }

  .q-icon {
    font-size: 18px;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .q-text {
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .agents-row {
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
    align-items: stretch;
  }

  .agent-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
</style>
