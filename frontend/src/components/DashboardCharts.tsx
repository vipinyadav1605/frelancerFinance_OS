import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { getDashboardInsights } from "../api/endpoints";
import type { DashboardInsights } from "../types";

const PIE_COLORS = ["#1a2b4c", "#b9770e", "#1e8449", "#c0392b", "#6f95df", "#8e6bbf", "#2e8b8b"];

function money(amount: unknown) {
  return `₹${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 0 })}`;
}

export function DashboardCharts({ periodStart, periodEnd }: { periodStart: string; periodEnd: string }) {
  const [insights, setInsights] = useState<DashboardInsights | null>(null);

  useEffect(() => {
    getDashboardInsights(periodStart, periodEnd).then(setInsights).catch(() => {});
  }, [periodStart, periodEnd]);

  if (!insights) return null;

  const trendData = insights.monthly_revenue_trend.map((p) => ({
    month: p.month.slice(2), // "2026-06" -> "26-06", keeps axis labels short
    Income: Number(p.total_income),
    Expenses: Number(p.total_expense),
  }));
  const expenseData = insights.expense_breakdown.map((e) => ({ name: e.category, value: Number(e.total) }));
  const topClients = insights.top_clients.map((c) => ({ name: c.client_name, value: Number(c.total) }));

  return (
    <>
      <div className="card">
        <h3>Revenue Trend (last 12 months)</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="month" stroke="var(--grey)" fontSize={12} />
            <YAxis stroke="var(--grey)" fontSize={12} tickFormatter={(v) => money(v)} />
            <Tooltip formatter={(v: unknown) => money(v)} contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }} />
            <Legend />
            <Line type="monotone" dataKey="Income" stroke="var(--green)" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="Expenses" stroke="var(--red)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="dashboard-cards" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="card" style={{ marginBottom: 0 }}>
          <h3>Expense Breakdown</h3>
          {expenseData.length === 0 ? (
            <div className="empty-state">No expenses in this period.</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={expenseData} dataKey="value" nameKey="name" outerRadius={80} label={(d) => d.name}>
                  {expenseData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v: unknown) => money(v)} contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card" style={{ marginBottom: 0 }}>
          <h3>Top Clients</h3>
          {topClients.length === 0 ? (
            <div className="empty-state">No paid invoices in this period.</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={topClients} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis type="number" stroke="var(--grey)" fontSize={12} tickFormatter={(v) => money(v)} />
                <YAxis type="category" dataKey="name" stroke="var(--grey)" fontSize={12} width={90} />
                <Tooltip formatter={(v: unknown) => money(v)} contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }} />
                <Bar dataKey="value" fill="var(--navy)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </>
  );
}
