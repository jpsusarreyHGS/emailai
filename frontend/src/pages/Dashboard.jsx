import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import HgsLogo from "../assets/HgsLogo.svg";
import EmailDetail from "../components/EmailDetail";
import EmailList from "../components/EmailList";
import { fetchEmailDoc, fetchEmailsByAgent, saveDraft, updateEmailTicket } from "../utils/api";
import "./Dashboard.css";

const ROSTER = {
  agent_001: { id: "agent_001", name: "Coach Gerver" },
  agent_002: { id: "agent_002", name: "Alice Thompson" },
  agent_003: { id: "agent_003", name: "Bob Hernandez" },
  agent_004: { id: "agent_004", name: "Cara Park" },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const selectedProfile = state?.profile || ROSTER.agent_001;

  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  // Function to refresh emails
  const refreshEmails = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Refreshing emails for agent:', selectedProfile.id);
      
      // Fetch emails assigned to this agent
      const agentEmails = await fetchEmailsByAgent(selectedProfile.id);
      
      console.log('Received emails:', agentEmails.length);
      
      // Transform backend email format to Dashboard format
      const transformedEmails = agentEmails.map((email, idx) => {
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
          id: email.id || `EML-${idx + 1}`,
          subject: email.subject || 'No Subject',
          from: {
            name: fromName,
            email: fromEmail
          },
          body: email.body?.content || email.body || '',
          attachments: email.attachments || [],
          received_at: email.receivedDateTime || new Date().toISOString(),
          messageId: email.id || `msg-${idx + 1}`,
          assignee: { id: selectedProfile.id, name: selectedProfile.name },
          tags: email.tags || [],
          ticket: email.ticket || 'new', // Default to 'new' if no ticket status
          labels: email.labels || null, // Include labels for category display
          hasAttachments: !!(email.attachments && email.attachments.length > 0)
        };
      });
      
      console.log('Transformed emails:', transformedEmails);
      setEmails(transformedEmails);
    } catch (err) {
      console.error('Failed to refresh emails:', err);
      setError(err.message);
      setEmails([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  // Fetch emails for the selected agent on component mount
  useEffect(() => {
    async function loadEmails() {
      try {
        setLoading(true);
        setError(null);
        
        console.log('Fetching emails for agent:', selectedProfile.id);
        
        // Fetch emails assigned to this agent
        const agentEmails = await fetchEmailsByAgent(selectedProfile.id);
        
        console.log('Received emails:', agentEmails.length);
        
        // Transform backend email format to Dashboard format
        const transformedEmails = agentEmails.map((email, idx) => {
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
            id: email.id || `EML-${idx + 1}`,
            subject: email.subject || 'No Subject',
            from: {
              name: fromName,
              email: fromEmail
            },
            body: email.body?.content || email.body || '',
            attachments: email.attachments || [],
            received_at: email.receivedDateTime || new Date().toISOString(),
            messageId: email.id || `msg-${idx + 1}`,
            assignee: { id: selectedProfile.id, name: selectedProfile.name },
            tags: email.tags || [],
            ticket: email.ticket || 'new', // Default to 'new' if no ticket status
            labels: email.labels || null, // Include labels for category display
            hasAttachments: !!(email.attachments && email.attachments.length > 0)
          };
        });
        
        console.log('Transformed emails:', transformedEmails);
        setEmails(transformedEmails);
      } catch (err) {
        console.error('Failed to load emails:', err);
        setError(err.message);
        setEmails([]); // Set empty array on error
      } finally {
        setLoading(false);
      }
    }
    
    loadEmails();
  }, [selectedProfile.id, selectedProfile.name]);

  // Split emails into three columns based on ticket field
  const newEmails = useMemo(() => {
    return emails.filter(email => email.ticket === 'new');
  }, [emails]);

  const openEmails = useMemo(() => {
    return emails.filter(email => email.ticket === 'open');
  }, [emails]);

  const closedEmails = useMemo(() => {
    return emails.filter(email => email.ticket === 'closed');
  }, [emails]);

  const handleOpenEmail = async (emailId) => {
    const email = emails.find(e => e.id === emailId);
    if (!email) return;

    // Immediately open the email detail view (no waiting)
    const doc = await fetchEmailDoc(email.id).catch(() => ({}));
    const atts = (doc.attachments || email.attachments || []).map((a, i) => ({
      sasUrl: a.blobPath || `mock/blob/${i}`,
      blob: a.blobPath || `mock/blob/${i}`,
      name: a.name || a.filename || a?.name || `attachment_${i}`,
      ocr: a.ocr || null,
    }));

    const ticket = {
      id: doc.id || email.id,
      email_id: doc.id || email.id,
      subject: doc.subject || email.subject,
      sender: email.from,
      received_at: doc.receivedDateTime || email.received_at,
      status: doc.ticket || "awaiting_review",
      email_body: doc.body?.content || doc.body || email.body,
      attachments: atts,
      extracted: { merchant: null, date: null, total: null, model: null, store_number: null },
      attachmentName: atts[0]?.name,
      scores: { confidence: 0, duplication: 0 },
      overall_confidence: doc.overall_confidence || 0,
      overall_duplication: doc.overall_duplication || 0,
      draft_reply: doc.draft_reply || { template: "response", body: "" },
      thread: [ { id: email.messageId, direction: "in", subject: email.subject, body: email.body, at: email.received_at } ],
      assignee: email.assignee,
      tags: email.tags || []
    };
    setSelected(ticket);

    // If this is a 'new' email, update its ticket status to 'open' in the background
    if (email.ticket === 'new') {
      // Fire and forget - don't await this call
      updateEmailTicket(emailId, 'open')
        .then(() => {
          console.log(`Successfully updated email ${emailId} ticket status to 'open'`);
          // Update the local state after the background call completes
          setEmails(prevEmails => 
            prevEmails.map(e => 
              e.id === emailId ? { ...e, ticket: 'open' } : e
            )
          );
        })
        .catch(error => {
          console.error('Failed to update email ticket status:', error);
        });
    }
  };

  const handleSave = async (ticketId, draftBody) => {
    try {
      // Update draft locally (backend draft save/send not implemented here)
      if (selected && selected.id === ticketId) {
        setSelected(prev => ({
          ...prev,
          draft_reply: { ...prev.draft_reply, body: draftBody }
        }));
      }

      // Persist draft to backend
      await saveDraft(ticketId, draftBody);

      // Refresh the email document to reflect persisted data
      const updated = await fetchEmailDoc(ticketId).catch(() => ({}));
      const atts = (updated.attachments || []).map((a, i) => ({
        sasUrl: a.blobPath || `mock/blob/${i}`,
        blob: a.blobPath || `mock/blob/${i}`,
        name: a.name || a.filename || `attachment_${i}`,
        ocr: a.ocr || null,
      }));
      setSelected(prev => ({
        ...prev,
        // extracted unchanged (read-only, controlled via Generate)
        attachments: atts,
      }));
    } catch (e) {
      console.error('Failed to save edits:', e);
      alert('Failed to save edits');
    }
  };

  const handleSend = (ticketId, draftBody) => {
    // For now, just close the detail view
    // In a real implementation, this would call an API to send the email
    setSelected(null);
  };

  const handleSimulateReply = (ticketId) => {
    // For now, just close the detail view
    // In a real implementation, this would simulate a customer reply
    setSelected(null);
  };

  const handleBackHome = () => setSelected(null);

  // Receive refreshed data from EmailDetail Generate flow
  const handleDetailRefresh = (freshDoc) => {
    console.log("Dashboard received refresh data:", freshDoc);
    setSelected(prev => ({
      ...prev,
      // Keep core ticket identity
      id: freshDoc.id || prev.id,
      email_id: freshDoc.id || prev.email_id,
      subject: freshDoc.subject || prev.subject,
      email_body: freshDoc.body?.content || freshDoc.body || prev.email_body,
          // Update visuals
          attachments: freshDoc.attachments || prev.attachments,
          extracted: freshDoc.extracted || prev.extracted,
          scores: freshDoc.scores || prev.scores,
          overall_confidence: freshDoc.overall_confidence || prev.overall_confidence,
          overall_duplication: freshDoc.overall_duplication || prev.overall_duplication,
      // Preserve draft body if provided
      draft_reply: freshDoc.draft_reply || prev.draft_reply,
    }));
  };

  const viewTitle = `${selectedProfile.name} Dashboard`;
  const roleSubtitle = `Agent ID: ${selectedProfile.id}`;

  return (
    <div className="dashboard">
      <div className="header">
        <div className="brand">
          <img className="logo" src={HgsLogo} alt="EmailAI logo" />
          <div>
            <div className="title">{viewTitle}</div>
            <div className="subtitle">{roleSubtitle}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className="btn secondary"
            onClick={refreshEmails}
            disabled={loading}
            style={{ 
              background: '#1976d2',
              color: 'white',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button className="btn secondary" onClick={() => navigate("/")}>
            ← Back to Home
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading emails...</div>
      ) : error ? (
        <div className="error">
          <p>Error loading emails: {error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      ) : !selected ? (
        <div className="board">
          <section className="column">
            <h2>New Emails ({newEmails.length})</h2>
            <EmailList
              items={newEmails.map(e => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from?.email || ""}>`,
                at: e.received_at,
                tags: e.tags,
                labels: e.labels,
                hasAttachments: e.hasAttachments
              }))}
              onOpen={handleOpenEmail}
            />
          </section>

          <section className="column">
            <h2>Open Emails ({openEmails.length})</h2>
            <EmailList
              items={openEmails.map(e => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from?.email || ""}>`,
                at: e.received_at,
                tags: e.tags,
                labels: e.labels,
                hasAttachments: e.hasAttachments
              }))}
              onOpen={handleOpenEmail}
            />
          </section>

          <section className="column">
            <h2>Closed Emails ({closedEmails.length})</h2>
            <EmailList
              items={closedEmails.map(e => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from?.email || ""}>`,
                at: e.received_at,
                tags: e.tags,
                labels: e.labels,
                hasAttachments: e.hasAttachments
              }))}
              onOpen={handleOpenEmail}
            />
          </section>
        </div>
      ) : (
        <main className="detail">
          <EmailDetail
            ticket={selected}
            onSave={handleSave}
            onSend={handleSend}
            onBack={handleBackHome}
            onSimReply={handleSimulateReply}
            onRefresh={handleDetailRefresh}
          />
        </main>
      )}
    </div>
  );
}