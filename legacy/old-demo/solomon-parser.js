/**
 * Solomon Benchmark Parser
 * Parses Solomon VRPTW benchmark format
 */

class SolomonParser {
    /**
     * Parse Solomon instance file
     * Format:
     * - Line 1-4: Problem name, vehicle info
     * - Line 5: CUST NO. XCOORD. YCOORD. DEMAND READY TIME DUE DATE SERVICE TIME
     * - Line 6+: Customer data
     */
    static parseSolomonFile(content) {
        const lines = content.trim().split('\n').map(line => line.trim());
        
        // Skip header lines 
        let dataStartIndex = 0;
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].includes('CUST NO.') || lines[i].match(/^\d+\s+[\d.]+/)) {
                dataStartIndex = i;
                break;
            }
        }
        
        const instance = {
            name: '',
            vehicleCapacity: 0,
            depot: null,
            customers: []
        };
        
        // Parse data lines
        for (let i = dataStartIndex; i < lines.length; i++) {
            const line = lines[i];
            if (!line || line.startsWith('CUST NO.')) continue;
            
            const parts = line.split(/\s+/).filter(p => p.length > 0);
            if (parts.length < 7) continue;
            
            const customer = {
                id: parseInt(parts[0]),
                x: parseFloat(parts[1]),
                y: parseFloat(parts[2]),
                demand: parseFloat(parts[3]),
                readyTime: parseFloat(parts[4]),
                dueTime: parseFloat(parts[5]),
                serviceTime: parseFloat(parts[6])
            };
            
            // First customer (id 0) is usually the depot
            if (customer.id === 0) {
                instance.depot = customer;
            } else {
                instance.customers.push(customer);
            }
        }
        
        // Try to extract vehicle capacity from header
        for (let i = 0; i < dataStartIndex; i++) {
            const line = lines[i];
            if (line.includes('CAPACITY') || line.includes('Capacity')) {
                const match = line.match(/(\d+)/);
                if (match) {
                    instance.vehicleCapacity = parseInt(match[1]);
                }
            }
            if (line && !instance.name) {
                instance.name = line;
            }
        }
        
        return instance;
    }
    
    /**
     * Calculate Euclidean distance between two points
     */
    static calculateDistance(point1, point2) {
        const dx = point1.x - point2.x;
        const dy = point1.y - point2.y;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    /**
     * Calculate total distance for a route
     */
    static calculateRouteDistance(route, depot, customers) {
        if (route.length === 0) return 0;
        
        let distance = 0;
        let current = depot;
        
        for (const customerId of route) {
            const customer = customers.find(c => c.id === customerId);
            if (customer) {
                distance += this.calculateDistance(current, customer);
                current = customer;
            }
        }
        
        // Return to depot
        distance += this.calculateDistance(current, depot);
        
        return distance;
    }
    
    /**
     * Calculate total time for a route (including service times)
     */
    static calculateRouteTime(route, depot, customers) {
        if (route.length === 0) return 0;
        
        let time = 0;
        let current = depot;
        
        for (const customerId of route) {
            const customer = customers.find(c => c.id === customerId);
            if (customer) {
                const travelTime = this.calculateDistance(current, customer);
                time += travelTime;
                time += customer.serviceTime;
                current = customer;
            }
        }
        
        // Return to depot
        time += this.calculateDistance(current, depot);
        
        return time;
    }
}

