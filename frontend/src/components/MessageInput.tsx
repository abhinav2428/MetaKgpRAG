import { useRef, useEffect, useState } from 'react';
import type { KeyboardEvent } from 'react';

const MAX_CHARS = 2048;

const IconSend = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
    <path d="M12 19V5M5 12l7-7 7 7" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function MessageInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [value]);

  const handleSend = () => {
    const msg = value.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setValue('');
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const remaining = MAX_CHARS - value.length;

  return (
    <div className="input-area">
      <div className="input-inner">
        <div className="input-box">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={e => setValue(e.target.value.slice(0, MAX_CHARS))}
            onKeyDown={handleKey}
            placeholder="Message GraphMind AI or ask about KGP wiki…"
            rows={1}
            disabled={disabled}
          />
          <div className="input-actions">
            <div className="input-left">
              <div className="input-pill">
                <div className="input-pill-dot" />
                MetaKGP Wiki: On
              </div>
              <div className="input-pill"># All Campuses</div>
            </div>
            <div className="input-right">
              <span className="char-count">{remaining} / {MAX_CHARS}</span>
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={!value.trim() || disabled}
                title="Send (Enter)"
              >
                <IconSend />
              </button>
            </div>
          </div>
        </div>
        <p className="input-footer">
          GraphMind AI is an independent community project. Verify critical info on{' '}
          <a href="https://wiki.metakgp.org" target="_blank" rel="noreferrer">wiki.metakgp.org</a>
        </p>
      </div>
    </div>
  );
}
