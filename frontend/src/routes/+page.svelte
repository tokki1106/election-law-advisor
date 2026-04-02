<script lang="ts">
  import { onMount, tick } from 'svelte';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import ModeSelector from '$lib/components/ModeSelector.svelte';
  import ChatMessage from '$lib/components/ChatMessage.svelte';
  import {
    createConversation,
    getConversation,
    streamChat,
  } from '$lib/api';
  import type { Message } from '$lib/api';
  import {
    conversations,
    activeConversationId,
    refreshConversations,
  } from '$lib/stores/conversations';
  import {
    chatHistory,
    currentTurn,
    isStreaming,
    activePhase,
    conversationMode,
    resetChat,
  } from '$lib/stores/chat';
  import type { ChatTurn } from '$lib/stores/chat';

  let inputText = $state('');
  let chatAreaEl: HTMLDivElement | undefined = $state();
  let textareaEl: HTMLTextAreaElement | undefined = $state();

  onMount(() => {
    refreshConversations();
  });

  async function scrollToBottom() {
    await tick();
    if (chatAreaEl) {
      chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
    }
  }

  async function handleModeSelect(mode: string) {
    const { id } = await createConversation(mode);
    activeConversationId.set(id);
    conversationMode.set(mode);
    resetChat();
    conversationMode.set(mode);
    await refreshConversations();
  }

  function handleNewChat() {
    activeConversationId.set(null);
    resetChat();
  }

  async function handleSelectConversation(id: string) {
    activeConversationId.set(id);
    resetChat();

    const data = await getConversation(id);
    conversationMode.set(data.conversation.mode);

    // Group messages into ChatTurns
    const turns: ChatTurn[] = [];
    let currentGroup: Message[] = [];

    for (const msg of data.messages) {
      if (msg.role === 'user') {
        if (currentGroup.length > 0) {
          turns.push(buildTurn(currentGroup));
        }
        currentGroup = [msg];
      } else {
        currentGroup.push(msg);
      }
    }
    if (currentGroup.length > 0) {
      turns.push(buildTurn(currentGroup));
    }

    chatHistory.set(turns);
    await scrollToBottom();
  }

  function buildTurn(messages: Message[]): ChatTurn {
    const turn: ChatTurn = {
      question: '',
      conservative: '',
      conservativeCited: [],
      liberal: '',
      liberalCited: [],
      consensus: '',
      consensusCited: [],
      riskLevel: '',
      requestFeedback: false,
      feedbackGiven: null,
    };

    for (const m of messages) {
      switch (m.role) {
        case 'user':
          turn.question = m.content;
          break;
        case 'conservative':
          turn.conservative = m.content;
          turn.conservativeCited = m.cited_articles ? m.cited_articles.split(',').map(s => s.trim()).filter(Boolean) : [];
          break;
        case 'liberal':
          turn.liberal = m.content;
          turn.liberalCited = m.cited_articles ? m.cited_articles.split(',').map(s => s.trim()).filter(Boolean) : [];
          break;
        case 'consensus':
          turn.consensus = m.content;
          turn.riskLevel = m.risk_level || '';
          turn.consensusCited = m.cited_articles ? m.cited_articles.split(',').map(s => s.trim()).filter(Boolean) : [];
          turn.requestFeedback = true;
          break;
      }
    }

    return turn;
  }

  async function handleSend() {
    const question = inputText.trim();
    if (!question || $isStreaming || !$activeConversationId) return;

    inputText = '';
    isStreaming.set(true);

    const turn: ChatTurn = {
      question,
      conservative: '',
      conservativeCited: [],
      liberal: '',
      liberalCited: [],
      consensus: '',
      consensusCited: [],
      riskLevel: '',
      requestFeedback: false,
      feedbackGiven: null,
    };
    currentTurn.set(turn);
    activePhase.set('idle');
    await scrollToBottom();

    const convId = $activeConversationId;

    streamChat(convId, question, {
      onConservativeStart: () => {
        activePhase.set('conservative');
        currentTurn.update(t => t ? { ...t } : t);
        scrollToBottom();
      },
      onConservativeToken: (token: string) => {
        currentTurn.update(t => {
          if (!t) return t;
          return { ...t, conservative: t.conservative + token };
        });
        scrollToBottom();
      },
      onConservativeEnd: (data: { cited_articles: string[] }) => {
        currentTurn.update(t => {
          if (!t) return t;
          return { ...t, conservativeCited: data.cited_articles || [] };
        });
        scrollToBottom();
      },
      onLiberalStart: () => {
        activePhase.set('liberal');
        currentTurn.update(t => t ? { ...t } : t);
        scrollToBottom();
      },
      onLiberalToken: (token: string) => {
        currentTurn.update(t => {
          if (!t) return t;
          return { ...t, liberal: t.liberal + token };
        });
        scrollToBottom();
      },
      onLiberalEnd: (data: { cited_articles: string[] }) => {
        currentTurn.update(t => {
          if (!t) return t;
          return { ...t, liberalCited: data.cited_articles || [] };
        });
        scrollToBottom();
      },
      onConsensus: (data) => {
        activePhase.set('consensus');
        currentTurn.update(t => {
          if (!t) return t;
          return {
            ...t,
            consensus: data.content,
            riskLevel: data.risk_level,
            consensusCited: data.cited_articles || [],
            requestFeedback: data.request_feedback,
          };
        });

        // Move completed turn to history
        currentTurn.update(t => {
          if (t) {
            chatHistory.update(h => [...h, {
              ...t,
              consensus: data.content,
              riskLevel: data.risk_level,
              consensusCited: data.cited_articles || [],
              requestFeedback: data.request_feedback,
            }]);
          }
          return null;
        });

        isStreaming.set(false);
        activePhase.set('idle');
        refreshConversations();
        scrollToBottom();
      },
    });
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const modeLabels: Record<string, string> = {
    citizen: '일반 시민 모드',
    candidate: '후보자 · 선거운동원 모드',
  };
</script>

<div class="app-layout">
  <Sidebar
    onSelectConversation={handleSelectConversation}
    onNewChat={handleNewChat}
  />

  <main class="main-area">
    {#if !$activeConversationId}
      <ModeSelector onSelect={handleModeSelect} />
    {:else}
      <div class="chat-container">
        {#if $conversationMode}
          <div class="mode-indicator">
            {modeLabels[$conversationMode] || $conversationMode}
          </div>
        {/if}

        <div class="chat-area" bind:this={chatAreaEl}>
          <div class="chat-content">
            {#each $chatHistory as turn, i (i)}
              <ChatMessage
                {turn}
                conversationId={$activeConversationId}
                conservativeActive={false}
                liberalActive={false}
              />
            {/each}

            {#if $currentTurn}
              <ChatMessage
                turn={$currentTurn}
                conversationId={$activeConversationId}
                conservativeActive={$activePhase === 'conservative'}
                liberalActive={$activePhase === 'liberal'}
              />
            {/if}
          </div>
        </div>

        <div class="input-area">
          <div class="input-wrapper">
            <textarea
              bind:this={textareaEl}
              bind:value={inputText}
              onkeydown={handleKeydown}
              placeholder="선거법에 대해 질문하세요..."
              rows={1}
              disabled={$isStreaming}
            ></textarea>
            <button
              class="send-btn"
              onclick={handleSend}
              disabled={$isStreaming || !inputText.trim()}
            >
              전송
            </button>
          </div>
        </div>
      </div>
    {/if}
  </main>
</div>

<style>
  .app-layout {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  .main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .mode-indicator {
    padding: 10px 20px;
    background: var(--sidebar-bg);
    border-bottom: 1px solid var(--border);
    font-size: 13px;
    font-weight: 500;
    color: var(--text-muted);
    text-align: center;
    flex-shrink: 0;
  }

  .chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  .chat-content {
    max-width: 800px;
    margin: 0 auto;
  }

  .input-area {
    border-top: 1px solid var(--border);
    padding: 16px 24px;
    background: var(--bg);
    flex-shrink: 0;
  }

  .input-wrapper {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }

  textarea {
    flex: 1;
    resize: none;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    background: white;
    font-size: 14px;
    line-height: 1.5;
    min-height: 44px;
    max-height: 120px;
    outline: none;
    transition: border-color 0.2s;
  }

  textarea:focus {
    border-color: var(--accent);
  }

  textarea:disabled {
    opacity: 0.6;
  }

  .send-btn {
    padding: 10px 20px;
    background: var(--accent);
    color: white;
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
    transition: opacity 0.2s;
    flex-shrink: 0;
  }

  .send-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
