export function loadGoogleMaps(apiKey: string): Promise<void> {
  return new Promise((resolve) => {
    if ((window as any).google?.maps) {
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}`;
    script.async = true;
    script.onload = () => resolve();
    document.body.appendChild(script);
  });
}
