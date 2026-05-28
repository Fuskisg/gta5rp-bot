window.globalEventSource = null;

window.addEventListener('load', () => {
    const loader = document.getElementById('loader');
    if (loader) loader.classList.add('hidden');
});

window.logManager = {
    append: function(text) {
        const container = document.getElementById('log-container');
        if (!container) return;
        const div = document.createElement('div');
        div.textContent = text;

        if (text.includes("Сглаживание шрифтов: выключено")) {
            div.classList.add('log-highlight');
        }

        container.appendChild(div);
        if (container.children.length > 100) container.removeChild(container.firstChild);
        container.scrollTop = container.scrollHeight;
    },
    handleSSE: function(event) {
        window.logManager.append(event.data);
        const isActive = event.data.includes("запущен") || event.data.includes("запустил");
        const isStopped = event.data.includes("остановлен");
        
        if (isActive && typeof window.updatePageUI === 'function') window.updatePageUI(true);
        if (isStopped && typeof window.updatePageUI === 'function') window.updatePageUI(false);
    }
};

window.updateModuleUI = function(btnId, active) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.innerText = active ? 'ОСТАНОВИТЬ' : 'ЗАПУСТИТЬ';
    btn.classList.toggle('running', active);
    btn.style.background = '';
};

window.loadModuleLogs = function(moduleName) {
    const container = document.getElementById('log-container');
    if (container) container.innerHTML = '';
    
    fetch('/api/get_logs')
        .then(res => res.json())
        .then(data => {
            if (window.logManager && data.logs) {
                data.logs
                    .filter(l => l.includes(`[${moduleName}]`))
                    .forEach(l => window.logManager.append(l));
            }
        })
        .catch(err => console.error('Ошибка загрузки логов:', err));
};

function refreshUIConfig() {
    return fetch('/api/settings/get')
        .then(res => res.json())
        .then(settings => {
            window.UI_CONFIG = {
                hoverEnabled: settings.switch_hover,
                clickEnabled: settings.switch_click,
                hoverVol: settings.volume_hover / 100,
                clickVol: settings.volume_click / 100,
                background: settings.background || 'bot'
            };
        })
        .catch(err => console.error('Ошибка обновления UI_CONFIG:', err));
}

function loadPageContent(url) {
    const container = document.querySelector('.container');
    if (!container) return;
    
    container.classList.add('loading');
    
    fetch(url)
        .then(res => res.text())
        .then(html => {
            const parser = new DOMParser();
            const newDoc = parser.parseFromString(html, 'text/html');
            const newContent = newDoc.querySelector('.container');

            if (newContent) {
                document.querySelectorAll('.dynamic-script').forEach(s => s.remove());
                container.innerHTML = newContent.innerHTML;
                
                updateActiveLink();
                initSliders();
                initSounds();
                initTooltips();
                container.classList.remove('loading');
                
                requestAnimationFrame(() => {
                    newContent.querySelectorAll('script').forEach((oldScript, index) => {
                        setTimeout(() => {
                            const newScript = document.createElement('script');
                            newScript.classList.add('dynamic-script');
                            if (oldScript.src) {
                                newScript.src = oldScript.src;
                            } else {
                                newScript.textContent = oldScript.textContent;
                            }
                            document.body.appendChild(newScript);
                        }, index * 10);
                    });
                });
                
                const pathParts = window.location.pathname.split('/').filter(p => p);
                const pageName = pathParts[pathParts.length - 1] || 'index';
                fetch('/api/set_active_tab/' + pageName, { method: 'POST' }).catch(() => {});
            }
        })
        .catch(err => {
            console.error("Ошибка загрузки страницы:", err);
            container.classList.remove('loading');
        });
}

function initEventSource() {
    if (!window.globalEventSource) {
        window.globalEventSource = new EventSource('/api/events');
        window.globalEventSource.onmessage = window.logManager.handleSSE;
    }
}

function initSliders() {
    document.querySelectorAll('input[type="range"]').forEach(slider => {
        if (slider.dataset.initialized === 'true') return;
        
        const update = () => {
            const percent = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;
            // Qt WebEngine repaint fix: set backgroundSize directly (numeric property repaints reliably)
            slider.style.backgroundSize = `${percent}% 100%`;
        };
        
        // Qt WebEngine repaint fix: drive hover/active via JS classes
        // because :hover/:active on ::-webkit-slider-thumb don't trigger repaint in Qt
        slider.addEventListener('mouseenter', () => {
            slider.classList.add('is-hover');
        });
        slider.addEventListener('mouseleave', () => {
            slider.classList.remove('is-hover', 'is-active');
        });
        slider.addEventListener('mousedown', () => {
            slider.classList.add('is-active');
        });
        slider.addEventListener('mouseup', () => {
            slider.classList.remove('is-active');
        });

        update();
        slider.addEventListener('input', update);
        slider.dataset.initialized = 'true';
    });
}

function updateActiveLink() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.classList.toggle('active', link.getAttribute('href') === currentPath);
    });
}

function quickPlay(type, event) {
    const config = window.UI_CONFIG;
    if (!config) return;

    if (event && event.target) {
        const toggle = event.target.closest('.toggle-switch');
        if (toggle && (toggle.id === 'switch-hover' || toggle.id === 'switch-click')) {
            return;
        }
    }

    let audioId = (type === 'hover') ? 'hover-sound' : 'click-sound';
    let isEnabled = (type === 'hover') ? config.hoverEnabled : config.clickEnabled;
    let volume = (type === 'hover') ? config.hoverVol : config.clickVol;

    if (isEnabled) {
        const audio = document.getElementById(audioId);
        if (audio) {
            audio.volume = volume;
            audio.currentTime = 0;
            audio.play().catch(() => {});
        }
    }
}

const handleHover = (e) => quickPlay('hover', e);
const handleClick = (e) => quickPlay('click', e);

function initSounds() {
    const soundElements = document.querySelectorAll('.module-switch, .btn-action, .nav-links a, button, .slider');
    
    soundElements.forEach(el => {
        if (el.dataset.soundInit === 'true') return;
        
        el.addEventListener('mouseenter', handleHover);
        el.addEventListener('click', handleClick);
        el.dataset.soundInit = 'true';
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initEventSource();
    
    document.addEventListener('click', (e) => {
        const link = e.target.closest('.nav-links a');
        if (link && link.getAttribute('href') && !link.getAttribute('href').startsWith('http')) {
            e.preventDefault();
            const targetUrl = link.href;
            document.body.classList.remove('sidebar-open');
            
            if (window.location.href !== targetUrl) {
                window.history.pushState({}, '', targetUrl);
                loadPageContent(targetUrl);
            }
        }
    });

    window.onpopstate = () => loadPageContent(window.location.pathname);

    updateActiveLink();
    initSounds();
    initSliders();
    initTooltips();
});

function initTooltips() {
    let tooltipContainer = document.getElementById('global-tooltip');
    if (!tooltipContainer) {
        tooltipContainer = document.createElement('div');
        tooltipContainer.id = 'global-tooltip';
        tooltipContainer.className = 'custom-tooltip';
        document.body.appendChild(tooltipContainer);
    }
    
    const navItems = document.querySelectorAll('.nav-item[data-tooltip]');
    
    navItems.forEach(item => {
        const tooltipText = item.getAttribute('data-tooltip');
        if (!tooltipText) return;
        
        item.addEventListener('mouseenter', (e) => {
            const isClosed = !document.body.classList.contains('sidebar-open');
            if (!isClosed) return;
            
            const rect = item.getBoundingClientRect();
            tooltipContainer.textContent = tooltipText;
            tooltipContainer.style.left = (rect.right + 10) + 'px';
            tooltipContainer.style.top = (rect.top + rect.height / 2) + 'px';
            tooltipContainer.style.setProperty('opacity', '1', 'important');
            tooltipContainer.style.setProperty('visibility', 'visible', 'important');
        });
        
        item.addEventListener('mouseleave', () => {
            tooltipContainer.style.setProperty('opacity', '0', 'important');
            tooltipContainer.style.setProperty('visibility', 'hidden', 'important');
        });
    });
}

function toggleSidebar() {
    document.body.classList.toggle('sidebar-open');
}

// Qt WebEngine repaint fix: animate checkbox ::after via JS class instead of :checked CSS trigger
document.addEventListener('change', function(e) {
    const el = e.target;
    if (!el.classList.contains('checkbox-input')) return;
    el.classList.remove('is-checked', 'is-unchecked');
    requestAnimationFrame(() => {
        el.classList.add(el.checked ? 'is-checked' : 'is-unchecked');
    });
}, true);

window.sendLogsToTelegram = function() {
    const container = document.getElementById('log-container');
    if (!container || container.innerText.trim() === "") {
        alert("Логи пусты!");
        return;
    }
    const logText = container.innerText;
    const message = `Вот логи:\n${logText}`;
    const telegramUrl = `https://t.me/id3001?text=${encodeURIComponent(message)}`;
    window.open(telegramUrl, '_blank');
};