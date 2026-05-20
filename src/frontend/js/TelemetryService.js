// js/TelemetryService.js
import { collection, onSnapshot } from "firebase/firestore";

export class TelemetryService {
    constructor(db, mapController) {
        this.db = db;
        this.map = mapController;
        this.unsubscribe = null;
    }

    // Subscribe to live vehicle movements in Firestore
    startStreaming() {
        if (!this.db) return;
        if (this.unsubscribe) return; // already streaming

        try {
            const vehiclesRef = collection(this.db, "vehicles");

            this.unsubscribe = onSnapshot(
                vehiclesRef,
                (snapshot) => {
                    snapshot.forEach((doc) => {
                        const data = doc.data();
                        this.map.updateVehicle(doc.id, data.lat, data.lng, data.status);
                    });
                },
                (error) => {
                    // Known: Firestore emulator gRPC-Web streaming triggers CORS errors.
                    // Silently degrade — telemetry is not critical for routing.
                    console.warn('[Telemetry] Firestore streaming error (safe to ignore on emulator):', error?.message || error);
                    this.stopStreaming();
                }
            );
        } catch (e) {
            console.warn('[Telemetry] Failed to start streaming:', e?.message || e);
        }
    }

    stopStreaming() {
        if (this.unsubscribe) {
            this.unsubscribe();
            this.unsubscribe = null;
        }
    }
}