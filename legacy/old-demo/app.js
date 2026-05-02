/**
 * VRPTW Visualization App
 */

// Global state
let map = null;
let currentInstance = null;
let currentRoutes = null;
let markers = [];
let routeLayers = [];
let coordinateBounds = null; // Store bounds for scaling

// Vehicle colors for visualization
const VEHICLE_COLORS = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
    '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52BE80',
    '#EC7063', '#5DADE2', '#58D68D', '#F4D03F', '#AF7AC5'
];

// Initialize map
function initMap() {
    // Start with a default view - will be adjusted when instance is loaded
    map = L.map('map').setView([50, 10], 6);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
}

// Convert Solomon coordinates (0-100) to a local map region
// We'll use a small region in Europe as the base
function solomonToLatLng(x, y, bounds) {
    // Use a fixed region in Europe (e.g., around Germany/Central Europe)
    // Base coordinates: lat 50-55, lng 5-15
    const baseLat = 50.0;
    const baseLng = 5.0;
    const latRange = 5.0;  // 5 degrees
    const lngRange = 10.0; // 10 degrees
    
    // Add small padding to bounds to avoid edge cases
    const padding = 1.0;
    const rangeX = (bounds.maxX - bounds.minX) || 1;
    const rangeY = (bounds.maxY - bounds.minY) || 1;
    
    // Normalize Solomon coordinates with padding
    const normX = ((x - bounds.minX) + padding) / (rangeX + 2 * padding);
    const normY = ((y - bounds.minY) + padding) / (rangeY + 2 * padding);
    
    // Clamp to [0, 1] to ensure no overflow
    const clampedX = Math.max(0, Math.min(1, normX));
    const clampedY = Math.max(0, Math.min(1, normY));
    
    // Map to lat/lng
    const lat = baseLat + clampedY * latRange;
    const lng = baseLng + clampedX * lngRange;
    
    return [lat, lng];
}

// Calculate bounds from instance
function calculateBounds(instance) {
    const allPoints = [instance.depot, ...instance.customers];
    const xs = allPoints.map(p => p.x);
    const ys = allPoints.map(p => p.y);
    
    return {
        minX: Math.min(...xs),
        maxX: Math.max(...xs),
        minY: Math.min(...ys),
        maxY: Math.max(...ys)
    };
}

// Show status message
function showStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
    
    if (type !== 'info') {
        setTimeout(() => {
            statusEl.className = 'status';
            statusEl.textContent = '';
        }, 5000);
    }
}

// Load Solomon instance
async function loadInstance(instanceName) {
    try {
        showStatus('Loading instance...', 'info');
        
        const response = await fetch(`data/${instanceName}.txt`);
        if (!response.ok) {
            throw new Error(`Failed to load instance: ${instanceName}`);
        }
        
        const content = await response.text();
        currentInstance = SolomonParser.parseSolomonFile(content);
        
        if (!currentInstance.depot || currentInstance.customers.length === 0) {
            throw new Error('Invalid instance format');
        }
        
        visualizeInstance(currentInstance);
        showInstanceInfo(currentInstance, instanceName);
        showStatus(`Loaded instance: ${instanceName}`, 'success');
        
        // Enable inference button
        document.getElementById('run-inference-btn').disabled = false;
        
    } catch (error) {
        console.error('Error loading instance:', error);
        showStatus(`Error: ${error.message}`, 'error');
        currentInstance = null;
        // Ensure inference button is disabled on error
        document.getElementById('run-inference-btn').disabled = true;
    }
}

// Visualize instance on map
function visualizeInstance(instance) {
    // Clear only visual elements, not the instance data
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    routeLayers.forEach(layer => map.removeLayer(layer));
    routeLayers = [];
    
    // Reset metrics display
    document.getElementById('total-distance').textContent = '-';
    document.getElementById('total-time').textContent = '-';
    document.getElementById('avg-distance').textContent = '-';
    document.getElementById('vehicles-used').textContent = '-';
    document.getElementById('customers-served').textContent = '-';
    document.getElementById('coverage').textContent = '-';
    
    // Calculate bounds for coordinate conversion
    coordinateBounds = calculateBounds(instance);
    
    // Convert all coordinates to calculate bounds for map fitting
    const allLatLngs = [
        solomonToLatLng(instance.depot.x, instance.depot.y, coordinateBounds),
        ...instance.customers.map(c => solomonToLatLng(c.x, c.y, coordinateBounds))
    ];
    
    // Fit map to show all points
    const bounds = L.latLngBounds(allLatLngs);
    map.fitBounds(bounds, { padding: [50, 50] });
    
    // Add depot marker (first point in allLatLngs)
    const depotLatLng = allLatLngs[0];
    const depotIcon = L.divIcon({
        className: 'depot-marker',
        html: '<div style="background-color: #ff0000; border: 3px solid white; border-radius: 50%; width: 20px; height: 20px;"></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });
    
    const depotMarker = L.marker(depotLatLng, { icon: depotIcon })
        .addTo(map)
        .bindPopup(`<b>Depot</b><br>ID: ${instance.depot.id}<br>Solomon: (${instance.depot.x}, ${instance.depot.y})`);
    
    markers.push(depotMarker);
    
    // Add customer markers (skip first point which is depot)
    instance.customers.forEach((customer, idx) => {
        const customerLatLng = allLatLngs[idx + 1];
        
        const customerIcon = L.divIcon({
            className: 'customer-marker',
            html: `<div style="background-color: #007bff; border: 2px solid white; border-radius: 50%; width: 12px; height: 12px;"></div>`,
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });
        
        const popupContent = `
            <b>Customer ${customer.id}</b><br>
            Demand: ${customer.demand}<br>
            Time Window: [${customer.readyTime}, ${customer.dueTime}]<br>
            Service Time: ${customer.serviceTime}<br>
            Solomon: (${customer.x}, ${customer.y})
        `;
        
        const customerMarker = L.marker(customerLatLng, { icon: customerIcon })
            .addTo(map)
            .bindPopup(popupContent);
        
        markers.push(customerMarker);
    });
}

// Visualize routes
function visualizeRoutes(routes, instance) {
    // Clear existing routes
    routeLayers.forEach(layer => map.removeLayer(layer));
    routeLayers = [];
    
    if (!routes || routes.length === 0) {
        showStatus('No routes to display', 'info');
        return;
    }
    
    if (!coordinateBounds) {
        coordinateBounds = calculateBounds(instance);
    }
    
    routes.forEach((route, vehicleIndex) => {
        if (route.length === 0) return;
        
        const color = VEHICLE_COLORS[vehicleIndex % VEHICLE_COLORS.length];
        
        // Create route path with converted coordinates
        const path = [instance.depot];
        
        route.forEach(customerId => {
            const customer = instance.customers.find(c => c.id === customerId);
            if (customer) {
                path.push(customer);
            }
        });
        
        path.push(instance.depot); // Return to depot
        
        // Convert to LatLng array using proper coordinate conversion
        const latlngs = path.map(p => solomonToLatLng(p.x, p.y, coordinateBounds));
        
        // Draw polyline with improved styling to reduce overlap
        const polyline = L.polyline(latlngs, {
            color: color,
            weight: 2.5,
            opacity: 0.65,
            smoothFactor: 1.0
        }).addTo(map);
        
        routeLayers.push(polyline);
        
        // Add vehicle number label only at first customer of each route
        if (route.length > 0) {
            const firstCustomerId = route[0];
            const firstCustomer = instance.customers.find(c => c.id === firstCustomerId);
            if (firstCustomer) {
                const firstCustomerLatLng = solomonToLatLng(firstCustomer.x, firstCustomer.y, coordinateBounds);
                const vehicleLabel = L.marker(firstCustomerLatLng, {
                    icon: L.divIcon({
                        className: 'vehicle-label',
                        html: `<div style="background-color: ${color}; color: white; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">V${vehicleIndex + 1}</div>`,
                        iconSize: [28, 28],
                        iconAnchor: [14, 14]
                    })
                }).addTo(map);
                
                routeLayers.push(vehicleLabel);
            }
        }
    });
    
    // Calculate and display metrics
    updateMetrics(routes, instance);
}

// Show instance information
function showInstanceInfo(instance, instanceName) {
    const infoPanel = document.getElementById('instance-info');
    if (instance) {
        document.getElementById('instance-name').textContent = instanceName.toUpperCase() || instance.name || '-';
        document.getElementById('total-customers').textContent = instance.customers.length;
        document.getElementById('vehicle-capacity').textContent = instance.vehicleCapacity || '-';
        infoPanel.style.display = 'block';
    } else {
        infoPanel.style.display = 'none';
    }
}

// Update metrics display
function updateMetrics(routes, instance) {
    let totalDistance = 0;
    let totalTime = 0;
    let vehiclesUsed = 0;
    let customersServed = new Set();
    
    routes.forEach(route => {
        if (route.length > 0) {
            vehiclesUsed++;
            totalDistance += SolomonParser.calculateRouteDistance(route, instance.depot, instance.customers);
            totalTime += SolomonParser.calculateRouteTime(route, instance.depot, instance.customers);
            route.forEach(customerId => customersServed.add(customerId));
        }
    });
    
    // Calculate additional metrics
    const avgDistance = vehiclesUsed > 0 ? (totalDistance / vehiclesUsed).toFixed(2) : '0.00';
    const coverage = instance.customers.length > 0 
        ? ((customersServed.size / instance.customers.length) * 100).toFixed(1) + '%'
        : '0%';
    
    document.getElementById('total-distance').textContent = totalDistance.toFixed(2);
    document.getElementById('total-time').textContent = totalTime.toFixed(2);
    document.getElementById('avg-distance').textContent = avgDistance;
    document.getElementById('vehicles-used').textContent = vehiclesUsed;
    document.getElementById('customers-served').textContent = customersServed.size;
    document.getElementById('coverage').textContent = coverage;
}

// Generate mock routes for testing
function generateMockRoutes(instance, numVehicles) {
    const routes = [];
    const customers = [...instance.customers];
    const customersPerVehicle = Math.ceil(customers.length / numVehicles);
    
    for (let i = 0; i < numVehicles; i++) {
        const route = [];
        const startIdx = i * customersPerVehicle;
        const endIdx = Math.min(startIdx + customersPerVehicle, customers.length);
        
        for (let j = startIdx; j < endIdx; j++) {
            route.push(customers[j].id);
        }
        
        routes.push(route);
    }
    
    return routes;
}

// Run inference (mock for now)
function runInference() {
    const inferenceBtn = document.getElementById('run-inference-btn');
    
    // Double check instance is loaded
    if (!currentInstance || !currentInstance.depot || !currentInstance.customers) {
        showStatus('Please load an instance first', 'error');
        inferenceBtn.disabled = true;
        return;
    }
    
    // Disable button during inference
    inferenceBtn.disabled = true;
    inferenceBtn.textContent = 'Running...';
    
    const numVehicles = parseInt(document.getElementById('num-vehicles').value) || 5;
    
    showStatus('Running inference...', 'info');
    
    // Simulate API call delay
    setTimeout(() => {
        // For now, use mock routes
        // TODO: Replace with actual API call to model
        currentRoutes = generateMockRoutes(currentInstance, numVehicles);
        visualizeRoutes(currentRoutes, currentInstance);
        showStatus('Inference completed', 'success');
        
        // Re-enable button
        inferenceBtn.disabled = false;
        inferenceBtn.textContent = 'Run Inference';
    }, 1000);
}

// Clear map
function clearMap() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    routeLayers.forEach(layer => map.removeLayer(layer));
    routeLayers = [];
    
    currentRoutes = null;
    currentInstance = null;
    coordinateBounds = null;
    
    // Hide instance info
    document.getElementById('instance-info').style.display = 'none';
    
    // Reset metrics
    document.getElementById('total-distance').textContent = '-';
    document.getElementById('total-time').textContent = '-';
    document.getElementById('avg-distance').textContent = '-';
    document.getElementById('vehicles-used').textContent = '-';
    document.getElementById('customers-served').textContent = '-';
    document.getElementById('coverage').textContent = '-';
    
    // Disable inference button
    document.getElementById('run-inference-btn').disabled = true;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    
    document.getElementById('load-instance-btn').addEventListener('click', () => {
        const instanceName = document.getElementById('instance-select').value;
        if (instanceName) {
            loadInstance(instanceName);
        } else {
            showStatus('Please select an instance', 'error');
        }
    });
    
    document.getElementById('run-inference-btn').addEventListener('click', runInference);
    
    document.getElementById('clear-btn').addEventListener('click', clearMap);
});

