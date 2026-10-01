import type { Message } from '../api/client';

// Simple markdown-like renderer for assistant messages
function renderContent(text: string) {
  // Bold
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code style="background:#1e1e1e;padding:1px 5px;border-radius:4px;font-family:monospace;font-size:12px">$1</code>');
  // Newlines
  text = text.replace(/\n/g, '<br/>');
  return text;
}

interface Props {
  messages: Message[];
  isThinking: boolean;
}

export default function MessageList({ messages, isThinking }: Props) {
  return (
    <div className="messages-list">
      {messages.map(msg => (
        <div key={msg.id} className={`message ${msg.role}`}>
          <div className="message-role">
            {msg.role === 'user' ? 'You' : 'GraphMind'}
          </div>
          <div
            className="message-bubble"
            dangerouslySetInnerHTML={
              msg.role === 'assistant'
                ? { __html: renderContent(msg.content) }
                : undefined
            }
          >
            {msg.role === 'user' ? msg.content : undefined}
          </div>
        </div>
      ))}

      {isThinking && (
        <div className="message assistant">
          <div className="message-role">GraphMind</div>
          <div className="thinking-bubble">
            <div className="thinking-dots">
              <div className="thinking-dot" />
              <div className="thinking-dot" />
              <div className="thinking-dot" />
            </div>
            Searching knowledge base…
          </div>
        </div>
      )}
    </div>
  );
}
