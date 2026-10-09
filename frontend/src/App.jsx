import { useState, useEffect, useRef, useCallback } from 'react';
import { api, formatINR, pct, stars } from './api.js';

/* ─── Small helpers ─────────────────────────────────────── */
function Spinner() { return <span className="spinner" />; }

function Badge({ cat }) {
  const map = {
    'BEST MATCH':      'badge-best-match',
    'BEST VALUE':      'badge-best-value',
    'BEST EXPERIENCE': 'badge-best-exp',
    'PREMIUM':         'badge-premium',
    'ALTERNATIVE':     'badge-alt',
  };
  const cls = Object.entries(map).find(([k]) => cat?.includes(k))?.[1] || 'badge-alt';
  return <span className={`rec-badge ${cls}`}>{cat || 'ALTERNATIVE'}</span>;
}

function ConfidenceFill({ val }) {
  const color = val >= .8 ? 'var(--emerald)' : val >= .5 ? 'var(--amber)' : 'var(--rose)';
  return (
    <div className="confidence-bar">
      <div className="confidence-fill" style={{ width: `${(val || 0) * 100}%`, background: color }} />
    </div>
  );
}

function HealthFill({ val }) {
  const color = val >= 80 ? 'var(--emerald)' : val >= 60 ? 'var(--amber)' : 'var(--rose)';
  return (
    <div className="supplier-health-bar">
      <div className="supplier-health-fill" style={{ width: `${val}%`, background: color }} />
    </div>
  );
}

/* ─── Topbar ────────────────────────────────────────────── */
function Topbar({ apiOk }) {
  return (
    <header className="topbar">
      <div className="topbar-logo">
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="32" height="32" rx="8" fill="#6366f1"/>
          <path d="M8 22L16 10L24 22" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M10.5 18H21.5" stroke="white" strokeWidth="2" strokeLinecap="round"/>
        </svg>
        <span>TravClan <em>Agent Copilot</em></span>
      </div>
      <div className="topbar-sep" />
      <div className="topbar-badge">
        <span className="dot" style={{ background: apiOk === true ? 'var(--emerald)' : apiOk === false ? 'var(--rose)' : 'var(--amber)' }} />
        {apiOk === true ? 'API Connected' : apiOk === false ? 'API Offline' : 'Connecting…'}
      </div>
    </header>
  );
}

/* ─── Sidebar ───────────────────────────────────────────── */
const NAV = [
  { id: 'copilot',      icon: '✦', label: 'Copilot Chat' },
  { id: 'destinations', icon: '🌍', label: 'Destinations' },
  { id: 'suppliers',    icon: '🏢', label: 'Suppliers' },
];

function Sidebar({ page, setPage }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-section-label">Workspace</div>
      {NAV.map(n => (
        <div
          key={n.id}
          id={`nav-${n.id}`}
          className={`nav-item ${page === n.id ? 'active' : ''}`}
          onClick={() => setPage(n.id)}
        >
          <span className="icon">{n.icon}</span>
          {n.label}
        </div>
      ))}
    </nav>
  );
}

/* ─── Extraction card ───────────────────────────────────── */
function ExtractionCard({ result }) {
  if (!result) return null;
  const { requirement: r, confidence, overall_confidence, missing, clarifications } = result;
  const fields = [
    ['Destination', r.destination, confidence?.destination],
    ['Nights', r.nights, confidence?.duration],
    ['Budget', r.budget ? formatINR(r.budget) : null, confidence?.budget],
    ['Adults', r.travelers?.adults, null],
    ['Stars', r.hotel_star_rating ? `${r.hotel_star_rating}★` : null, null],
    ['Style', r.travel_style, null],
    ['Month', r.month, confidence?.month],
  ].filter(([, v]) => v != null);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <div className="card-title">Extracted Requirement</div>
        <span className="tag" style={{ borderColor: 'var(--indigo-glow)', color: 'var(--indigo-light)' }}>
          {(overall_confidence * 100).toFixed(0)}% confident
        </span>
      </div>
      {clarifications?.length > 0 && (
        <div className="clarify-banner">
          <div className="clarify-title">⚠ Needs clarification</div>
          <ul className="clarify-list">
            {clarifications.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}
      <div className="extraction-grid">
        {fields.map(([label, value, conf]) => (
          <div key={label} className="ext-field">
            <div className="ext-label">{label}</div>
            <div className="ext-value">{String(value)}</div>
            {conf != null && <ConfidenceFill val={conf} />}
          </div>
        ))}
      </div>
      {r.activities?.length > 0 && (
        <div className="flex gap-2" style={{ flexWrap: 'wrap', marginTop: 4 }}>
          {r.activities.map(a => <span key={a} className="tag">{a}</span>)}
        </div>
      )}
      {missing?.length > 0 && (
        <div className="mt-2 text-xs text-muted">Missing: {missing.join(', ')}</div>
      )}
    </div>
  );
}

/* ─── Recommendation cards ──────────────────────────────── */
function RecCard({ item, selected, onSelect }) {
  return (
    <div
      id={`rec-${item.hotel_id}`}
      className={`rec-card ${selected ? 'selected' : ''}`}
      onClick={() => onSelect(item)}
    >
      <div className="rec-card-header">
        <div>
          <div className="rec-hotel-name">{item.name}</div>
          <div className="rec-area">{item.area}</div>
        </div>
        <Badge cat={item.category} />
      </div>
      <div className="rec-meta">
        <span className="rec-stars">{stars(item.star_rating)}</span>
        <span className="tag" style={{ borderColor: 'transparent' }}>⭐ {item.rating?.toFixed(1)}</span>
        <span className="rec-price">
          <span className="currency">est. </span>
          {formatINR(item.estimated_total)}
        </span>
        {item.above_budget && <span className="tag" style={{ color: 'var(--rose)', borderColor: 'rgba(244,63,94,.25)' }}>Over budget</span>}
      </div>
      <div className="rec-score-row">
        <span className="score-chip">score <span>{item.scores?.final}</span></span>
        {item.scores?.diversity != null && <span className="score-chip">div <span>{item.scores.diversity}</span></span>}
        {item.scores?.mmr != null && <span className="score-chip">mmr <span>{item.scores.mmr}</span></span>}
        {item.supplier_risk?.length > 0 && <span className="score-chip" style={{ color: 'var(--amber)' }}>⚠ risk</span>}
      </div>
      <div className="text-xs text-muted mt-2" style={{ lineHeight: 1.5 }}>{item.explanation}</div>
    </div>
  );
}

/* ─── Quote panel ───────────────────────────────────────── */
function QuotePanel({ quote, onModify, modifying }) {
  const [cmd, setCmd] = useState('');
  if (!quote) return null;

  const { pricing: p, summary: s, validation: v, itinerary, budget_optimizer: bo } = quote;

  const COMMANDS = [
    'replace hotel with something cheaper',
    'make it more relaxed',
    'add a cultural activity',
    'set markup 10%',
    'apply discount 5000',
  ];

  return (
    <div className="quote-section">
      {/* Summary */}
      <div className="card">
        <div className="card-title">Quote Summary</div>
        <div style={{ fontSize: '.9rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
          {s?.hotel?.name}
        </div>
        <div className="text-xs text-secondary mb-2">
          {s?.destination} · {s?.nights} nights · {s?.travelers?.adults} adults{s?.travelers?.children > 0 ? ` + ${s.travelers.children} children` : ''}
          {s?.month ? ` · ${s.month}` : ''}
        </div>
        <div className="price-breakdown">
          {p?.hotel_cost != null && <div className="price-row"><span className="label">Hotel ({s?.nights}N × {s?.travelers?.adults} pax)</span><span className="amount">{formatINR(p.hotel_cost)}</span></div>}
          {p?.activity_cost != null && p.activity_cost > 0 && <div className="price-row"><span className="label">Activities</span><span className="amount">{formatINR(p.activity_cost)}</span></div>}
          {p?.transfer_cost != null && p.transfer_cost > 0 && <div className="price-row"><span className="label">Transfers</span><span className="amount">{formatINR(p.transfer_cost)}</span></div>}
          {p?.markup_amount != null && p.markup_amount > 0 && <div className="price-row"><span className="label">Markup ({pct(p.markup_rate)})</span><span className="amount">{formatINR(p.markup_amount)}</span></div>}
          {p?.discount != null && p.discount > 0 && <div className="price-row"><span className="label">Discount</span><span className="amount" style={{ color: 'var(--emerald)' }}>−{formatINR(p.discount)}</span></div>}
          <div className="price-row total">
            <span>Total</span>
            <span className="amount">{formatINR(p?.total)}</span>
          </div>
          {p?.gross_margin != null && (
            <div className="price-row"><span className="label text-muted">Gross margin</span><span className="amount text-emerald">{formatINR(p.gross_margin)} ({pct(p.margin_rate)})</span></div>
          )}
        </div>
      </div>

      {/* Budget optimiser */}
      {bo?.suggested_hotel && (
        <div className="card" style={{ background: 'var(--emerald-subtle)', borderColor: 'rgba(16,185,129,.25)' }}>
          <div className="card-title" style={{ color: 'var(--emerald)' }}>💡 Budget Optimiser</div>
          <div className="text-sm text-secondary">
            Switch to <strong style={{ color: 'var(--text-primary)' }}>{bo.suggested_hotel.name}</strong> to save{' '}
            <strong style={{ color: 'var(--emerald)' }}>{formatINR(bo.savings)}</strong>
          </div>
        </div>
      )}

      {/* Validation */}
      {v && (
        <div className="card">
          <div className="card-title">Validation</div>
          <div className="validation-list">
            {v.map((item, i) => (
              <div key={i} className={`val-item ${item.status}`}>
                <span className="val-icon">{item.status === 'pass' ? '✓' : item.status === 'fail' ? '✗' : '⚠'}</span>
                <div>
                  <strong>{item.check.replace(/_/g, ' ')}</strong>
                  {item.message && <div className="val-msg">{item.message}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Itinerary */}
      {itinerary?.days && (
        <div className="card">
          <div className="card-title">Itinerary</div>
          {itinerary.days.map((day, i) => (
            <div key={i} className="itinerary-day">
              <div className="itinerary-day-label">Day {day.day}</div>
              {day.activities?.map((a, j) => (
                <div key={j} className="itinerary-activity">{a.name || a}</div>
              ))}
              {(!day.activities || day.activities.length === 0) && (
                <div className="itinerary-activity" style={{ opacity: .5 }}>Free exploration</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modify */}
      <div className="card">
        <div className="card-title">Modify Trip</div>
        <div className="modify-suggestions">
          {COMMANDS.map(c => (
            <button key={c} id={`cmd-${c.replace(/\s+/g,'-').slice(0,30)}`} className="modify-chip" onClick={() => setCmd(c)}>
              {c}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            id="modify-input"
            type="text"
            placeholder="e.g. add a hiking activity"
            value={cmd}
            onChange={e => setCmd(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && cmd && onModify(cmd)}
          />
          <button id="modify-submit" className="btn btn-primary btn-sm" disabled={!cmd || modifying} onClick={() => onModify(cmd)}>
            {modifying ? <Spinner /> : '↵'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Modify diff panel ─────────────────────────────────── */
function ModifyResult({ result }) {
  if (!result) return null;
  const { note, changed, delta, before, after } = result;

  return (
    <div className="card">
      <div className="card-title">Modification Result</div>
      <div className="text-sm" style={{ marginBottom: 8, color: changed ? 'var(--emerald)' : 'var(--amber)' }}>
        {changed ? '✓' : '⚠'} {note}
      </div>
      {changed && delta && (
        <div className="delta-card">
          <div className="delta-item">
            <div className="delta-label">Price change</div>
            <div className={`delta-value ${delta.price < 0 ? 'neg' : 'pos'}`}>
              {delta.price < 0 ? '−' : '+'}{formatINR(Math.abs(delta.price))}
            </div>
          </div>
          <div className="delta-item">
            <div className="delta-label">Margin change</div>
            <div className={`delta-value ${delta.margin > 0 ? 'neg' : 'pos'}`}>
              {delta.margin >= 0 ? '+' : '−'}{formatINR(Math.abs(delta.margin))}
            </div>
          </div>
          <div className="delta-item">
            <div className="delta-label">Before</div>
            <div className="delta-value" style={{ color: 'var(--text-secondary)', fontSize: '.9rem' }}>
              {formatINR(before?.pricing?.total)}
            </div>
          </div>
          <div className="delta-item">
            <div className="delta-label">After</div>
            <div className="delta-value" style={{ color: 'var(--text-primary)', fontSize: '.9rem' }}>
              {formatINR(after?.pricing?.total)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Copilot Chat page ─────────────────────────────────── */
const SAMPLE_QUERIES = [
  'Plan a 5-night Dubai trip for 2 adults, budget ₹1.5 lakh, 4-star hotel, balanced',
  '4 adults, Bangkok, 7 nights, ₹2 lakh, packed, cultural activities',
  'Relaxed 4 nights in Maldives for 2 adults, budget ₹3 lakh',
  '6 nights Japan for 3 adults, 1.4 lakh, packed, 4 star',
];

function CopilotPage() {
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      content: 'Hi! I\'m your TravClan Agent Copilot. Describe the trip your customer wants and I\'ll extract the requirements, rank matching hotels, and generate a full quote with itinerary.',
    },
  ]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [extraction, setExtraction] = useState(null);
  const [recs, setRecs]         = useState(null);
  const [selectedRec, setSelectedRec] = useState(null);
  const [quote, setQuote]       = useState(null);
  const [modifyResult, setModifyResult] = useState(null);
  const [modifying, setModifying] = useState(false);
  const [currentTrip, setCurrentTrip] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(scrollToBottom, [messages]);

  const addMsg = (role, content) => setMessages(m => [...m, { role, content }]);

  const handleSend = useCallback(async (text) => {
    const q = (text || input).trim();
    if (!q) return;
    setInput('');
    addMsg('user', q);
    setLoading(true);
    setRecs(null); setSelectedRec(null); setQuote(null); setModifyResult(null);

    try {
      // 1. Extract
      addMsg('ai', '🔍 Extracting requirements…');
      const ext = await api.extract(q);
      setExtraction(ext);

      const r = ext.requirement;
      const missing = ext.missing || [];
      const hasClarify = ext.clarifications?.length > 0;

      if (!r.destination || missing.includes('destination')) {
        setMessages(m => [...m.slice(0, -1), { role: 'ai', content: '⚠️ I couldn\'t detect a destination. Could you specify where your customer wants to travel?' }]);
        setLoading(false);
        return;
      }

      // 2. Recommend
      setMessages(m => [...m.slice(0, -1), {
        role: 'ai',
        content: `✓ Extracted: **${r.destination}**, ${r.nights || '?'} nights, ${formatINR(r.budget)}, ${r.travelers?.adults} adults.${hasClarify ? '\n⚠ Some details need clarification.' : ''}\n\n🏨 Finding best-matched hotels…`,
      }]);

      const recBody = { requirement: r, use_mmr: true, top_k: 5 };
      const recResult = await api.recommend(recBody);
      setRecs(recResult);

      if (!recResult.items?.length) {
        addMsg('ai', `❌ No hotels found matching the hard constraints (destination, stars, budget). ${recResult.message || ''}`);
        setLoading(false);
        return;
      }

      const top = recResult.items[0];
      setSelectedRec(top);

      // 3. Quote for top pick
      addMsg('ai', `✓ Found **${recResult.items.length}** matching hotels (${recResult.candidates_after_hard_filters} after hard filters). Generating quote for **${top.name}**…`);

      const trip = {
        requirement: r,
        hotel_id: top.hotel_id,
        activity_ids: [],
        transfer_type: 'private',
      };
      const q2 = await api.quote(trip);
      setQuote(q2);
      setCurrentTrip(trip);

      const ready = q2.ready_to_send;
      addMsg('ai',
        `✅ Quote ready for **${top.name}** (${top.star_rating}★, ${top.area}).\n` +
        `Total: **${formatINR(q2.pricing?.total)}** | Margin: **${formatINR(q2.pricing?.gross_margin)}**\n` +
        `${ready ? '🟢 Ready to send to customer.' : '🟡 Review validation issues before sending.'}\n\n` +
        `You can pick another hotel from the list or use the **Modify** panel to adjust the trip.`
      );
    } catch (e) {
      addMsg('ai', `❌ Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [input]);

  const handleSelectRec = useCallback(async (item) => {
    if (item.hotel_id === selectedRec?.hotel_id) return;
    setSelectedRec(item);
    setModifyResult(null);
    setLoading(true);
    addMsg('ai', `Switching to **${item.name}**…`);
    try {
      const trip = { requirement: extraction.requirement, hotel_id: item.hotel_id, activity_ids: [], transfer_type: 'private' };
      const q = await api.quote(trip);
      setQuote(q);
      setCurrentTrip(trip);
      addMsg('ai', `✓ Updated quote for **${item.name}**: **${formatINR(q.pricing?.total)}**`);
    } catch (e) {
      addMsg('ai', `❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [selectedRec, extraction]);

  const handleModify = useCallback(async (cmd) => {
    if (!currentTrip) return;
    setModifying(true);
    try {
      const result = await api.modify(currentTrip, cmd);
      setModifyResult(result);
      if (result.changed) {
        setQuote(result.after);
        setCurrentTrip(result.after?.trip);
      }
      addMsg('ai', `${result.changed ? '✓' : '⚠'} ${result.note}`);
    } catch (e) {
      addMsg('ai', `❌ ${e.message}`);
    } finally {
      setModifying(false);
    }
  }, [currentTrip]);

  return (
    <div className="chat-layout">
      {/* Left: Chat */}
      <div className="chat-panel">
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className={`msg-avatar ${m.role}`}>{m.role === 'ai' ? '✦' : 'A'}</div>
              <div className="msg-body">
                <div className="msg-sender">{m.role === 'ai' ? 'Copilot' : 'Agent'}</div>
                <div className="msg-bubble" style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="msg ai">
              <div className="msg-avatar ai">✦</div>
              <div className="msg-body">
                <div className="msg-sender">Copilot</div>
                <div className="msg-bubble"><Spinner /></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Sample queries */}
        {messages.length <= 2 && !loading && (
          <div style={{ padding: '0 20px 12px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {SAMPLE_QUERIES.map(q => (
              <button
                key={q}
                className="modify-chip"
                style={{ fontSize: '.75rem' }}
                onClick={() => handleSend(q)}
              >
                {q.slice(0, 50)}…
              </button>
            ))}
          </div>
        )}

        <div className="chat-input-bar">
          <textarea
            id="chat-input"
            className="chat-textarea"
            placeholder="Describe the customer's trip (destination, nights, budget, style)…"
            value={input}
            rows={1}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          />
          <button
            id="chat-send"
            className="btn btn-primary"
            disabled={!input.trim() || loading}
            onClick={() => handleSend()}
          >
            {loading ? <Spinner /> : 'Send'}
          </button>
        </div>
      </div>

      {/* Right: contextual panels */}
      <div className="right-panel">
        <ExtractionCard result={extraction} />

        {recs?.items?.length > 0 && (
          <div className="card">
            <div className="flex items-center justify-between mb-2">
              <div className="card-title">Hotel Recommendations</div>
              <span className="tag">{recs.items.length} results · {recs.latency_ms}ms</span>
            </div>
            <div className="rec-cards">
              {recs.items.map(item => (
                <RecCard
                  key={item.hotel_id}
                  item={item}
                  selected={selectedRec?.hotel_id === item.hotel_id}
                  onSelect={handleSelectRec}
                />
              ))}
            </div>
          </div>
        )}

        <ModifyResult result={modifyResult} />
        <QuotePanel quote={quote} onModify={handleModify} modifying={modifying} />
      </div>
    </div>
  );
}

/* ─── Destinations page ─────────────────────────────────── */
const DEST_EMOJI = {
  Dubai: '🏙', Japan: '🗾', Maldives: '🏝', Bali: '🌺', London: '🎡',
  Paris: '🗼', Bangkok: '🛺', Singapore: '🦁', 'New York': '🗽', Sydney: '🦘',
  Rome: '🏛', Amsterdam: '🌷', Istanbul: '🕌', Barcelona: '💃', Prague: '🏰',
  Vienna: '🎭', Athens: '🏺', Cairo: '🐫',
};

function DestinationsPage() {
  const [dests, setDests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.destinations()
      .then(d => { setDests(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <div className="loading-overlay"><Spinner /> Loading destinations…</div>;
  if (error)   return <div className="loading-overlay" style={{ color: 'var(--rose)' }}>❌ {error}</div>;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Destinations</h1>
        <p className="page-subtitle">{dests.length} destinations in inventory</p>
      </div>
      <div className="dest-grid">
        {dests.map(d => (
          <div key={d.name} id={`dest-${d.name?.replace(/\s/g,'-')}`} className="dest-card">
            <div className="dest-cover">{DEST_EMOJI[d.name] || '✈️'}</div>
            <div className="dest-info">
              <div className="dest-name">{d.name}</div>
              <div className="dest-meta">
                {d.country || d.region}
                {d.peak_season && ` · Peak: ${d.peak_season}`}
              </div>
              {d.tags && (
                <div className="flex gap-2 mt-1" style={{ flexWrap: 'wrap' }}>
                  {d.tags.slice(0, 3).map(t => <span key={t} className="tag">{t}</span>)}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

/* ─── Suppliers page ────────────────────────────────────── */
function SuppliersPage() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [selected, setSelected]   = useState(null);
  const [detail, setDetail]       = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    api.suppliers()
      .then(s => { setSuppliers(s); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const handleSelect = async (s) => {
    setSelected(s);
    setDetail(null);
    setDetailLoading(true);
    try {
      const d = await api.supplierHealth(s.id);
      setDetail(d);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) return <div className="loading-overlay"><Spinner /> Loading suppliers…</div>;
  if (error)   return <div className="loading-overlay" style={{ color: 'var(--rose)' }}>❌ {error}</div>;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Suppliers</h1>
        <p className="page-subtitle">{suppliers.length} suppliers · sorted by health score</p>
      </div>
      <div className="grid-2" style={{ gap: 20 }}>
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table className="supplier-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Health</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map(s => (
                <tr
                  key={s.id}
                  id={`supplier-${s.id}`}
                  style={{ cursor: 'pointer', background: selected?.id === s.id ? 'var(--indigo-subtle)' : undefined }}
                  onClick={() => handleSelect(s)}
                >
                  <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{s.name}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ color: s.health >= 80 ? 'var(--emerald)' : s.health >= 60 ? 'var(--amber)' : 'var(--rose)', fontWeight: 600 }}>
                        {s.health}
                      </span>
                      <div style={{ flex: 1, minWidth: 60 }}><HealthFill val={s.health} /></div>
                    </div>
                  </td>
                  <td>{s.type || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Detail panel */}
        <div className="card">
          {!selected && (
            <div className="empty-state">
              <div className="icon">🏢</div>
              <h3>Select a supplier</h3>
              <p>Click any supplier to see health metrics and risk flags</p>
            </div>
          )}
          {detailLoading && <div className="loading-overlay"><Spinner /></div>}
          {detail && !detailLoading && (
            <>
              <div className="card-title">Supplier Detail</div>
              <div className="font-semibold text-primary mb-2">{selected?.name}</div>
              <div className="flex items-center gap-3 mb-3">
                <span style={{ fontSize: '1.8rem', fontWeight: 700, color: detail.health >= 80 ? 'var(--emerald)' : detail.health >= 60 ? 'var(--amber)' : 'var(--rose)' }}>
                  {detail.health}
                </span>
                <div>
                  <div className="text-xs text-muted">Health Score</div>
                  <HealthFill val={detail.health} />
                </div>
              </div>
              {Object.entries(detail.metrics || {}).map(([k, v]) => (
                <div key={k} className="price-row">
                  <span className="label">{k.replace(/_/g, ' ')}</span>
                  <span className="amount">{typeof v === 'number' ? v.toFixed(1) : String(v)}</span>
                </div>
              ))}
              {detail.risks?.length > 0 && (
                <div className="mt-3">
                  <div className="card-title" style={{ color: 'var(--rose)' }}>Risk Flags</div>
                  <div className="validation-list">
                    {detail.risks.map((r, i) => (
                      <div key={i} className="val-item warn">
                        <span className="val-icon">⚠</span>
                        <div className="val-msg">{r}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {(!detail.risks || detail.risks.length === 0) && (
                <div className="val-item pass mt-2"><span className="val-icon">✓</span><div className="val-msg">No risk flags</div></div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

/* ─── Root App ──────────────────────────────────────────── */
export default function App() {
  const [page, setPage]   = useState('copilot');
  const [apiOk, setApiOk] = useState(null);

  useEffect(() => {
    api.health()
      .then(() => setApiOk(true))
      .catch(() => setApiOk(false));
  }, []);

  return (
    <div className="app-shell">
      <Topbar apiOk={apiOk} />
      <Sidebar page={page} setPage={setPage} />
      <main className="main-content">
        {page === 'copilot'      && <CopilotPage />}
        {page === 'destinations' && <DestinationsPage />}
        {page === 'suppliers'    && <SuppliersPage />}
      </main>
    </div>
  );
}
