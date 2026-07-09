import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Spinner } from '@/components/ui/Spinner';
import { Home } from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = lazy(() => import('@/pages/Dashboard'));
const SatelliteUpload = lazy(() => import('@/pages/SatelliteUpload'));
const LSTViewer = lazy(() => import('@/pages/LSTViewer'));
const SpectralIndices = lazy(() => import('@/pages/SpectralIndices'));
const UrbanHeatViewer = lazy(() => import('@/pages/UrbanHeatViewer'));
const Forecasting = lazy(() => import('@/pages/Forecasting'));
const Recommendations = lazy(() => import('@/pages/Recommendations'));
const ScenarioSimulator = lazy(() => import('@/pages/ScenarioSimulator'));
const ModelExplainability = lazy(() => import('@/pages/ModelExplainability'));
const Reports = lazy(() => import('@/pages/Reports'));
const Admin = lazy(() => import('@/pages/Admin'));

function App() {
  return (
    <Suspense fallback={<div className="h-screen flex items-center justify-center bg-surface-50"><Spinner size="lg" /></div>}>
      <Routes>
        <Route element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="satellite" element={<SatelliteUpload />} />
          <Route path="lst" element={<LSTViewer />} />
          <Route path="indices" element={<SpectralIndices />} />
          <Route path="uhi" element={<UrbanHeatViewer />} />
          <Route path="forecasting" element={<Forecasting />} />
          <Route path="recommendations" element={<Recommendations />} />
          <Route path="scenarios" element={<ScenarioSimulator />} />
          <Route path="xai" element={<ModelExplainability />} />
          <Route path="reports" element={<Reports />} />
          <Route path="admin" element={<Admin />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-6">
        <span className="text-2xl font-bold text-accent">404</span>
      </div>
      <h1 className="text-xl font-semibold text-text-primary mb-2">Page Not Found</h1>
      <p className="text-sm text-text-secondary mb-6 max-w-sm">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-surface-50 text-sm font-medium rounded-lg hover:bg-accent-hover transition-colors"
      >
        <Home className="h-4 w-4" /> Go Home
      </Link>
    </div>
  );
}

export default App;
