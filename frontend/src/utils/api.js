const API_BASE_URL = 'http://localhost:7071/api';

export async function fetchEmails(status = null) {
  const url = status 
    ? `${API_BASE_URL}/emails?status=${status}`
    : `${API_BASE_URL}/emails`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch emails: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.emails || [];
}

export async function fetchEmailsByAgent(assignedAgent) {
  const url = `${API_BASE_URL}/emails?assigned_agent=${assignedAgent}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch emails for agent: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.emails || [];
}

export async function categorizeEmails() {
  const response = await fetch(`${API_BASE_URL}/emails/categorize`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to categorize emails: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data;
}

export async function ingestEmails() {
  const response = await fetch(`${API_BASE_URL}/emails/ingest`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to ingest emails: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data;
}
