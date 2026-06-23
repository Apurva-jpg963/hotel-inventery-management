// Global JavaScript for Hotel Saiprasad Finance ERP

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // 2. Setup Theme Toggler
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    if (themeToggleBtn && themeIcon) {
        themeToggleBtn.addEventListener('click', () => {
            if (document.documentElement.classList.contains('dark')) {
                document.documentElement.classList.remove('dark');
                localStorage.setItem('theme', 'light');
                themeIcon.setAttribute('data-lucide', 'moon');
            } else {
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
                themeIcon.setAttribute('data-lucide', 'sun');
            }
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        });
    }

    // 3. Mobile Sidebar Toggle
    const sidebar = document.getElementById('sidebar');
    const sidebarOpenBtn = document.getElementById('sidebar-open');
    const sidebarCloseBtn = document.getElementById('sidebar-close');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebarOpenBtn && sidebar && sidebarOverlay) {
        sidebarOpenBtn.addEventListener('click', () => {
            sidebar.classList.remove('-translate-x-full');
            sidebarOverlay.classList.remove('hidden');
        });
    }

    if (sidebarCloseBtn && sidebar && sidebarOverlay) {
        sidebarCloseBtn.addEventListener('click', () => {
            sidebar.classList.add('-translate-x-full');
            sidebarOverlay.classList.add('hidden');
        });
    }

    if (sidebarOverlay && sidebar) {
        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.add('-translate-x-full');
            sidebarOverlay.classList.add('hidden');
        });
    }

    // 4. Auto-dismiss Flash Alerts
    const alerts = document.querySelectorAll('.flash-alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'all 0.5s ease-out';
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 4000);
    });
});

// 5. Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `animate-toast max-w-sm w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl rounded-2xl p-4 flex items-start gap-3 pointer-events-auto transition-all duration-300`;

    let iconColor = 'text-blue-500';
    let iconName = 'info';

    if (type === 'success') {
        iconColor = 'text-emerald-500';
        iconName = 'check-circle';
    } else if (type === 'warning') {
        iconColor = 'text-amber-500';
        iconName = 'alert-triangle';
    } else if (type === 'danger') {
        iconColor = 'text-rose-500';
        iconName = 'x-circle';
    }

    toast.innerHTML = `
        <div class="${iconColor} mt-0.5">
            <i data-lucide="${iconName}" class="w-5 h-5"></i>
        </div>
        <div class="flex-1">
            <p class="text-sm font-medium text-slate-900 dark:text-slate-100">${message}</p>
        </div>
        <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 ml-2" onclick="this.parentElement.remove()">
            <i data-lucide="x" class="w-4 h-4"></i>
        </button>
    `;

    container.appendChild(toast);
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Auto-remove toast after 4s
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.5s ease-out';
        setTimeout(() => {
            toast.remove();
        }, 500);
    }, 4000);
}
