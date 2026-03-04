import "@testing-library/jest-dom/vitest";

// Align Request implementation with jsdom AbortSignal in router tests.
if (typeof window !== "undefined" && window.Request) {
    globalThis.Request = window.Request;
}
