const TOKEN_KEY = "token";

const safeSessionStorage = () => {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
};

export const tokenStorage = {
  get() {
    const storage = safeSessionStorage();
    if (!storage) return "";
    return storage.getItem(TOKEN_KEY) || "";
  },
  set(token) {
    const storage = safeSessionStorage();
    if (!storage) return;
    if (token) {
      storage.setItem(TOKEN_KEY, token);
    } else {
      storage.removeItem(TOKEN_KEY);
    }
  },
  remove() {
    const storage = safeSessionStorage();
    if (!storage) return;
    storage.removeItem(TOKEN_KEY);
  }
};

