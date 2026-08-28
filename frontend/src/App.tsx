import { Navigate, Route, Routes } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import { BusinessProfilePage } from "./pages/BusinessProfilePage";
import { ClientsPage } from "./pages/ClientsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ExpensesPage } from "./pages/ExpensesPage";
import { InvoiceCreatePage } from "./pages/InvoiceCreatePage";
import { InvoiceDetailPage } from "./pages/InvoiceDetailPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { InvoiceListPage } from "./pages/InvoiceListPage";
import { LoginPage } from "./pages/LoginPage";
import { RecurringInvoicesPage } from "./pages/RecurringInvoicesPage";
import { PublicInvoicePage } from "./pages/PublicInvoicePage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SharedReportPage } from "./pages/SharedReportPage";

function App() {
  const { loading } = useAuth();

  if (loading) return <div className="page-loading">Loading...</div>;

  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password/:uid/:token" element={<ResetPasswordPage />} />
        <Route path="/shared/:token" element={<SharedReportPage />} />
        <Route path="/pay/:token" element={<PublicInvoicePage />} />
        <Route path="/business-profile" element={<ProtectedRoute><BusinessProfilePage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/clients" element={<ProtectedRoute><ClientsPage /></ProtectedRoute>} />
        <Route path="/expenses" element={<ProtectedRoute><ExpensesPage /></ProtectedRoute>} />
        <Route path="/invoices" element={<ProtectedRoute><InvoiceListPage /></ProtectedRoute>} />
        <Route path="/invoices/new" element={<ProtectedRoute><InvoiceCreatePage /></ProtectedRoute>} />
        <Route path="/invoices/:id" element={<ProtectedRoute><InvoiceDetailPage /></ProtectedRoute>} />
        <Route path="/recurring-invoices" element={<ProtectedRoute><RecurringInvoicesPage /></ProtectedRoute>} />
        <Route path="/integrations" element={<ProtectedRoute><IntegrationsPage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </>
  );
}

export default App;
