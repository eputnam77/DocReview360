import { useEffect } from "react";
import { useUserStore } from "@/state/user";
export default function ThemeProvider({ children }) {
    const theme = useUserStore((s) => s.theme);
    useEffect(() => {
        const root = document.documentElement;
        const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const dark = theme === "dark" || (theme === "system" && systemDark);
        root.classList.toggle("dark", dark);
    }, [theme]);
    return <>{children}</>;
}
