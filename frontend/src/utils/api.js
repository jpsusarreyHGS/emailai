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
