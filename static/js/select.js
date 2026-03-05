function createCustomSelect(config) {
    var selectEl = document.getElementById(config.id);
    var trigger = selectEl.querySelector('.custom-select-trigger');
    var isOpen = false;
    var currentValue = config.selected || '';

    var optionsPanel = document.createElement('div');
    optionsPanel.className = 'custom-select-options';
    optionsPanel.style.cssText = 'position:fixed;display:none;z-index:999999;max-height:200px;overflow-y:auto;';
    optionsPanel.innerHTML = config.options.map(function(opt) {
        var val = typeof opt === 'object' ? opt.value : opt;
        var label = typeof opt === 'object' ? opt.label : opt;
        return '<div class="custom-select-option' + (val === currentValue ? ' selected' : '') + '" data-value="' + val + '">' + label + '</div>';
    }).join('');
    document.body.appendChild(optionsPanel);

    var options = optionsPanel.querySelectorAll('.custom-select-option');

    function positionDropdown() {
        var rect = trigger.getBoundingClientRect();
        optionsPanel.style.top = (rect.bottom + 4) + 'px';
        optionsPanel.style.left = rect.left + 'px';
        optionsPanel.style.width = rect.width + 'px';
    }

    function openSelect() {
        positionDropdown();
        optionsPanel.style.display = 'block';
        selectEl.classList.add('open');
        isOpen = true;
    }

    function closeSelect() {
        optionsPanel.style.display = 'none';
        selectEl.classList.remove('open');
        isOpen = false;
    }

    trigger.addEventListener('click', function() {
        if (isOpen) closeSelect(); else openSelect();
    });

    options.forEach(function(opt) {
        opt.addEventListener('click', function() {
            options.forEach(function(o) { o.classList.remove('selected'); });
            opt.classList.add('selected');
            trigger.textContent = opt.textContent;
            currentValue = opt.getAttribute('data-value');
            closeSelect();
            if (config.onChange) config.onChange(currentValue);
        });
    });

    document.addEventListener('click', function(e) {
        if (!selectEl.contains(e.target) && !optionsPanel.contains(e.target)) {
            closeSelect();
        }
    });

    optionsPanel.addEventListener('wheel', function(e) {
        var maxScroll = optionsPanel.scrollHeight - optionsPanel.clientHeight;
        if (maxScroll <= 0) return;
        var newTop = optionsPanel.scrollTop + e.deltaY;
        if (newTop < 0) newTop = 0;
        if (newTop > maxScroll) newTop = maxScroll;
        optionsPanel.scrollTop = newTop;
        e.preventDefault();
        e.stopPropagation();
    }, { passive: false });

    window.addEventListener('scroll', function(e) {
        if (isOpen && !optionsPanel.contains(e.target)) closeSelect();
    }, true);

    return {
        getValue: function() { return currentValue; }
    };
}
