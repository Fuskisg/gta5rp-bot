(function() {
    if (window.__dragInitialized) return;
    window.__dragInitialized = true;

    let bridge = null;
    let currentX = 0;
    let currentY = 0;

    function initBridge() {
        if (typeof QWebChannel === 'undefined' || typeof qt === 'undefined') return;
        new QWebChannel(qt.webChannelTransport, function(channel) {
            bridge = channel.objects.windowBridge;
            bridge.getPosition(function(pos) {
                currentX = pos.x || 0;
                currentY = pos.y || 0;
            });
        });
    }
    initBridge();

    window.minimizeWindow = function() {
        if (bridge) bridge.minimize();
    };

    window.closeWindow = function() {
        if (bridge) bridge.closeWindow();
    };

    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let initialWindowX = 0;
    let initialWindowY = 0;

    let moveScheduled = false;
    let lastMoveX = 0;
    let lastMoveY = 0;

    function flushMove() {
        moveScheduled = false;
        if (bridge) {
            bridge.moveWindow(lastMoveX, lastMoveY);
            currentX = lastMoveX;
            currentY = lastMoveY;
        }
    }

    function sendMove(x, y) {
        lastMoveX = x;
        lastMoveY = y;
        if (!moveScheduled) {
            moveScheduled = true;
            requestAnimationFrame(flushMove);
        }
    }

    const dragRegion = document.querySelector('.titlebar-drag-region');

    const handleMouseDown = (e) => {
        if (e.button !== 0) return;
        isDragging = true;
        dragStartX = e.screenX;
        dragStartY = e.screenY;
        initialWindowX = currentX;
        initialWindowY = currentY;
        e.preventDefault();
    };

    const handleMouseMove = (e) => {
        if (!isDragging) return;
        sendMove(
            initialWindowX + (e.screenX - dragStartX),
            initialWindowY + (e.screenY - dragStartY)
        );
    };

    const handleMouseUp = () => { isDragging = false; };

    if (dragRegion) {
        dragRegion.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        document.addEventListener('mouseleave', handleMouseUp);
    }
})();
