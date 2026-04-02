<script lang="ts">
  import { onMount, tick } from 'svelte';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import ModeSelector from '$lib/components/ModeSelector.svelte';
  import ChatMessage from '$lib/components/ChatMessage.svelte';
  import TurnNavigator from '$lib/components/TurnNavigator.svelte';
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
    conservativeActive,
    liberalActive,
    conversationMode,
    resetChat,
  } from '$lib/stores/chat';
  import type { ChatTurn } from '$lib/stores/chat';
  import { initTheme } from '$lib/stores/theme';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';

  let inputText = $state('');
  let chatAreaEl: HTMLDivElement | undefined = $state();
  let activeTurnIndex = $state(-1);
  let sidebarOpen = $state(false);

  onMount(() => {
    initTheme();
    refreshConversations();
  });

  async function scrollToBottom() {
    await tick();
    if (chatAreaEl) {
      chatAreaEl.scrollTop = chatAreaEl.scrollHeight;
    }
  }

  function scrollToTurn(index: number) {
    activeTurnIndex = index;
    const el = document.getElementById(`turn-${index}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    activeTurnIndex = -1;
  }

  async function handleSelectConversation(id: string) {
    activeConversationId.set(id);
    resetChat();
    activeTurnIndex = -1;

    const data = await getConversation(id);
    conversationMode.set(data.conversation.mode);

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

  function parseCited(raw: string | undefined): string[] {
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    } catch {}
    return raw.split(',').map(s => s.trim()).filter(Boolean);
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
          turn.conservativeCited = parseCited(m.cited_articles);
          break;
        case 'liberal':
          turn.liberal = m.content;
          turn.liberalCited = parseCited(m.cited_articles);
          break;
        case 'consensus':
          turn.consensus = m.content;
          turn.riskLevel = m.risk_level || '';
          turn.consensusCited = parseCited(m.cited_articles);
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
    conservativeActive.set(false);
    liberalActive.set(false);
    await scrollToBottom();

    const convId = $activeConversationId;

    streamChat(convId, question, {
      onConservativeStart: () => {
        conservativeActive.set(true);
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
        conservativeActive.set(false);
        currentTurn.update(t => {
          if (!t) return t;
          return { ...t, conservativeCited: data.cited_articles || [] };
        });
      },
      onLiberalStart: () => {
        liberalActive.set(true);
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
        liberalActive.set(false);
        currentTurn.update(t => {
          if (!t) return t;
          return { ...t, liberalCited: data.cited_articles || [] };
        });
      },
      onConsensus: (data) => {
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
        conservativeActive.set(false);
        liberalActive.set(false);
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

{#if sidebarOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="mobile-overlay" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.4); z-index:90;" onclick={() => sidebarOpen = false} onkeydown={() => {}}></div>
{/if}

<div class="app-layout">
  <div class="sidebar-mobile-wrap" class:open={sidebarOpen}>
    <Sidebar
      onSelectConversation={(id) => { sidebarOpen = false; handleSelectConversation(id); }}
      onNewChat={() => { sidebarOpen = false; handleNewChat(); }}
    />
  </div>

  <main class="main-area">
    {#if !$activeConversationId}
      <ModeSelector onSelect={handleModeSelect} />
    {:else}
      <div class="chat-container">
        <div class="top-bar">
          <button class="mobile-menu-btn" style="display:none; position:absolute; left:12px; top:50%; transform:translateY(-50%); padding:6px; border-radius:6px; color:var(--text-muted);" onclick={() => sidebarOpen = !sidebarOpen}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          {#if $conversationMode}
            <span class="mode-label">
              {modeLabels[$conversationMode] || $conversationMode}
            </span>
          {/if}
          <div class="theme-toggle-wrap">
            <ThemeToggle />
          </div>
        </div>

        <div class="chat-area" bind:this={chatAreaEl}>
          <div class="chat-content">
            {#each $chatHistory as turn, i (i)}
              <ChatMessage
                {turn}
                conversationId={$activeConversationId}
                conservativeActive={false}
                liberalActive={false}
                turnIndex={i}
              />
            {/each}

            {#if $currentTurn}
              <ChatMessage
                turn={$currentTurn}
                conversationId={$activeConversationId}
                conservativeActive={$conservativeActive}
                liberalActive={$liberalActive}
                turnIndex={$chatHistory.length}
              />
            {/if}
          </div>
        </div>

        <TurnNavigator
          turns={$chatHistory}
          {activeTurnIndex}
          onSelect={scrollToTurn}
        />

        <div class="input-area">
          <div class="input-wrapper">
            <textarea
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

    {#if !$activeConversationId}
      <div class="floating-controls">
        <button class="mobile-menu-btn" style="display:none; padding:6px; border-radius:6px; color:var(--text-muted); background:var(--bg-elevated); border:1px solid var(--border);" onclick={() => sidebarOpen = !sidebarOpen}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        <ThemeToggle />
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
    position: relative;
    min-width: 0;
  }

  .chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .top-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 20px;
    background: var(--sidebar-bg);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    position: relative;
  }

  .mode-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-muted);
  }

  .theme-toggle-wrap {
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
  }

  .floating-controls {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    padding-right: 48px;
  }

  .chat-content {
    max-width: 900px;
    margin: 0 auto;
  }

  .input-area {
    border-top: 1px solid var(--border);
    padding: 16px 24px;
    background: var(--bg);
    flex-shrink: 0;
  }

  .input-wrapper {
    max-width: 900px;
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
    background: var(--bg-elevated);
    font-size: 16px;
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

  @media (max-width: 768px) { .chat-area { padding: 16px; } }
  @media (max-width: 768px) { .input-area { padding: 12px 16px; } }
  @media (max-width: 768px) { .input-wrapper { gap: 8px; } }
  @media (max-width: 768px) { .send-btn { padding: 10px 14px; } }
  @media (max-width: 768px) { .top-bar { padding: 8px 48px; } }
</style>
