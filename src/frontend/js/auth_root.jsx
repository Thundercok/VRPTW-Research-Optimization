import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppContextProvider } from './context/AppContext.jsx';
import AuthView from './components/AuthView.jsx';
import ToastContainer from './components/ToastContainer.jsx';

function AuthContent() {
  React.useEffect(() => {
    window.location.replace('app.html');
  }, []);

  return null;
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <AppContextProvider>
    <AuthContent />
  </AppContextProvider>
);
