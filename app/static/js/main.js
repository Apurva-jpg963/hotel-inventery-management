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

// 6. Universal Bulk Select & Delete System
document.addEventListener('DOMContentLoaded', () => {
    const rowBoxes = document.querySelectorAll('.row-checkbox');
    if (rowBoxes.length > 0) {
        // Create the floating bulk bar dynamically if not already present
        let bulkBar = document.getElementById('bulk-delete-bar');
        if (!bulkBar) {
            bulkBar = document.createElement('div');
            bulkBar.id = 'bulk-delete-bar';
            bulkBar.className = 'fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-slate-900/95 dark:bg-slate-950/95 text-white py-3.5 px-6 rounded-2xl shadow-2xl border border-slate-850 flex items-center gap-6 z-50 transition-all duration-300 translate-y-20 opacity-0';
            bulkBar.innerHTML = `
                <span id="selected-count-label" class="text-xs font-semibold tracking-wider text-slate-300">0 items selected</span>
                <div class="h-4 w-px bg-slate-800"></div>
                <button id="btn-bulk-delete" class="flex items-center gap-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold py-1.5 px-4 rounded-xl transition-all shadow-md cursor-pointer">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash-2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                    Delete Selected
                </button>
            `;
            document.body.appendChild(bulkBar);
        }

        const selectAllBoxes = document.querySelectorAll('.select-all-checkbox');
        const selectedCountLabel = document.getElementById('selected-count-label');
        const btnBulkDelete = document.getElementById('btn-bulk-delete');

        function updateBulkBarVisibility() {
            const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
            const count = checkedBoxes.length;

            if (count > 0) {
                bulkBar.classList.remove('translate-y-20', 'opacity-0');
                bulkBar.classList.add('translate-y-0', 'opacity-100');
                if (selectedCountLabel) selectedCountLabel.textContent = `${count} item(s) selected`;
            } else {
                bulkBar.classList.remove('translate-y-0', 'opacity-100');
                bulkBar.classList.add('translate-y-20', 'opacity-0');
            }
        }

        selectAllBoxes.forEach(allBox => {
            allBox.addEventListener('change', (e) => {
                const isChecked = e.target.checked;
                rowBoxes.forEach(box => {
                    box.checked = isChecked;
                });
                updateBulkBarVisibility();
            });
        });

        rowBoxes.forEach(box => {
            box.addEventListener('change', () => {
                updateBulkBarVisibility();
                selectAllBoxes.forEach(allBox => {
                    allBox.checked = (document.querySelectorAll('.row-checkbox:not(:checked)').length === 0 && rowBoxes.length > 0);
                });
            });
        });

        if (btnBulkDelete) {
            btnBulkDelete.addEventListener('click', () => {
                const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
                if (checkedBoxes.length === 0) return;
                
                const ids = Array.from(checkedBoxes).map(box => box.value);
                
                // Get type from closest ancestor with data-type attribute
                let entryType = 'income';
                const container = checkedBoxes[0].closest('[data-type]');
                if (container) {
                    entryType = container.getAttribute('data-type');
                }

                if (ids.length === 0) return;

                if (confirm(`Are you sure you want to delete these ${ids.length} item(s)? This will reverse all corresponding cashbook log entries and cannot be undone.`)) {
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/finance/delete-bulk';

                    const typeInput = document.createElement('input');
                    typeInput.type = 'hidden';
                    typeInput.name = 'type';
                    typeInput.value = entryType;
                    form.appendChild(typeInput);

                    const idsInput = document.createElement('input');
                    idsInput.type = 'hidden';
                    idsInput.name = 'ids';
                    idsInput.value = ids.join(',');
                    form.appendChild(idsInput);

                    document.body.appendChild(form);
                    form.submit();
                }
            });
        }
    }
});
