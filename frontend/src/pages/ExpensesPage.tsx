import { type FormEvent, useEffect, useState } from "react";
import {
  createExpense, createExpenseCategory, deleteExpense, importBankStatementCsv, listExpenseCategories,
  listExpenses, type ImportCsvResult,
} from "../api/endpoints";
import type { Expense, ExpenseCategory } from "../types";
import { extractErrorMessage } from "../utils/errors";

function money(amount: string) {
  return `₹${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

const emptyExpenseForm = { category: "", vendor_name: "", amount: "", gst_paid: "", expense_date: todayISO(), notes: "" };

export function ExpensesPage() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [showManualForm, setShowManualForm] = useState(false);
  const [form, setForm] = useState(emptyExpenseForm);
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [manualError, setManualError] = useState("");
  const [savingManual, setSavingManual] = useState(false);

  const [showImport, setShowImport] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [dateColumn, setDateColumn] = useState("");
  const [descriptionColumn, setDescriptionColumn] = useState("");
  const [amountColumn, setAmountColumn] = useState("");
  const [importError, setImportError] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportCsvResult | null>(null);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  function loadCategories() {
    listExpenseCategories().then(setCategories);
  }

  function loadExpenses() {
    setLoading(true);
    const filters: Record<string, string | number> = { page };
    if (categoryFilter) filters.category = categoryFilter;
    if (dateFrom) filters.date_from = dateFrom;
    if (dateTo) filters.date_to = dateTo;
    listExpenses(filters)
      .then((data) => {
        setExpenses(data.results);
        setCount(data.count);
        setHasNext(data.next !== null);
        setHasPrevious(data.previous !== null);
      })
      .finally(() => setLoading(false));
  }

  useEffect(loadCategories, []);
  useEffect(() => { setSelected(new Set()); loadExpenses(); }, [categoryFilter, dateFrom, dateTo, page]);

  function updateFilter(setter: (v: string) => void, value: string) {
    setter(value);
    setPage(1);
  }

  function toggleSelected(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelected((prev) => (prev.size === expenses.length ? new Set() : new Set(expenses.map((e) => e.id))));
  }

  async function handleBulkDelete() {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} expense(s)? This cannot be undone.`)) return;
    setBulkDeleting(true);
    try {
      await Promise.all(Array.from(selected).map((id) => deleteExpense(id)));
      setSelected(new Set());
      loadExpenses();
    } finally {
      setBulkDeleting(false);
    }
  }

  async function handleAddCategory() {
    if (!newCategoryName.trim()) return;
    const category = await createExpenseCategory(newCategoryName.trim());
    setCategories((prev) => [...prev, category].sort((a, b) => a.name.localeCompare(b.name)));
    setForm((f) => ({ ...f, category: String(category.id) }));
    setNewCategoryName("");
  }

  async function handleManualSubmit(e: FormEvent) {
    e.preventDefault();
    setManualError("");
    if (!form.category) { setManualError("Please select a category."); return; }
    setSavingManual(true);
    try {
      await createExpense({
        category: Number(form.category),
        vendor_name: form.vendor_name,
        amount: form.amount,
        gst_paid: form.gst_paid || "0",
        expense_date: form.expense_date,
        notes: form.notes || undefined,
        receipt_file: receiptFile ?? undefined,
      });
      setForm(emptyExpenseForm);
      setReceiptFile(null);
      setShowManualForm(false);
      loadExpenses();
    } catch (err) {
      setManualError(extractErrorMessage(err, "Could not save expense."));
    } finally {
      setSavingManual(false);
    }
  }

  function handleCsvFileSelect(file: File | null) {
    setCsvFile(file);
    setCsvHeaders([]);
    setImportResult(null);
    setImportError("");
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      const firstLine = text.split(/\r?\n/, 1)[0] ?? "";
      const headers = firstLine.split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
      setCsvHeaders(headers);
      setDateColumn(headers[0] ?? "");
      setDescriptionColumn(headers[1] ?? "");
      setAmountColumn(headers[2] ?? "");
    };
    reader.readAsText(file);
  }

  async function handleImportSubmit(e: FormEvent) {
    e.preventDefault();
    if (!csvFile) return;
    setImportError("");
    setImporting(true);
    try {
      const result = await importBankStatementCsv(csvFile, dateColumn, descriptionColumn, amountColumn);
      setImportResult(result);
      loadExpenses();
    } catch (err) {
      setImportError(extractErrorMessage(err, "Could not import this CSV file."));
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h1>Expenses</h1>
          <p className="page-subtitle">Track business expenses manually or import a bank/UPI statement CSV.</p>
        </div>
        <div className="form-actions">
          <button className="btn btn-secondary" onClick={() => { setShowImport((v) => !v); setShowManualForm(false); }}>
            Import CSV
          </button>
          <button className="btn btn-primary" onClick={() => { setShowManualForm((v) => !v); setShowImport(false); }}>
            + Add Expense
          </button>
        </div>
      </div>

      {showManualForm && (
        <form className="card form" onSubmit={handleManualSubmit}>
          {manualError && <div className="alert alert-error">{manualError}</div>}
          <label>Vendor
            <input value={form.vendor_name} onChange={(e) => setForm((f) => ({ ...f, vendor_name: e.target.value }))} required />
          </label>
          <div className="form-row">
            <label>Amount
              <input type="number" step="0.01" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} required />
            </label>
            <label>Date
              <input type="date" value={form.expense_date} onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))} required />
            </label>
            <label>GST paid (if any)
              <input type="number" step="0.01" value={form.gst_paid} onChange={(e) => setForm((f) => ({ ...f, gst_paid: e.target.value }))} placeholder="0.00" />
            </label>
          </div>
          <div className="form-row">
            <label>Category
              <select value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))} required>
                <option value="">Select category</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
            <label>Add new category
              <span className="form-inline" style={{ gap: "0.5rem" }}>
                <input value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} placeholder="e.g. Internet Bills" />
                <button type="button" className="btn btn-secondary" onClick={handleAddCategory}>Add</button>
              </span>
            </label>
          </div>
          <label>Notes
            <input value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
          </label>
          <label>Receipt (optional)
            <input type="file" onChange={(e) => setReceiptFile(e.target.files?.[0] ?? null)} />
          </label>
          <button className="btn btn-primary" type="submit" disabled={savingManual}>
            {savingManual ? "Saving..." : "Save Expense"}
          </button>
        </form>
      )}

      {showImport && (
        <form className="card form" onSubmit={handleImportSubmit}>
          {importError && <div className="alert alert-error">{importError}</div>}
          <label>Bank / UPI statement CSV
            <input type="file" accept=".csv" onChange={(e) => handleCsvFileSelect(e.target.files?.[0] ?? null)} required />
          </label>

          {csvHeaders.length > 0 && (
            <>
              <p className="page-subtitle">Match your file's columns to the fields we need:</p>
              <div className="form-row">
                <label>Date column
                  <select value={dateColumn} onChange={(e) => setDateColumn(e.target.value)}>
                    {csvHeaders.map((h) => <option key={h} value={h}>{h}</option>)}
                  </select>
                </label>
                <label>Description column
                  <select value={descriptionColumn} onChange={(e) => setDescriptionColumn(e.target.value)}>
                    {csvHeaders.map((h) => <option key={h} value={h}>{h}</option>)}
                  </select>
                </label>
                <label>Debit/withdrawal amount column
                  <select value={amountColumn} onChange={(e) => setAmountColumn(e.target.value)}>
                    {csvHeaders.map((h) => <option key={h} value={h}>{h}</option>)}
                  </select>
                </label>
              </div>
              <div className="alert alert-info">
                Use the debit/withdrawal column, not credit/deposit &mdash; only money going out is
                imported as an expense. Rows we can't read are skipped, not guessed.
              </div>
              <button className="btn btn-primary" type="submit" disabled={importing}>
                {importing ? "Importing..." : "Import"}
              </button>
            </>
          )}

          {importResult && (
            <div className="alert alert-success">
              Imported {importResult.import.imported_count} expense(s), skipped {importResult.import.skipped_count}{" "}
              row(s) we couldn't read. Categories were suggested automatically &mdash; edit any that look wrong.
            </div>
          )}
        </form>
      )}

      <div className="filter-bar">
        <select value={categoryFilter} onChange={(e) => updateFilter(setCategoryFilter, e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={(e) => updateFilter(setDateFrom, e.target.value)} title="From date" />
        <input type="date" value={dateTo} onChange={(e) => updateFilter(setDateTo, e.target.value)} title="To date" />
      </div>

      {selected.size > 0 && (
        <div className="bulk-toolbar">
          <span>{selected.size} selected</span>
          <button className="btn btn-secondary" onClick={handleBulkDelete} disabled={bulkDeleting} style={{ color: "var(--red)", borderColor: "var(--red)" }}>
            {bulkDeleting ? "Deleting..." : "Delete Selected"}
          </button>
        </div>
      )}

      {loading ? (
        <div className="page-loading">Loading...</div>
      ) : expenses.length === 0 ? (
        <div className="empty-state">No expenses yet. Add one manually or import a bank statement.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th><input type="checkbox" checked={selected.size === expenses.length} onChange={toggleSelectAll} /></th>
              <th>Date</th><th>Vendor</th><th>Category</th><th>Amount</th><th>GST Paid</th><th>Source</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((exp) => (
              <tr key={exp.id}>
                <td><input type="checkbox" checked={selected.has(exp.id)} onChange={() => toggleSelected(exp.id)} /></td>
                <td>{exp.expense_date}</td>
                <td>{exp.vendor_name}</td>
                <td>{exp.category_name}</td>
                <td>{money(exp.amount)}</td>
                <td>{money(exp.gst_paid)}</td>
                <td><span className={`badge ${exp.source === "manual" ? "badge-blue" : "badge-grey"}`}>{exp.source === "manual" ? "Manual" : "CSV"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!loading && count > 0 && (
        <div className="filter-bar" style={{ justifyContent: "space-between", marginTop: "1rem" }}>
          <span className="page-subtitle">{count} expense{count === 1 ? "" : "s"} total</span>
          <div className="form-actions">
            <button className="btn btn-secondary" disabled={!hasPrevious} onClick={() => setPage((p) => p - 1)}>Previous</button>
            <span className="page-subtitle" style={{ alignSelf: "center" }}>Page {page}</span>
            <button className="btn btn-secondary" disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
