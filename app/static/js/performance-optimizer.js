/**
 * フロントエンド パフォーマンス最適化
 * - DOM操作の最適化
 * - イベントリスナーの効率化
 * - メモリリーク防止
 * - 非同期処理の最適化
 */

class PerformanceOptimizer {
    constructor() {
        this.domObserver = null;
        this.resizeObserver = null;
        this.throttledFunctions = new Map();
        this.debouncedFunctions = new Map();
        this.virtualScrollConfig = {
            itemHeight: 50,
            bufferSize: 5
        };
        
        this.init();
    }
    
    init() {
        this.setupIntersectionObserver();
        this.setupResizeObserver();
        this.optimizeScrolling();
        this.setupMemoryLeakPrevention();
        this.optimizeImages();
    }
    
    /**
     * Intersection Observer セットアップ（遅延読み込み用）
     */
    setupIntersectionObserver() {
        if ('IntersectionObserver' in window) {
            this.intersectionObserver = new IntersectionObserver(
                (entries) => this.handleIntersection(entries),
                {
                    rootMargin: '50px 0px',
                    threshold: 0.1
                }
            );
        }
    }
    
    /**
     * Resize Observer セットアップ
     */
    setupResizeObserver() {
        if ('ResizeObserver' in window) {
            this.resizeObserver = new ResizeObserver(
                this.throttle((entries) => this.handleResize(entries), 100)
            );
        }
    }
    
    /**
     * スクロール最適化
     */
    optimizeScrolling() {
        // パッシブリスナーでスクロール性能向上
        const scrollElements = [
            document.getElementById('chatMessages'),
            document.getElementById('documentList')
        ];
        
        scrollElements.forEach(element => {
            if (element) {
                element.addEventListener('scroll', 
                    this.throttle(() => this.handleScroll(element), 16),
                    { passive: true }
                );
            }
        });
    }
    
    /**
     * メモリリーク防止
     */
    setupMemoryLeakPrevention() {
        // ページアンロード時のクリーンアップ
        window.addEventListener('beforeunload', () => this.cleanup());
        
        // 定期的なガベージコレクション促進
        setInterval(() => this.performMaintenance(), 30000); // 30秒ごと
    }
    
    /**
     * 画像最適化
     */
    optimizeImages() {
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => {
            if (this.intersectionObserver) {
                this.intersectionObserver.observe(img);
            }
        });
    }
    
    /**
     * スロットル関数
     */
    throttle(func, wait) {
        const key = func.toString();
        
        if (this.throttledFunctions.has(key)) {
            return this.throttledFunctions.get(key);
        }
        
        let timeout;
        let previous = 0;
        
        const throttled = function(...args) {
            const now = Date.now();
            const remaining = wait - (now - previous);
            
            if (remaining <= 0 || remaining > wait) {
                if (timeout) {
                    clearTimeout(timeout);
                    timeout = null;
                }
                previous = now;
                return func.apply(this, args);
            } else if (!timeout) {
                timeout = setTimeout(() => {
                    previous = Date.now();
                    timeout = null;
                    return func.apply(this, args);
                }, remaining);
            }
        };
        
        this.throttledFunctions.set(key, throttled);
        return throttled;
    }
    
    /**
     * デバウンス関数
     */
    debounce(func, wait) {
        const key = func.toString();
        
        if (this.debouncedFunctions.has(key)) {
            return this.debouncedFunctions.get(key);
        }
        
        let timeout;
        const debounced = function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
        
        this.debouncedFunctions.set(key, debounced);
        return debounced;
    }
    
    /**
     * 仮想スクロール実装
     */
    createVirtualList(container, items, renderItem) {
        if (!container || !items.length) return;
        
        const { itemHeight, bufferSize } = this.virtualScrollConfig;
        const containerHeight = container.clientHeight;
        const visibleCount = Math.ceil(containerHeight / itemHeight);
        const totalHeight = items.length * itemHeight;
        
        // スクロールコンテナ作成
        const scrollContainer = document.createElement('div');
        scrollContainer.style.height = `${totalHeight}px`;
        scrollContainer.style.position = 'relative';
        
        // 表示エリア作成
        const viewport = document.createElement('div');
        viewport.style.height = `${containerHeight}px`;
        viewport.style.overflow = 'auto';
        
        let startIndex = 0;
        
        const updateVisibleItems = () => {
            const scrollTop = viewport.scrollTop;
            startIndex = Math.floor(scrollTop / itemHeight);
            const endIndex = Math.min(startIndex + visibleCount + bufferSize, items.length);
            
            // 既存の要素をクリア
            scrollContainer.innerHTML = '';
            
            // 表示する要素を作成
            for (let i = startIndex; i < endIndex; i++) {
                const item = renderItem(items[i], i);
                item.style.position = 'absolute';
                item.style.top = `${i * itemHeight}px`;
                item.style.height = `${itemHeight}px`;
                scrollContainer.appendChild(item);
            }
        };
        
        viewport.addEventListener('scroll', this.throttle(updateVisibleItems, 16));
        viewport.appendChild(scrollContainer);
        container.appendChild(viewport);
        
        updateVisibleItems();
        
        return {
            update: (newItems) => {
                items = newItems;
                updateVisibleItems();
            },
            scrollToIndex: (index) => {
                viewport.scrollTop = index * itemHeight;
            }
        };
    }
    
    /**
     * DOM操作バッチ処理
     */
    batchDOMOperations(operations) {
        return new Promise((resolve) => {
            requestAnimationFrame(() => {
                const fragment = document.createDocumentFragment();
                
                operations.forEach(op => {
                    switch (op.type) {
                        case 'create':
                            const element = document.createElement(op.tag);
                            if (op.properties) {
                                Object.assign(element, op.properties);
                            }
                            if (op.attributes) {
                                Object.entries(op.attributes).forEach(([key, value]) => {
                                    element.setAttribute(key, value);
                                });
                            }
                            if (op.parent === 'fragment') {
                                fragment.appendChild(element);
                            } else if (op.parent) {
                                op.parent.appendChild(element);
                            }
                            break;
                            
                        case 'update':
                            if (op.element) {
                                Object.assign(op.element, op.properties || {});
                            }
                            break;
                            
                        case 'remove':
                            if (op.element && op.element.parentNode) {
                                op.element.parentNode.removeChild(op.element);
                            }
                            break;
                    }
                });
                
                resolve(fragment);
            });
        });
    }
    
    /**
     * イベント委譲の最適化
     */
    setupEventDelegation(container, eventType, selector, handler) {
        if (!container) return;
        
        const delegatedHandler = (event) => {
            const target = event.target.closest(selector);
            if (target) {
                handler(event, target);
            }
        };
        
        container.addEventListener(eventType, delegatedHandler);
        
        return () => container.removeEventListener(eventType, delegatedHandler);
    }
    
    /**
     * メモリプールの実装
     */
    createObjectPool(createFn, resetFn, initialSize = 10) {
        const pool = [];
        
        // 初期オブジェクトを作成
        for (let i = 0; i < initialSize; i++) {
            pool.push(createFn());
        }
        
        return {
            acquire: () => {
                return pool.length > 0 ? pool.pop() : createFn();
            },
            release: (obj) => {
                if (resetFn) resetFn(obj);
                pool.push(obj);
            },
            size: () => pool.length
        };
    }
    
    /**
     * Intersection Observer コールバック
     */
    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    this.intersectionObserver.unobserve(img);
                }
            }
        });
    }
    
    /**
     * Resize Observer コールバック
     */
    handleResize(entries) {
        entries.forEach(entry => {
            // レスポンシブ対応
            const element = entry.target;
            const { width, height } = entry.contentRect;
            
            if (element.classList.contains('chat-container')) {
                this.adjustChatLayout(element, width, height);
            }
        });
    }
    
    /**
     * スクロールハンドラー
     */
    handleScroll(element) {
        // 無限スクロールの実装
        const scrollPosition = element.scrollTop + element.clientHeight;
        const scrollHeight = element.scrollHeight;
        
        if (scrollHeight - scrollPosition < 100) {
            this.triggerLoadMore(element);
        }
    }
    
    /**
     * チャットレイアウト調整
     */
    adjustChatLayout(container, width, height) {
        const isMobile = width < 768;
        
        if (isMobile) {
            container.classList.add('mobile-layout');
        } else {
            container.classList.remove('mobile-layout');
        }
    }
    
    /**
     * 追加読み込みトリガー
     */
    triggerLoadMore(element) {
        if (element.dataset.loading === 'true') return;
        
        element.dataset.loading = 'true';
        
        // 実際のデータ読み込み処理
        this.loadMoreData(element).finally(() => {
            element.dataset.loading = 'false';
        });
    }
    
    /**
     * データの追加読み込み
     */
    async loadMoreData(element) {
        // 具体的な実装は使用箇所で定義
        if (typeof window.loadMoreChatMessages === 'function') {
            await window.loadMoreChatMessages();
        }
    }
    
    /**
     * パフォーマンス測定
     */
    measurePerformance(name, fn) {
        const startTime = performance.now();
        const result = fn();
        const endTime = performance.now();
        
        console.log(`Performance [${name}]: ${endTime - startTime}ms`);
        
        return result;
    }
    
    /**
     * 定期メンテナンス
     */
    performMaintenance() {
        // 未使用のイベントリスナーをクリーンアップ
        this.cleanupUnusedListeners();
        
        // キャッシュの整理
        this.cleanupCache();
        
        // メモリ使用量チェック
        if (window.performance && window.performance.memory) {
            const memory = window.performance.memory;
            const ratio = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
            
            if (ratio > 0.8) {
                console.warn('High memory usage detected:', ratio);
                this.forceGarbageCollection();
            }
        }
    }
    
    /**
     * 未使用リスナーのクリーンアップ
     */
    cleanupUnusedListeners() {
        // 削除されたDOM要素のリスナーをクリーンアップ
        this.throttledFunctions.clear();
        this.debouncedFunctions.clear();
    }
    
    /**
     * キャッシュクリーンアップ
     */
    cleanupCache() {
        // ローカルストレージの古いデータを削除
        const keys = Object.keys(localStorage);
        const now = Date.now();
        
        keys.forEach(key => {
            if (key.startsWith('cache_')) {
                try {
                    const data = JSON.parse(localStorage.getItem(key));
                    if (data.expiry && now > data.expiry) {
                        localStorage.removeItem(key);
                    }
                } catch (e) {
                    // 無効なデータは削除
                    localStorage.removeItem(key);
                }
            }
        });
    }
    
    /**
     * 強制ガベージコレクション
     */
    forceGarbageCollection() {
        // 大きなオブジェクトを作成・削除してGCを促進
        if (window.gc) {
            window.gc();
        } else {
            // フォールバック: 大きな配列を作成して削除
            let temp = new Array(1000000);
            temp = null;
        }
    }
    
    /**
     * クリーンアップ
     */
    cleanup() {
        if (this.intersectionObserver) {
            this.intersectionObserver.disconnect();
        }
        
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        
        this.throttledFunctions.clear();
        this.debouncedFunctions.clear();
    }
}

// グローバル初期化
let performanceOptimizer;

document.addEventListener('DOMContentLoaded', () => {
    performanceOptimizer = new PerformanceOptimizer();
    
    // グローバルアクセス用
    window.performanceOptimizer = performanceOptimizer;
});

// エクスポート
window.PerformanceOptimizer = PerformanceOptimizer;