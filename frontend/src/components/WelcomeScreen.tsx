const SUGGESTIONS = [
  {
    icon: '🏢',
    title: 'Halls of Residence',
    tag: 'CAMPUS',
    body: 'How many halls of residence are there in IIT KGP?',
  },
  {
    icon: '💡',
    title: '180DC Advisors',
    tag: 'SOCIETIES',
    body: 'Who are the current faculty advisors of 180 Degrees Consulting (180DC)?',
  },
  {
    icon: '📚',
    title: 'Branch Change',
    tag: 'ACADEMIC',
    body: 'What is the exact procedure and CGPA requirement for a branch change after the first year?',
  },
  {
    icon: '🎉',
    title: 'Campus Fests',
    tag: 'CULTURE',
    body: 'When are Spring Fest and Kshitij usually held during the academic calendar?',
  },
];

interface Props {
  onSuggest: (text: string) => void;
}

export default function WelcomeScreen({ onSuggest }: Props) {
  return (
    <div className="welcome">
      <div className="welcome-icon">G</div>
      <h1>Where knowledge meets <span className="highlight">KGP</span></h1>
      <p className="welcome-sub">
        Ask anything about courses, hall guidelines, CDC internships,<br />
        ERP procedures, or campus lore.
      </p>

      <div className="suggestions-grid">
        {SUGGESTIONS.map(s => (
          <button
            key={s.title}
            className="suggestion-card"
            onClick={() => onSuggest(s.body)}
          >
            <div className="suggestion-card-header">
              <div className="suggestion-card-title">
                {s.icon} {s.title}
              </div>
              <span className="suggestion-tag">{s.tag}</span>
            </div>
            <div className="suggestion-card-body">{s.body}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
