export function timeToMinutes(timeStr) {
  if (!timeStr) return null;
  const clean = timeStr.replace(/\s+/g, '').toLowerCase();
  let hours = 0;
  let minutes = 0;

  if (clean.includes('h')) {
    const match = clean.match(/^(\d{1,2})h(\d{2})?$/);
    if (match) {
      hours = parseInt(match[1], 10);
      minutes = match[2] ? parseInt(match[2], 10) : 0;
    } else {
      return null;
    }
  } else if (clean.includes(':')) {
    const match = clean.match(/^(\d{1,2}):(\d{2})$/);
    if (match) {
      hours = parseInt(match[1], 10);
      minutes = parseInt(match[2], 10);
    } else {
      return null;
    }
  } else {
    return null;
  }
  return hours * 60 + minutes;
}

export function normalizeTimeStr(timeStr) {
  if (!timeStr) return "";
  const minutes = timeToMinutes(timeStr);
  if (minutes === null || isNaN(minutes)) return "";
  const h = Math.floor(minutes / 60).toString().padStart(2, '0');
  const m = (minutes % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

export function buildInternalGeoModel(depotGeocoded, customersGeocoded) {
  const depot = {
    id: 0,
    address: depotGeocoded.address,
    lat: depotGeocoded.lat,
    lng: depotGeocoded.lng,
    demand: 0,
    ready: "00:00", // Depot open 24h
    due: "23:59",
    service_time: 0,
    isDepot: true,
    name: "Depot"
  };

  const customers = customersGeocoded.map((c, idx) => ({
    id: idx + 1,
    address: c.address,
    lat: c.lat,
    lng: c.lng,
    demand: parseInt(c.demand || 0, 10),
    ready: c.ready,
    due: c.due,
    service_time: 10, // default 10 minutes service time
    isDepot: false,
    name: `Customer #${idx + 1}`
  }));

  return [depot, ...customers];
}

export function buildSolverModel(geoModelPoints) {
  // Convert internal geo models to Point schema consumed by backend solver
  return geoModelPoints.map(p => ({
    id: p.id,
    name: p.name,
    address: p.address,
    lat: p.lat,
    lng: p.lng,
    demand: p.demand,
    isDepot: p.isDepot,
    ready: timeToMinutes(p.ready), // float/int minutes
    due: timeToMinutes(p.due),     // float/int minutes
    service: p.service_time        // service duration in minutes
  }));
}
