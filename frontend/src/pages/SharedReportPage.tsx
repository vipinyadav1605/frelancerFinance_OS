import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSharedReport } from "../api/endpoints";
import type { SharedReport } from "../types";
import { extractErrorMessage } from "../utils/errors";

function money(amount: string | number) {
  return `₹${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

export function SharedReportPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<SharedReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    getSharedReport(token)
      .then(setData)
      .catch((err) => setError(extractErrorMessage(err, "This link is invalid or has expired.")))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="page-loading"><span className="spinner-lg" /> Loading...</div>;

  if (error || !data) {
    return (
      <div className="page">
        <div className="alert alert-error">{error || "This link is invalid or has expired."}</div>
      </div>
    );
  }

  const { report, gstr1_summary, gstr3b_summary } = data;

  return (
    <div className="page">
      <div className="page-header">
        <h1>{data.business_name || "Financial Report"}</h1>
        <p className="page-subtitle">
          {data.label && <>{data.label} &mdash; </>}
          Period {report.period_start} to {report.period_end} &mdash; shared read-only via Freelancer Finance OS
        </p>
      </div>

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

      <div className="card">
        <h3>GST Estimate</h3>
        <div className="invoice-totals" style={{ marginLeft: 0, maxWidth: "100%" }}>
          <div><span>Output tax collected</span><span>{money(report.gst_output_tax)}</span></div>
          <div><span>Input tax credit (from expenses)</span><span>-{money(report.gst_input_tax_credit)}</span></div>
          <div className="invoice-total-final"><span>Estimated GST liability</span><span>{money(report.estimated_gst_liability)}</span></div>
        </div>
      </div>

      <div className="card">
        <h3>GSTR-1 Pre-fill Summary</h3>
        <div className="table-scroll" style={{ marginTop: "0.8rem" }}>
          <table className="data-table">
            <thead><tr><th>Bucket</th><th>Invoices</th><th>Taxable Value</th><th>Tax</th></tr></thead>
            <tbody>
              <tr><td>B2B (registered domestic)</td><td>{gstr1_summary.b2b_totals.count}</td><td>{money(gstr1_summary.b2b_totals.taxable_value)}</td><td>{money(gstr1_summary.b2b_totals.tax_amount)}</td></tr>
              <tr><td>B2C (unregistered domestic)</td><td>{gstr1_summary.b2c_totals.count}</td><td>{money(gstr1_summary.b2c_totals.taxable_value)}</td><td>{money(gstr1_summary.b2c_totals.tax_amount)}</td></tr>
              <tr><td>Exports (zero-rated under LUT)</td><td>{gstr1_summary.exports_totals.count}</td><td>{money(gstr1_summary.exports_totals.taxable_value)}</td><td>{money(gstr1_summary.exports_totals.tax_amount)}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>GSTR-3B Summary</h3>
        <div className="table-scroll" style={{ marginTop: "0.8rem" }}>
          <table className="data-table">
            <thead><tr><th>Section</th><th>Taxable Value</th><th>IGST</th><th>CGST</th><th>SGST</th></tr></thead>
            <tbody>
              <tr>
                <td>3.1(a) Outward taxable supplies</td>
                <td>{money(gstr3b_summary.outward_taxable_supplies.taxable_value)}</td>
                <td>{money(gstr3b_summary.outward_taxable_supplies.integrated_tax)}</td>
                <td>{money(gstr3b_summary.outward_taxable_supplies.central_tax)}</td>
                <td>{money(gstr3b_summary.outward_taxable_supplies.state_tax)}</td>
              </tr>
              <tr>
                <td>3.1(b) Outward zero-rated supplies (exports)</td>
                <td>{money(gstr3b_summary.outward_zero_rated_supplies.taxable_value)}</td>
                <td>-</td><td>-</td><td>-</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="invoice-totals" style={{ marginLeft: 0, maxWidth: "100%", marginTop: "1rem" }}>
          <div><span>Eligible ITC (from expenses)</span><span>-{money(gstr3b_summary.eligible_itc)}</span></div>
          {Number(gstr3b_summary.itc_carried_forward) > 0 && (
            <div><span>ITC carried forward</span><span>{money(gstr3b_summary.itc_carried_forward)}</span></div>
          )}
          <div className="invoice-total-final"><span>Net tax payable</span><span>{money(gstr3b_summary.net_tax_payable)}</span></div>
        </div>
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
          <div className="invoice-total-final"><span>Estimated income tax</span><span>{money(report.estimated_income_tax)}</span></div>
        </div>
        <div className="alert alert-info" style={{ marginTop: "0.9rem" }}>{report.income_tax_detail.disclaimer}</div>
      </div>

      <p className="public-page-brand">
        Reporting by <a href="/">Freelancer Finance OS</a>
      </p>
    </div>
  );
}
