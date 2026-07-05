export function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const dLat = deg2rad(lat2 - lat1);
  const dLon = deg2rad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function deg2rad(deg) {
  return deg * (Math.PI / 180);
}

export async function fetchDistanceMatrix(points) {
  if (!Array.isArray(points) || points.length < 2) {
    return [[0.0]];
  }

  const coords = points.map(p => `${p.lng},${p.lat}`).join(';');
  const url = `https://router.project-osrm.org/table/v1/driving/${coords}?annotations=distance`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`OSRM table request failed with status: ${response.status}`);
    }
    const data = await response.json();
    if (Array.isArray(data.distances)) {
      // Convert OSRM meters to kilometers
      return data.distances.map(row => row.map(v => (v ?? 0.0) / 1000));
    }
    throw new Error("OSRM distances field was not found in response.");
  } catch (error) {
    console.warn("OSRM Table API call failed; falling back to Haversine calculations:", error);
    const matrix = [];
    for (let i = 0; i < points.length; i++) {
      const row = [];
      for (let j = 0; j < points.length; j++) {
        row.push(haversineDistance(points[i].lat, points[i].lng, points[j].lat, points[j].lng));
      }
      matrix.push(row);
    }
    return matrix;
  }
}
