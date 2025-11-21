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

    const urlParams = new URLSearchParams(window.location.search);
    const fadeMode = urlParams.get('fade') === 'true';

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
            if (!fadeMode) {
                drawGrid();
            }
        } else if (data.type === 'pixels_removed') {
            if (!fadeMode) {
                data.coords.forEach(coord => {
                    const key = `${coord.x},${coord.y}`;
                    gridState.delete(key);
                });
                drawGrid();
            }
        } else if (data.type === 'clear') {
            gridState.clear();
            if (!fadeMode) {
                drawGrid();
            }
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

        const now = Date.now();
        const toRemove = [];

        gridState.forEach((item, key) => {
            if (item.draw) {
                let opacity = 1.0;

                if (fadeMode && item.timestamp && item.ttl) {
                    const elapsed = (now - item.timestamp) / 1000;
                    const remaining = item.ttl - elapsed;

                    if (remaining <= 0) {
                        toRemove.push(key);
                        return;
                    }

                    opacity = Math.max(0, Math.min(1, remaining / item.ttl));
                }

                ctx.globalAlpha = opacity;
                ctx.fillStyle = item.color;
                const x = item.x * cw + p;
                const y = item.y * cw + p;
                ctx.fillRect(x, y, cw, cw);
                ctx.globalAlpha = 1.0;
            }
        });

        toRemove.forEach(key => gridState.delete(key));
    }

    if (fadeMode) {
        function animate() {
            drawGrid();
            requestAnimationFrame(animate);
        }
        animate();
    }

    connectWebSocket();
});
