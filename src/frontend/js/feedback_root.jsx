import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppContextProvider } from './context/AppContext.jsx';
import FeedbackView from './components/FeedbackView.jsx';
import ToastContainer from './components/ToastContainer.jsx';

function FeedbackContent() {
  return (
    <>
      <FeedbackView />
      <ToastContainer />
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <AppContextProvider>
    <FeedbackContent />
  </AppContextProvider>
);
