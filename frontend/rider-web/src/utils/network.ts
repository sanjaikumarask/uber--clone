type Listener = (online: boolean) => void;

const listeners = new Set<Listener>();

export function watchNetwork(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

window.addEventListener("online", () => {
  listeners.forEach((l) => l(true));
});

window.addEventListener("offline", () => {
  listeners.forEach((l) => l(false));
});
