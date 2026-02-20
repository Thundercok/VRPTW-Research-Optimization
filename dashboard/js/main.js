import { TabController } from './components/TabController.js';
import { Store } from './core/Store.js';
import { DataLoader } from './core/DataLoader.js';
// Thêm InspectorView vào (chúng ta sẽ tạo nó ở bước 2)
import { InspectorView } from './views/InspectorView.js';

document.addEventListener('DOMContentLoaded', () => {
  console.log('Nexus Dashboard: Initializing...');

  // 1. Khởi động UI Tabs
  const tabController = new TabController();

  // 2. Khởi tạo kho chứa dữ liệu ngầm
  const store = new Store();

  // 3. Gắn Data Loader vào Store (để tải JSON)
  const dataLoader = new DataLoader(store);

  // 4. Khởi tạo giao diện Bảng Dữ Liệu và cho nó "lắng nghe" Store
  const inspectorView = new InspectorView(store);
});