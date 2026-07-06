import { API_BASE } from '../constants.js';

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function geocodeAddress(address) {
  if (!address || !address.trim()) return null;

  const url = `${API_BASE}/geocode?q=${encodeURIComponent(address)}&limit=1`;
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Backend geocoder returned status: ${response.status}`);
    }

    const data = await response.json();
    if (data && Array.isArray(data.items) && data.items.length > 0) {
      return {
        lat: parseFloat(data.items[0].lat),
        lng: parseFloat(data.items[0].lng),
        address: data.items[0].address || address
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
