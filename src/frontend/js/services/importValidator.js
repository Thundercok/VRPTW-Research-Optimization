import { timeToMinutes } from './modelMapper.js';

export function validateParsedImport(parsed) {
  const errors = [];

  if (!parsed.depot || !parsed.depot.address || !parsed.depot.address.trim()) {
    errors.push("Kho (Depot): Địa chỉ kho trống hoặc không tồn tại.");
  }

  if (!Array.isArray(parsed.customers) || parsed.customers.length === 0) {
    errors.push("Danh sách Khách hàng: Không có khách hàng nào được nhập.");
  } else {
    parsed.customers.forEach((cust, index) => {
      const idxStr = `Khách hàng #${index + 1}`;

      if (!cust.address || !cust.address.trim()) {
        errors.push(`${idxStr}: Thiếu địa chỉ giao hàng.`);
      }

      if (cust.demand === null || cust.demand === undefined || isNaN(cust.demand)) {
        errors.push(`${idxStr}: Thiếu khối lượng hàng hóa (demand).`);
      } else if (cust.demand < 0) {
        errors.push(`${idxStr}: Khối lượng hàng hóa không thể âm.`);
      }

      if (!cust.ready) {
        errors.push(`${idxStr}: Thiếu thời gian bắt đầu (ready time).`);
      }
      if (!cust.due) {
        errors.push(`${idxStr}: Thiếu thời gian kết thúc (due time).`);
      }

      if (cust.ready && cust.due) {
        const readyMin = timeToMinutes(cust.ready);
        const dueMin = timeToMinutes(cust.due);
        if (readyMin === null || isNaN(readyMin)) {
          errors.push(`${idxStr}: Định dạng thời gian bắt đầu '${cust.ready}' không hợp lệ (ví dụ: 08:00, 8h30).`);
        }
        if (dueMin === null || isNaN(dueMin)) {
          errors.push(`${idxStr}: Định dạng thời gian kết thúc '${cust.due}' không hợp lệ (ví dụ: 10:00, 10h).`);
        }
        if (readyMin !== null && dueMin !== null && !isNaN(readyMin) && !isNaN(dueMin) && dueMin <= readyMin) {
          errors.push(`${idxStr}: Thời gian kết thúc (${cust.due}) phải lớn hơn thời gian bắt đầu (${cust.ready}).`);
        }
      }
    });
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}
