import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiRequest, clearAuthSession, endpoints, getStoredRefreshToken, refreshAuthAccessToken, restoreAuthSession, setAuthSession } from "../api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        restoreAuthSession()
            .then((restoredUser) => {
                if (active) {
                    setUser(restoredUser);
                }
            })
            .finally(() => {
                if (active) {
                    setLoading(false);
                }
            });
        return () => {
            active = false;
        };
    }, []);

    const login = useCallback(async (email, password) => {
        const payload = await apiRequest(endpoints.login, {
            method: "POST",
            body: { email, password },
            auth: false,
        });
        setAuthSession(payload);
        setUser(payload.user);
        return payload.user;
    }, []);

    const register = useCallback(async (values) => {
        return apiRequest(endpoints.register, {
            method: "POST",
            body: values,
            auth: false,
        });
    }, []);

    const logout = useCallback(async () => {
        try {
            await refreshAuthAccessToken();
            const refresh = getStoredRefreshToken();
            if (refresh) {
                await apiRequest(endpoints.logout, {
                    method: "POST",
                    body: { refresh },
                });
            }
        } catch {
            // Local session cleanup still proceeds if the API is unavailable.
        }
        clearAuthSession();
        setUser(null);
    }, []);

    const value = useMemo(() => ({
        user,
        loading,
        login,
        register,
        logout,
        isAuthenticated: Boolean(user),
        hasRole: (role) => Boolean(user?.roles?.includes(role)),
        hasAnyRole: (roles) => roles.some((role) => user?.roles?.includes(role)),
    }), [user, loading, login, register, logout]);

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider.");
    }
    return context;
}
