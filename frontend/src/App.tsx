import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './contexts/AuthContext';
import { api } from './api/client';
import type { Conversation, Message } from './api/client';
import Sidebar from './components/Sidebar';
import WelcomeScreen from './components/WelcomeScreen';
import MessageList from './components/MessageList';
import MessageInput from './components/MessageInput';
import AuthModal from './components/AuthModal';

// ── Icons ────────────────────────────────────────────────────────────────────
const IconSearch = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
    <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35" strokeLinecap="round"/>
  </svg>
);

function genId() {
  return Math.random().toString(36).slice(2);
}

export default function App() {
  const { user, isLoading } = useAuth();

  // ── State ────────────────────────────────────────────────────────────────
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [showAuth, setShowAuth] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Load conversation list when user changes ──────────────────────────────
  useEffect(() => {
    if (user) {
      api.listConversations().then(setConversations).catch(console.error);
    } else {
      setConversations([]);
      setActiveConvId(null);
      setMessages([]);
    }
  }, [user]);

  // ── Load messages when active conversation changes ───────────────────────
  useEffect(() => {
    if (!activeConvId || activeConvId === 'guest') return;
    api.getConversation(activeConvId)
      .then(detail => setMessages(detail.messages))
      .catch(console.error);
  }, [activeConvId]);

  // ── Auto-scroll to bottom ─────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  // ── Handle new conversation ───────────────────────────────────────────────
  const handleNew = useCallback(() => {
    setActiveConvId(null);
    setMessages([]);
  }, []);

  // ── Handle conversation select ────────────────────────────────────────────
  const handleSelect = useCallback((id: string) => {
    setActiveConvId(id);
  }, []);

  // ── Handle delete ─────────────────────────────────────────────────────────
  const handleDelete = useCallback(async (id: string) => {
    try {
      await api.deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));
      if (activeConvId === id) {
        setActiveConvId(null);
        setMessages([]);
      }
    } catch (e) {
      console.error(e);
    }
  }, [activeConvId]);

  // ── Handle send ──────────────────────────────────────────────────────────
  const handleSend = useCallback(async (text: string) => {
    // Optimistic user message
    const optimisticId = genId();
    const userMsg: Message = {
      id: optimisticId,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsThinking(true);

    try {
      const res = await api.chat(text, activeConvId ?? undefined);

      // For authenticated users: update conversation list + set active
      if (user) {
        setActiveConvId(res.conversation_id);
        // Refresh conversation list (to get updated title/timestamp)
        const updatedList = await api.listConversations();
        setConversations(updatedList);
        // Append assistant reply
        const assistantMsg: Message = {
          id: genId(),
          role: 'assistant',
          content: res.answer,
          created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        // Guest: just show the response
        setActiveConvId('guest');
        const assistantMsg: Message = {
          id: genId(),
          role: 'assistant',
          content: res.answer,
          created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMsg]);
      }
    } catch (err: unknown) {
      const errMsg: Message = {
        id: genId(),
        role: 'assistant',
        content: err instanceof Error ? `Error: ${err.message}` : 'Something went wrong. Please try again.',
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsThinking(false);
    }
  }, [activeConvId, user]);

  // ── Loading ───────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        <div className="thinking-dots">
          <div className="thinking-dot" />
          <div className="thinking-dot" />
          <div className="thinking-dot" />
        </div>
      </div>
    );
  }

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : user?.email?.[0].toUpperCase() ?? '?';

  return (
    <div className="app-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeConvId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
        onSignIn={() => setShowAuth(true)}
      />

      <div className="main-area">
        {/* Top bar */}
        <div className="topbar">
          <div className="topbar-left">
            <div className="model-badge">
              <div className="model-dot" />
              GraphMind AI
              <span className="version-tag">v1.0</span>
            </div>
          </div>
          <div className="topbar-right">
            <button className="icon-btn" title="Search"><IconSearch /></button>
            {user ? (
              <div className="topbar-avatar" title={user.email}>{initials}</div>
            ) : (
              <button
                className="icon-btn"
                style={{ padding: '0 12px', width: 'auto', fontSize: 12, color: 'var(--accent)' }}
                onClick={() => setShowAuth(true)}
              >
                Sign In
              </button>
            )}
          </div>
        </div>

        {/* Status strip */}
        <div className="status-strip">
          <div className="status-left">
            <div className="status-item">
              <div className="status-dot" />
              RAG INDEX: SYNCHRONIZED
            </div>
            <span className="status-sep">•</span>
            <div className="status-item">4,420 WIKI CHUNKS</div>
          </div>
          <div className="status-right">
            <div className="status-item">
              <a href="https://wiki.metakgp.org" target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                wiki.metakgp.org
              </a>
            </div>
            <span className="status-sep">•</span>
            <div className="status-item">MODEL: gemini-2.5-flash ● ACTIVE</div>
          </div>
        </div>

        {/* Chat viewport */}
        <div className="chat-viewport">
          <div className="chat-inner">
            {messages.length === 0 && !isThinking ? (
              <WelcomeScreen onSuggest={handleSend} />
            ) : (
              <MessageList messages={messages} isThinking={isThinking} />
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <MessageInput onSend={handleSend} disabled={isThinking} />
      </div>

      {/* Auth modal */}
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}
