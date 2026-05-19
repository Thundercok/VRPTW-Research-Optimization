import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
  getFirestore,
  serverTimestamp,
  doc,
  setDoc,
  addDoc,
  collection,
  connectFirestoreEmulator // <-- ADDED THIS IMPORT
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";
// Native Auth Imports
import { getAuth, signInWithEmailAndPassword, connectAuthEmulator } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import { firebaseConfig, hasFirebaseConfig } from "./firebaseConfig.js";

class FirebaseService {
  constructor() {
    this.enabled = false;
    this.db = null;
    this.auth = null;
    this.userKey = null;

    // Initialize immediately so Auth is ready before Playwright clicks login
    if (hasFirebaseConfig()) {
      const app = getApps().length > 0 ? getApps()[0] : initializeApp(firebaseConfig);
      this.db = getFirestore(app);
      this.auth = getAuth(app);

      // Route Auth and Firestore traffic to the local emulators during local development/testing
      if (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") {
        connectAuthEmulator(this.auth, "http://127.0.0.1:9099", { disableWarnings: true });
        connectFirestoreEmulator(this.db, "127.0.0.1", 8080); // <-- ADDED THIS LINE
      }
    }
  }

  // NEW WRAPPER: Handles login natively inside the module
  async loginUser(email, password) {
    if (!this.auth) throw new Error("Firebase Auth is not initialized. Check your config.");
    const userCredential = await signInWithEmailAndPassword(this.auth, email, password);
    return userCredential.user;
  }

  async init(email) {
    if (!this.db) {
      this.enabled = false;
      return false;
    }

    this.userKey = this.makeUserKey(email);
    this.enabled = true;

    await setDoc(
      doc(this.db, "users", this.userKey),
      {
        email,
        lastLoginAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      },
      { merge: true }
    );

    return true;
  }

  makeUserKey(email) {
    return btoa(unescape(encodeURIComponent(email))).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  }

  async logEvent(type, meta = {}) {
    if (!this.enabled || !this.db || !this.userKey) return;
    try {
      await addDoc(collection(this.db, "users", this.userKey, "events"), {
        type,
        meta,
        createdAt: serverTimestamp()
      });
    } catch (error) {
      console.warn("firebase logEvent skipped:", error?.message || error);
    }
  }

  async saveJobStart(jobId, payload) {
    if (!this.enabled || !this.db || !this.userKey) return;
    try {
      await setDoc(
        doc(this.db, "users", this.userKey, "jobs", jobId),
        {
          jobId,
          status: "submitted",
          input: payload,
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp()
        },
        { merge: true }
      );
    } catch (error) {
      console.warn("firebase saveJobStart skipped:", error?.message || error);
    }
  }

  async saveJobResult(jobId, result) {
    if (!this.enabled || !this.db || !this.userKey) return;
    try {
      await setDoc(
        doc(this.db, "users", this.userKey, "jobs", jobId),
        {
          status: "done",
          output: this.toFirestoreSafe(result),
          updatedAt: serverTimestamp()
        },
        { merge: true }
      );
    } catch (error) {
      console.warn("firebase saveJobResult skipped:", error?.message || error);
    }
  }

  toFirestoreSafe(value) {
    if (Array.isArray(value)) {
      return value.map((item) => {
        if (Array.isArray(item)) {
          if (item.length === 2 && item.every((v) => typeof v === "number")) {
            return { lat: item[0], lng: item[1] };
          }
          return { items: this.toFirestoreSafe(item) };
        }
        return this.toFirestoreSafe(item);
      });
    }

    if (value && typeof value === "object") {
      const out = {};
      for (const [k, v] of Object.entries(value)) {
        out[k] = this.toFirestoreSafe(v);
      }
      return out;
    }

    return value;
  }
}

export const firebaseService = new FirebaseService();