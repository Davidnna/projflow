export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

const REFRESH_TOKEN_KEY = "projflow.refresh-token";
const USER_KEY = "projflow.user";
let accessToken = null;
let refreshPromise = null;

export class ApiError extends Error {
    constructor(message, statusCode = 0, payload = null) {
        super(message);
        this.name = "ApiError";
        this.statusCode = statusCode;
        this.payload = payload;
    }
}

function readSessionValue(key) {
    try {
        return sessionStorage.getItem(key);
    } catch {
        return null;
    }
}

function writeSessionValue(key, value) {
    try {
        if (value === null || value === undefined || value === "") {
            sessionStorage.removeItem(key);
        } else {
            sessionStorage.setItem(key, value);
        }
    } catch {
        return;
    }
}

function getErrorMessage(payload, fallback = "The request could not be completed.") {
    if (!payload) {
        return fallback;
    }
    if (typeof payload.detail === "string") {
        return payload.detail;
    }
    if (typeof payload.message === "string") {
        return payload.message;
    }
    if (typeof payload === "string") {
        return payload;
    }
    const messages = [];
    Object.entries(payload).forEach(([field, value]) => {
        const label = field === "non_field_errors" ? "" : `${field.replaceAll("_", " ")}: `;
        if (Array.isArray(value)) {
            messages.push(`${label}${value.join(" ")}`);
        } else if (typeof value === "string") {
            messages.push(`${label}${value}`);
        } else if (value && typeof value === "object") {
            messages.push(`${label}${getErrorMessage(value, "Please check this field.")}`);
        }
    });
    return messages.length ? messages.join(" ") : fallback;
}

async function parseResponse(response) {
    if (response.status === 204 || response.status === 205) {
        return null;
    }
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        return response.json().catch(() => null);
    }
    return response.text().catch(() => "");
}

async function refreshAccessToken() {
    if (refreshPromise) {
        return refreshPromise;
    }
    const refresh = readSessionValue(REFRESH_TOKEN_KEY);
    if (!refresh || !API_BASE_URL) {
        return false;
    }

    refreshPromise = (async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/token/refresh/`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Accept: "application/json" },
                body: JSON.stringify({ refresh }),
                cache: "no-store",
            });
            const payload = await parseResponse(response);
            if (!response.ok || !payload?.access) {
                clearAuthSession();
                return false;
            }
            accessToken = payload.access;
            if (payload.refresh) {
                writeSessionValue(REFRESH_TOKEN_KEY, payload.refresh);
            }
            return true;
        } catch {
            return false;
        } finally {
            refreshPromise = null;
        }
    })();

    return refreshPromise;
}

export function setAuthSession({ access, refresh, user }) {
    accessToken = access || null;
    writeSessionValue(REFRESH_TOKEN_KEY, refresh || null);
    writeSessionValue(USER_KEY, user ? JSON.stringify(user) : null);
}

export function clearAuthSession() {
    accessToken = null;
    writeSessionValue(REFRESH_TOKEN_KEY, null);
    writeSessionValue(USER_KEY, null);
}

export function getStoredRefreshToken() {
    return readSessionValue(REFRESH_TOKEN_KEY);
}

export async function refreshAuthAccessToken() {
    return refreshAccessToken();
}

export function getStoredUser() {
    const value = readSessionValue(USER_KEY);
    if (!value) {
        return null;
    }
    try {
        return JSON.parse(value);
    } catch {
        return null;
    }
}

export async function restoreAuthSession() {
    const user = getStoredUser();
    const refreshed = await refreshAccessToken();
    if (!refreshed || !user) {
        clearAuthSession();
        return null;
    }
    return user;
}

export async function apiRequest(path, options = {}) {
    if (!API_BASE_URL) {
        throw new ApiError("The API address has not been configured. Set VITE_API_BASE_URL and redeploy the frontend.");
    }

    const {
        method = "GET",
        body,
        formData = false,
        auth = true,
        retry = true,
        headers: customHeaders = {},
        signal,
    } = options;
    const headers = { Accept: "application/json", ...customHeaders };
    if (body !== undefined && !formData) {
        headers["Content-Type"] = "application/json";
    }
    if (auth && accessToken) {
        headers.Authorization = `Bearer ${accessToken}`;
    }

    let response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, {
            method,
            headers,
            body: body === undefined ? undefined : formData ? body : JSON.stringify(body),
            cache: "no-store",
            signal: signal || AbortSignal.timeout(30000),
        });
    } catch (error) {
        if (error.name === "AbortError" || error.name === "TimeoutError") {
            throw new ApiError("The request timed out. Please try again.");
        }
        throw new ApiError("Could not reach the ProjFlow API. Check your connection and try again.");
    }

    if (response.status === 401 && auth && retry) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            return apiRequest(path, { ...options, retry: false });
        }
    }

    const payload = await parseResponse(response);
    if (!response.ok) {
        throw new ApiError(getErrorMessage(payload), response.status, payload);
    }
    return payload;
}

export async function checkPlatformStatus() {
    if (!API_BASE_URL) {
        return { configured: false, api: "not-configured", database: "not-checked" };
    }

    const [healthResult, readinessResult] = await Promise.allSettled([
        apiRequest("/api/health/", { auth: false }),
        apiRequest("/api/ready/", { auth: false }),
    ]);

    const api = healthResult.status === "fulfilled" ? "online" : "unavailable";
    const database = readinessResult.status === "fulfilled"
        && readinessResult.value?.database === "connected"
        ? "connected" : "unavailable";

    return {
        configured: true,
        api,
        database,
        apiPayload: healthResult.status === "fulfilled" ? healthResult.value : null,
    };
}

export function getList(payload) {
    if (Array.isArray(payload)) {
        return payload;
    }
    if (Array.isArray(payload?.results)) {
        return payload.results;
    }
    return [];
}

export const endpoints = {
    login: "/api/auth/token/",
    register: "/api/auth/register/",
    logout: "/api/auth/logout/",
    sessions: "/api/academics/sessions/",
    roster: "/api/academics/roster/",
    rosterImportPreview: "/api/academics/roster-imports/preview/",
    rosterImports: "/api/academics/roster-imports/",
    enrollments: "/api/academics/enrollments/",
    lecturers: "/api/academics/lecturers/",
    lecturerWorkloads: "/api/academics/lecturer-workloads/",
    assignments: "/api/academics/supervisor-assignments/",
};
