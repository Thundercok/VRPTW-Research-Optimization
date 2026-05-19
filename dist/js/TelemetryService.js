// js/TelemetryService.js
import { collection, onSnapshot } from "firebase/firestore";

export class TelemetryService {
    constructor(db, mapController) {
        this.db = db;
        this.map = mapController;
    }

    // Subscribe to live vehicle movements in Firestore
    startStreaming() {
        const vehiclesRef = collection(this.db, "vehicles");

        onSnapshot(vehiclesRef, (snapshot) => {
            snapshot.forEach((doc) => {
                const data = doc.data();
                // Push the update to the map controller immediately
                this.map.updateVehicle(doc.id, data.lat, data.lng, data.status);
            });
        });
    }
}