import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { createInitialState } from '../createInitialState.js';
import { firebaseService, auth, db } from '../firebaseService.js';
import { API_BASE } from '../constants.js';
import { APP_COPY } from './translations.js';
import { solveDemo } from '../DemoEngine.js';
import { onAuthStateChanged, signOut } from 'https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js';

const AppContext = createContext();

export function AppContextProvider({ children }) {
  const [state, setState] = useState(() => {
    const s = createInitialState();
    // Pre-populate fleet if stored in localStorage
    const savedFleet = localStorage.getItem('vrptw_fleet_config');
    if (savedFleet) {
      try {
        s.fleet = JSON.parse(savedFleet);
      } catch (e) {
        console.warn('Failed to parse saved fleet:', e);
      }
    }
    return s;
  });

  const [toasts, setToasts] = useState([]);
  const [status, setStatusText] = useState('Ready.');
  const [statusTone, setStatusTone] = useState('');
  const [user, setUser] = useState(null);
  const [isLoadingUser, setIsLoadingUser] = useState(true);
  const [loadingState, setLoadingState] = useState({
    active: false,
    progress: 0,
    title: 'AI is optimizing routes...',
    subtitle: 'Sending request to the backend solver...',
    phase: 'Queueing job...',
    elapsed: '0s',
    backend: 'queued',
    backendTone: '',
    device: '—',
    logs: [],
  });

  // Track run session state for cancelling active backend jobs
  const runSession = useRef({
    token: 0,
    cancelled: false,
    abortController: null,
  });

  const setLang = (lang) => {
    localStorage.setItem('vrptw_demo_lang', lang);
    setState((prev) => ({ ...prev, lang }));
  };

  const updateState = (updater) => {
    setState((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      // Sync simple config back to localStorage
      if (next.token !== undefined) localStorage.setItem('vrptw_token', next.token);
      if (next.email !== undefined) localStorage.setItem('vrptw_email', next.email);
      if (next.role !== undefined) localStorage.setItem('vrptw_role', next.role);
      return { ...prev, ...next };
    });
  };

  const toast = (title, message = '', tone = '') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, title, message, tone }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, tone === 'error' ? 6500 : 4200);
  };

  const setStatus = (message, tone = '') => {
    setStatusText(message || '');
    setStatusTone(tone || '');
  };

  const addConsoleLog = (line) => {
    setLoadingState((prev) => ({
      ...prev,
      logs: [...prev.logs, line],
    }));
  };

  // Auth Subscription
  useEffect(() => {
    if (auth) {
      const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
        if (fbUser) {
          setUser(fbUser);
          updateState({
            token: await fbUser.getIdToken(),
            email: fbUser.email,
            role: fbUser.email.includes('admin') ? 'admin' : 'operator',
            unlocked: true,
          });
          try {
            await firebaseService.init(fbUser.email);
          } catch (err) {
            console.warn('Firebase user init failed:', err);
          }
        } else {
          setUser(null);
          updateState({
            token: '',
            email: '',
            role: 'operator',
            unlocked: false,
          });
        }
        setIsLoadingUser(false);
      });
      return unsubscribe;
    } else {
      setIsLoadingUser(false);
    }
  }, []);

  const loginAsGuest = () => {
    updateState({
      token: 'demo-guest',
      email: 'guest@nami.local',
      role: 'guest',
      unlocked: true,
    });
    toast('Demo Mode', 'Continuing as guest operator.', 'ok');
  };

  const logout = async () => {
    if (auth) {
      await firebaseService.markLogout();
      await signOut(auth);
    }
    updateState({
      token: '',
      email: '',
      role: 'operator',
      unlocked: false,
    });
    toast('Logged Out', 'You have been signed out successfully.', 'ok');
  };

  // General Fetch API requests
  const request = async (path, options = {}) => {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (state.token && state.token !== 'demo-guest') {
      headers.Authorization = `Bearer ${state.token}`;
    }
    try {
      const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
      if (!response.ok) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const data = await response.json().catch(() => null);
          throw new Error(data?.detail || data?.message || `HTTP ${response.status}`);
        }
        const body = await response.text();
        throw new Error(body || `HTTP ${response.status}`);
      }
      return response.json();
    } catch (error) {
      const message = String(error?.message || error || '');
      if (error instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(message)) {
        throw new Error(`Cannot reach backend API at ${API_BASE}. Start the backend server on port 8000.`);
      }
      throw error;
    }
  };

  // Submit route optimization job
  const submitJob = async () => {
    try {
      if (!state.token) {
        toast('Not Logged In', 'Please log in before running the model.', 'error');
        return;
      }
      if (state.customers.length < 2) {
        setStatus('At least depot and 1 customer are required.', 'error');
        return;
      }

      setLoadingState((prev) => ({
        ...prev,
        active: true,
        progress: 0,
        logs: ['Submitting optimization job to background queue...'],
      }));

      runSession.current.token += 1;
      runSession.current.cancelled = false;
      runSession.current.abortController?.abort();
      runSession.current.abortController = new AbortController();
      setStatus('Submitting optimization job to background queue...');
      toast('Processing', 'Job is being queued and will run in the background.', 'ok');

      const payload = {
        mode: state.mode,
        fleet: { vehicles: state.vehicles, capacity: state.capacity },
        customers: state.customers,
      };

      updateState({ lastRunFleet: { ...payload.fleet } });

      const submit = await request('/jobs', {
        method: 'POST',
        body: JSON.stringify(payload),
        signal: runSession.current.abortController.signal,
      });

      if (typeof window.vrptwTrack === 'function') {
        window.vrptwTrack('job_submit', {
          mode: state.mode,
          customers: state.customers.length,
          vehicles: state.vehicles,
          capacity: state.capacity,
        });
      }

      await firebaseService.saveJobStart(submit.job_id, {
        mode: state.mode,
        fleet: payload.fleet,
        customerCount: state.customers.length,
        customers: state.customers,
      });

      const pollLimitMs = estimatePollTimeoutMs(state.customers.length);
      await pollJob(submit.job_id, pollLimitMs, runSession.current.token);
    } catch (error) {
      if (runSession.current.cancelled || error?.name === 'AbortError') {
        return;
      }

      // Guest / offline fallback
      const isGuest = state.role === 'guest' || state.token === 'demo-guest';
      if (isGuest) {
        try {
          setStatus('Backend unavailable — running client-side solver...', 'warn');
          toast('Local Solver', 'Backend is offline. Running in-browser ALNS solver.', 'ok');
          const demoResult = solveDemo(
            state.customers,
            state.vehicles,
            state.capacity,
            state.fleet
          );

          updateState({ lastResult: demoResult });
          setLoadingState((prev) => ({ ...prev, active: false }));
          setStatus('Client-side optimization complete.', 'ok');
          toast('Model Completed', 'Results rendered using the in-browser solver.', 'ok');
          return;
        } catch (fallbackErr) {
          console.error('Client-side solver also failed:', fallbackErr);
        }
      }

      const friendly = error?.message || 'Submit failed';
      setStatus(`Submit error: ${friendly}`, 'error');
      toast('Submit Failed', friendly, 'error');
      setLoadingState((prev) => ({ ...prev, active: false }));
    } finally {
      runSession.current.abortController = null;
    }
  };

  const estimatePollTimeoutMs = (customerCount) => {
    const count = Math.max(0, Number(customerCount) || 0);
    const baseline = 600000;
    const scaled = baseline + count * 6000;
    return Math.min(1800000, Math.max(baseline, scaled));
  };

  const pollJob = async (jobId, timeoutMs = 180000, sessionToken = 0) => {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeoutMs) {
      if (runSession.current.cancelled || sessionToken !== runSession.current.token) return;
      const data = await request(`/jobs/${jobId}`, {
        method: 'GET',
        signal: runSession.current.abortController?.signal,
      });
      if (runSession.current.cancelled || sessionToken !== runSession.current.token) return;

      const phase = data?.debug?.phase || data.status;
      const events = data?.debug?.events || [];
      const newLogs = events.map((evt) => evt.message || '').filter(Boolean);

      setLoadingState((prev) => ({
        ...prev,
        backend: phase,
        logs: [...new Set([...prev.logs, ...newLogs])],
        device: data?.debug?.device || prev.device,
        progress: phase === 'done' ? 100 : Math.min(95, prev.progress + 5),
      }));

      if (phase === 'queued') {
        setStatus('Backend has accepted the job. Waiting for a worker thread.');
      } else if (phase === 'processing') {
        setStatus('Worker reserved. Preparing solver inputs...');
      } else if (phase === 'matrix') {
        setStatus('Computing distance matrix for route optimization...');
      } else if (phase === 'solving') {
        setStatus('Running parallel DDQN-ALNS hybrid and ALNS baseline solvers...');
      }

      if (data.status === 'done') {
        if (runSession.current.cancelled || sessionToken !== runSession.current.token) return;
        updateState({ lastResult: data.result });
        await firebaseService.saveJobResult(jobId, data.result);
        setLoadingState((prev) => ({ ...prev, active: false }));
        setStatus('Received optimization results from backend.', 'ok');
        toast('Model Completed', 'Results have been rendered on the dashboard.', 'ok');
        return;
      }
      if (data.status === 'failed') {
        throw new Error(data.error || 'Job failed');
      }
      await new Promise((resolve) => setTimeout(resolve, 1400));
    }
    throw new Error('Job timeout.');
  };

  const cancelJob = () => {
    runSession.current.cancelled = true;
    runSession.current.abortController?.abort();
    setLoadingState((prev) => ({ ...prev, active: false }));
    setStatus('Job execution cancelled by operator.', 'warn');
    toast('Cancelled', 'Background optimization task cancelled.', 'warn');
  };

  const loadAvailableDatasets = async () => {
    try {
      const data = await request('/solomon/list', { method: 'GET' });
      const list = Array.isArray(data?.datasets) ? data.datasets : [];
      updateState({ solomonDatasets: list });
      return list;
    } catch (error) {
      setStatus('Could not load Solomon list. Keeping demo dataset only.', 'error');
      toast('Solomon List Failed', error.message || 'Error loading Solomon datasets', 'error');
      return [];
    }
  };

  const loadSolomonDataset = async (name = 'demo') => {
    try {
      const data = await request(`/solomon?name=${encodeURIComponent(name)}`, { method: 'GET' });
      const incoming = Array.isArray(data?.customers) ? data.customers : [];
      if (incoming.length < 2) throw new Error('Solomon dataset is empty or invalid.');

      const customers = incoming.map((c, idx) => ({
        ...c,
        id: idx,
        demand: Number(c.demand) || 0,
        ready: Number.isFinite(Number(c.ready)) ? Number(c.ready) : 0,
        due: Number.isFinite(Number(c.due)) ? Number(c.due) : 1000,
        service: Number.isFinite(Number(c.service)) ? Number(c.service) : 10,
        isDepot: Boolean(c.isDepot),
        priority: c.priority || (idx === 0 ? 'Normal' : ['Normal', 'High', 'Low'][idx % 3]),
        skill: c.skill || (idx === 0 ? 'None' : idx % 5 === 1 ? 'Refrigerated' : idx % 5 === 2 ? 'Hazmat' : 'None'),
      }));

      const fleetVehicles = Math.max(1, Number(data?.fleet?.vehicles) || state.vehicles);
      const fleetCapacity = Math.max(1, Number(data?.fleet?.capacity) || state.capacity);

      updateState({
        customers,
        vehicles: fleetVehicles,
        capacity: fleetCapacity,
        selectedDataset: name,
      });

      return customers;
    } catch (error) {
      toast('Load Failed', error.message || 'Error loading Solomon dataset', 'error');
    }
  };

  // Auto-load Solomon dataset on initial dashboard render when unlocked
  useEffect(() => {
    if (state.unlocked && state.mode === 'sample' && state.customers.length === 0) {
      loadAvailableDatasets().then(async (list) => {
        const defaultDs = list.some(d => d.name === 'demo') ? 'demo' : (list[0]?.name || 'demo');
        await loadSolomonDataset(defaultDs);
      });
    }
  }, [state.unlocked, state.mode]);

  const t = (key) => {
    const lang = state.lang === 'vn' ? 'vn' : 'en';
    return APP_COPY[lang][key] || key;
  };

  return (
    <AppContext.Provider
      value={{
        state,
        toasts,
        status,
        statusTone,
        user,
        isLoadingUser,
        loadingState,
        setLang,
        updateState,
        toast,
        setStatus,
        request,
        submitJob,
        cancelJob,
        loginAsGuest,
        logout,
        t,
        loadAvailableDatasets,
        loadSolomonDataset,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  return useContext(AppContext);
}
