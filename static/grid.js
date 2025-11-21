document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const p = 10;
    const cw = 20;
    const bw = 500;
    const bh = 500;

    const cols = bw / cw;
    const rows = bh / cw;

    canvas.width = bw + 2*p;
    canvas.height = bh + 2*p;

    let gridState = new Map();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let ws;

    function connectWebSocket() {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            fetchInitialState();
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting in 2s...');
            setTimeout(connectWebSocket, 2000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    function handleWebSocketMessage(data) {
        if (data.type === 'pixels_added') {
            data.coords.forEach(coord => {
                const key = `${coord.x},${coord.y}`;
                gridState.set(key, coord);
            });
            drawGrid();
        } else if (data.type === 'pixels_removed') {
            data.coords.forEach(coord => {
                const key = `${coord.x},${coord.y}`;
                gridState.delete(key);
            });
            drawGrid();
        } else if (data.type === 'clear') {
            gridState.clear();
            drawGrid();
        }
    }

    async function fetchInitialState() {
        try {
            const response = await fetch('/api/coords');
            const data = await response.json();
            gridState.clear();
            data.coords.forEach(coord => {
                const key = `${coord.x},${coord.y}`;
                gridState.set(key, coord);
            });
            drawGrid();
        } catch (err) {
            console.error('Error fetching initial state:', err);
        }
    }

    function drawGrid() {
        ctx.fillStyle = "lightgreen";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        gridState.forEach(item => {
            if (item.draw) {
                ctx.fillStyle = item.color;
                const x = item.x * cw + p;
                const y = item.y * cw + p;
                ctx.fillRect(x, y, cw, cw);
            }
        });
    }

    connectWebSocket();
});
