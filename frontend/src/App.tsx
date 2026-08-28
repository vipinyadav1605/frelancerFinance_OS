import { Navigate, Route, Routes } from "react-router-dom";
import { Footer } from "./components/Footer";
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
import { GitHubCallbackPage } from "./pages/GitHubCallbackPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { InvoiceListPage } from "./pages/InvoiceListPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { PrivacyPolicyPage } from "./pages/PrivacyPolicyPage";
import { RecurringInvoicesPage } from "./pages/RecurringInvoicesPage";
import { PublicInvoicePage } from "./pages/PublicInvoicePage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SharedReportPage } from "./pages/SharedReportPage";
import { TermsOfServicePage } from "./pages/TermsOfServicePage";

function App() {
  const { loading } = useAuth();

  if (loading) return <div className="page-loading"><span className="spinner-lg" /> Loading...</div>;

  return (
    <div className="app-shell">
      <Navbar />
      <div className="app-content">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/terms" element={<TermsOfServicePage />} />
          <Route path="/privacy" element={<PrivacyPolicyPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/auth/github/callback" element={<GitHubCallbackPage />} />
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      <Footer />
    </div>
  );
}

export default App;
