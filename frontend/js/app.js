/**
 * 主应用逻辑
 */

// ============ 状态管理 ============
const state = {
    currentPage: 'today',
    todayCards: [],
    todayIndex: 0,
    allCards: [],
    weakCards: [],
    tags: [],
    selectedCards: new Set(),
    currentFilterTag: null,
    isFlipped: false
};

// ============ 工具函数 ============
function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

function getErrorMessage(err) {
    if (typeof err === 'string') return err;
    if (err && err.message) return err.message;
    if (err && err.detail) return err.detail;
    return '未知错误';
}

function showToast(message, type = 'info') {
    const container = $('.toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function formatDate(dateStr, showYear = false) {
    if (!dateStr) return '-';
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]);
        const day = parseInt(parts[2]);
        const currentYear = new Date().getFullYear();
        if (showYear || year !== currentYear) {
            return `${month}/${day}/${year}`;
        }
        return `${month}/${day}`;
    }
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
}

function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

// ============ 初始化 ============
async function init() {
    if (!api.token) {
        showLoginPage();
        return;
    }

    try {
        await api.verify();
        showApp();
        await loadTags();
        navigateTo('today');
    } catch (err) {
        console.error('验证失败:', err);
        showLoginPage();
    }
}

function showLoginPage() {
    $('.login-container').style.display = 'flex';
    $('.app-container').style.display = 'none';
    $('.bottom-nav').style.display = 'none';
}

function showApp() {
    $('.login-container').style.display = 'none';
    $('.app-container').style.display = 'block';
    $('.bottom-nav').style.display = 'flex';
}

// ============ 登录 ============
async function handleLogin(e) {
    e.preventDefault();
    const password = $('#password').value;
    
    try {
        await api.login(password);
        showApp();
        await loadTags();
        navigateTo('today');
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// ============ 导航 ============
function navigateTo(page) {
    state.currentPage = page;
    state.selectedCards.clear();
    
    $$('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });
    
    switch (page) {
        case 'today':
            loadTodayPage();
            break;
        case 'add':
            loadAddPage();
            break;
        case 'weak':
            loadWeakPage();
            break;
        case 'manage':
            loadManagePage();
            break;
    }
}

// ============ 加载标签 ============
async function loadTags() {
    try {
        state.tags = await api.getTags();
    } catch (err) {
        console.error('加载标签失败:', err);
        state.tags = [];
    }
}

// ============ 今日复习页面 ============
async function loadTodayPage() {
    const content = $('#page-content');
    content.innerHTML = '<div class="empty-state"><p>加载中...</p></div>';
    
    try {
        const [cards, stats] = await Promise.all([
            api.getTodayCards(state.currentFilterTag),
            api.getTodayStats()
        ]);
        
        state.todayCards = cards || [];
        state.todayIndex = 0;
        state.isFlipped = false;
        
        renderTodayPage(stats);
    } catch (err) {
        console.error('加载今日卡片失败:', err);
        content.innerHTML = `<div class="empty-state"><p>加载失败: ${getErrorMessage(err)}</p></div>`;
    }
}

function renderTodayPage(stats) {
    const content = $('#page-content');
    
    if (state.todayCards.length === 0) {
        content.innerHTML = `
            <div class="page-header">
                <h1>今日复习</h1>
                <span class="stats-badge">全部完成!</span>
            </div>
            <div class="empty-state">
                <div class="icon">🎉</div>
                <h2>太棒了！</h2>
                <p>今天没有需要复习的内容</p>
            </div>
        `;
        return;
    }
    
    let filterHtml = `
        <div class="filter-bar">
            <div class="filter-chip ${!state.currentFilterTag ? 'active' : ''}" onclick="filterToday(null)">全部</div>
            ${state.tags.map(tag => `
                <div class="filter-chip ${state.currentFilterTag === tag.id ? 'active' : ''}" 
                     onclick="filterToday(${tag.id})">${tag.name}</div>
            `).join('')}
        </div>
    `;
    
    content.innerHTML = `
        <div class="page-header">
            <h1>今日复习</h1>
            <span class="stats-badge">${state.todayIndex + 1} / ${state.todayCards.length}</span>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${(state.todayIndex / state.todayCards.length) * 100}%"></div>
        </div>
        
        ${filterHtml}
        
        <div class="flashcard-container">
            <div class="flashcard" onclick="flipCard()">
                <div class="flashcard-front">
                    ${renderCardContent(state.todayCards[state.todayIndex], 'question')}
                </div>
                <div class="flashcard-back">
                    ${renderCardContent(state.todayCards[state.todayIndex], 'answer')}
                </div>
            </div>
        </div>
        
        <div class="review-actions">
            <button class="btn btn-danger" onclick="submitReview(false)">😕 没掌握</button>
            <button class="btn btn-success" onclick="submitReview(true)">😊 掌握了</button>
        </div>
    `;
}

function renderCardContent(card, side) {
    if (!card) return '<div class="flashcard-content"><p>加载中...</p></div>';
    
    const isQuestion = side === 'question';
    const text = isQuestion ? card.question : card.answer;
    
    // 只有答案面才显示图片和音频
    let mediaHtml = '';
    if (!isQuestion) {
        if (card.image_path) {
            mediaHtml += `<img src="/media/${card.image_path}" alt="图片">`;
        }
        if (card.audio_path) {
            mediaHtml += `<audio controls src="/media/${card.audio_path}"></audio>`;
        }
    }
    
    const tags = card.tags || [];
    const tagsHtml = tags.map(tag => 
        `<span class="tag" style="background: ${tag.color}20; color: ${tag.color}">${tag.name}</span>`
    ).join('');
    
    return `
        <div class="flashcard-content">
            <h2>${isQuestion ? '问题' : '答案'}</h2>
            <p>${text}</p>
            ${mediaHtml ? `<div class="flashcard-media">${mediaHtml}</div>` : ''}
        </div>
        ${isQuestion ? '<p class="flashcard-hint">点击卡片查看答案</p>' : ''}
        <div class="flashcard-tags">${tagsHtml}</div>
    `;
}

function flipCard() {
    const card = $('.flashcard');
    if (card) {
        card.classList.toggle('flipped');
        state.isFlipped = !state.isFlipped;
    }
}

async function filterToday(tagId) {
    state.currentFilterTag = tagId;
    await loadTodayPage();
}

async function submitReview(mastered) {
    if (!state.isFlipped) {
        showToast('请先查看答案', 'error');
        return;
    }
    
    const card = state.todayCards[state.todayIndex];
    if (!card) return;
    
    try {
        const result = await api.submitReview(card.id, mastered);
        showToast(result.message || '已提交', mastered ? 'success' : 'info');
        
        state.todayIndex++;
        state.isFlipped = false;
        
        if (state.todayIndex >= state.todayCards.length) {
            loadTodayPage();
        } else {
            const stats = await api.getTodayStats();
            renderTodayPage(stats);
        }
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// ============ 添加页面 ============
function loadAddPage() {
    const content = $('#page-content');
    
    const tagsHtml = state.tags.map(tag => `
        <div class="tag-option" data-id="${tag.id}" onclick="toggleTag(this)">
            ${tag.name}
        </div>
    `).join('');
    
    content.innerHTML = `
        <div class="page-header">
            <h1>添加卡片</h1>
        </div>
        
        <form id="add-form" onsubmit="handleAddCard(event)">
            <div class="form-group">
                <label class="form-label">问题 *</label>
                <textarea class="form-textarea" id="add-question" required placeholder="输入问题..."></textarea>
            </div>
            
            <div class="form-group">
                <label class="form-label">答案 *</label>
                <textarea class="form-textarea" id="add-answer" required placeholder="输入答案..."></textarea>
            </div>
            
            <div class="form-group">
                <label class="form-label">标签</label>
                <div class="tag-selector" id="tag-selector">
                    ${tagsHtml || '<span style="color: var(--gray-500)">暂无标签，请在管理页面添加</span>'}
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">图片（可选）</label>
                <div class="file-upload" onclick="$('#add-image').click()">
                    <input type="file" id="add-image" accept="image/*" onchange="previewImage(this)">
                    <p>📷 点击上传图片或拍照</p>
                    <div class="file-preview" id="image-preview"></div>
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">音频（可选）</label>
                <div class="file-upload" onclick="$('#add-audio').click()">
                    <input type="file" id="add-audio" accept="audio/*" onchange="previewAudio(this)">
                    <p>🎵 点击上传音频或录音</p>
                    <div class="file-preview" id="audio-preview"></div>
                </div>
            </div>
            
            <button type="submit" class="btn btn-primary btn-block">保存卡片</button>
        </form>
    `;
}

function toggleTag(el) {
    el.classList.toggle('selected');
}

function previewImage(input) {
    const preview = $('#image-preview');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            preview.innerHTML = `<img src="${e.target.result}">`;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function previewAudio(input) {
    const preview = $('#audio-preview');
    if (input.files && input.files[0]) {
        preview.innerHTML = `<p>已选择: ${input.files[0].name}</p>`;
    }
}

async function handleAddCard(e) {
    e.preventDefault();
    
    const question = $('#add-question').value;
    const answer = $('#add-answer').value;
    const image = $('#add-image').files[0];
    const audio = $('#add-audio').files[0];
    
    const selectedTags = Array.from($$('.tag-option.selected')).map(el => el.dataset.id);
    
    const formData = new FormData();
    formData.append('question', question);
    formData.append('answer', answer);
    formData.append('tag_ids', selectedTags.join(','));
    if (image) formData.append('image', image);
    if (audio) formData.append('audio', audio);
    
    try {
        await api.createCard(formData);
        showToast('卡片添加成功！', 'success');
        loadAddPage();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// ============ 弱项页面 ============
async function loadWeakPage() {
    const content = $('#page-content');
    content.innerHTML = '<div class="empty-state"><p>加载中...</p></div>';
    
    try {
        state.weakCards = await api.getWeakCards() || [];
        renderWeakPage();
    } catch (err) {
        console.error('加载弱项失败:', err);
        content.innerHTML = `<div class="empty-state"><p>加载失败: ${getErrorMessage(err)}</p></div>`;
    }
}

function renderWeakPage() {
    const content = $('#page-content');
    
    if (state.weakCards.length === 0) {
        content.innerHTML = `
            <div class="page-header">
                <h1>⚠️ 弱项</h1>
            </div>
            <div class="empty-state">
                <div class="icon">💪</div>
                <h2>没有弱项</h2>
                <p>继续保持！所有内容都掌握得很好</p>
            </div>
        `;
        return;
    }
    
    content.innerHTML = `
        <div class="page-header">
            <h1>⚠️ 弱项</h1>
            <span class="stats-badge">${state.weakCards.length} 项</span>
        </div>
        
        <div class="card-list">
            ${state.weakCards.map(card => `
                <div class="card-item" onclick="showCardDetail(${card.id})">
                    <div class="card-info">
                        <div class="card-question">${card.question}</div>
                        <div class="card-meta">
                            ${(card.tags || []).map(t => `<span class="tag" style="background: ${t.color}20; color: ${t.color}">${t.name}</span>`).join('')}
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); removeWeak(${card.id})">移除</button>
                </div>
            `).join('')}
        </div>
    `;
}

async function removeWeak(cardId) {
    try {
        await api.removeWeakMark(cardId);
        showToast('已移除弱项标记', 'success');
        loadWeakPage();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// ============ 卡片详情/编辑模态框 ============
async function showCardDetail(cardId) {
    try {
        const card = await api.getCard(cardId);
        const schedule = await api.getCardSchedule(cardId);
        
        const cardTags = card.tags || [];
        const cardTagIds = cardTags.map(t => t.id);
        
        const createdDate = card.created_at ? card.created_at.split(' ')[0].split('T')[0] : '';
        
        const modalBody = $('#modal-body');
        modalBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">问题</label>
                <textarea class="form-textarea" id="edit-question">${card.question}</textarea>
            </div>
            <div class="form-group">
                <label class="form-label">答案</label>
                <textarea class="form-textarea" id="edit-answer">${card.answer}</textarea>
            </div>
            <div class="form-group">
                <label class="form-label">标签</label>
                <div class="tag-selector" id="edit-tags">
                    ${state.tags.map(tag => `
                        <div class="tag-option ${cardTagIds.includes(tag.id) ? 'selected' : ''}" 
                             data-id="${tag.id}" onclick="toggleTag(this)">
                            ${tag.name}
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">首次学习日期</label>
                <input type="date" class="form-input" id="edit-created-at" value="${createdDate}">
                <p style="font-size: 12px; color: var(--gray-500); margin-top: 4px;">
                    修改后复习计划会自动重新计算
                </p>
            </div>
            <div class="form-group">
                <label class="select-all-label" style="cursor: pointer;">
                    <input type="checkbox" id="edit-is-weak" ${card.is_weak ? 'checked' : ''} style="width: 18px; height: 18px;">
                    <span>标记为弱项 ⚠️</span>
                </label>
            </div>
            <div class="form-group">
                <label class="form-label">图片</label>
                ${card.image_path ? `
                    <img src="/media/${card.image_path}" style="max-width: 100%; max-height: 150px; border-radius: 8px; margin-bottom: 8px;">
                    <button type="button" class="btn btn-sm btn-danger" onclick="removeMedia(${card.id}, 'image')" style="margin-bottom: 8px;">删除图片</button>
                ` : ''}
                <div class="file-upload" onclick="$('#edit-image').click()" style="padding: 12px;">
                    <input type="file" id="edit-image" accept="image/*" onchange="previewEditImage(this)">
                    <p style="margin: 0;">📷 ${card.image_path ? '替换图片' : '上传图片'}</p>
                    <div id="edit-image-preview"></div>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">音频</label>
                ${card.audio_path ? `
                    <audio controls src="/media/${card.audio_path}" style="width: 100%; margin-bottom: 8px;"></audio>
                    <button type="button" class="btn btn-sm btn-danger" onclick="removeMedia(${card.id}, 'audio')" style="margin-bottom: 8px;">删除音频</button>
                ` : ''}
                <div class="file-upload" onclick="$('#edit-audio').click()" style="padding: 12px;">
                    <input type="file" id="edit-audio" accept="audio/*" onchange="previewEditAudio(this)">
                    <p style="margin: 0;">🎵 ${card.audio_path ? '替换音频' : '上传音频'}</p>
                    <div id="edit-audio-preview"></div>
                </div>
            </div>
            <div style="background: var(--gray-100); padding: 12px; border-radius: 8px; margin-top: 16px;">
                <p><strong>当前阶段:</strong> ${schedule.stage_description}</p>
                <p><strong>下次复习:</strong> ${formatDate(card.next_review) || '已完成'}</p>
            </div>
            
            <div class="form-group" style="margin-top: 16px;">
                <label class="form-label">复习计划</label>
                <div style="background: var(--gray-50); border-radius: 8px; overflow: hidden;">
                    ${(schedule.schedule || []).map((s, idx) => {
                        const stageNames = ['', '第1次 (+1天)', '第2次 (+3天)', '第3次 (+1周)', '第4次 (+2周)', '第5次 (+1月)', '第6次 (+3月)', '第7次 (+1年)'];
                        const today = new Date().toISOString().split('T')[0];
                        const isOverdue = !s.reviewed && s.scheduled_date < today;
                        return `
                            <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid var(--gray-200); ${isOverdue ? 'background: #FEF2F2;' : ''}">
                                <div style="flex: 1;">
                                    <span style="font-weight: 500;">${stageNames[s.stage] || '阶段' + s.stage}</span>
                                    <span style="color: var(--gray-500); margin-left: 8px;">${formatDate(s.scheduled_date, true)}</span>
                                    ${isOverdue ? '<span style="color: #EF4444; margin-left: 8px; font-size: 12px;">逾期</span>' : ''}
                                </div>
                                <label style="display: flex; align-items: center; cursor: pointer;">
                                    <input type="checkbox" 
                                           ${s.reviewed ? 'checked' : ''} 
                                           onchange="toggleStageReviewed(${card.id}, ${s.stage}, this.checked)"
                                           style="width: 18px; height: 18px; margin-right: 6px;">
                                    <span style="font-size: 13px; color: ${s.reviewed ? 'var(--success)' : 'var(--gray-500)'};">
                                        ${s.reviewed ? '已复习' : '未复习'}
                                    </span>
                                </label>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            <div style="margin-top: 16px;">
                <button type="button" class="btn btn-danger btn-sm" onclick="deleteCardFromModal(${card.id})">🗑️ 删除此卡片</button>
            </div>
        `;
        
        // 保存当前卡片ID用于后续操作
        modalBody.dataset.cardId = cardId;
        
        $('#modal-title').textContent = '编辑卡片';
        $('#modal-confirm').textContent = '保存修改';
        $('#modal-confirm').style.display = 'inline-flex';
        $('#modal-confirm').onclick = () => saveCardEdit(cardId);
        $('.modal-overlay').classList.add('show');
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

function previewEditImage(input) {
    const preview = $('#edit-image-preview');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            preview.innerHTML = `<img src="${e.target.result}" style="max-width: 100%; max-height: 100px; margin-top: 8px; border-radius: 4px;">`;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function previewEditAudio(input) {
    const preview = $('#edit-audio-preview');
    if (input.files && input.files[0]) {
        preview.innerHTML = `<p style="margin-top: 8px; color: var(--success);">已选择: ${input.files[0].name}</p>`;
    }
}

async function removeMedia(cardId, type) {
    if (!confirm(`确定删除${type === 'image' ? '图片' : '音频'}吗？`)) return;
    try {
        await api.updateCardMedia(cardId, type, null);
        showToast('已删除', 'success');
        showCardDetail(cardId);
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

async function saveCardEdit(cardId) {
    const question = $('#edit-question').value.trim();
    const answer = $('#edit-answer').value.trim();
    const createdAt = $('#edit-created-at').value;
    const isWeak = $('#edit-is-weak').checked;
    const selectedTags = Array.from($$("#edit-tags .tag-option.selected")).map(el => parseInt(el.dataset.id));
    const newImage = $('#edit-image').files[0];
    const newAudio = $('#edit-audio').files[0];
    
    if (!question || !answer) {
        showToast('问题和答案不能为空', 'error');
        return;
    }
    
    try {
        // 如果有新的媒体文件，先上传
        if (newImage || newAudio) {
            const formData = new FormData();
            formData.append('question', question);
            formData.append('answer', answer);
            formData.append('tag_ids', selectedTags.join(','));
            if (newImage) formData.append('image', newImage);
            if (newAudio) formData.append('audio', newAudio);
            await api.updateCardWithMedia(cardId, formData);
        }
        
        // 更新其他字段
        const updateData = {
            question,
            answer,
            tag_ids: selectedTags,
            is_weak: isWeak
        };
        if (createdAt) {
            updateData.created_at = createdAt;
        }
        await api.updateCard(cardId, updateData);
        
        showToast('保存成功', 'success');
        closeModal();
        
        if (state.currentPage === 'manage') {
            await loadCardsTab();
        } else if (state.currentPage === 'weak') {
            await loadWeakPage();
        } else if (state.currentPage === 'today') {
            await loadTodayPage();
        }
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}


// ============ 管理页面 ============
let manageTab = 'cards';

async function loadManagePage() {
    const content = $('#page-content');
    
    content.innerHTML = `
        <div class="page-header">
            <h1>📁 管理</h1>
        </div>
        
        <div class="tabs">
            <div class="tab ${manageTab === 'cards' ? 'active' : ''}" onclick="switchManageTab('cards')">卡片</div>
            <div class="tab ${manageTab === 'tags' ? 'active' : ''}" onclick="switchManageTab('tags')">标签</div>
            <div class="tab ${manageTab === 'transfer' ? 'active' : ''}" onclick="switchManageTab('transfer')">导入/导出</div>
        </div>
        
        <div id="manage-content"></div>
    `;
    
    switchManageTab(manageTab);
}

async function switchManageTab(tab) {
    manageTab = tab;
    $$('.tabs .tab').forEach(t => t.classList.toggle('active', t.textContent.trim() === 
        (tab === 'cards' ? '卡片' : tab === 'tags' ? '标签' : '导入/导出')));
    
    switch (tab) {
        case 'cards':
            await loadCardsTab();
            break;
        case 'tags':
            await loadTagsTab();
            break;
        case 'transfer':
            loadTransferTab();
            break;
    }
}

// ============ 卡片管理 Tab ============
async function loadCardsTab() {
    const container = $('#manage-content');
    container.innerHTML = '<p>加载中...</p>';
    
    try {
        const params = {};
        if (state.currentFilterTag) params.tag_id = state.currentFilterTag;
        state.allCards = await api.getCards(params) || [];
        await loadTags();
        renderCardsTab();
    } catch (err) {
        console.error('加载卡片失败:', err);
        container.innerHTML = `<p>加载失败: ${getErrorMessage(err)}</p>`;
    }
}

function renderCardsTab() {
    const container = $('#manage-content');
    
    let filterHtml = `
        <div class="filter-bar">
            <div class="filter-chip ${!state.currentFilterTag ? 'active' : ''}" onclick="filterCards(null)">全部</div>
            ${state.tags.map(tag => `
                <div class="filter-chip ${state.currentFilterTag === tag.id ? 'active' : ''}" 
                     onclick="filterCards(${tag.id})">${tag.name} (${tag.card_count || 0})</div>
            `).join('')}
        </div>
    `;
    
    let searchHtml = `
        <div class="search-box">
            <input type="text" class="search-input" placeholder="搜索卡片..." 
                   onchange="searchCards(this.value)">
        </div>
    `;
    
    // 检查是否全选了当前列表
    const allSelected = state.allCards.length > 0 && state.allCards.every(card => state.selectedCards.has(card.id));
    
    let batchHtml = `
        <div class="batch-bar ${state.selectedCards.size > 0 ? 'show' : ''}" id="batch-bar">
            <span>已选 ${state.selectedCards.size} 项</span>
            <div class="batch-actions">
                <button class="btn btn-sm btn-outline" onclick="clearSelection()">取消选择</button>
                <button class="btn btn-sm btn-outline" onclick="showMoveModal()">移动</button>
                <button class="btn btn-sm btn-danger" onclick="batchDelete()">删除</button>
            </div>
        </div>
    `;
    
    if (state.allCards.length === 0) {
        container.innerHTML = `
            ${filterHtml}
            <div class="empty-state">
                <div class="icon">📭</div>
                <h2>暂无卡片</h2>
                <p>点击下方"添加"创建第一张卡片</p>
            </div>
        `;
        return;
    }
    
    // 全选复选框
    let selectAllHtml = `
        <div class="select-all-bar">
            <label class="select-all-label">
                <input type="checkbox" class="card-checkbox" 
                       ${allSelected ? 'checked' : ''} 
                       onchange="toggleSelectAll(this.checked)">
                <span>全选当前 ${state.allCards.length} 张卡片</span>
            </label>
        </div>
    `;
    
    container.innerHTML = `
        ${filterHtml}
        ${searchHtml}
        ${batchHtml}
        ${selectAllHtml}
        
        <div class="card-list">
            ${state.allCards.map(card => `
                <div class="card-item ${state.selectedCards.has(card.id) ? 'selected' : ''}">
                    <input type="checkbox" class="card-checkbox" 
                           ${state.selectedCards.has(card.id) ? 'checked' : ''}
                           onchange="toggleCardSelect(${card.id})">
                    <div class="card-info" onclick="showCardDetail(${card.id})">
                        <div class="card-question">${card.question}</div>
                        <div class="card-meta">
                            ${card.is_weak ? '<span class="weak-badge">弱项</span>' : ''}
                            ${(card.tags || []).map(t => `<span class="tag" style="background: ${t.color}20; color: ${t.color}">${t.name}</span>`).join('')}
                            <span>下次: ${formatDate(card.next_review)}</span>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); showCardDetail(${card.id})">编辑</button>
                </div>
            `).join('')}
        </div>
    `;
}

// 全选/取消全选当前列表
function toggleSelectAll(checked) {
    if (checked) {
        state.allCards.forEach(card => state.selectedCards.add(card.id));
    } else {
        state.allCards.forEach(card => state.selectedCards.delete(card.id));
    }
    renderCardsTab();
}

// 取消所有选择
function clearSelection() {
    state.selectedCards.clear();
    renderCardsTab();
}

async function filterCards(tagId) {
    state.currentFilterTag = tagId;
    state.selectedCards.clear();
    await loadCardsTab();
}

async function searchCards(keyword) {
    try {
        const params = { search: keyword };
        if (state.currentFilterTag) params.tag_id = state.currentFilterTag;
        state.allCards = await api.getCards(params) || [];
        renderCardsTab();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

function toggleCardSelect(cardId) {
    if (state.selectedCards.has(cardId)) {
        state.selectedCards.delete(cardId);
    } else {
        state.selectedCards.add(cardId);
    }
    renderCardsTab();
}

function showMoveModal() {
    const modalBody = $('#modal-body');
    
    modalBody.innerHTML = `
        <p style="margin-bottom: 16px;">选择目标标签：</p>
        <div class="tag-selector" id="move-tags">
            ${state.tags.map(tag => `
                <div class="tag-option" data-id="${tag.id}" onclick="toggleTag(this)">
                    ${tag.name}
                </div>
            `).join('')}
        </div>
    `;
    
    $('#modal-title').textContent = '移动卡片';
    $('#modal-confirm').textContent = '确定';
    $('#modal-confirm').style.display = 'inline-flex';
    $('#modal-confirm').onclick = confirmMove;
    $('.modal-overlay').classList.add('show');
}

async function confirmMove() {
    const selectedTags = Array.from($$("#move-tags .tag-option.selected")).map(el => parseInt(el.dataset.id));
    
    if (selectedTags.length === 0) {
        showToast('请选择至少一个标签', 'error');
        return;
    }
    
    try {
        await api.batchMoveCards(Array.from(state.selectedCards), selectedTags);
        showToast('移动成功', 'success');
        closeModal();
        state.selectedCards.clear();
        await loadTags();
        await loadCardsTab();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

async function batchDelete() {
    if (!confirm(`确定删除选中的 ${state.selectedCards.size} 张卡片吗？`)) return;
    
    try {
        await api.batchDeleteCards(Array.from(state.selectedCards));
        showToast('删除成功', 'success');
        state.selectedCards.clear();
        await loadCardsTab();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// ============ 标签管理 Tab ============
async function loadTagsTab() {
    await loadTags();
    renderTagsTab();
}

function renderTagsTab() {
    const container = $('#manage-content');
    
    container.innerHTML = `
        <button class="btn btn-primary btn-block" onclick="showAddTagModal()" style="margin-bottom: 16px;">
            + 新建标签
        </button>
        
        <div class="tag-list">
            ${state.tags.map(tag => `
                <div class="tag-item">
                    <div class="tag-item-info">
                        <div class="tag-color" style="background: ${tag.color}"></div>
                        <span>${tag.name}</span>
                        <span style="color: var(--gray-500)">(${tag.card_count || 0}张)</span>
                    </div>
                    <div class="tag-item-actions">
                        <button class="btn btn-sm btn-outline" onclick="showEditTagModal(${tag.id}, '${tag.name}', '${tag.color}')">编辑</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteTag(${tag.id})">删除</button>
                    </div>
                </div>
            `).join('')}
        </div>
        
        ${state.tags.length >= 2 ? `
            <div class="transfer-section" style="margin-top: 20px;">
                <h3>合并标签</h3>
                <p style="color: var(--gray-500); margin-bottom: 12px;">选择要合并的标签，输入新名称</p>
                <div class="tag-selector" id="merge-tags" style="margin-bottom: 12px;">
                    ${state.tags.map(tag => `
                        <div class="tag-option" data-id="${tag.id}" onclick="toggleTag(this)">
                            ${tag.name}
                        </div>
                    `).join('')}
                </div>
                <input type="text" class="form-input" id="merge-name" placeholder="合并后的新名称" style="margin-bottom: 12px;">
                <button class="btn btn-primary" onclick="mergeTags()">合并</button>
            </div>
        ` : ''}
    `;
}

function showAddTagModal() {
    const modalBody = $('#modal-body');
    
    modalBody.innerHTML = `
        <div class="form-group">
            <label class="form-label">标签名称</label>
            <input type="text" class="form-input" id="new-tag-name" placeholder="输入标签名称">
        </div>
        <div class="form-group">
            <label class="form-label">颜色</label>
            <input type="color" id="new-tag-color" value="#3B82F6" style="width: 100%; height: 40px;">
        </div>
    `;
    
    $('#modal-title').textContent = '新建标签';
    $('#modal-confirm').textContent = '确定';
    $('#modal-confirm').style.display = 'inline-flex';
    $('#modal-confirm').onclick = confirmAddTag;
    $('.modal-overlay').classList.add('show');
}

async function confirmAddTag() {
    const name = $('#new-tag-name').value.trim();
    const color = $('#new-tag-color').value;
    
    if (!name) {
        showToast('请输入标签名称', 'error');
        return;
    }
    
    try {
        await api.createTag(name, color);
        showToast('创建成功', 'success');
        closeModal();
        await loadTagsTab();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

function showEditTagModal(id, name, color) {
    const modalBody = $('#modal-body');
    
    modalBody.innerHTML = `
        <div class="form-group">
            <label class="form-label">标签名称</label>
            <input type="text" class="form-input" id="edit-tag-name" value="${name}">
        </div>
        <div class="form-group">
            <label class="form-label">颜色</label>
            <input type="color" id="edit-tag-color" value="${color}" style="width: 100%; height: 40px;">
        </div>
    `;
    
    $('#modal-title').textContent = '编辑标签';
    $('#modal-confirm').textContent = '确定';
    $('#modal-confirm').style.display = 'inline-flex';
    $('#modal-confirm').onclick = () => confirmEditTag(id);
    $('.modal-overlay').classList.add('show');
}

async function confirmEditTag(id) {
    const name = $('#edit-tag-name').value.trim();
    const color = $('#edit-tag-color').value;
    
    if (!name) {
        showToast('请输入标签名称', 'error');
        return;
    }
    
    try {
        await api.updateTag(id, { name, color });
        showToast('更新成功', 'success');
        closeModal();
        await loadTagsTab();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

async function deleteTag(id) {
    if (!confirm('确定删除此标签吗？卡片不会被删除。')) return;
    
    try {
        await api.deleteTag(id);
        showToast('删除成功', 'success');
        await loadTags();
        renderTagsTab();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

async function mergeTags() {
    const selectedTags = Array.from($$("#merge-tags .tag-option.selected")).map(el => parseInt(el.dataset.id));
    const newName = $('#merge-name').value.trim();
    
    if (selectedTags.length < 2) {
        showToast('请至少选择两个标签', 'error');
        return;
    }
    
    if (!newName) {
        showToast('请输入合并后的名称', 'error');
        return;
    }
    
    try {
        await api.mergeTags(selectedTags, newName);
        showToast('合并成功', 'success');
        await loadTags();
        renderTagsTab();
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// ============ 导入导出 Tab ============
function loadTransferTab() {
    const container = $('#manage-content');
    
    container.innerHTML = `
        <div class="transfer-section">
            <h3>📤 导出数据</h3>
            <p style="color: var(--gray-500); margin-bottom: 16px;">导出所有卡片和媒体文件为 ZIP 压缩包</p>
            <div class="transfer-buttons">
                <button class="btn btn-outline" onclick="exportData('csv')">导出 CSV</button>
                <button class="btn btn-primary" onclick="exportData('json')">导出 JSON (完整备份)</button>
            </div>
        </div>
        
        <div class="transfer-section">
            <h3>📥 导入数据</h3>
            <p style="color: var(--gray-500); margin-bottom: 16px;">支持 CSV、JSON 或包含媒体的 ZIP 文件</p>
            <div class="file-upload" onclick="$('#import-file').click()">
                <input type="file" id="import-file" accept=".csv,.json,.zip" onchange="importData(this)">
                <p>点击选择文件上传</p>
            </div>
            <button class="btn btn-outline" onclick="downloadTemplate()" style="margin-top: 12px;">
                下载 CSV 模板
            </button>
        </div>
    `;
}

async function exportData(format) {
    try {
        showToast('正在导出...', 'info');
        const blob = await api.exportData(format);
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `flashcards_export_${new Date().toISOString().slice(0,10)}.zip`;
        a.click();
        URL.revokeObjectURL(url);
        
        showToast('导出成功', 'success');
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

async function importData(input) {
    if (!input.files || !input.files[0]) return;
    
    try {
        showToast('正在导入...', 'info');
        const result = await api.importData(input.files[0]);
        showToast(`导入成功！卡片: ${result.cards_imported}, 标签: ${result.tags_imported}`, 'success');
        
        if (result.errors && result.errors.length > 0) {
            console.warn('导入警告:', result.errors);
        }
        
        await loadTags();
        input.value = '';
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

async function downloadTemplate() {
    try {
        const blob = await api.downloadTemplate();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'import_template.csv';
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// ============ 模态框 ============
function closeModal() {
    $('.modal-overlay').classList.remove('show');
    $('#modal-confirm').style.display = 'inline-flex';
    $('#modal-confirm').textContent = '确定';
}

// ============ 启动 ============
document.addEventListener('DOMContentLoaded', init);

// 切换复习阶段状态
async function toggleStageReviewed(cardId, stage, reviewed) {
    try {
        await api.updateStageReviewed(cardId, stage, reviewed);
        showToast(reviewed ? '已标记为已复习' : '已标记为未复习', 'success');
        // 刷新卡片详情
        showCardDetail(cardId);
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

// 从模态框中删除卡片
async function deleteCardFromModal(cardId) {
    if (!confirm('确定删除此卡片吗？此操作不可撤销。')) return;
    try {
        await api.deleteCard(cardId);
        showToast('删除成功', 'success');
        closeModal();
        // 刷新当前页面
        if (state.currentPage === 'manage') {
            await loadCardsTab();
        } else if (state.currentPage === 'weak') {
            await loadWeakPage();
        } else if (state.currentPage === 'today') {
            await loadTodayPage();
        }
    } catch (err) {
        showToast(getErrorMessage(err), 'error');
    }
}

