const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000") + "/api/v1";

let apiAuthToken: string | null = null;

export function setApiAuthToken(token: string | null) {
  apiAuthToken = token;
}

async function securedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = options.headers ? { ...options.headers } as Record<string, string> : {};
  if (apiAuthToken) {
    headers["Authorization"] = `Bearer ${apiAuthToken}`;
  }
  return fetch(url, {
    ...options,
    headers,
  });
}

async function handleResponse(response: Response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Error del servidor: ${response.status}`);
  }
  return response.json();
}

export async function validateApiKey(apiKey: string, provider: string = "gemini") {
  const formData = new FormData();
  formData.append("api_key", apiKey);
  formData.append("provider", provider);

  const response = await securedFetch(`${API_URL}/validate-key`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function uploadFile(file: File, userId: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);

  const response = await securedFetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function analyzeData(query: string, apiKey: string, userId: string, chatId?: number, dataSourceId?: number, provider?: "gemini" | "mistral" | "hybrid", mistralKey?: string) {
  const formData = new FormData();
  formData.append("query", query);
  formData.append("api_key", apiKey);
  formData.append("user_id", userId);
  if (chatId) formData.append("chat_id", chatId.toString());
  if (dataSourceId) formData.append("data_source_id", dataSourceId.toString());
  if (provider) formData.append("provider", provider);
  if (mistralKey) formData.append("mistral_key", mistralKey);

  const response = await securedFetch(`${API_URL}/analyze`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function getHistory(userId: string) {
  const response = await securedFetch(`${API_URL}/history?user_id=${userId}`);
  return handleResponse(response);
}

export async function getChatDetails(chatId: number, userId: string) {
  const response = await securedFetch(`${API_URL}/history/${chatId}?user_id=${userId}`);
  return handleResponse(response);
}

export async function getDataSources(userId: string) {
  const response = await securedFetch(`${API_URL}/sources?user_id=${userId}`);
  return handleResponse(response);
}

export async function connectSql(url: string, userId: string) {
  const formData = new FormData();
  formData.append("url", url);
  formData.append("user_id", userId);

  const response = await securedFetch(`${API_URL}/connect-sql`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function connectGoogleSheets(url: string, userId: string) {
  const formData = new FormData();
  formData.append("url", url);
  formData.append("user_id", userId);

  const response = await securedFetch(`${API_URL}/connect-gsheets`, {
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

  const response = await securedFetch(`${API_URL}/dashboard/pin`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function pinCustomDashboardItem(userId: string, item: any) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("item_json", JSON.stringify(item));

  const response = await securedFetch(`${API_URL}/dashboard/pin-custom`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function getDashboard(userId: string) {
  const response = await securedFetch(`${API_URL}/dashboard?user_id=${userId}`);
  return handleResponse(response);
}

export async function filterDashboard(userId: string, filters: object) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("filters_json", JSON.stringify(filters));

  const response = await securedFetch(`${API_URL}/dashboard/filter`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function deleteDashboardItem(itemId: number, userId: string) {
  const response = await securedFetch(`${API_URL}/dashboard/${itemId}?user_id=${userId}`, {
    method: "DELETE",
  });
  return handleResponse(response);
}

export async function exportChartAsPng(figJson: any) {
  const response = await securedFetch(`${API_URL}/export/chart`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(figJson),
  });
  if (!response.ok) throw new Error("Error exportando imagen");
  return response.blob();
}

export async function generateReportSummary(query: string, apiKey: string, userId: string, provider?: "gemini" | "mistral" | "hybrid", mistralKey?: string) {
  const formData = new FormData();
  formData.append("query", query);
  formData.append("api_key", apiKey);
  formData.append("user_id", userId);
  if (provider) formData.append("provider", provider);
  if (mistralKey) formData.append("mistral_key", mistralKey);

  const response = await securedFetch(`${API_URL}/generate-report-summary`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function exportProfessionalReport(reportData: any) {
  const response = await securedFetch(`${API_URL}/export/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reportData),
  });
  if (!response.ok) throw new Error("Error exportando reporte profesional");
  return response.blob();
}

export async function exportProfessionalPptx(reportData: any) {
  const response = await securedFetch(`${API_URL}/export-pptx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reportData),
  });
  if (!response.ok) throw new Error("Error exportando PPTX profesional");
  return response.blob();
}

export async function generateAutoDashboard(apiKey: string, userId: string, dataSourceId?: number, chatId?: number, provider?: "gemini" | "mistral" | "hybrid", mistralKey?: string) {
  const formData = new FormData();
  formData.append("api_key", apiKey);
  formData.append("user_id", userId);
  if (dataSourceId) formData.append("data_source_id", dataSourceId.toString());
  if (chatId) formData.append("chat_id", chatId.toString());
  if (provider) formData.append("provider", provider);
  if (mistralKey) formData.append("mistral_key", mistralKey);

  const response = await securedFetch(`${API_URL}/auto-dashboard`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function suggestQuestions(userId: string, apiKey: string, dataSourceId?: number, chatId?: number, provider?: "gemini" | "mistral" | "hybrid", mistralKey?: string) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("api_key", apiKey);
  if (dataSourceId) formData.append("data_source_id", dataSourceId.toString());
  if (chatId) formData.append("chat_id", chatId.toString());
  if (provider) formData.append("provider", provider);
  if (mistralKey) formData.append("mistral_key", mistralKey);

  const response = await securedFetch(`${API_URL}/suggest-questions`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function removeSessionSource(userId: string, sourceId: number) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("source_id", sourceId.toString());

  const response = await securedFetch(`${API_URL}/remove-session-source`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function exportPdf(chatId: number, userId: string): Promise<Blob> {
  const response = await securedFetch(`${API_URL}/export/pdf/${chatId}?user_id=${userId}`);
  if (!response.ok) throw new Error("Error exportando PDF");
  return response.blob();
}

export async function exportSimulationPdf(simId: number, userId: string): Promise<Blob> {
  const response = await securedFetch(`${API_URL}/export/simulation/${simId}?user_id=${userId}`);
  if (!response.ok) throw new Error("Error exportando PDF de simulación");
  return response.blob();
}

export async function cleanData(userId: string, apiKey: string, dataSourceId?: number, chatId?: number, provider?: "gemini" | "mistral" | "hybrid", mistralKey?: string) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("api_key", apiKey);
  if (dataSourceId) formData.append("data_source_id", dataSourceId.toString());
  if (chatId) formData.append("chat_id", chatId.toString());
  if (provider) formData.append("provider", provider);
  if (mistralKey) formData.append("mistral_key", mistralKey);

  const response = await securedFetch(`${API_URL}/clean-data`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

// --- DATA SOURCES ---

export async function saveDataSource(userId: string, name: string, type: 'sql' | 'gsheets' | 'file', url: string, columns?: string[]) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("name", name);
  formData.append("type", type);
  formData.append("url", url);
  if (columns) formData.append("columns", JSON.stringify(columns));

  const response = await securedFetch(`${API_URL}/data-sources`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function deleteDataSource(sourceId: number, userId: string) {
  const response = await securedFetch(`${API_URL}/data-sources/${sourceId}?user_id=${userId}`, {
    method: "DELETE",
  });
  return handleResponse(response);
}

// --- SIMULATION (MIROFISH LITE) ---

export async function createSimulation(
  userId: string, 
  title: string, 
  hypothesis: string, 
  dataSourceId?: number, 
  apiKey?: string, 
  selectedIds?: number[], 
  provider: string = "gemini", 
  mistralKey?: string
) {
  const response = await securedFetch(`${API_URL}/simulation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userId: userId,
      title,
      hypothesis,
      dataSourceId,
      selectedIds: selectedIds,
      apiKey: apiKey,
      provider: provider,
      mistralKey: mistralKey
    }),
  });
  return handleResponse(response);
}

export async function getSimulationSuggestions(
  userId: string, 
  selectedIds: number[], 
  apiKey: string, 
  provider: string = "gemini", 
  mistralKey?: string
) {
  const response = await securedFetch(`${API_URL}/simulation/suggestions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userId: userId,
      selectedIds: selectedIds,
      apiKey: apiKey,
      provider: provider,
      mistralKey: mistralKey
    }),
  });
  return handleResponse(response);
}

export async function getSimulations(userId: string) {
  const response = await securedFetch(`${API_URL}/simulation/user/${userId}`);
  return handleResponse(response);
}

export async function getSimulationDetails(simId: number) {
  const response = await securedFetch(`${API_URL}/simulation/${simId}`);
  return handleResponse(response);
}

export async function getSimulationMessages(simId: number) {
  const response = await securedFetch(`${API_URL}/simulation/${simId}/messages`);
  return handleResponse(response);
}

export async function retrySimulation(simId: number) {
  const response = await securedFetch(`${API_URL}/simulation/${simId}/retry`, {
    method: "POST",
  });
  return handleResponse(response);
}

export async function generateVisualSummary(
  text: string,
  apiKey: string,
  userId: string,
  provider: string = "gemini",
  mistralKey?: string,
  visualType?: string,
  mode: string = "rapido"
) {
  const formData = new FormData();
  formData.append("text", text);
  formData.append("api_key", apiKey);
  formData.append("user_id", userId);
  formData.append("provider", provider);
  if (mistralKey) formData.append("mistral_key", mistralKey);
  if (visualType) formData.append("visual_type", visualType);
  formData.append("mode", mode);

  const response = await securedFetch(`${API_URL}/visual-summary`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

// --- USER CONFIG ENDPOINTS ---

export async function getUserConfig(userId: string) {
  const response = await securedFetch(`${API_URL}/user-config?user_id=${userId}`);
  return handleResponse(response);
}

export async function setUserConfig(
  userId: string,
  geminiKey?: string,
  mistralKey?: string,
  gammaKey?: string,
  preferredProvider?: string
) {
  const formData = new FormData();
  formData.append("user_id", userId);
  if (geminiKey !== undefined) formData.append("gemini_key", geminiKey);
  if (mistralKey !== undefined) formData.append("mistral_key", mistralKey);
  if (gammaKey !== undefined) formData.append("gamma_key", gammaKey);
  if (preferredProvider !== undefined) formData.append("preferred_provider", preferredProvider);

  const response = await securedFetch(`${API_URL}/user-config`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function clearSession(userId: string) {
  const formData = new FormData();
  formData.append("user_id", userId);

  const response = await securedFetch(`${API_URL}/clear-session`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}
