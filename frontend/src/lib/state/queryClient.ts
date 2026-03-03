type CacheMap = Map<string, unknown>;

const cache: CacheMap = new Map();

export function getCachedQuery<T>(key: string): T | null {
    if (!cache.has(key)) {
        return null;
    }
    return cache.get(key) as T;
}

export function setCachedQuery<T>(key: string, value: T): void {
    cache.set(key, value);
}

export function clearQueryCache(): void {
    cache.clear();
}
