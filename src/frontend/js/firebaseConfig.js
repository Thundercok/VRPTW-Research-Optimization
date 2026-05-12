export const firebaseConfig = {
  apiKey: "AIzaSyDN79GLbCxzim88cTw7LajhcmZT0UoM7P4",
  authDomain: "vrptw-54d81.firebaseapp.com",
  projectId: "vrptw-54d81",
  storageBucket: "vrptw-54d81.firebasestorage.app",
  messagingSenderId: "408665257538",
  appId: "1:408665257538:web:041d814fbcab593e625fdb"
};

export function hasFirebaseConfig() {
  return Boolean(
    firebaseConfig.apiKey &&
    firebaseConfig.authDomain &&
    firebaseConfig.projectId &&
    firebaseConfig.appId
  );
}
