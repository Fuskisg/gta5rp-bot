(function() {
    const hotkeyInputs = document.querySelectorAll('.hotkey-input');
    if (!hotkeyInputs.length) return;

    hotkeyInputs.forEach(function(input) {
        input.addEventListener('click', function() {
            this.value = '...';
            this.classList.add('active');
        });

        input.addEventListener('keydown', function(e) {
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

            this.value = key.toUpperCase();
            this.classList.remove('active');
            this.blur();
        });

        input.addEventListener('blur', function() {
            if (this.value === '...') {
                this.value = this.defaultValue || '';
            }
            this.classList.remove('active');
        });
    });

    window.getSelectedHotkey = function() {
        return hotkeyInputs[0].value.toLowerCase();
    };
})();
