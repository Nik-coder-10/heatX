import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { ThemeProvider } from '@/hooks/useTheme';
import { AppStateProvider } from '@/store/AppState';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <AppStateProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AppStateProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
