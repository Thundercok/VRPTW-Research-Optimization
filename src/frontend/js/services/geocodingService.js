const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function geocodeAddress(address) {
  if (!address || !address.trim()) return null;

  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}&format=json&limit=1`;
  try {
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'VRPTW-Research-Optimization-App'
      }
    });

    if (!response.ok) {
      throw new Error(`Nominatim returned status: ${response.status}`);
    }

    const data = await response.json();
    if (Array.isArray(data) && data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
        address: data[0].display_name || address
      };
    }
    return null;
  } catch (error) {
    console.error(`Geocoding error for address [${address}]:`, error);
    return null;
  }
}

export async function geocodeBatch(addresses, onProgress) {
  const results = [];
  for (let i = 0; i < addresses.length; i++) {
    const addr = addresses[i];
    if (typeof onProgress === 'function') {
      onProgress(i, addresses.length, addr);
    }
    const res = await geocodeAddress(addr);
    results.push(res);
    // Respect Nominatim rate limit guidelines (max 1 request/sec)
    if (i < addresses.length - 1) {
      await delay(1000);
    }
  }
  return results;
}
