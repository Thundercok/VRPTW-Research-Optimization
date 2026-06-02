export class TableController {
  constructor(app) {
    this.app = app;
    this.tableInputVisible = false;
    this.tableInputRefs = {};
  }

  wireEvents() {
    const el = this.app.el;
    el.addRow?.addEventListener('click', () => {
      this.tableInputVisible = true;
      this.render();
    });
    el.deleteSelected?.addEventListener('click', () => this.app.deleteSelectedCustomers());
    el.parsePaste?.addEventListener('click', () => this.parsePasteData());

    // Wire Excel logic
    el.pickExcel?.addEventListener('click', () => el.excelInput?.click());
    el.excelInput?.addEventListener('change', (e) => this.handleExcelFile(e));

    // Wire inline editing
    el.customerRows?.addEventListener('dblclick', (e) => {
      const cell = e.target.closest('td[data-editable="true"]');
      if (cell) this.startCustomerCellEdit(cell);
    });
  }

  render() {
    const el = this.app.el;
    this.tableInputRefs = {};
    el.customerRows.innerHTML = '';

    this.app.state.customers.forEach((c) => {
      const tr = document.createElement('tr');
      tr.dataset.customerId = String(c.id);

      tr.addEventListener('click', (e) => {
        if (!e.target.closest('input, [data-editable="true"]')) this.app.toggleCustomerSelection(c.id);
      });

      // Quick cell generator
      const makeCell = (val, editable, field) => {
        const td = document.createElement('td');
        td.textContent = val;
        if (editable) {
          td.dataset.editable = 'true';
          td.dataset.field = field;
          td.classList.add('cell-editable');
        }
        return td;
      };

      tr.appendChild(makeCell(this.app.selectedCustomerIds.has(c.id) ? '✓' : '○', false));
      tr.appendChild(makeCell(c.id, false));
      tr.appendChild(makeCell(c.name, true, 'name'));
      tr.appendChild(makeCell(c.address, true, 'address'));
      tr.appendChild(makeCell(Number(c.lat).toFixed(4), false));
      tr.appendChild(makeCell(Number(c.lng).toFixed(4), false));
      tr.appendChild(makeCell(c.demand, true, 'demand'));
      tr.appendChild(makeCell(c.ready, true, 'ready'));
      tr.appendChild(makeCell(c.due, true, 'due'));
      tr.appendChild(makeCell(c.service, true, 'service'));

      el.customerRows.appendChild(tr);
    });
  }

  async parsePasteData() {
    const text = this.app.el.pasteBox?.value?.trim() || '';
    if (!text) return;
    const lines = text.split(/\r?\n/).map((l) => l.split(/\t|,/));
    const customers = await this.app.parseRowsToCustomers(lines);
    customers.forEach((c) => this.app.pushCustomer(c));
  }

  async handleExcelFile(event) {
    const [file] = event.target.files ?? [];
    if (!file) return;
    try {
      const buffer = await file.arrayBuffer();
      const wb = XLSX.read(buffer, { type: 'array' });
      const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1 });
      const customers = await this.app.parseRowsToCustomers(rows);
      customers.forEach((c) => this.app.pushCustomer(c));
    } catch (e) {
      this.app.toast('Excel Error', e.message, 'error');
    }
  }

  startCustomerCellEdit(cell) {
    const row = cell.closest('tr');
    const customer = this.app.state.customers.find((c) => c.id === Number(row.dataset.customerId));
    if (!customer || cell.classList.contains('is-editing')) return;

    const input = document.createElement('input');
    input.value = customer[cell.dataset.field];

    cell.classList.add('is-editing');
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();

    input.addEventListener('blur', () => {
      customer[cell.dataset.field] = input.value;
      this.render();
      this.app.mapController.renderMarkers();
    });
  }
}
