import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../context/AppContext.jsx';
import { MapController } from '../MapController.js';
import { SimulationController } from '../SimulationController.js';
import { GanttController } from '../GanttController.js';

export default function LiveDispatchView() {
  const { state, updateState, toast, setStatus, request, t } = useAppContext();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [editingCell, setEditingCell] = useState(null); // { id, field }
  const [editValue, setEditValue] = useState('');
  const [pasteData, setPasteData] = useState('');

  // Forms states for inline row addition
  const [isAddingRow, setIsAddingRow] = useState(false);
  const [addRowData, setAddRowData] = useState({
    name: '',
    address: '',
    demand: '10',
    ready: '0',
    due: '1000',
    service: '10',
    priority: 'Normal',
    skill: 'None'
  });

  const fileInputRef = useRef(null);

  // Reference hooks for Leaflet map & playback simulators
  const mapControllerRef = useRef(null);
  const simulationControllerRef = useRef(null);
  const ganttControllerRef = useRef(null);

  // Custom mock of the app context passed to legacy controllers
  const appMockRef = useRef({
    state,
    toast,
    lang: state.lang,
    escapeHtml: (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    request,
    setStatus,
    mapController: null,
    simulationController: null,
    ganttController: null,
    pushCustomer: (cust) => {
      updateState((prev) => {
        const list = [...(prev.customers || [])];
        const nextId = list.length === 0 ? 0 : Math.max(...list.map((c) => c.id)) + 1;
        const newCust = { ...cust, id: nextId };
        return { customers: [...list, newCust] };
      });
    },
    addMapPoint: async (latlng) => {
      try {
        const res = await request(`/reverse-geocode?lat=${encodeURIComponent(latlng.lat)}&lng=${encodeURIComponent(latlng.lng)}`, { method: 'GET' });
        const address = res?.short_address || res?.address || `Lat ${latlng.lat.toFixed(5)}, Lng ${latlng.lng.toFixed(5)}`;
        
        updateState((prev) => {
          const list = [...(prev.customers || [])];
          const isFirst = list.length === 0;
          const nextId = isFirst ? 0 : Math.max(...list.map((c) => c.id)) + 1;
          const newCust = {
            id: nextId,
            name: isFirst ? 'Depot' : `Pin-${list.length}`,
            address,
            lat: latlng.lat,
            lng: latlng.lng,
            demand: 0,
            ready: 0,
            due: 1000,
            service: isFirst ? 0 : 10,
            isDepot: isFirst,
            priority: 'Normal',
            skill: 'None'
          };
          return { customers: [...list, newCust] };
        });
        setStatus('Dropped a new delivery pin.', 'ok');
        toast('Pin Added', 'Point was added directly on the map.', 'ok');
      } catch (err) {
        console.warn('Reverse geocode failed:', err);
      }
    }
  });

  // Sync state reference on update
  useEffect(() => {
    appMockRef.current.state = state;
    appMockRef.current.lang = state.lang;
  }, [state]);

  // Map & Simulation Controllers Initializer hook
  useEffect(() => {
    // 1. Map Controller
    const mapCtrl = new MapController(appMockRef.current);
    mapCtrl.init();
    mapControllerRef.current = mapCtrl;
    appMockRef.current.mapController = mapCtrl;

    // 2. Simulation Controller
    const simCtrl = new SimulationController(appMockRef.current);
    simCtrl.init();
    simulationControllerRef.current = simCtrl;
    appMockRef.current.simulationController = simCtrl;

    // 3. Gantt Controller
    const ganttCtrl = new GanttController(appMockRef.current);
    ganttCtrl.init();
    ganttControllerRef.current = ganttCtrl;
    appMockRef.current.ganttController = ganttCtrl;

    // Add map click listener (fixes legacy click-to-pin missing listener)
    mapCtrl.map.on('click', (e) => {
      if (appMockRef.current.state.mode === 'real') {
        appMockRef.current.addMapPoint(e.latlng);
      }
    });

    // Initial renders
    if (state.customers && state.customers.length > 0) {
      mapCtrl.renderMarkers();
    }

    if (state.lastResult) {
      mapCtrl.clearRoutes();
      mapCtrl.paintResult();
      
      let maxTime = 240;
      Object.values(state.lastResult).forEach((algo) => {
        (algo.routes || []).forEach((route) => {
          if (route.schedule && route.schedule.length > 0) {
            const lastStep = route.schedule[route.schedule.length - 1];
            if (lastStep.arrival > maxTime) maxTime = lastStep.arrival;
          }
        });
      });
      simCtrl.start(maxTime + 30);
    }

    // Expose window.app for E2E tests and backward compatibility
    window.app = appMockRef.current;

    return () => {
      window.app = null;
      simCtrl.stopLoop();
      mapCtrl.clearRoutes();
      ganttCtrl.destroy();
    };
  }, []);

  // Update map markers when customers list updates
  useEffect(() => {
    if (mapControllerRef.current && state.customers) {
      mapControllerRef.current.renderMarkers();
      
      const tableEmptyEl = document.getElementById('table-empty');
      if (tableEmptyEl) {
        tableEmptyEl.classList.toggle('hidden', state.customers.length > 0);
      }
    }
  }, [state.customers]);

  // Update route displays when solver finishes
  useEffect(() => {
    if (state.lastResult && mapControllerRef.current && simulationControllerRef.current && ganttControllerRef.current) {
      mapControllerRef.current.clearRoutes();
      mapControllerRef.current.paintResult();
      
      let maxTime = 240;
      Object.values(state.lastResult).forEach((algo) => {
        (algo.routes || []).forEach((route) => {
          if (route.schedule && route.schedule.length > 0) {
            const lastStep = route.schedule[route.schedule.length - 1];
            if (lastStep.arrival > maxTime) maxTime = lastStep.arrival;
          }
        });
      });

      simulationControllerRef.current.start(maxTime + 30);
      ganttControllerRef.current.render(state.lastResult, 'ddqn');
      
      const emptyDdqn = document.getElementById('map-empty-ddqn');
      const emptyAlns = document.getElementById('map-empty-alns');
      emptyDdqn?.classList.add('hidden');
      emptyAlns?.classList.add('hidden');
    }
  }, [state.lastResult]);

  // Row selection handler
  const toggleSelection = (id) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const deleteSelected = () => {
    if (selectedIds.size === 0) return;
    const remaining = state.customers.filter((c) => !selectedIds.has(c.id));
    // Ensure depot stays as ID 0
    if (remaining.length > 0) {
      remaining.forEach((c, idx) => {
        c.id = idx;
        if (idx === 0) c.isDepot = true;
      });
    }
    updateState({ customers: remaining });
    setSelectedIds(new Set());
    toast('Rows Deleted', `Removed ${selectedIds.size} row(s).`, 'ok');
  };

  // Inline table double click edits
  const startEdit = (id, field, value) => {
    setEditingCell({ id, field });
    setEditValue(String(value));
  };

  const saveEdit = async (id, field) => {
    if (!editingCell) return;
    setEditingCell(null);

    const val = editValue.trim();
    const updated = state.customers.map((c) => {
      if (c.id !== id) return c;

      const updatedCust = { ...c };
      if (field === 'name') {
        if (!val) {
          toast('Invalid Name', 'Name cannot be empty.', 'error');
          return c;
        }
        updatedCust.name = val;
      } else if (field === 'demand') {
        const num = Number(val);
        if (!Number.isFinite(num) || num < 0) {
          toast('Invalid Demand', 'Demand must be >= 0.', 'error');
          return c;
        }
        updatedCust.demand = Math.round(num);
      } else if (field === 'ready' || field === 'due' || field === 'service') {
        const num = Number(val);
        if (!Number.isFinite(num) || num < 0) {
          toast('Invalid Time', `${field} must be a positive number.`, 'error');
          return c;
        }
        if (field === 'ready' && Number(c.due) <= num) {
          toast('Invalid Window', 'Ready must be < Due.', 'error');
          return c;
        }
        if (field === 'due' && Number(c.ready) >= num) {
          toast('Invalid Window', 'Due must be > Ready.', 'error');
          return c;
        }
        updatedCust[field] = num;
      } else if (field === 'priority') {
        updatedCust.priority = val;
      } else if (field === 'skill') {
        updatedCust.skill = val;
      } else if (field === 'address') {
        if (!val) {
          toast('Invalid Address', 'Address cannot be empty.', 'error');
          return c;
        }
        updatedCust.address = val;
        // Trigger background geocoding request
        request(`/geocode?q=${encodeURIComponent(val)}&limit=1`, { method: 'GET' })
          .then((res) => {
            if (res.items?.length > 0) {
              updateState((prev) => {
                const list = prev.customers.map((item) => {
                  if (item.id === id) {
                    return { ...item, lat: Number(res.items[0].lat), lng: Number(res.items[0].lng) };
                  }
                  return item;
                });
                return { customers: list };
              });
              setStatus('Address geocoded successfully.', 'ok');
            }
          })
          .catch((err) => console.warn('Geocoding failed:', err));
      }
      return updatedCust;
    });

    updateState({ customers: updated });
  };

  // Add stop inline row creator
  const saveNewRow = async () => {
    if (!addRowData.name || !addRowData.address) {
      toast('Missing Fields', 'Name and Address are required.', 'error');
      return;
    }
    
    setStatus('Geocoding new waypoint stop coordinates...', 'info');
    let lat = 10.73;
    let lng = 106.70;
    try {
      const geo = await request(`/geocode?q=${encodeURIComponent(addRowData.address)}&limit=1`, { method: 'GET' });
      if (geo.items?.length > 0) {
        lat = Number(geo.items[0].lat);
        lng = Number(geo.items[0].lng);
      } else {
        toast('Geocode Failed', 'Could not locate address, using default coordinates.', 'warn');
      }
    } catch {
      toast('Geocode Error', 'Network error during address geocoding.', 'warn');
    }

    updateState((prev) => {
      const list = [...(prev.customers || [])];
      const isFirst = list.length === 0;
      const nextId = isFirst ? 0 : Math.max(...list.map((c) => c.id)) + 1;
      
      const newCust = {
        id: nextId,
        name: addRowData.name,
        address: addRowData.address,
        lat,
        lng,
        demand: isFirst ? 0 : Math.max(0, Number(addRowData.demand) || 0),
        ready: Math.max(0, Number(addRowData.ready) || 0),
        due: Math.max(1, Number(addRowData.due) || 1000),
        service: isFirst ? 0 : Math.max(0, Number(addRowData.service) || 10),
        isDepot: isFirst,
        priority: addRowData.priority,
        skill: addRowData.skill
      };
      return { customers: [...list, newCust] };
    });

    setIsAddingRow(false);
    setAddRowData({
      name: '',
      address: '',
      demand: '10',
      ready: '0',
      due: '1000',
      service: '10',
      priority: 'Normal',
      skill: 'None'
    });
    setStatus('Added stop successfully.', 'ok');
  };

  // Clipboard Paste parser
  const handlePasteData = async () => {
    if (!pasteData.trim()) return;
    try {
      setStatus('Parsing copy-pasted dataset...', 'info');
      const lines = pasteData.trim().split(/\r?\n/).map(l => l.trim()).filter(Boolean);
      const isTab = lines.some(l => l.includes('\t'));
      const delimiter = isTab ? /\t/ : /,/;
      const rows = lines.map(l => l.split(delimiter).map(c => c.trim()));

      // Deduce columns mapping index
      const headers = rows[0].map(h => h.toLowerCase());
      const mapIdx = {
        name: headers.indexOf('name'),
        address: headers.indexOf('address'),
        lat: headers.indexOf('lat'),
        lng: headers.indexOf('lng'),
        demand: headers.indexOf('demand'),
        ready: headers.indexOf('ready'),
        due: headers.indexOf('due'),
        service: headers.indexOf('service'),
        priority: headers.indexOf('priority'),
        skill: headers.indexOf('skill'),
      };

      const hasHeaders = Object.values(mapIdx).some(idx => idx !== -1);
      const dataRows = hasHeaders ? rows.slice(1) : rows;

      const list = [...state.customers];
      for (const row of dataRows) {
        if (row.length === 0) continue;
        let name = row[mapIdx.name !== -1 ? mapIdx.name : 0] || `Cust-${Math.random().toString().substring(2,5)}`;
        let addr = row[mapIdx.address !== -1 ? mapIdx.address : 1] || 'Address';
        let rawLat = row[mapIdx.lat !== -1 ? mapIdx.lat : 2];
        let rawLng = row[mapIdx.lng !== -1 ? mapIdx.lng : 3];
        let demand = Number(row[mapIdx.demand !== -1 ? mapIdx.demand : 4]) || 10;
        let ready = Number(row[mapIdx.ready !== -1 ? mapIdx.ready : 5]) || 0;
        let due = Number(row[mapIdx.due !== -1 ? mapIdx.due : 6]) || 1000;
        let svc = Number(row[mapIdx.service !== -1 ? mapIdx.service : 7]) || 10;

        let lat = Number(rawLat);
        let lng = Number(rawLng);

        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
          // Attempt online geocoding
          const geo = await request(`/geocode?q=${encodeURIComponent(addr)}&limit=1`, { method: 'GET' }).catch(() => null);
          lat = geo?.items?.[0] ? Number(geo.items[0].lat) : 10.73;
          lng = geo?.items?.[0] ? Number(geo.items[0].lng) : 106.70;
        }

        const isFirst = list.length === 0;
        list.push({
          id: isFirst ? 0 : Math.max(...list.map(c => c.id)) + 1,
          name,
          address: addr,
          lat,
          lng,
          demand: isFirst ? 0 : demand,
          ready,
          due,
          service: isFirst ? 0 : svc,
          isDepot: isFirst,
          priority: row[mapIdx.priority] || 'Normal',
          skill: row[mapIdx.skill] || 'None'
        });
      }

      updateState({ customers: list });
      setPasteData('');
      setStatus(`Imported ${dataRows.length} points from clipboard.`, 'ok');
      toast('Paste Success', `Loaded ${dataRows.length} stops.`, 'ok');
    } catch (err) {
      toast('Paste Failed', err.message, 'error');
    }
  };

  // Excel / CSV File Uploader
  const triggerExcelUpload = (e) => {
    e.preventDefault();
    if (state.mode !== 'real') {
      toast('Real Mode Required', 'Please switch dataset picker to custom import first.', 'error');
      return;
    }
    fileInputRef.current?.click();
  };

  const handleFileUploadChange = async (e) => {
    const [file] = e.target.files || [];
    if (!file) return;

    try {
      const nameLower = file.name.toLowerCase();
      if (nameLower.endsWith('.csv')) {
        setStatus('Parsing CSV file on the server...', 'info');
        const formData = new FormData();
        formData.append('file', file);

        const headers = {};
        if (state.token && state.token !== 'demo-guest') {
          headers.Authorization = `Bearer ${state.token}`;
        }
        const response = await fetch(`${API_BASE}/solomon/import-csv`, {
          method: 'POST',
          headers,
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => null);
          throw new Error(errData?.detail || `HTTP ${response.status}`);
        }

        const resData = await response.json();
        const incoming = Array.isArray(resData?.customers) ? resData.customers : [];
        if (!incoming.length) throw new Error('No valid customer rows found.');

        updateState((prev) => {
          const list = [...prev.customers];
          incoming.forEach((c) => {
            const isFirst = list.length === 0;
            list.push({
              id: isFirst ? 0 : Math.max(...list.map(item => item.id)) + 1,
              name: c.name,
              address: c.address,
              lat: c.lat,
              lng: c.lng,
              demand: isFirst ? 0 : c.demand,
              ready: c.ready,
              due: c.due,
              service: c.service,
              isDepot: c.isDepot,
              priority: c.priority || 'Normal',
              skill: c.skill || 'None'
            });
          });
          return { customers: list };
        });
        setStatus(`Successfully imported ${incoming.length} customers from CSV file.`, 'ok');
        toast('Import Successful', `Loaded ${incoming.length} rows from CSV.`, 'ok');
      } else {
        // Excel file parsing via sheetjs XLSX
        if (typeof window.XLSX === 'undefined') throw new Error('SheetJS XLSX library is not loaded');
        const buffer = await file.arrayBuffer();
        const workbook = window.XLSX.read(buffer, { type: 'array' });
        const firstSheet = workbook.SheetNames[0];
        const sheet = workbook.Sheets[firstSheet];
        const rows = window.XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
        
        // Convert to tabular text and reuse paste parser
        const text = rows.map((cols) => cols.map((cell) => String(cell ?? '')).join('\t')).join('\n');
        setPasteData(text);
        toast('Excel Read Success', 'Sheet parsed, click Parse Clipboard to commit.', 'ok');
      }
    } catch (error) {
      toast('Import Failed', error.message, 'error');
    }
  };

  // Solver Metrics Math
  const dRes = state.lastResult?.ddqn || {};
  const aRes = state.lastResult?.alns || {};

  const gapPct = (dRes.distance_km && aRes.distance_km) 
    ? (((dRes.distance_km - aRes.distance_km) / aRes.distance_km) * 100).toFixed(2)
    : '-0.00';

  return (
    <div id="view-dispatch" className="view-panel">
      {/* Solver KPI Metrics cards */}
      <section className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-title">Algorithm Gap (DDQN vs ALNS)</div>
          <div className={`kpi-value ${Number(gapPct) <= 0 ? 'highlight-emerald' : 'text-danger'}`}>
            {gapPct}%
          </div>
          <div className="kpi-sub">Closer to BKS is better</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-title">Total Distance (km)</div>
          <div className="kpi-split">
            <div>
              <span className="kpi-label">DDQN</span>
              <strong id="kpi-dist-ddqn">{Number(dRes.distance_km || 0).toFixed(2)}</strong>
            </div>
            <div>
              <span className="kpi-label">ALNS</span>
              <strong id="kpi-dist-alns">{Number(aRes.distance_km || 0).toFixed(2)}</strong>
            </div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-title">Vehicles Dispatched</div>
          <div className="kpi-split">
            <div>
              <span className="kpi-label">DDQN</span>
              <strong id="kpi-veh-ddqn">{dRes.routes?.length || 0}</strong>
            </div>
            <div>
              <span className="kpi-label">ALNS</span>
              <strong id="kpi-veh-alns">{aRes.routes?.length || 0}</strong>
            </div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-title">Compute Time</div>
          <div className="kpi-split">
            <div>
              <span className="kpi-label">DDQN</span>
              <strong id="kpi-time-ddqn">{Number(dRes.runtime_s || 0).toFixed(1)}s</strong>
            </div>
            <div>
              <span className="kpi-label">ALNS</span>
              <strong id="kpi-time-alns">{Number(aRes.runtime_s || 0).toFixed(1)}s</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="workspace-full" style={{ position: 'relative' }}>
        {/* Slide-out Manifest Drawer (over the map) */}
        <div id="manifest-drawer" className={`manifest-drawer ${drawerOpen ? 'open' : ''}`}>
          <div className="drawer-header">
            <h3>Manifest (Waypoints)</h3>
            <div className="drawer-header-actions" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button className="btn-secondary btn-sm" onClick={() => setIsAddingRow(true)}>
                + Add Stop
              </button>
              {selectedIds.size > 0 && (
                <button className="btn-danger btn-sm" onClick={deleteSelected}>
                  Delete Selected ({selectedIds.size})
                </button>
              )}
              <button id="btn-close-drawer" className="drawer-close-btn" onClick={() => setDrawerOpen(false)} title="Close">
                &times;
              </button>
            </div>
          </div>
          <div className="table-container" style={{ overflow: 'auto', maxHeight: '380px' }}>
            <table className="saas-table">
              <thead>
                <tr>
                  <th style={{ width: '28px' }}></th>
                  <th style={{ width: '40px' }}>ID</th>
                  <th>Name</th>
                  <th>Address</th>
                  <th>Lat</th>
                  <th>Lng</th>
                  <th className="num">Demand</th>
                  <th className="num">Ready</th>
                  <th className="num">Due</th>
                  <th className="num">Service</th>
                  <th style={{ width: '90px' }}>Priority</th>
                  <th style={{ width: '100px' }}>Req. Skill</th>
                </tr>
              </thead>
              <tbody id="customer-rows">
                {/* Inline Addition Row */}
                {isAddingRow && (
                  <tr style={{ backgroundColor: 'var(--bg-highlight)' }}>
                    <td></td>
                    <td><strong className="font-mono">+</strong></td>
                    <td>
                      <input 
                        type="text" 
                        className="table-inline-input"
                        placeholder="Stop Name"
                        value={addRowData.name}
                        onChange={(e) => setAddRowData({ ...addRowData, name: e.target.value })}
                      />
                    </td>
                    <td>
                      <input 
                        type="text" 
                        className="table-inline-input"
                        placeholder="Address text..."
                        value={addRowData.address}
                        onChange={(e) => setAddRowData({ ...addRowData, address: e.target.value })}
                      />
                    </td>
                    <td>—</td>
                    <td>—</td>
                    <td>
                      <input 
                        type="number" 
                        className="table-inline-input num"
                        value={addRowData.demand}
                        onChange={(e) => setAddRowData({ ...addRowData, demand: e.target.value })}
                      />
                    </td>
                    <td>
                      <input 
                        type="number" 
                        className="table-inline-input num"
                        value={addRowData.ready}
                        onChange={(e) => setAddRowData({ ...addRowData, ready: e.target.value })}
                      />
                    </td>
                    <td>
                      <input 
                        type="number" 
                        className="table-inline-input num"
                        value={addRowData.due}
                        onChange={(e) => setAddRowData({ ...addRowData, due: e.target.value })}
                      />
                    </td>
                    <td>
                      <input 
                        type="number" 
                        className="table-inline-input num"
                        value={addRowData.service}
                        onChange={(e) => setAddRowData({ ...addRowData, service: e.target.value })}
                      />
                    </td>
                    <td>
                      <select 
                        className="table-inline-input"
                        value={addRowData.priority}
                        onChange={(e) => setAddRowData({ ...addRowData, priority: e.target.value })}
                      >
                        <option value="Low">Low</option>
                        <option value="Normal">Normal</option>
                        <option value="High">High</option>
                      </select>
                    </td>
                    <td>
                      <select 
                        className="table-inline-input"
                        value={addRowData.skill}
                        onChange={(e) => setAddRowData({ ...addRowData, skill: e.target.value })}
                      >
                        <option value="None">None</option>
                        <option value="Refrigerated">Refrigerated</option>
                        <option value="Hazmat">Hazmat</option>
                      </select>
                    </td>
                    <td>
                      <button className="btn-primary btn-sm" onClick={saveNewRow}>Save</button>
                      <button className="btn-text btn-sm" onClick={() => setIsAddingRow(false)}>Cancel</button>
                    </td>
                  </tr>
                )}

                {/* Normal customer rows */}
                {state.customers.map((c) => {
                  const isSelected = selectedIds.has(c.id);
                  return (
                    <tr key={c.id} className={isSelected ? 'table-row-selected' : ''}>
                      <td className="table-pick-cell" onClick={() => toggleSelection(c.id)}>
                        {isSelected ? '✓' : '○'}
                      </td>
                      <td><strong className="font-mono">#{c.id}</strong></td>
                      
                      {/* Name cell */}
                      <td 
                        className="cell-editable" 
                        onDoubleClick={() => startEdit(c.id, 'name', c.name)}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'name' ? (
                          <input 
                            type="text" 
                            className="table-edit-input" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'name')}
                            onKeyDown={(e) => e.key === 'Enter' && saveEdit(c.id, 'name')}
                            autoFocus
                          />
                        ) : (
                          <>
                            {c.name || 'Stop'}
                            {c.isDepot && <span className="depot-badge" style={{ marginLeft: '6px' }}>DEPOT</span>}
                          </>
                        )}
                      </td>

                      {/* Address cell */}
                      <td 
                        className="cell-editable" 
                        onDoubleClick={() => startEdit(c.id, 'address', c.address)}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'address' ? (
                          <input 
                            type="text" 
                            className="table-edit-input" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'address')}
                            onKeyDown={(e) => e.key === 'Enter' && saveEdit(c.id, 'address')}
                            autoFocus
                          />
                        ) : (
                          c.address || '-'
                        )}
                      </td>

                      <td>{Number(c.lat).toFixed(5)}</td>
                      <td>{Number(c.lng).toFixed(5)}</td>

                      {/* Demand cell */}
                      <td 
                        className="num cell-editable" 
                        onDoubleClick={() => !c.isDepot && startEdit(c.id, 'demand', c.demand)}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'demand' ? (
                          <input 
                            type="number" 
                            className="table-edit-input num" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'demand')}
                            onKeyDown={(e) => e.key === 'Enter' && saveEdit(c.id, 'demand')}
                            autoFocus
                          />
                        ) : (
                          c.demand
                        )}
                      </td>

                      {/* Ready Window cell */}
                      <td 
                        className="num cell-editable" 
                        onDoubleClick={() => startEdit(c.id, 'ready', c.ready)}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'ready' ? (
                          <input 
                            type="number" 
                            className="table-edit-input num" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'ready')}
                            onKeyDown={(e) => e.key === 'Enter' && saveEdit(c.id, 'ready')}
                            autoFocus
                          />
                        ) : (
                          c.ready
                        )}
                      </td>

                      {/* Due Window cell */}
                      <td 
                        className="num cell-editable" 
                        onDoubleClick={() => startEdit(c.id, 'due', c.due)}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'due' ? (
                          <input 
                            type="number" 
                            className="table-edit-input num" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'due')}
                            onKeyDown={(e) => e.key === 'Enter' && saveEdit(c.id, 'due')}
                            autoFocus
                          />
                        ) : (
                          c.due
                        )}
                      </td>

                      {/* Service cell */}
                      <td 
                        className="num cell-editable" 
                        onDoubleClick={() => !c.isDepot && startEdit(c.id, 'service', c.service)}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'service' ? (
                          <input 
                            type="number" 
                            className="table-edit-input num" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'service')}
                            onKeyDown={(e) => e.key === 'Enter' && saveEdit(c.id, 'service')}
                            autoFocus
                          />
                        ) : (
                          c.service
                        )}
                      </td>

                      {/* Priority cell */}
                      <td 
                        className="cell-editable" 
                        onDoubleClick={() => !c.isDepot && startEdit(c.id, 'priority', c.priority || 'Normal')}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'priority' ? (
                          <select 
                            className="table-edit-input" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'priority')}
                            onChangeCapture={() => setTimeout(() => saveEdit(c.id, 'priority'), 100)}
                            autoFocus
                          >
                            <option value="Low">Low</option>
                            <option value="Normal">Normal</option>
                            <option value="High">High</option>
                          </select>
                        ) : (
                          !c.isDepot && (
                            <span 
                              className="priority-badge"
                              style={
                                c.priority === 'High'
                                  ? { background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239,68,68,0.2)', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', fontSize: '10px', display: 'inline-block', textAlign: 'center', width: '55px' }
                                  : c.priority === 'Low'
                                  ? { background: 'rgba(107, 114, 128, 0.1)', color: 'var(--text-muted)', border: '1px solid rgba(107,114,128,0.2)', fontWeight: 500, padding: '2px 6px', borderRadius: '4px', fontSize: '10px', display: 'inline-block', textAlign: 'center', width: '55px' }
                                  : { background: 'rgba(59, 130, 246, 0.1)', color: 'var(--primary)', border: '1px solid rgba(59,130,246,0.2)', fontWeight: 600, padding: '2px 6px', borderRadius: '4px', fontSize: '10px', display: 'inline-block', textAlign: 'center', width: '55px' }
                              }
                            >
                              {c.priority || 'Normal'}
                            </span>
                          )
                        )}
                      </td>

                      {/* Required Skill cell */}
                      <td 
                        className="cell-editable" 
                        onDoubleClick={() => !c.isDepot && startEdit(c.id, 'skill', c.skill || 'None')}
                      >
                        {editingCell?.id === c.id && editingCell?.field === 'skill' ? (
                          <select 
                            className="table-edit-input" 
                            value={editValue} 
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => saveEdit(c.id, 'skill')}
                            onChangeCapture={() => setTimeout(() => saveEdit(c.id, 'skill'), 100)}
                            autoFocus
                          >
                            <option value="None">None</option>
                            <option value="Refrigerated">Refrigerated</option>
                            <option value="Hazmat">Hazmat</option>
                          </select>
                        ) : (
                          !c.isDepot && (
                            <span 
                              style={
                                c.skill && c.skill !== 'None'
                                  ? { background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', border: '1px solid rgba(16,185,129,0.2)', fontWeight: 600, padding: '2px 6px', borderRadius: '4px', fontSize: '10px', display: 'inline-block' }
                                  : { color: 'var(--text-muted)', fontSize: '10px' }
                              }
                            >
                              {c.skill || 'None'}
                            </span>
                          )
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Import Paste / File Section */}
          {state.mode === 'real' && (
            <div className="manifest-import-box" style={{ padding: '12px', background: '#f8fafc', borderTop: '1px solid var(--border)' }}>
              <h4 style={{ margin: '0 0 8px', fontSize: '11px' }}>Paste TSV / CSV Data or Import Excel</h4>
              <textarea 
                className="saas-textarea" 
                placeholder="Pasted rows: Name, Address, Demand, Ready, Due, Service"
                style={{ width: '100%', height: '40px', fontSize: '10px', marginBottom: '8px' }}
                value={pasteData}
                onChange={(e) => setPasteData(e.target.value)}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-secondary btn-sm" onClick={handlePasteData}>Parse Clipboard</button>
                <button className="btn-secondary btn-sm" onClick={triggerExcelUpload}>Upload Excel/CSV</button>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }} 
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUploadChange}
                />
              </div>
            </div>
          )}
        </div>

        {/* Full-width Map Pane */}
        <div className="pane pane-map-full" style={{ position: 'relative' }}>
          <div className="pane-header">
            <div className="pane-header-left" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button 
                id="btn-toggle-drawer" 
                className={`drawer-toggle-btn ${drawerOpen ? 'active' : ''}`} 
                onClick={() => setDrawerOpen(!drawerOpen)}
                title="Toggle Manifest"
              >
                <span className="drawer-toggle-icon">☰</span>
                <span className="drawer-toggle-label">Manifest</span>
              </button>
              <h3>Geospatial View</h3>
            </div>
            <div className="map-toggles">
              <label><input type="radio" name="map_view" value="ddqn" defaultChecked /> DDQN</label>
              <label><input type="radio" name="map_view" value="alns" /> ALNS Base</label>
            </div>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', minHeight: 0 }}>
            {/* Direct Leaflet Canvas Container */}
            <div id="map-container" className="map-view" style={{ flex: 1 }}></div>

            {/* Simulation Control Bar */}
            <div id="sim-control-panel" className="sim-control-bar hidden">
              <button id="btn-sim-play" className="btn-sim-play">▶ Play</button>
              <span id="sim-time-display" className="sim-time-text">Time: 00:00m</span>
              <div className="sim-slider-container">
                <input type="range" id="sim-slider" className="sim-slider" min="0" max="100" defaultValue="0" />
              </div>
              <select id="sim-speed" className="sim-speed-select">
                <option value="1">1x Speed</option>
                <option value="2" defaultValue>2x Speed</option>
                <option value="5">5x Speed</option>
                <option value="10">10x Speed</option>
                <option value="50">50x Speed</option>
              </select>
            </div>
          </div>

          {/* Vehicle Status Panel */}
          <div id="sim-vehicle-panel" className="sim-vehicle-panel hidden"></div>

          {/* Floating Mobile Companion App Emulator Trigger Button */}
          <button
            id="btn-toggle-driver-app"
            className="hidden"
            style={{
              position: 'absolute',
              bottom: '85px',
              right: '20px',
              zIndex: 1000,
              background: 'var(--primary)',
              color: 'white',
              padding: '10px 18px',
              borderRadius: '30px',
              fontSize: '11px',
              fontWeight: 700,
              boxShadow: 'var(--shadow-md)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <span>📱 Driver App Companion</span>
            <span
              id="driver-app-notif"
              style={{
                background: 'var(--danger)',
                color: 'white',
                fontSize: '8px',
                fontWeight: 800,
                borderRadius: '50%',
                width: '14px',
                height: '14px',
                display: 'none',
                alignItems: 'center',
                justifyContent: 'center',
                lineHeight: 1,
              }}
            >
              1
            </span>
          </button>

          {/* Mobile Driver App Emulator Mockup Container */}
          <div id="driver-app-emulator" className="driver-app-mockup hidden">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '4px 18px 2px',
                fontSize: '9px',
                fontWeight: 700,
                color: '#a1a1aa',
                position: 'relative',
              }}
            >
              <span>9:41 AM</span>
              <div
                style={{
                  width: '50px',
                  height: '10px',
                  background: '#000',
                  borderRadius: '5px',
                  position: 'absolute',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  top: '4px',
                }}
              ></div>
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <span>📶</span>
                <span>🔋</span>
              </div>
            </div>
            <div className="driver-app-screen">
              <div
                style={{
                  background: 'var(--primary)',
                  color: 'white',
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <strong style={{ fontSize: '11px', letterSpacing: '-0.2px' }}>NAMI Driver View</strong>
                <select
                  id="driver-app-select"
                  style={{
                    background: 'rgba(255, 255, 255, 0.18)',
                    color: 'white',
                    border: 'none',
                    fontSize: '10px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontWeight: 600,
                    outline: 'none',
                    width: '120px',
                    cursor: 'pointer',
                  }}
                >
                  <option value="" style={{ color: '#000' }}>Select Driver...</option>
                </select>
              </div>
              <div
                id="driver-app-content"
                style={{ flex: 1, overflowY: 'auto', padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}
              >
                <div style={{ textAlign: 'center', marginTop: '100px', padding: '0 16px' }}>
                  <div style={{ fontSize: '32px', marginBottom: '12px' }}>🚚</div>
                  <h4 style={{ margin: '0 0 6px', fontSize: '13px', color: '#27272a' }}>Driver Companion Emulator</h4>
                  <p style={{ margin: 0, fontSize: '10px', color: '#71717a', lineHeight: '1.4' }}>
                    Select an active driver above to simulate mobile deliveries, log signatures, and track live routes.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
