export function normalizeTimeStr(timeStr) {
  if (!timeStr) return "";
  let clean = timeStr.trim().toLowerCase();
  clean = clean.replace(/\s+/g, '');
  
  // Check format like "8h30" or "8h"
  const hMatch = clean.match(/^(\d{1,2})h(\d{2})?$/);
  if (hMatch) {
    const hours = hMatch[1].padStart(2, '0');
    const minutes = (hMatch[2] || '00').padStart(2, '0');
    return `${hours}:${minutes}`;
  }
  
  // Check format like "8:30" or "08:30"
  const colonMatch = clean.match(/^(\d{1,2}):(\d{2})$/);
  if (colonMatch) {
    const hours = colonMatch[1].padStart(2, '0');
    const minutes = colonMatch[2];
    return `${hours}:${minutes}`;
  }
  return "";
}

export function parseNaturalText(text) {
  if (!text) return { depot: null, customers: [] };

  const lines = text.split('\n').map(line => line.trim()).filter(line => line.length > 0);
  
  let depotAddress = "";
  const customers = [];

  let currentCustomer = null;
  let parsingMode = "none"; // "depot" or "customers"

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check for Depot marker
    if (/^(kho|depot):/i.test(line)) {
      parsingMode = "depot";
      const match = line.match(/^(?:kho|depot):\s*(.+)$/i);
      if (match && match[1].trim()) {
        depotAddress = match[1].trim();
      }
      continue;
    }

    // Check for Customer marker
    if (/^(khách hàng|customers)$/i.test(line)) {
      parsingMode = "customers";
      continue;
    }

    // Check for numbered customer start (e.g. "1.", "1/", "[1]", etc.)
    const numStartMatch = line.match(/^\[?\d+\]?[\.\/\-]?$/);
    if (numStartMatch) {
      if (currentCustomer) {
        customers.push(currentCustomer);
      }
      currentCustomer = { address: "", demand: null, ready: "", due: "" };
      parsingMode = "customers";
      continue;
    }

    if (parsingMode === "depot") {
      // Append line to depot address unless we hit another marker
      if (/^(khách hàng|customers)$/i.test(line) || /^\[?\d+\]?[\.\/\-]?$/.test(line)) {
        parsingMode = "none";
        i--; // re-evaluate line
      } else {
        depotAddress = depotAddress ? `${depotAddress}, ${line}` : line;
      }
    } else if (parsingMode === "customers") {
      if (!currentCustomer) {
        currentCustomer = { address: "", demand: null, ready: "", due: "" };
      }

      // Address line
      if (/^(địa chỉ|address):\s*(.+)$/i.test(line)) {
        currentCustomer.address = line.match(/^(?:địa chỉ|address):\s*(.+)$/i)[1].trim();
      } else if (/^(địa chỉ|address):$/i.test(line)) {
        if (i + 1 < lines.length && !/^(khối lượng|demand|weight|thời gian|time|window):/i.test(lines[i + 1])) {
          currentCustomer.address = lines[i + 1].trim();
          i++;
        }
      }
      // Demand line
      else if (/^(khối lượng|demand|weight):\s*(.+)$/i.test(line)) {
        const demandText = line.match(/^(?:khối lượng|demand|weight):\s*(.+)$/i)[1].trim();
        const numMatch = demandText.match(/\d+/);
        if (numMatch) {
          currentCustomer.demand = parseInt(numMatch[0], 10);
        }
      } else if (/^(khối lượng|demand|weight):$/i.test(line)) {
        if (i + 1 < lines.length) {
          const numMatch = lines[i + 1].match(/\d+/);
          if (numMatch) {
            currentCustomer.demand = parseInt(numMatch[0], 10);
            i++;
          }
        }
      }
      // Time line
      else if (/^(thời gian|time|window):\s*(.+)$/i.test(line)) {
        const timeText = line.match(/^(?:thời gian|time|window):\s*(.+)$/i)[1].trim();
        const timeMatch = timeText.match(/(\d{1,2}h\d{2}|\d{1,2}h|\d{1,2}:\d{2})\s*-\s*(\d{1,2}h\d{2}|\d{1,2}h|\d{1,2}:\d{2})/i);
        if (timeMatch) {
          currentCustomer.ready = normalizeTimeStr(timeMatch[1]);
          currentCustomer.due = normalizeTimeStr(timeMatch[2]);
        }
      } else if (/^(thời gian|time|window):$/i.test(line)) {
        if (i + 1 < lines.length) {
          const timeMatch = lines[i + 1].match(/(\d{1,2}h\d{2}|\d{1,2}h|\d{1,2}:\d{2})\s*-\s*(\d{1,2}h\d{2}|\d{1,2}h|\d{1,2}:\d{2})/i);
          if (timeMatch) {
            currentCustomer.ready = normalizeTimeStr(timeMatch[1]);
            currentCustomer.due = normalizeTimeStr(timeMatch[2]);
            i++;
          }
        }
      }
    }
  }

  if (currentCustomer) {
    customers.push(currentCustomer);
  }

  // Final cleanup: filter out completely empty customers
  const filteredCustomers = customers.filter(c => c.address || c.demand !== null || c.ready || c.due);

  return {
    depot: depotAddress ? { address: depotAddress } : null,
    customers: filteredCustomers
  };
}
