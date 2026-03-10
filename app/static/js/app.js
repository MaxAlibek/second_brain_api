/**
 * Second Brain — Клиентская логика (Vanilla JS)
 * ================================================
 * Отвечает за:
 * - JWT авторизацию (localStorage)
 * - Fetch-обертку с автоматическим Authorization header
 * - Toast-уведомления
 * - CRUD операции с заметками
 * - AI Chat (мессенджер)
 * - Decision Engine UI
 * - Skeleton loaders
 */

const API = '';  // Пустая строка = тот же хост (SSR)

// ============================================================
// УТИЛИТЫ: JWT + Fetch
// ============================================================

/** Получить JWT из localStorage */
function getToken() {
    return localStorage.getItem('access_token');
}

/** Сохранить JWT */
function setToken(token) {
    localStorage.setItem('access_token', token);
}

/** Удалить JWT (logout) */
function clearToken() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
}

/** Проверка: залогинен ли пользователь? Если нет — редирект на /login */
function requireAuth() {
    if (!getToken()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

/**
 * Обертка вокруг fetch с автоматической подстановкой JWT.
 * Если получаем 401 — токен протух, редирект на /login.
 */
async function apiFetch(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API}${url}`, { ...options, headers });

    if (response.status === 401) {
        clearToken();
        window.location.href = '/login';
        return null;
    }

    return response;
}


// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const icons = {
        success: '<i data-lucide="check-circle"></i>',
        error: '<i data-lucide="alert-circle"></i>',
        info: '<i data-lucide="info"></i>'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `${icons[type] || ''} <span>${message}</span>`;
    container.appendChild(toast);

    // Инициализируем иконку в тосте (если Lucide загружен)
    if (window.lucide) lucide.createIcons();

    setTimeout(() => toast.remove(), 3000);
}


// ============================================================
// SKELETON LOADERS
// ============================================================

function renderSkeletons(container, count = 6) {
    container.innerHTML = '';
    for (let i = 0; i < count; i++) {
        container.innerHTML += `
            <div class="skeleton-card card">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text"></div>
            </div>
        `;
    }
}


// ============================================================
// LOGIN / REGISTER
// ============================================================

function initLoginPage() {
    const tabs = document.querySelectorAll('.login-tab');
    const forms = document.querySelectorAll('.login-form');

    // Переключение вкладок (Логин ↔ Регистрация)
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            forms.forEach(f => f.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tab.dataset.form).classList.add('active');
            document.getElementById('login-error').textContent = '';
        });
    });

    // Форма логина
    document.getElementById('login-section')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorEl = document.getElementById('login-error');
        errorEl.textContent = '';

        const formData = new URLSearchParams();
        formData.append('username', document.getElementById('login-username').value);
        formData.append('password', document.getElementById('login-password').value);

        try {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData,
            });
            if (!res.ok) {
                const data = await res.json();
                errorEl.textContent = data.detail || 'Неверный логин или пароль';
                return;
            }
            const data = await res.json();
            setToken(data.access_token);
            localStorage.setItem('username', document.getElementById('login-username').value);
            window.location.href = '/dashboard';
        } catch (err) {
            errorEl.textContent = 'Ошибка соединения с сервером';
        }
    });

    // Форма регистрации
    document.getElementById('register-section')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorEl = document.getElementById('login-error');
        errorEl.textContent = '';

        const body = {
            username: document.getElementById('reg-username').value,
            email: document.getElementById('reg-email').value,
            password: document.getElementById('reg-password').value,
        };

        try {
            const res = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const data = await res.json();
                errorEl.textContent = data.detail || 'Ошибка регистрации';
                return;
            }

            // Автологин после регистрации
            const formData = new URLSearchParams();
            formData.append('username', body.username);
            formData.append('password', body.password);
            const loginRes = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData,
            });
            if (loginRes.ok) {
                const data = await loginRes.json();
                setToken(data.access_token);
                localStorage.setItem('username', body.username);
                window.location.href = '/dashboard';
            }
        } catch (err) {
            errorEl.textContent = 'Ошибка соединения с сервером';
        }
    });
}


// ============================================================
// DASHBOARD (ЗАМЕТКИ)
// ============================================================

async function initDashboard() {
    if (!requireAuth()) return;
    updateSidebarUser();
    await loadNotes();
}

async function loadNotes() {
    const grid = document.getElementById('notes-grid');
    if (!grid) return;
    renderSkeletons(grid);

    const res = await apiFetch('/brain/');
    if (!res) return;
    const notes = await res.json();

    if (notes.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <i data-lucide="notebook-pen"></i>
                <p>У тебя пока нет заметок. Создай первую!</p>
                <button class="btn btn-primary" onclick="openNoteModal()">
                    <i data-lucide="plus"></i> Новая заметка
                </button>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    grid.innerHTML = notes.map(note => `
        <div class="card" onclick="openNoteModal(${note.id})">
            <div class="card-actions">
                <button class="btn btn-icon btn-ghost" onclick="event.stopPropagation(); deleteNote(${note.id})" title="Удалить">
                    <i data-lucide="trash-2" style="width:16px;height:16px;"></i>
                </button>
            </div>
            <div class="card-title">${escapeHtml(note.title || 'Без названия')}</div>
            <div class="card-text">${escapeHtml(note.content)}</div>
            <div class="card-meta">
                <span>${formatDate(note.created_at)}</span>
                ${note.category ? `<span class="card-tag">${escapeHtml(note.category)}</span>` : ''}
            </div>
        </div>
    `).join('');

    if (window.lucide) lucide.createIcons();
}

function openNoteModal(noteId = null) {
    const overlay = document.getElementById('note-modal');
    const title = document.getElementById('modal-title');
    const form = document.getElementById('note-form');
    const noteIdInput = document.getElementById('note-id');

    if (noteId) {
        title.textContent = 'Редактировать заметку';
        noteIdInput.value = noteId;
        // Загрузить данные заметки
        apiFetch(`/brain/${noteId}`).then(async res => {
            if (res) {
                const note = await res.json();
                document.getElementById('note-title').value = note.title || '';
                document.getElementById('note-content').value = note.content || '';
                document.getElementById('note-category').value = note.category || '';
            }
        });
    } else {
        title.textContent = 'Новая заметка';
        noteIdInput.value = '';
        form.reset();
    }

    overlay.classList.add('active');
}

function closeNoteModal() {
    document.getElementById('note-modal').classList.remove('active');
}

async function saveNote(e) {
    e.preventDefault();
    const noteId = document.getElementById('note-id').value;
    const body = {
        title: document.getElementById('note-title').value,
        content: document.getElementById('note-content').value,
        category: document.getElementById('note-category').value || null,
    };

    let res;
    if (noteId) {
        res = await apiFetch(`/brain/${noteId}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
        res = await apiFetch('/brain/', { method: 'POST', body: JSON.stringify(body) });
    }

    if (res && res.ok) {
        showToast(noteId ? 'Заметка обновлена!' : 'Заметка создана!');
        closeNoteModal();
        await loadNotes();
    } else {
        showToast('Ошибка при сохранении', 'error');
    }
}

async function deleteNote(noteId) {
    if (!confirm('Удалить заметку?')) return;
    const res = await apiFetch(`/brain/${noteId}`, { method: 'DELETE' });
    if (res && (res.ok || res.status === 204)) {
        showToast('Заметка удалена');
        await loadNotes();
    } else {
        showToast('Ошибка удаления', 'error');
    }
}

// Поиск по заметкам (фильтрация на клиенте)
function initSearch() {
    const input = document.getElementById('search-input');
    if (!input) return;
    input.addEventListener('input', () => {
        const query = input.value.toLowerCase();
        document.querySelectorAll('#notes-grid .card').forEach(card => {
            const text = card.textContent.toLowerCase();
            card.style.display = text.includes(query) ? '' : 'none';
        });
    });
}


// ============================================================
// AI CHAT
// ============================================================

async function initChat() {
    if (!requireAuth()) return;
    updateSidebarUser();

    const form = document.getElementById('chat-form');
    form?.addEventListener('submit', sendMessage);
}

async function sendMessage(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const messages = document.getElementById('chat-messages');
    const question = input.value.trim();
    if (!question) return;

    // Добавляем сообщение юзера
    messages.innerHTML += `<div class="message message-user">${escapeHtml(question)}</div>`;
    input.value = '';
    messages.scrollTop = messages.scrollHeight;

    // Показываем typing indicator
    const typingEl = document.createElement('div');
    typingEl.className = 'typing-indicator';
    typingEl.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    messages.appendChild(typingEl);
    messages.scrollTop = messages.scrollHeight;

    try {
        const res = await apiFetch('/ai/chat', {
            method: 'POST',
            body: JSON.stringify({ question }),
        });

        typingEl.remove();

        if (res && res.ok) {
            const data = await res.json();
            messages.innerHTML += `<div class="message message-ai">${escapeHtml(data.answer)}</div>`;
        } else {
            messages.innerHTML += `<div class="message message-ai">Произошла ошибка. Попробуйте позже.</div>`;
        }
    } catch {
        typingEl.remove();
        messages.innerHTML += `<div class="message message-ai">Не удалось связаться с сервером.</div>`;
    }

    messages.scrollTop = messages.scrollHeight;
}


// ============================================================
// DECISION ENGINE
// ============================================================

async function initDecisions() {
    if (!requireAuth()) return;
    updateSidebarUser();
    await loadDecisions();
}

async function loadDecisions() {
    const grid = document.getElementById('decisions-grid');
    if (!grid) return;
    renderSkeletons(grid, 3);

    const res = await apiFetch('/decisions/');
    if (!res) return;
    const decisions = await res.json();

    if (decisions.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <i data-lucide="scale"></i>
                <p>Пока нет решений. Создай первое!</p>
                <button class="btn btn-primary" onclick="openDecisionModal()">
                    <i data-lucide="plus"></i> Новое решение
                </button>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    grid.innerHTML = decisions.map(d => `
        <div class="card" onclick="viewDecision(${d.id})">
            <div class="card-title">${escapeHtml(d.title)}</div>
            <div class="card-text">${escapeHtml(d.description || 'Нет описания')}</div>
            <div class="card-meta">
                <span>${formatDate(d.created_at)}</span>
                <span class="card-tag">${(d.options || []).length} вариантов</span>
                <span class="card-tag">${(d.criteria || []).length} критериев</span>
            </div>
        </div>
    `).join('');

    if (window.lucide) lucide.createIcons();
}

function openDecisionModal() {
    document.getElementById('decision-modal').classList.add('active');
}

function closeDecisionModal() {
    document.getElementById('decision-modal').classList.remove('active');
    document.getElementById('decision-form').reset();
}

async function saveDecision(e) {
    e.preventDefault();

    const title = document.getElementById('dec-title').value;
    const description = document.getElementById('dec-description').value;

    // Парсим критерии и варианты из текстовых полей (по строкам)
    const criteriaText = document.getElementById('dec-criteria').value;
    const optionsText = document.getElementById('dec-options').value;

    const criteria = criteriaText.split('\n').filter(l => l.trim()).map(line => {
        const parts = line.split(':');
        return { name: parts[0].trim(), weight: parseInt(parts[1]) || 5 };
    });

    const options = optionsText.split('\n').filter(l => l.trim()).map(name => ({ name: name.trim() }));

    const body = { title, description, criteria, options };

    const res = await apiFetch('/decisions/', { method: 'POST', body: JSON.stringify(body) });
    if (res && res.ok) {
        showToast('Решение создано!');
        closeDecisionModal();
        await loadDecisions();
    } else {
        showToast('Ошибка при создании решения', 'error');
    }
}

async function viewDecision(id) {
    const res = await apiFetch(`/decisions/${id}`);
    if (!res) return;
    const dec = await res.json();

    // Попытаемся получить результаты
    let results = null;
    try {
        const resResults = await apiFetch(`/decisions/${id}/results`);
        if (resResults && resResults.ok) {
            results = await resResults.json();
        }
    } catch {}

    const overlay = document.getElementById('decision-view-modal');
    const content = document.getElementById('decision-view-content');

    let html = `<h3 style="margin-bottom:8px;">${escapeHtml(dec.title)}</h3>`;
    html += `<p style="color:var(--text-secondary); margin-bottom:24px;">${escapeHtml(dec.description || '')}</p>`;

    if (results && results.ranking) {
        const maxScore = results.ranking[0]?.total_score || 1;
        html += `<h4 style="margin-bottom:16px;">Результаты</h4>`;
        results.ranking.forEach((item, i) => {
            const pct = Math.round((item.total_score / maxScore) * 100);
            const isWinner = i === 0;
            html += `
                <div class="result-bar ${isWinner ? 'result-winner' : ''}">
                    <div class="result-bar-header">
                        <span class="result-bar-name">${isWinner ? '🏆 ' : ''}${escapeHtml(item.option_name)}</span>
                        <span class="result-bar-score">${item.total_score} баллов</span>
                    </div>
                    <div class="result-bar-track">
                        <div class="result-bar-fill" style="width: 0%;" data-width="${pct}%"></div>
                    </div>
                </div>
            `;
        });
    } else {
        html += `<p style="color:var(--text-muted);">Нет результатов. Выставите оценки через API (/decisions/${id}/scores).</p>`;
    }

    content.innerHTML = html;
    overlay.classList.add('active');

    // Анимация прогресс-баров
    setTimeout(() => {
        overlay.querySelectorAll('.result-bar-fill').forEach(bar => {
            bar.style.width = bar.dataset.width;
        });
    }, 100);
}

function closeDecisionView() {
    document.getElementById('decision-view-modal').classList.remove('active');
}


// ============================================================
// SIDEBAR & LOGOUT
// ============================================================

function updateSidebarUser() {
    const usernameEl = document.getElementById('sidebar-username');
    const avatarEl = document.getElementById('sidebar-avatar');
    const name = localStorage.getItem('username') || 'User';
    if (usernameEl) usernameEl.textContent = name;
    if (avatarEl) avatarEl.textContent = name.charAt(0).toUpperCase();
}

function logout() {
    clearToken();
    window.location.href = '/login';
}


// ============================================================
// HELPERS
// ============================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
}
