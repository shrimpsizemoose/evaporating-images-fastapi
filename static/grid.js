document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const cw = 20;

    let gridWidth = 25;
    let gridHeight = 25;
    let backgroundColor = 'lightgreen';
    let gridState = new Map();

    const urlParams = new URLSearchParams(window.location.search);
    const fadeMode = urlParams.get('fade') === 'true';

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let ws;

    function resizeCanvas(width, height) {
        gridWidth = width;
        gridHeight = height;
        canvas.width = gridWidth * cw;
        canvas.height = gridHeight * cw;
        drawGrid();
    }

    function setBackgroundColor(color) {
        backgroundColor = color;
        document.body.style.backgroundColor = color;
        drawGrid();
    }

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
        } else if (data.type === 'figure_changed') {
            resizeCanvas(data.figure.grid_width, data.figure.grid_height);
            setBackgroundColor(data.figure.background_color);
            gridState.clear();
        } else if (data.type === 'background_changed') {
            setBackgroundColor(data.background_color);
        }
    }

    async function fetchInitialState() {
        try {
            const settingsResponse = await fetch('/api/figure-settings');
            const settings = await settingsResponse.json();
            resizeCanvas(settings.grid_width, settings.grid_height);
            setBackgroundColor(settings.background_color);

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
        ctx.fillStyle = backgroundColor;
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
                const x = item.x * cw;
                const y = item.y * cw;
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
