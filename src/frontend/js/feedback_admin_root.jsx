import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppContextProvider } from './context/AppContext.jsx';
import FeedbackAdminView from './components/FeedbackAdminView.jsx';
import ToastContainer from './components/ToastContainer.jsx';

function FeedbackAdminContent() {
  return (
    <>
      <FeedbackAdminView />
      <ToastContainer />
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <AppContextProvider>
    <FeedbackAdminContent />
  </AppContextProvider>
);
