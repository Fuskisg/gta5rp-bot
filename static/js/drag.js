(function() {
    if (window.__dragInitialized) {
        return;
    }
    window.__dragInitialized = true;

    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let initialWindowX = 0;
    let initialWindowY = 0;
    const dragRegion = document.querySelector('.titlebar-drag-region');

    window.minimizeWindow = function() {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.minimize();
        }
    };

    window.closeWindow = function() {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.close();
        }
    };

    const handleMouseDown = async (e) => {
        if (e.button !== 0) return;
        
        isDragging = true;
        dragStartX = e.screenX;
        dragStartY = e.screenY;
        
        if (window.pywebview && window.pywebview.api) {
            try {
                const pos = await window.pywebview.api.get_position();
                initialWindowX = pos.x || 0;
                initialWindowY = pos.y || 0;
            } catch (err) {
                initialWindowX = window.screenX || 0;
                initialWindowY = window.screenY || 0;
            }
        } else {
            initialWindowX = window.screenX || 0;
            initialWindowY = window.screenY || 0;
        }
        
        e.preventDefault();
    };

    const handleMouseMove = (e) => {
        if (!isDragging) return;
        
        const deltaX = e.screenX - dragStartX;
        const deltaY = e.screenY - dragStartY;
        
        const newX = initialWindowX + deltaX;
        const newY = initialWindowY + deltaY;
        
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.move(newX, newY);
        }
    };

    const handleMouseUp = () => {
        isDragging = false;
    };

    if (dragRegion) {
        dragRegion.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        document.addEventListener('mouseleave', handleMouseUp);
    }
})();
