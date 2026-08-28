import { lazy, Suspense, useEffect, useState } from "react";
import {
  createReportShareLink, deleteReportShareLink, downloadGstr1Export, downloadProfitLossExport,
  getGstr1Summary, getGstr3bSummary, getProfitLossReport, listReportShareLinks,
} from "../api/endpoints";
import { OnboardingChecklist } from "../components/OnboardingChecklist";
import { useToast } from "../context/ToastContext";
import type { Gstr1Summary, Gstr3bSummary, ProfitLossReport, ReportShareLink } from "../types";
import { extractErrorMessage } from "../utils/errors";

// recharts is the single largest dependency in this app - lazy-loaded so its
// ~250KB only loads once someone actually opens the Dashboard, not on every
// page (login, invoice list, etc. never need it).
const DashboardCharts = lazy(() => import("../components/DashboardCharts").then((m) => ({ default: m.DashboardCharts })));

function money(amount: string | number) {
  return `₹${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

function toISO(d: Date) {
  return d.toISOString().slice(0, 10);
}

function thisMonthRange() {
  const now = new Date();
  return { start: toISO(new Date(now.getFullYear(), now.getMonth(), 1)), end: toISO(new Date(now.getFullYear(), now.getMonth() + 1, 0)) };
}

function thisQuarterRange() {
  const now = new Date();
  const quarterStartMonth = Math.floor(now.getMonth() / 3) * 3;
  return { start: toISO(new Date(now.getFullYear(), quarterStartMonth, 1)), end: toISO(new Date(now.getFullYear(), quarterStartMonth + 3, 0)) };
}

function thisYearRange() {
  const now = new Date();
  return { start: toISO(new Date(now.getFullYear(), 0, 1)), end: toISO(new Date(now.getFullYear(), 11, 31)) };
}

type Preset = "month" | "quarter" | "year" | "custom";

export function DashboardPage() {
  const toast = useToast();
  const [preset, setPreset] = useState<Preset>("month");
  const [periodStart, setPeriodStart] = useState(thisMonthRange().start);
  const [periodEnd, setPeriodEnd] = useState(thisMonthRange().end);
  const [report, setReport] = useState<ProfitLossReport | null>(null);
  const [gstr1, setGstr1] = useState<Gstr1Summary | null>(null);
  const [gstr3b, setGstr3b] = useState<Gstr3bSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState<"csv" | "pdf" | null>(null);
  const [exportingGstr1, setExportingGstr1] = useState(false);

  const [shareLinks, setShareLinks] = useState<ReportShareLink[]>([]);
  const [shareLabel, setShareLabel] = useState("");
  const [shareExpiryDays, setShareExpiryDays] = useState(14);
  const [sharing, setSharing] = useState(false);
  const [shareError, setShareError] = useState("");

  function applyPreset(p: Preset) {
    setPreset(p);
    if (p === "month") { const r = thisMonthRange(); setPeriodStart(r.start); setPeriodEnd(r.end); }
    if (p === "quarter") { const r = thisQuarterRange(); setPeriodStart(r.start); setPeriodEnd(r.end); }
    if (p === "year") { const r = thisYearRange(); setPeriodStart(r.start); setPeriodEnd(r.end); }
  }

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      getProfitLossReport(periodStart, periodEnd),
      getGstr1Summary(periodStart, periodEnd),
      getGstr3bSummary(periodStart, periodEnd),
    ])
      .then(([reportData, gstr1Data, gstr3bData]) => { setReport(reportData); setGstr1(gstr1Data); setGstr3b(gstr3bData); })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the report.")))
      .finally(() => setLoading(false));
  }, [periodStart, periodEnd]);

  function loadShareLinks() {
    listReportShareLinks().then(setShareLinks);
  }

  useEffect(loadShareLinks, []);

  async function handleCreateShareLink() {
    setSharing(true);
    setShareError("");
    try {
      await createReportShareLink(periodStart, periodEnd, shareLabel, shareExpiryDays);
      setShareLabel("");
      loadShareLinks();
      toast.success("Share link created.");
    } catch (err) {
      setShareError(extractErrorMessage(err, "Could not create the share link."));
    } finally {
      setSharing(false);
    }
  }

  async function handleDeleteShareLink(id: number) {
    if (!confirm("Revoke this share link? It will stop working immediately.")) return;
    await deleteReportShareLink(id);
    loadShareLinks();
    toast.success("Share link revoked.");
  }

  function shareUrl(token: string) {
    return `${window.location.origin}/shared/${token}`;
  }

  async function copyShareUrl(token: string) {
    try {
      await navigator.clipboard.writeText(shareUrl(token));
      toast.success("Link copied to clipboard.");
    } catch {
      toast.error("Could not copy the link - your browser may be blocking clipboard access.");
    }
  }

  async function handleExport(format: "csv" | "pdf") {
    setExporting(format);
    try {
      await downloadProfitLossExport(periodStart, periodEnd, format);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not export the report."));
    } finally {
      setExporting(null);
    }
  }

  async function handleGstr1Export() {
    setExportingGstr1(true);
    try {
      await downloadGstr1Export(periodStart, periodEnd);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not export the GSTR-1 worksheet."));
    } finally {
      setExportingGstr1(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h1>Dashboard</h1>
          <p className="page-subtitle">Your profit, GST liability, and income tax estimate in one place.</p>
        </div>
        <div className="form-actions">
          <button className="btn btn-secondary" onClick={() => handleExport("csv")} disabled={exporting !== null}>
            {exporting === "csv" && <span className="btn-spinner" />}
            {exporting === "csv" ? "Exporting..." : "Export CSV"}
          </button>
          <button className="btn btn-secondary" onClick={() => handleExport("pdf")} disabled={exporting !== null}>
            {exporting === "pdf" && <span className="btn-spinner" />}
            {exporting === "pdf" ? "Exporting..." : "Export PDF"}
          </button>
        </div>
      </div>

      <OnboardingChecklist />

      <div className="filter-bar">
        <button className={`filter-chip ${preset === "month" ? "filter-chip-active" : ""}`} onClick={() => applyPreset("month")}>This Month</button>
        <button className={`filter-chip ${preset === "quarter" ? "filter-chip-active" : ""}`} onClick={() => applyPreset("quarter")}>This Quarter</button>
        <button className={`filter-chip ${preset === "year" ? "filter-chip-active" : ""}`} onClick={() => applyPreset("year")}>This Year</button>
        <input type="date" value={periodStart} onChange={(e) => { setPreset("custom"); setPeriodStart(e.target.value); }} />
        <span style={{ alignSelf: "center", color: "var(--grey)" }}>to</span>
        <input type="date" value={periodEnd} onChange={(e) => { setPreset("custom"); setPeriodEnd(e.target.value); }} />
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading || !report ? (
        <div className="page-loading"><span className="spinner-lg" /> Loading...</div>
      ) : (
        <>
          <div className="dashboard-cards">
            <div className="card dashboard-card">
              <div className="dashboard-card-label">Total Income (excl. GST)</div>
              <div className="dashboard-card-value">{money(report.total_income)}</div>
            </div>
            <div className="card dashboard-card">
              <div className="dashboard-card-label">Total Expenses</div>
              <div className="dashboard-card-value">{money(report.total_expense)}</div>
            </div>
            <div className="card dashboard-card dashboard-card-highlight">
              <div className="dashboard-card-label">Net Profit</div>
              <div className="dashboard-card-value">{money(report.net_profit)}</div>
            </div>
          </div>

          <Suspense fallback={<div className="page-loading"><span className="spinner-lg" /> Loading charts...</div>}>
            <DashboardCharts periodStart={periodStart} periodEnd={periodEnd} />
          </Suspense>

          <div className="card">
            <h3>GST Estimate</h3>
            <p className="page-subtitle">Based on invoices paid in this period, minus GST you paid on expenses.</p>
            <div className="invoice-totals" style={{ marginLeft: 0, maxWidth: "100%" }}>
              <div><span>Output tax collected</span><span>{money(report.gst_output_tax)}</span></div>
              <div><span>Input tax credit (from expenses)</span><span>-{money(report.gst_input_tax_credit)}</span></div>
              <div className="invoice-total-final"><span>Estimated GST liability</span><span>{money(report.estimated_gst_liability)}</span></div>
            </div>
          </div>

          {gstr1 && (
            <div className="card">
              <div className="page-header-row">
                <div>
                  <h3>GSTR-1 Pre-fill Worksheet</h3>
                  <p className="page-subtitle">
                    Invoices issued this period, bucketed the way the GST portal expects &mdash; a
                    working paper to speed up manual filing, not a filed return.
                  </p>
                </div>
                <button className="btn btn-secondary" onClick={handleGstr1Export} disabled={exportingGstr1}>
                  {exportingGstr1 && <span className="btn-spinner" />}
                  {exportingGstr1 ? "Exporting..." : "Export CSV"}
                </button>
              </div>
              <div className="table-scroll" style={{ marginTop: "0.8rem" }}>
                <table className="data-table">
                  <thead>
                    <tr><th>Bucket</th><th>Invoices</th><th>Taxable Value</th><th>Tax</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>B2B (registered domestic)</td><td>{gstr1.b2b_totals.count}</td><td>{money(gstr1.b2b_totals.taxable_value)}</td><td>{money(gstr1.b2b_totals.tax_amount)}</td></tr>
                    <tr><td>B2C (unregistered domestic)</td><td>{gstr1.b2c_totals.count}</td><td>{money(gstr1.b2c_totals.taxable_value)}</td><td>{money(gstr1.b2c_totals.tax_amount)}</td></tr>
                    <tr><td>Exports (zero-rated under LUT)</td><td>{gstr1.exports_totals.count}</td><td>{money(gstr1.exports_totals.taxable_value)}</td><td>{money(gstr1.exports_totals.tax_amount)}</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {gstr3b && (
            <div className="card">
              <h3>GSTR-3B Summary</h3>
              <p className="page-subtitle">
                The self-assessed summary return, based on the same accrual-basis figures as the
                GSTR-1 worksheet above &mdash; a working paper, not a filed return.
              </p>
              <div className="table-scroll" style={{ marginTop: "0.8rem" }}>
                <table className="data-table">
                  <thead>
                    <tr><th>Section</th><th>Taxable Value</th><th>IGST</th><th>CGST</th><th>SGST</th></tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>3.1(a) Outward taxable supplies</td>
                      <td>{money(gstr3b.outward_taxable_supplies.taxable_value)}</td>
                      <td>{money(gstr3b.outward_taxable_supplies.integrated_tax)}</td>
                      <td>{money(gstr3b.outward_taxable_supplies.central_tax)}</td>
                      <td>{money(gstr3b.outward_taxable_supplies.state_tax)}</td>
                    </tr>
                    <tr>
                      <td>3.1(b) Outward zero-rated supplies (exports)</td>
                      <td>{money(gstr3b.outward_zero_rated_supplies.taxable_value)}</td>
                      <td>-</td><td>-</td><td>-</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="invoice-totals" style={{ marginLeft: 0, maxWidth: "100%", marginTop: "1rem" }}>
                <div><span>Eligible ITC (from expenses)</span><span>-{money(gstr3b.eligible_itc)}</span></div>
                {Number(gstr3b.itc_carried_forward) > 0 && (
                  <div><span>ITC carried forward</span><span>{money(gstr3b.itc_carried_forward)}</span></div>
                )}
                <div className="invoice-total-final"><span>Net tax payable</span><span>{money(gstr3b.net_tax_payable)}</span></div>
              </div>
            </div>
          )}

          <div className="card">
            <h3>Share with your CA</h3>
            <p className="page-subtitle">
              Create a read-only link to this exact report (P&amp;L + GSTR-1 + GSTR-3B) &mdash; no
              account needed to view it, and it expires automatically.
            </p>
            {shareError && <div className="alert alert-error">{shareError}</div>}
            <div className="form-row" style={{ alignItems: "flex-end" }}>
              <label style={{ flex: 2 }}>Label (optional)
                <input value={shareLabel} onChange={(e) => setShareLabel(e.target.value)} placeholder="e.g. For Ramesh, my CA" />
              </label>
              <label>Expires in
                <select value={shareExpiryDays} onChange={(e) => setShareExpiryDays(Number(e.target.value))}>
                  <option value={7}>7 days</option>
                  <option value={14}>14 days</option>
                  <option value={30}>30 days</option>
                  <option value={90}>90 days</option>
                </select>
              </label>
              <button className="btn btn-primary" onClick={handleCreateShareLink} disabled={sharing}>
                {sharing && <span className="btn-spinner" />}
                {sharing ? "Creating..." : "Create Link"}
              </button>
            </div>

            {shareLinks.length > 0 && (
              <div className="table-scroll" style={{ marginTop: "1rem" }}>
                <table className="data-table">
                  <thead><tr><th>Label</th><th>Period</th><th>Expires</th><th></th></tr></thead>
                  <tbody>
                    {shareLinks.map((link) => (
                      <tr key={link.id}>
                        <td>{link.label || "-"}</td>
                        <td>{link.period_start} to {link.period_end}</td>
                        <td>{new Date(link.expires_at).toLocaleDateString()}</td>
                        <td>
                          <button className="btn-link" onClick={() => copyShareUrl(link.token)}>Copy Link</button>
                          {" "}&middot;{" "}
                          <button className="btn-link" onClick={() => handleDeleteShareLink(link.id)}>Revoke</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <h3>Income Tax Estimate (44ADA)</h3>
            <p className="page-subtitle">
              Financial year {report.financial_year_start} to {report.financial_year_end} &mdash;
              {" "}<span className={`badge ${report.income_tax_detail.is_44ada_eligible ? "badge-green" : "badge-red"}`}>
                {report.income_tax_detail.is_44ada_eligible ? "44ADA eligible" : "Above 44ADA limit"}
              </span>
            </p>
            <div className="invoice-totals" style={{ marginLeft: 0, maxWidth: "100%" }}>
              <div><span>Gross receipts (full financial year)</span><span>{money(report.financial_year_gross_receipts)}</span></div>
              <div><span>Presumptive taxable income (50%)</span><span>{money(report.income_tax_detail.presumptive_taxable_income)}</span></div>
              {report.income_tax_detail.rebate_87a_applied && (
                <div><span>Section 87A rebate</span><span>Applied &mdash; tax reduced to nil</span></div>
              )}
              <div className="invoice-total-final"><span>Estimated income tax</span><span>{money(report.estimated_income_tax)}</span></div>
            </div>
            <div className="alert alert-info" style={{ marginTop: "0.9rem" }}>{report.income_tax_detail.disclaimer}</div>
          </div>
        </>
      )}
    </div>
  );
}
