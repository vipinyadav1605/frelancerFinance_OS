export interface User {
  id: number;
  email: string;
  name: string;
  has_business_profile: boolean;
}

export interface BusinessProfile {
  id: number;
  business_name: string;
  pan: string;
  gstin: string;
  is_gst_registered: boolean;
  address: string;
  state: string;
  invoice_prefix: string;
  lut_reference: string;
  email_signoff: string;
}

export interface NotificationPreference {
  payment_confirmation_emails: boolean;
  webhook_failure_emails: boolean;
}

export interface OnboardingStatus {
  has_business_profile: boolean;
  has_client: boolean;
  has_invoice: boolean;
  has_sent_invoice: boolean;
}

export type NotificationType =
  | "invoice_overdue" | "invoice_paid" | "recurring_invoice_generated" | "webhook_failed";

export interface AppNotification {
  id: number;
  notification_type: NotificationType;
  message: string;
  link_path: string;
  is_read: boolean;
  created_at: string;
}

export interface Client {
  id: number;
  name: string;
  email: string;
  billing_address: string;
  country: string;
  state: string;
  gstin: string;
  is_international: boolean;
}

export type InvoiceStatus = "draft" | "sent" | "paid" | "overdue";
export type Currency = "INR" | "USD" | "EUR" | "GBP";
export type TaxType = "CGST_SGST" | "IGST" | "EXPORT_ZERO_RATED";

export interface InvoiceItemInput {
  description: string;
  hsn_sac_code: string;
  quantity: string;
  unit_price: string;
  tax_rate_percent: string;
}

export interface InvoiceItem extends InvoiceItemInput {
  id: number;
  amount: string;
}

export interface Payment {
  id: number;
  amount: string;
  payment_date: string;
  method: "razorpay" | "manual";
  status: string;
}

export interface InvoiceListItem {
  id: number;
  invoice_number: string;
  client_name: string;
  issue_date: string;
  due_date: string;
  currency: Currency;
  total_amount: string;
  status: InvoiceStatus;
}

export interface ExpenseCategory {
  id: number;
  name: string;
  is_default: boolean;
}

export type ExpenseSource = "manual" | "csv_import";

export interface Expense {
  id: number;
  category: number;
  category_name: string;
  vendor_name: string;
  amount: string;
  gst_paid: string;
  expense_date: string;
  source: ExpenseSource;
  receipt_url: string | null;
  notes: string;
  created_at: string;
}

export type ImportStatus = "processing" | "completed" | "failed";

export interface BankStatementImport {
  id: number;
  file_name: string;
  status: ImportStatus;
  imported_count: number;
  skipped_count: number;
  error_message: string;
  imported_at: string;
}

export interface IncomeTaxDetail {
  gross_receipts: number;
  is_44ada_eligible: boolean;
  presumptive_taxable_income: number;
  rebate_87a_applied: boolean;
  base_tax: number;
  cess: number;
  estimated_total_tax: number;
  disclaimer: string;
}

export interface ProfitLossReport {
  period_start: string;
  period_end: string;
  total_income: string;
  total_expense: string;
  net_profit: string;
  gst_output_tax: string;
  gst_input_tax_credit: string;
  estimated_gst_liability: string;
  financial_year_start: string;
  financial_year_end: string;
  financial_year_gross_receipts: string;
  estimated_income_tax: string;
  income_tax_detail: IncomeTaxDetail;
  computed_at: string;
}

export type RecurringFrequency = "weekly" | "monthly" | "quarterly";

export interface RecurringInvoiceItemInput {
  description: string;
  hsn_sac_code: string;
  quantity: string;
  unit_price: string;
  tax_rate_percent: string;
}

export interface RecurringInvoiceProfile {
  id: number;
  client: number;
  client_name: string;
  frequency: RecurringFrequency;
  currency: Currency;
  exchange_rate_to_inr: string;
  due_in_days: number;
  next_run_date: string;
  is_active: boolean;
  auto_send: boolean;
  last_generated_invoice_number: string | null;
  items: RecurringInvoiceItemInput[];
  created_at: string;
}

export interface GstrBucketTotals {
  count: number;
  taxable_value: string;
  tax_amount: string;
  invoice_value: string;
}

export interface Gstr1Summary {
  period_start: string;
  period_end: string;
  b2b_totals: GstrBucketTotals;
  b2c_totals: GstrBucketTotals;
  exports_totals: GstrBucketTotals;
}

export interface Gstr3bSummary {
  period_start: string;
  period_end: string;
  outward_taxable_supplies: {
    taxable_value: string;
    integrated_tax: string;
    central_tax: string;
    state_tax: string;
  };
  outward_zero_rated_supplies: { taxable_value: string };
  eligible_itc: string;
  net_tax_payable: string;
  itc_carried_forward: string;
}

export interface ReferralStatus {
  referral_code: string;
  referral_count: number;
}

export interface ApiKey {
  id: number;
  name: string;
  display_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

export type WebhookEvent = "invoice.paid" | "invoice.overdue" | "expense.created";

export interface WebhookDelivery {
  id: number;
  event: string;
  status_code: number | null;
  success: boolean;
  error_message: string;
  created_at: string;
}

export interface WebhookSubscription {
  id: number;
  url: string;
  event: WebhookEvent;
  secret: string;
  is_active: boolean;
  created_at: string;
  recent_deliveries: WebhookDelivery[];
}

export interface ReportShareLink {
  id: number;
  token: string;
  period_start: string;
  period_end: string;
  label: string;
  expires_at: string;
  created_at: string;
}

export interface SharedReport {
  label: string;
  business_name: string;
  report: ProfitLossReport;
  gstr1_summary: {
    b2b_totals: GstrBucketTotals;
    b2c_totals: GstrBucketTotals;
    exports_totals: GstrBucketTotals;
  };
  gstr3b_summary: Gstr3bSummary;
}

export interface InvoiceDetail {
  id: number;
  invoice_number: string;
  client: number;
  client_name_snapshot: string;
  client_email_snapshot: string;
  client_address_snapshot: string;
  client_country_snapshot: string;
  client_gstin_snapshot: string;
  issue_date: string;
  due_date: string;
  currency: Currency;
  exchange_rate_to_inr: string;
  tax_type: TaxType;
  lut_reference: string;
  subtotal: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  total_amount: string;
  status: InvoiceStatus;
  payment_link_url: string;
  pdf_url: string | null;
  sent_at: string | null;
  paid_at: string | null;
  items: InvoiceItem[];
  payments: Payment[];
  public_view_token: string;
}

export interface PublicInvoice {
  invoice_number: string;
  business_name: string;
  business_gstin: string;
  client_name_snapshot: string;
  client_address_snapshot: string;
  client_country_snapshot: string;
  client_gstin_snapshot: string;
  issue_date: string;
  due_date: string;
  currency: Currency;
  tax_type: TaxType;
  lut_reference: string;
  subtotal: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  total_amount: string;
  status: InvoiceStatus;
  payment_link_url: string;
  pdf_url: string | null;
  items: InvoiceItem[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface SearchResult {
  type: "invoice" | "client";
  label: string;
  link_path: string;
}

export interface MonthlyRevenuePoint {
  month: string;
  total_income: string;
  total_expense: string;
}

export interface ExpenseBreakdownItem {
  category: string;
  total: string;
}

export interface TopClient {
  client_name: string;
  total: string;
}

export interface DashboardInsights {
  monthly_revenue_trend: MonthlyRevenuePoint[];
  expense_breakdown: ExpenseBreakdownItem[];
  top_clients: TopClient[];
}

export interface TwoFactorSetup {
  secret: string;
  otpauth_uri: string;
  qr_code_data_uri: string;
}

export interface TwoFactorStatus {
  is_enabled: boolean;
}

export interface BillingUsage {
  is_pro: boolean;
  invoices_this_month: number;
  free_tier_monthly_invoice_limit: number;
}
