import { apiClient, tokenStorage } from "./client";
import type {
  ApiKey, ApiKeyCreated, AppNotification, BankStatementImport, BillingUsage, BusinessProfile,
  Client, DashboardInsights, Expense, ExpenseCategory, Gstr1Summary, Gstr3bSummary, InvoiceDetail, InvoiceListItem,
  InvoiceItemInput, InvoiceStatus, Currency, NotificationPreference, OnboardingStatus, Paginated,
  ProfitLossReport, PublicInvoice, RecurringInvoiceProfile, RecurringInvoiceItemInput,
  RecurringFrequency, ReferralStatus, ReportShareLink, SearchResult, SharedReport, TwoFactorSetup,
  TwoFactorStatus, User, WebhookEvent, WebhookSubscription,
} from "../types";

export async function login(email: string, password: string, otpCode?: string) {
  const { data } = await apiClient.post("/auth/login/", {
    email, password, ...(otpCode ? { otp_code: otpCode } : {}),
  });
  tokenStorage.set(data.access, data.refresh);
}

export async function loginWithGoogle(idToken: string) {
  const { data } = await apiClient.post("/auth/google/", { id_token: idToken });
  tokenStorage.set(data.access, data.refresh);
}

export async function loginWithMicrosoft(idToken: string) {
  const { data } = await apiClient.post("/auth/microsoft/", { id_token: idToken });
  tokenStorage.set(data.access, data.refresh);
}

export async function loginWithGitHub(code: string) {
  const { data } = await apiClient.post("/auth/github/", { code });
  tokenStorage.set(data.access, data.refresh);
}

export async function register(email: string, password: string, name: string, referredByCode?: string) {
  await apiClient.post("/auth/register/", { email, password, name, referred_by_code: referredByCode || "" });
}

export async function getReferralStatus(): Promise<ReferralStatus> {
  const { data } = await apiClient.get("/auth/referral/");
  return data;
}

export async function joinWaitlist(email: string): Promise<void> {
  await apiClient.post("/waitlist/", { email });
}

export async function logout() {
  const refresh = tokenStorage.getRefresh();
  if (refresh) {
    // Must run BEFORE clearing storage below - it needs the still-present
    // access token attached (via the request interceptor) to authenticate,
    // and blacklists the refresh token server-side so it can't be replayed.
    // Best-effort: if this fails (e.g. offline), the user is still logged
    // out locally once storage is cleared.
    try {
      await apiClient.post("/auth/logout/", { refresh });
    } catch {
      // ignore
    }
  }
  tokenStorage.clear();
}

export async function requestPasswordReset(email: string): Promise<void> {
  await apiClient.post("/auth/password-reset/", { email });
}

export async function confirmPasswordReset(uid: string, token: string, newPassword: string): Promise<void> {
  await apiClient.post("/auth/password-reset-confirm/", { uid, token, new_password: newPassword });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.post("/auth/change-password/", { current_password: currentPassword, new_password: newPassword });
}

export async function changeEmail(newEmail: string, currentPassword: string): Promise<User> {
  const { data } = await apiClient.post("/auth/change-email/", {
    new_email: newEmail, current_password: currentPassword,
  });
  return data;
}

export async function deleteAccount(currentPassword: string): Promise<void> {
  await apiClient.post("/auth/delete-account/", { current_password: currentPassword });
}

export async function getNotificationPreference(): Promise<NotificationPreference> {
  const { data } = await apiClient.get("/auth/notification-preference/");
  return data;
}

export async function updateNotificationPreference(prefs: NotificationPreference): Promise<NotificationPreference> {
  const { data } = await apiClient.put("/auth/notification-preference/", prefs);
  return data;
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const { data } = await apiClient.get("/auth/onboarding-status/");
  return data;
}

export async function downloadDataExport(): Promise<void> {
  const response = await apiClient.get("/auth/data-export/", { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = "freelancer-finance-os-export.zip";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export async function listNotifications(): Promise<AppNotification[]> {
  const { data } = await apiClient.get("/notifications/");
  return data;
}

export async function getUnreadNotificationCount(): Promise<number> {
  const { data } = await apiClient.get("/notifications/unread-count/");
  return data.unread_count;
}

export async function markNotificationRead(id: number): Promise<void> {
  await apiClient.post(`/notifications/${id}/mark-read/`);
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiClient.post("/notifications/mark-all-read/");
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get("/auth/me/");
  return data;
}

export async function getBusinessProfile(): Promise<BusinessProfile | null> {
  const { data } = await apiClient.get("/auth/business-profile/");
  return data;
}

export async function saveBusinessProfile(profile: Partial<BusinessProfile>): Promise<BusinessProfile> {
  const { data } = await apiClient.put("/auth/business-profile/", profile);
  return data;
}

export async function listClients(): Promise<Client[]> {
  const { data } = await apiClient.get("/clients/");
  return data;
}

export async function createClient(client: Partial<Client>): Promise<Client> {
  const { data } = await apiClient.post("/clients/", client);
  return data;
}

export async function updateClient(id: number, client: Partial<Client>): Promise<Client> {
  const { data } = await apiClient.put(`/clients/${id}/`, client);
  return data;
}

export async function listInvoices(
  filters: { status?: InvoiceStatus; client?: number; page?: number } = {}
): Promise<Paginated<InvoiceListItem>> {
  const { data } = await apiClient.get("/invoices/", { params: filters });
  return data;
}

export async function getInvoice(id: number): Promise<InvoiceDetail> {
  const { data } = await apiClient.get(`/invoices/${id}/`);
  return data;
}

export interface CreateInvoicePayload {
  client: number;
  issue_date: string;
  due_date: string;
  currency: Currency;
  exchange_rate_to_inr: string;
  items: InvoiceItemInput[];
}

export async function createInvoice(payload: CreateInvoicePayload): Promise<InvoiceDetail> {
  const { data } = await apiClient.post("/invoices/", payload);
  return data;
}

export async function sendInvoice(id: number): Promise<InvoiceDetail> {
  const { data } = await apiClient.post(`/invoices/${id}/send/`);
  return data;
}

export async function markInvoicePaid(id: number, amount: string, paymentDate: string): Promise<InvoiceDetail> {
  const { data } = await apiClient.post(`/invoices/${id}/mark-paid/`, {
    amount, payment_date: paymentDate,
  });
  return data;
}

export async function listExpenseCategories(): Promise<ExpenseCategory[]> {
  const { data } = await apiClient.get("/expense-categories/");
  return data;
}

export async function createExpenseCategory(name: string): Promise<ExpenseCategory> {
  const { data } = await apiClient.post("/expense-categories/", { name });
  return data;
}

export interface ExpenseFilters {
  category?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
}

export async function listExpenses(filters: ExpenseFilters = {}): Promise<Paginated<Expense>> {
  const { data } = await apiClient.get("/expenses/", { params: filters });
  return data;
}

export interface CreateExpensePayload {
  category: number;
  vendor_name: string;
  amount: string;
  gst_paid?: string;
  expense_date: string;
  notes?: string;
  receipt_file?: File;
}

export async function createExpense(payload: CreateExpensePayload): Promise<Expense> {
  const form = new FormData();
  form.append("category", String(payload.category));
  form.append("vendor_name", payload.vendor_name);
  form.append("amount", payload.amount);
  form.append("gst_paid", payload.gst_paid || "0");
  form.append("expense_date", payload.expense_date);
  if (payload.notes) form.append("notes", payload.notes);
  if (payload.receipt_file) form.append("receipt_file", payload.receipt_file);

  const { data } = await apiClient.post("/expenses/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteExpense(id: number): Promise<void> {
  await apiClient.delete(`/expenses/${id}/`);
}

export async function listBankStatementImports(): Promise<BankStatementImport[]> {
  const { data } = await apiClient.get("/bank-statement-imports/");
  return data;
}

export interface ImportCsvResult {
  import: BankStatementImport;
  expenses: Expense[];
}

export async function importBankStatementCsv(
  file: File, dateColumn: string, descriptionColumn: string, amountColumn: string
): Promise<ImportCsvResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("date_column", dateColumn);
  form.append("description_column", descriptionColumn);
  form.append("amount_column", amountColumn);

  const { data } = await apiClient.post("/expenses/import-csv/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getProfitLossReport(periodStart: string, periodEnd: string): Promise<ProfitLossReport> {
  const { data } = await apiClient.get("/reports/profit-loss/", {
    params: { period_start: periodStart, period_end: periodEnd },
  });
  return data;
}

/**
 * Report export requires the JWT Authorization header (unlike invoice PDFs,
 * which are public media file links) - so this fetches as a blob and
 * triggers a save via a temporary object URL, rather than a plain <a href>.
 */
export async function downloadProfitLossExport(
  periodStart: string, periodEnd: string, exportFormat: "csv" | "pdf"
): Promise<void> {
  const response = await apiClient.get("/reports/profit-loss/export/", {
    params: { period_start: periodStart, period_end: periodEnd, export_format: exportFormat },
    responseType: "blob",
  });
  const blobUrl = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `profit-loss_${periodStart}_to_${periodEnd}.${exportFormat}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export async function listApiKeys(): Promise<ApiKey[]> {
  const { data } = await apiClient.get("/api-keys/");
  return data;
}

export async function createApiKey(name: string): Promise<ApiKeyCreated> {
  const { data } = await apiClient.post("/api-keys/", { name });
  return data;
}

export async function revokeApiKey(id: number): Promise<void> {
  await apiClient.delete(`/api-keys/${id}/`);
}

export async function listWebhookSubscriptions(): Promise<WebhookSubscription[]> {
  const { data } = await apiClient.get("/webhooks/");
  return data;
}

export async function createWebhookSubscription(url: string, event: WebhookEvent): Promise<WebhookSubscription> {
  const { data } = await apiClient.post("/webhooks/", { url, event });
  return data;
}

export async function updateWebhookSubscription(id: number, is_active: boolean): Promise<WebhookSubscription> {
  const { data } = await apiClient.patch(`/webhooks/${id}/`, { is_active });
  return data;
}

export async function deleteWebhookSubscription(id: number): Promise<void> {
  await apiClient.delete(`/webhooks/${id}/`);
}

export async function listReportShareLinks(): Promise<ReportShareLink[]> {
  const { data } = await apiClient.get("/report-share-links/");
  return data;
}

export async function createReportShareLink(
  periodStart: string, periodEnd: string, label: string, expiresInDays: number
): Promise<ReportShareLink> {
  const { data } = await apiClient.post("/report-share-links/", {
    period_start: periodStart, period_end: periodEnd, label, expires_in_days: expiresInDays,
  });
  return data;
}

export async function deleteReportShareLink(id: number): Promise<void> {
  await apiClient.delete(`/report-share-links/${id}/`);
}

export async function getSharedReport(token: string): Promise<SharedReport> {
  const { data } = await apiClient.get(`/shared/report/${token}/`);
  return data;
}

export async function getExchangeRate(currency: Exclude<Currency, "INR">): Promise<string> {
  const { data } = await apiClient.get("/invoicing/exchange-rate/", { params: { currency } });
  return data.exchange_rate_to_inr as string;
}

export async function listRecurringInvoiceProfiles(): Promise<RecurringInvoiceProfile[]> {
  const { data } = await apiClient.get("/recurring-invoices/");
  return data;
}

export interface RecurringInvoiceProfilePayload {
  client: number;
  frequency: RecurringFrequency;
  currency: Currency;
  exchange_rate_to_inr: string;
  due_in_days: number;
  next_run_date: string;
  is_active: boolean;
  auto_send: boolean;
  items: RecurringInvoiceItemInput[];
}

export async function createRecurringInvoiceProfile(
  payload: RecurringInvoiceProfilePayload
): Promise<RecurringInvoiceProfile> {
  const { data } = await apiClient.post("/recurring-invoices/", payload);
  return data;
}

export async function updateRecurringInvoiceProfile(
  id: number, payload: Partial<RecurringInvoiceProfilePayload>
): Promise<RecurringInvoiceProfile> {
  const { data } = await apiClient.patch(`/recurring-invoices/${id}/`, payload);
  return data;
}

export async function deleteRecurringInvoiceProfile(id: number): Promise<void> {
  await apiClient.delete(`/recurring-invoices/${id}/`);
}

export async function getGstr1Summary(periodStart: string, periodEnd: string): Promise<Gstr1Summary> {
  const { data } = await apiClient.get("/reports/gstr1-prefill/", {
    params: { period_start: periodStart, period_end: periodEnd },
  });
  return data;
}

export async function downloadGstr1Export(periodStart: string, periodEnd: string): Promise<void> {
  const response = await apiClient.get("/reports/gstr1-prefill/export/", {
    params: { period_start: periodStart, period_end: periodEnd },
    responseType: "blob",
  });
  const blobUrl = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `gstr1-prefill_${periodStart}_to_${periodEnd}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export async function getGstr3bSummary(periodStart: string, periodEnd: string): Promise<Gstr3bSummary> {
  const { data } = await apiClient.get("/reports/gstr3b-summary/", {
    params: { period_start: periodStart, period_end: periodEnd },
  });
  return data;
}

export async function getDashboardInsights(periodStart: string, periodEnd: string): Promise<DashboardInsights> {
  const { data } = await apiClient.get("/reports/insights/", {
    params: { period_start: periodStart, period_end: periodEnd },
  });
  return data;
}

export async function globalSearch(query: string): Promise<SearchResult[]> {
  const { data } = await apiClient.get("/search/", { params: { q: query } });
  return data.results;
}

export async function getPublicInvoice(token: string): Promise<PublicInvoice> {
  const { data } = await apiClient.get(`/public/invoice/${token}/`);
  return data;
}

export async function get2faStatus(): Promise<TwoFactorStatus> {
  const { data } = await apiClient.get("/auth/2fa/status/");
  return data;
}

export async function start2faSetup(): Promise<TwoFactorSetup> {
  const { data } = await apiClient.post("/auth/2fa/setup/");
  return data;
}

export async function confirm2faSetup(code: string): Promise<void> {
  await apiClient.post("/auth/2fa/confirm/", { code });
}

export async function disable2fa(currentPassword: string): Promise<void> {
  await apiClient.post("/auth/2fa/disable/", { current_password: currentPassword });
}

export async function getBillingStatus(): Promise<BillingUsage> {
  const { data } = await apiClient.get("/billing/status/");
  return data;
}

export async function subscribeToPro(): Promise<{ short_url: string }> {
  const { data } = await apiClient.post("/billing/subscribe/");
  return data;
}

export async function cancelSubscription(): Promise<void> {
  await apiClient.post("/billing/cancel/");
}
