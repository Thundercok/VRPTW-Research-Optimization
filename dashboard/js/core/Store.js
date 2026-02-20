export class Store {
    constructor() {
        this.state = {
            data: null,
            sourceLabel: 'No file loaded yet.',
            activeKey: null,
            selectedRouteIndex: 0,
        };

        this.solutionRegistry = [
            { key: 'rl_alns', label: 'DDQN-ALNS' },
            { key: 'alns', label: 'ALNS' },
        ];
        this.listeners = [];

        // --- TÍNH NĂNG MỚI: TỰ ĐỘNG LOAD TỪ LOCAL STORAGE ---
        this.loadFromCache();
    }

    subscribe(listener) {
        this.listeners.push(listener);
        // Nếu có sẵn data trong cache thì báo cho view vẽ luôn ngay lần đầu
        if (this.state.data) listener(this.state);
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }

    loadData(parsedData, label) {
        this.validateData(parsedData);
        this.state.data = parsedData;
        this.state.sourceLabel = label;
        this.state.activeKey = this.pickDefaultSolution(parsedData);
        this.state.selectedRouteIndex = 0;

        console.log('Store: Data loaded successfully!');

        // --- TÍNH NĂNG MỚI: LƯU VÀO LOCAL STORAGE ---
        try {
            localStorage.setItem('nexus_cache', JSON.stringify(this.state));
            console.log('Store: Session auto-saved to LocalStorage.');
        } catch (e) {
            console.warn('Store: File too large for LocalStorage, skipping auto-save.');
        }

        this.notify();
    }

    loadFromCache() {
        try {
            const cached = localStorage.getItem('nexus_cache');
            if (cached) {
                this.state = JSON.parse(cached);
                console.log('Store: Restored session from previous visit!');
            }
        } catch (e) {
            console.error('Store: Failed to read cache', e);
            localStorage.removeItem('nexus_cache');
        }
    }

    // Chức năng xuất file tải về máy
    exportData() {
        if (!this.state.data) return alert('No data to save!');

        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.state.data, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", "nexus_saved_session.json");
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }

    validateData(data) {
        if (!data || typeof data !== 'object') throw new Error('The JSON root must be an object.');
        if (!Array.isArray(data.nodes) || data.nodes.length < 2) throw new Error('Expected a nodes array with at least depot + 1 customer.');
        if (!data.alns && !data.rl_alns) throw new Error('Expected at least one solution block: alns or rl_alns.');
    }

    pickDefaultSolution(data) {
        const firstAvailable = this.solutionRegistry.find(item => Boolean(data[item.key]));
        return firstAvailable ? firstAvailable.key : null;
    }
}