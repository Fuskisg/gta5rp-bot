(function() {
    const hotkeyInput = document.getElementById('hotkey-input');
    if (!hotkeyInput) return;

    let selectedHotkey = hotkeyInput.value.toLowerCase();
    
    hotkeyInput.addEventListener('click', function() {
        this.value = '...';
        this.classList.add('active');
    });
    
    hotkeyInput.addEventListener('keydown', function(e) {
        e.preventDefault();
        
        const code = e.code;
        
        if (code.includes('Shift') || code.includes('Control') || code.includes('Alt') || 
            code.includes('Meta') || code === 'Tab' || code === 'Escape') {
            return;
        }
        
        let key = '';
        if (code.startsWith('Key')) {
            key = code.replace('Key', '').toLowerCase();
        } else if (code.startsWith('Digit')) {
            key = code.replace('Digit', '');
        } else if (code.startsWith('F') && code.length <= 3) {
            key = code.toLowerCase();
        } else {
            key = code.toLowerCase();
        }
        
        selectedHotkey = key;
        this.value = key.toUpperCase();
        this.classList.remove('active');
        this.blur();
    });
    
    hotkeyInput.addEventListener('blur', function() {
        if (this.value === '...') {
            this.value = selectedHotkey.toUpperCase();
        }
        this.classList.remove('active');
    });

    window.getSelectedHotkey = function() {
        return selectedHotkey;
    };
})();
