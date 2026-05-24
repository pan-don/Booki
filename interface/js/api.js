/**
 * Wrapper untuk panggilan API ke Backend.
 * Sesuaikan BASE_URL dengan port backend yang berjalan. (misal: localhost:8000)
 */
const BASE_URL = "http://localhost:7860/api";

async function requestJson(path, options = {}) {
    const method = options.method || "GET";
    const url = `${BASE_URL}${path}`;
    const startTime = Date.now();
    let response;

    try {
        response = await fetch(url, options);
    } catch (error) {
        console.error(`[API] ${method} ${url} - network error`, error);
        throw new Error(`Network error: ${error.message}`);
    }

    let payload = null;
    try {
        payload = await response.json();
    } catch (error) {
        payload = null;
    }

    const durationMs = Date.now() - startTime;
    if (!response.ok) {
        const message = (payload && (payload.error || payload.message)) || response.statusText;
        console.error(`[API] ${method} ${url} ${response.status} (${durationMs}ms)`, payload);
        throw new Error(`${response.status} ${message}`);
    }

    console.info(`[API] ${method} ${url} ${response.status} (${durationMs}ms)`);
    return payload;
}

const API = {
    // ---- CHAT & RECOMMENDATION ----
    askRecommendation: async (query) => {
        return requestJson("/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
        });
    },

    askDeepQA: async (query, selectedBookIds) => {
        return requestJson("/deep", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: query, book_ids: selectedBookIds })
        });
    },

    // ---- ADMIN CONTROL ----
    addBook: async (bookData) => {
        return requestJson("/admin/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bookData)
        });
    },

    updateBook: async (id, bookData) => {
        return requestJson(`/admin/update/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bookData)
        });
    },

    deleteBook: async (id) => {
        return requestJson(`/admin/delete/${id}`, {
            method: "DELETE"
        });
    },

    getDatabaseStatus: async () => {
        return requestJson("/admin/status", {
            method: "GET"
        });
    }
};