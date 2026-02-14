import React, { createContext, useState, useEffect, useContext } from "react";
import { Storage } from "../services/storage";

interface AuthContextType {
    isAuthenticated: boolean;
    login: (token: string, refresh: string, user: any) => Promise<void>;
    logout: () => Promise<void>;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType>({} as any);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        try {
            const token = await Storage.getToken();
            setIsAuthenticated(!!token);
        } catch (e) {
            setIsAuthenticated(false);
        } finally {
            setLoading(false);
        }
    };

    const login = async (token: string, refresh: string, user: any) => {
        await Storage.setToken(token);
        await Storage.setRefresh(refresh);
        await Storage.setUser(user);
        setIsAuthenticated(true);
    };

    const logout = async () => {
        await Storage.clear();
        setIsAuthenticated(false);
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
