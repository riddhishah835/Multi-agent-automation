import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { LogsProvider } from './context/LogsContext';
import { UploadProvider } from './context/UploadContext';
import { SearchProvider } from './context/SearchContext';
import './styles/index.css';

function Root() {
  return (
    <SearchProvider>
      <App />
    </SearchProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <LogsProvider>
              <UploadProvider>
                <Root />
              </UploadProvider>
            </LogsProvider>
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
