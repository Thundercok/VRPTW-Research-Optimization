import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
  getFirestore,
  serverTimestamp,
  doc,
  setDoc,
  addDoc,
  collection
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";

import { firebaseConfig, hasFirebaseConfig } from "./firebaseConfig.js";

class FirebaseService {
  constructor() {
    this.enabled = false;
    this.db = null;
    this.userKey = null;
  }

  async init(email) {
    if (!hasFirebaseConfig()) {
      this.enabled = false;
      return false;
    }

    const app = getApps().length > 0 ? getApps()[0] : initializeApp(firebaseConfig);
    this.db = getFirestore(app);
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
    return String(email || '').trim().toLowerCase();
  }

  async markLogout() {
    if (!this.enabled || !this.db || !this.userKey) return;
    try {
      await setDoc(
        doc(this.db, "users", this.userKey),
        {
          lastLogoutAt: serverTimestamp(),
          updatedAt: serverTimestamp()
        },
        { merge: true }
      );
    } catch (error) {
      console.warn("firebase markLogout skipped:", error?.message || error);
    }
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
