// js/MapController.js
export class MapController {
    constructor(containerId) {
        this.map = L.map(containerId).setView([10.7626, 106.6602], 13); // HCMC coords

        // Use a clean, professional base layer (CartoDB Positron)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '© OpenStreetMap & CartoDB'
        }).addTo(this.map);

        this.vehicles = new Map(); // Store vehicle markers by ID
    }

    // Add or update a vehicle marker
    updateVehicle(id, lat, lng, status) {
        if (!this.vehicles.has(id)) {
            // Create new marker if it doesn't exist
            const marker = L.circleMarker([lat, lng], {
                color: status === 'danger' ? '#ef4444' : '#10b981',
                radius: 6,
                fillOpacity: 1
            }).addTo(this.map);
            this.vehicles.set(id, marker);
        } else {
            // Smoothly update location
            this.vehicles.get(id).setLatLng([lat, lng]);
        }
    }
}