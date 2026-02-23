/**
 * API 封装
 */
const API_BASE = '/api';

class Api {
    constructor() {
        this.token = localStorage.getItem('flashcard_token');
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('flashcard_token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('flashcard_token');
    }

    async request(path, options = {}) {
        const url = API_BASE + path;
        const headers = { ...options.headers };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        const response = await fetch(url, { ...options, headers });

        if (response.status === 401) {
            this.clearToken();
            window.location.reload();
            throw new Error('未登录或登录已过期');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || '请求失败');
        }

        if (response.headers.get('content-type')?.includes('application/zip')) {
            return response.blob();
        }

        return response.json();
    }

    // 认证
    async login(password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ password })
        });
        this.setToken(data.access_token);
        return data;
    }

    async verify() {
        return this.request('/auth/verify');
    }

    // 卡片
    async getCards(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/cards?${query}`);
    }

    async getCard(id) {
        return this.request(`/cards/${id}`);
    }

    async createCard(formData) {
        return this.request('/cards', {
            method: 'POST',
            body: formData,
            headers: {}
        });
    }

    async updateCard(id, data) {
        return this.request(`/cards/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteCard(id) {
        return this.request(`/cards/${id}`, { method: 'DELETE' });
    }

    async batchMoveCards(cardIds, tagIds) {
        return this.request('/cards/batch/move', {
            method: 'POST',
            body: JSON.stringify({ card_ids: cardIds, tag_ids: tagIds })
        });
    }

    async batchDeleteCards(cardIds) {
        return this.request('/cards/batch/delete', {
            method: 'POST',
            body: JSON.stringify({ card_ids: cardIds })
        });
    }

    // 更新卡片媒体（删除）
    async updateCardMedia(cardId, type, value) {
        const data = {};
        if (type === 'image') data.image_path = value;
        if (type === 'audio') data.audio_path = value;
        return this.request(`/cards/${cardId}/media`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    // 更新卡片（带媒体文件）
    async updateCardWithMedia(cardId, formData) {
        return this.request(`/cards/${cardId}/media`, {
            method: 'POST',
            body: formData,
            headers: {}
        });
    }

    // 标签
    async getTags() {
        return this.request('/tags');
    }

    async createTag(name, color = '#3B82F6') {
        return this.request('/tags', {
            method: 'POST',
            body: JSON.stringify({ name, color })
        });
    }

    async updateTag(id, data) {
        return this.request(`/tags/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteTag(id) {
        return this.request(`/tags/${id}`, { method: 'DELETE' });
    }

    async mergeTags(sourceTagIds, newName) {
        return this.request('/tags/merge', {
            method: 'POST',
            body: JSON.stringify({ source_tag_ids: sourceTagIds, new_name: newName })
        });
    }

    // 复习
    async getTodayCards(tagId = null) {
        const params = tagId ? `?tag_id=${tagId}` : '';
        return this.request(`/review/today${params}`);
    }

    async getTodayStats() {
        return this.request('/review/today/stats');
    }

    async submitReview(cardId, mastered) {
        return this.request('/review/submit', {
            method: 'POST',
            body: JSON.stringify({ card_id: cardId, mastered })
        });
    }

    async getWeakCards() {
        return this.request('/review/weak');
    }

    async removeWeakMark(cardId) {
        return this.request(`/review/weak/${cardId}`, { method: 'DELETE' });
    }

    async getCardSchedule(cardId) {
        return this.request(`/review/schedule/${cardId}`);
    }

    // 更新复习阶段状态
    async updateStageReviewed(cardId, stage, reviewed) {
        return this.request(`/review/schedule/${cardId}/stage/${stage}?reviewed=${reviewed}`, {
            method: 'PUT'
        });
    }

    // 导入导出
    async exportData(format = 'csv') {
        return this.request(`/transfer/export?format=${format}`);
    }

    async importData(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/transfer/import', {
            method: 'POST',
            body: formData,
            headers: {}
        });
    }

    async downloadTemplate() {
        const response = await fetch(`${API_BASE}/transfer/template`);
        return response.blob();
    }
}

const api = new Api();
