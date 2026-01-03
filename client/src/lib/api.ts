const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handleResponse(response: Response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Error del servidor: ${response.status}`);
  }
  return response.json();
}

export async function validateApiKey(apiKey: string) {
  const formData = new FormData();
  formData.append("api_key", apiKey);

  const response = await fetch(`${API_URL}/validate-key`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function uploadFile(file: File, userId: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);

  const response = await fetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function analyzeData(query: string, apiKey: string, userId: string, chatId?: number) {
  const formData = new FormData();
  formData.append("query", query);
  formData.append("api_key", apiKey);
  formData.append("user_id", userId);
  if (chatId) formData.append("chat_id", chatId.toString());

  const response = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function getHistory(userId: string) {
  const response = await fetch(`${API_URL}/history?user_id=${userId}`);
  return handleResponse(response);
}

export async function getChatDetails(chatId: number, userId: string) {
  const response = await fetch(`${API_URL}/history/${chatId}?user_id=${userId}`);
  return handleResponse(response);
}

export async function connectSql(url: string, userId: string) {
  const formData = new FormData();
  formData.append("url", url);
  formData.append("user_id", userId);

  const response = await fetch(`${API_URL}/connect-sql`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function connectGoogleSheets(url: string, userId: string) {
  const formData = new FormData();
  formData.append("url", url);
  formData.append("user_id", userId);

  const response = await fetch(`${API_URL}/connect-gsheets`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

// --- DASHBOARD & EXPORTS ---

export async function pinToDashboard(userId: string, chatId: number, messageId: number) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("chat_id", chatId.toString());
  formData.append("message_id", messageId.toString());

  const response = await fetch(`${API_URL}/dashboard/pin`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function getDashboard(userId: string) {
  const response = await fetch(`${API_URL}/dashboard?user_id=${userId}`);
  return handleResponse(response);
}

export async function deleteDashboardItem(itemId: number, userId: string) {
  const response = await fetch(`${API_URL}/dashboard/${itemId}?user_id=${userId}`, {
    method: "DELETE",
  });
  return handleResponse(response);
}

export async function exportChartAsPng(figJson: any) {
  const response = await fetch(`${API_URL}/export/chart`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(figJson),
  });
  if (!response.ok) throw new Error("Error exportando imagen");
  return response.blob();
}

export const getPdfExportUrl = (chatId: number, userId: string) => 
  `${API_URL}/export/pdf/${chatId}?user_id=${userId}`;
