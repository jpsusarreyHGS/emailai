import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import HgsLogo from "../assets/HgsLogo.svg";
import PaperclipIcon from "../assets/paperclip-icon.png";
import { categorizeEmails, fetchEmails, ingestEmails } from "../utils/api";
import "./Dashboard.css";

const ANALYSTS = [
  { id: "agent_001", name: "Coach Gerver", role: "Unlicensed Agent", tags: ["Endorsements", "Document Requests"] },
  { id: "agent_002", name: "Alice Thompson", role: "Unlicensed Agent", tags: ["Appetite", "Billing & Payments"] },
  { id: "agent_003",   name: "Bob Hernandez",   role: "Unlicensed Agent", tags: ["Customer Proof of Purchase"] },
  { id: "agent_004",  name: "Cara Park",  role: "Licensed Agent", tags: ["Underwriting"] },
];

const CATEGORY_LABELS = {
  appetite: "Appetite",
  billing: "Billing/Payment", 
  docRequest: "Document Request",
  endorsement: "Endorsement",
  underwriting: "Underwriting",
  receipt: "Proof of Purchase"
};

const SEED_EMAILS = [
  {
    id: "E-1001",
    subject: "Warranty Request: Broken TV Screen (ZX100)",
    from: { name: "Jane Doe", email: "jane@example.com" },
    body: "My ZX100 TV screen cracked during installation. Store: BB-0421",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: false
  },
  {
    id: "E-1002",
    subject: "Fridge appliance issue under warranty",
    from: { name: "Rina Park", email: "rina@example.com" },
    body: "Our kitchen fridge compressor failed. Need warranty service.",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: false
  },
  {
    id: "E-1003",
    subject: "Car insurance claim – help needed",
    from: { name: "Evan Lin", email: "evan@example.com" },
    body: "Please review my car insurance claim. Paperwork attached.",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: true
  },
  {
    id: "E-1004",
    subject: "QX55 soundbar receipt for warranty",
    from: { name: "Mark Lee", email: "mark@example.com" },
    body: "Re-sending clearer receipt for QX55 soundbar purchase.",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: true
  },
];


export default function SortBoard() {
  const navigate = useNavigate();
  const [emails, setEmails] = useState([]);
  const [categorizedEmails, setCategorizedEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sorting, setSorting] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(null);

  // Fetch emails from backend on component mount
  useEffect(() => {
    async function loadEmails() {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch both new emails (for incoming) and categorized emails (for agent assignments)
        const [newEmails, categorizedApiEmails] = await Promise.all([
          fetchEmails('new'),
          fetchEmails('categorized')
        ]);
        
        // Transform backend email format to SortBoard format
        const transformEmailData = (email, idx, isNewEmail = false) => {
          // Handle the emailAddress parsing - it might come as a string representation
          let fromName = 'Unknown';
          let fromEmail = 'unknown@example.com';
          
          if (email.from?.emailAddress) {
            if (typeof email.from.emailAddress === 'string') {
              // Parse string representation like "@{name=Nina Davis; address=nina.davis@example.com}"
              const nameMatch = email.from.emailAddress.match(/name=([^;]+)/);
              const emailMatch = email.from.emailAddress.match(/address=([^}]+)/);
              fromName = nameMatch ? nameMatch[1] : 'Unknown';
              fromEmail = emailMatch ? emailMatch[1] : 'unknown@example.com';
            } else {
              // Handle as object
              fromName = email.from.emailAddress.name || 'Unknown';
              fromEmail = email.from.emailAddress.address || 'unknown@example.com';
            }
          }
          
          return {
            id: email.id || `E-${idx + 1}`,
            subject: email.subject || 'No Subject',
            from: {
              name: fromName,
              email: fromEmail
            },
            body: email.body?.content || email.body || '',
            at: email.receivedDateTime || new Date().toISOString(),
            tags: email.tags || [],
            assignedTo: isNewEmail ? null : (email.assigned_agent || null), // New emails are unassigned, categorized emails keep assignment
            hasAttachments: email.hasAttachments || false,
            labels: email.labels || null, // Include labels for category display
            ticket: email.ticket || null
          };
        };
        
        // Transform both sets of emails with different assignment logic
        const transformedNewEmails = newEmails.map((email, idx) => transformEmailData(email, idx, true));
        const transformedCategorizedEmails = categorizedApiEmails.map((email, idx) => transformEmailData(email, idx, false));
        
        setEmails(transformedNewEmails);
        setCategorizedEmails(transformedCategorizedEmails);
      } catch (err) {
        console.error('Failed to load emails:', err);
        setError(err.message);
        // Fallback to seed emails
        setEmails(SEED_EMAILS);
        setCategorizedEmails([]);
      } finally {
        setLoading(false);
      }
    }
    
    loadEmails();
  }, []);

  const inboxEmails = useMemo(() => emails.filter(e => !e.assignedTo), [emails]);
  const byAssignee = useMemo(() => {
    // Create dynamic grouping based on ANALYSTS array and categorizedEmails
    const grouped = {};
    
    ANALYSTS.forEach(analyst => {
      // All agents see only their assigned emails
      grouped[analyst.id] = categorizedEmails.filter(e => e.assignedTo === analyst.id);
    });
    
    return grouped;
  }, [categorizedEmails]);

  // Calculate ticket counts for each agent
  const ticketCounts = useMemo(() => {
    const counts = {};
    
    ANALYSTS.forEach(analyst => {
      const agentEmails = categorizedEmails.filter(e => e.assignedTo === analyst.id);
      counts[analyst.id] = {
        new: agentEmails.filter(e => e.ticket === 'new').length,
        open: agentEmails.filter(e => e.ticket === 'open').length
      };
    });
    
    return counts;
  }, [categorizedEmails]);

  const handleFilterSort = async () => {
    try {
      setSorting(true);
      setError(null);
      
      // Call the categorize endpoint
      await categorizeEmails();
      
      // Refresh both new and categorized emails after categorization
      const [newEmails, categorizedApiEmails] = await Promise.all([
        fetchEmails('new'),
        fetchEmails('categorized')
      ]);
      
      // Transform email data
      const transformEmailData = (email, idx, isNewEmail = false) => {
        let fromName = 'Unknown';
        let fromEmail = 'unknown@example.com';
        
        if (email.from?.emailAddress) {
          if (typeof email.from.emailAddress === 'string') {
            const nameMatch = email.from.emailAddress.match(/name=([^;]+)/);
            const emailMatch = email.from.emailAddress.match(/address=([^}]+)/);
            fromName = nameMatch ? nameMatch[1] : 'Unknown';
            fromEmail = emailMatch ? emailMatch[1] : 'unknown@example.com';
          } else {
            fromName = email.from.emailAddress.name || 'Unknown';
            fromEmail = email.from.emailAddress.address || 'unknown@example.com';
          }
        }
        
        return {
          id: email.id || `E-${idx + 1}`,
          subject: email.subject || 'No Subject',
          from: { name: fromName, email: fromEmail },
          body: email.body?.content || email.body || '',
          at: email.receivedDateTime || new Date().toISOString(),
          tags: email.tags || [],
          assignedTo: isNewEmail ? null : (email.assigned_agent || null),
          hasAttachments: email.hasAttachments || false,
          labels: email.labels || null,
          ticket: email.ticket || null
        };
      };
      
      const transformedNewEmails = newEmails.map((email, idx) => transformEmailData(email, idx, true));
      const transformedCategorizedEmails = categorizedApiEmails.map((email, idx) => transformEmailData(email, idx, false));
      
      setEmails(transformedNewEmails);
      setCategorizedEmails(transformedCategorizedEmails);
      
    } catch (err) {
      console.error('Failed to categorize emails:', err);
      setError(`Failed to categorize emails: ${err.message}`);
    } finally {
      setSorting(false);
    }
  };

  const handleCheckInbox = async () => {
    try {
      setChecking(true);
      setError(null);
      
      // Call the ingest endpoint
      await ingestEmails();
      
      // Refresh only the incoming emails (new emails)
      const newEmails = await fetchEmails('new');
      
      // Transform new emails
      const transformEmailData = (email, idx) => {
        let fromName = 'Unknown';
        let fromEmail = 'unknown@example.com';
        
        if (email.from?.emailAddress) {
          if (typeof email.from.emailAddress === 'string') {
            const nameMatch = email.from.emailAddress.match(/name=([^;]+)/);
            const emailMatch = email.from.emailAddress.match(/address=([^}]+)/);
            fromName = nameMatch ? nameMatch[1] : 'Unknown';
            fromEmail = emailMatch ? emailMatch[1] : 'unknown@example.com';
          } else {
            fromName = email.from.emailAddress.name || 'Unknown';
            fromEmail = email.from.emailAddress.address || 'unknown@example.com';
          }
        }
        
        return {
          id: email.id || `E-${idx + 1}`,
          subject: email.subject || 'No Subject',
          from: { name: fromName, email: fromEmail },
          body: email.body?.content || email.body || '',
          at: email.receivedDateTime || new Date().toISOString(),
          tags: email.tags || [],
          assignedTo: null, // New emails are unassigned
          hasAttachments: email.hasAttachments || false,
          labels: email.labels || null,
          ticket: email.ticket || null
        };
      };
      
      const transformedNewEmails = newEmails.map(transformEmailData);
      setEmails(transformedNewEmails);
      
    } catch (err) {
      console.error('Failed to check inbox:', err);
      setError(`Failed to check inbox: ${err.message}`);
    } finally {
      setChecking(false);
    }
  };


  const handleRefreshEmails = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch both new and categorized emails
      const [newEmails, categorizedApiEmails] = await Promise.all([
        fetchEmails('new'),
        fetchEmails('categorized')
      ]);
      
      // Use the same transformation function
      const transformEmailData = (email, idx, isNewEmail = false) => {
        let fromName = 'Unknown';
        let fromEmail = 'unknown@example.com';
        
        if (email.from?.emailAddress) {
          if (typeof email.from.emailAddress === 'string') {
            const nameMatch = email.from.emailAddress.match(/name=([^;]+)/);
            const emailMatch = email.from.emailAddress.match(/address=([^}]+)/);
            fromName = nameMatch ? nameMatch[1] : 'Unknown';
            fromEmail = emailMatch ? emailMatch[1] : 'unknown@example.com';
          } else {
            fromName = email.from.emailAddress.name || 'Unknown';
            fromEmail = email.from.emailAddress.address || 'unknown@example.com';
          }
        }
        
        return {
          id: email.id || `E-${idx + 1}`,
          subject: email.subject || 'No Subject',
          from: { name: fromName, email: fromEmail },
          body: email.body?.content || email.body || '',
          at: email.receivedDateTime || new Date().toISOString(),
          tags: email.tags || [],
          assignedTo: isNewEmail ? null : (email.assigned_agent || null),
          hasAttachments: email.hasAttachments || false,
          labels: email.labels || null, // Include labels for category display
          ticket: email.ticket || null
        };
      };
      
      const transformedNewEmails = newEmails.map((email, idx) => transformEmailData(email, idx, true));
      const transformedCategorizedEmails = categorizedApiEmails.map((email, idx) => transformEmailData(email, idx, false));
      
      setEmails(transformedNewEmails);
      setCategorizedEmails(transformedCategorizedEmails);
    } catch (err) {
      console.error('Failed to refresh emails:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openBoard = (profileId) => {
    const p = ANALYSTS.find(a => a.id === profileId) || ANALYSTS[0];
    navigate("/board", { state: { profile: { id: p.id, name: p.name, role: p.role }, emails: categorizedEmails } });
  };

  return (
    <div className="dashboard" style={{ cursor: (loading || sorting || checking) ? 'wait' : 'default' }}>
      <div className="header">
        <div className="brand">
          <img className="logo" src={HgsLogo} alt="EmailAI logo" />
          <div>
            <div className="title">EmailAI</div>
            <div className="subtitle">Process incoming messages and access agent dashboards</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={handleRefreshEmails} 
            disabled={loading}
            className="btn secondary"
            style={{ 
              background: '#1976d2',
              color: 'white',
              cursor: loading ? 'wait' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="preboard">
        <section className="inbox">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <h2 style={{ margin: '0', fontSize: '1.3rem', fontWeight: '800', color: '#eef2f7' }}>
              Incoming Email
            </h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                className="btn" 
                onClick={handleCheckInbox} 
                disabled={loading || sorting || checking}
                style={{
                  cursor: checking ? 'wait' : (loading || sorting) ? 'not-allowed' : 'pointer'
                }}
              >
                {checking ? 'Checking Inbox...' : 'Check Inbox'}
              </button>
              <button 
                className={inboxEmails.length === 0 ? "btn gray" : "btn"} 
                onClick={handleFilterSort}
                disabled={loading || sorting || checking || inboxEmails.length === 0}
                style={{
                  cursor: sorting ? 'wait' : (loading || checking || inboxEmails.length === 0) ? 'not-allowed' : 'pointer'
                }}
              >
                {sorting ? 'Sorting...' : 'Sort'}
              </button>
            </div>
          </div>
          {loading ? (
            <div className="empty">Loading messages...</div>
          ) : sorting ? (
            <div className="empty">Sorting messages. This may take a few moments...</div>
          ) : checking ? (
            <div className="empty">Checking Outlook inbox for new messages. This may take a few moments...</div>
          ) : error ? (
            <div className="error">
              <p>Error loading emails: {error}</p>
              <button onClick={() => window.location.reload()}>Retry</button>
            </div>
          ) : (
            <ul className="list">
              {inboxEmails.map(e => (
                <li key={e.id} className="item slide-in">
                  <EmailRow email={e} />
                </li>
              ))}
              {inboxEmails.length === 0 && (
                <div className="empty">There are currently no new messages.</div>
              )}
            </ul>
          )}
        </section>

        <section className="profiles-grid">
          {ANALYSTS.map(p => (
            <div key={p.id} className="profile-card">
              <div className="profile-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div className="avatar">{p.name[0]}</div>
                  <div>
                    <div className="profile-name">{p.name}</div>
                    <div className="profile-role">{p.role}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {/* New tickets count */}
                  <div style={{
                    backgroundColor: '#2196F3',
                    color: 'white',
                    width: '48px',
                    height: '48px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    borderRadius: '6px'
                  }}>
                    <div>New</div>
                    <div>{ticketCounts[p.id]?.new || 0}</div>
                  </div>
                  {/* Open tickets count */}
                  <div style={{
                    backgroundColor: '#FF9800',
                    color: 'white',
                    width: '48px',
                    height: '48px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    borderRadius: '6px'
                  }}>
                    <div>Open</div>
                    <div>{ticketCounts[p.id]?.open || 0}</div>
                  </div>
                </div>
              </div>

              <div className="tag-row" style={{ margin: "8px 0 12px" }}>
                {p.tags.map((t,i)=><span key={i} className="pill tag">{t}</span>)}
              </div>

              <ul className="list compact">
                {(byAssignee[p.id] || []).slice(0, 2).map(e => (
                  <li key={e.id} className={`item fade-in`}>
                    <EmailRow email={e} compact />
                  </li>
                ))}
                {(!byAssignee[p.id] || byAssignee[p.id].length === 0) && (
                  <div className="empty">No assignments yet.</div>
                )}
              </ul>

              <button className="btn secondary" onClick={() => openBoard(p.id)} style={{ width:"100%", marginTop: 12 }}>
                Open Board as {p.name}
              </button>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

function EmailRow({ email, compact=false }) {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'space-between',
      width: '100%'
    }}>
      <div style={{ flex: 1 }}>
        <div className="title">{email.subject}</div>
        <div className="sub">
          {email.from?.name || ""} &lt;{email.from?.email}&gt;
        </div>
        <div className="meta-row">
          <span className="pill time">{new Date(email.at).toLocaleString()}</span>
          {!!(email.tags && email.tags.length) && (
            <span className="pill tagline">
              {email.tags.map((t,i)=><span key={i} className="pill tag">{t}</span>)}
            </span>
          )}
          {email.labels?.category && (
            <span className="pill tag" style={{ marginLeft: '8px' }}>
              {CATEGORY_LABELS[email.labels.category] || email.labels.category}
            </span>
          )}
        </div>
      </div>
      {email.hasAttachments && (
        <div style={{
          marginLeft: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <img 
            src={PaperclipIcon}
            alt="Has attachments"
            title="Has attachments"
            style={{ 
              width: '24px',
              height: '24px',
              opacity: 0.7
            }}
          />
        </div>
      )}
    </div>
  );
}

