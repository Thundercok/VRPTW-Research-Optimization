# VRPTW Web Visualization

Web app visualize kết quả VRPTW (Vehicle Routing Problem with Time Windows) bằng Solomon benchmark.


## File Structure

```
web/
├── index.html          # Main HTML page
├── style.css           # Styling
├── app.js              # Main application logic
├── solomon-parser.js   # Parser cho Solomon format
├── data/               # Solomon benchmark instances
│   └── c101.txt        # Sample instance
└── README.md           # This file
```

## Done

- Load Solomon benchmark instances
- Visualize depot và customers trên map
- Hiển thị routes với màu sắc khác nhau
- Metrics: total distance, time, vehicles used, customers served
- Điều chỉnh số vehicles
- DoneMock inference để test visualization

## Tích hợp với Model

Để tích hợp với model:

1. Tạo API endpoint để gọi model inference
2. Sửa function `runInference()` trong `app.js`:
   ```javascript
   async function runInference() {
       // Gọi API endpoint
       const response = await fetch('/api/inference', {
           method: 'POST',
           body: JSON.stringify({
               instance: currentInstance,
               numVehicles: numVehicles
           })
       });
       const routes = await response.json();
       visualizeRoutes(routes, currentInstance);
   }
   ```

## Tech Stack

- **Frontend**: HTML + CSS + Vanilla JavaScript
- **Map**: Leaflet.js
- **Data Format**: Solomon benchmark format
# VRPTW-Visualization
