// src/services/sound.ts

const NOTIFICATION_SOUND_URL = "https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"; // A clean "ding" sound

class SoundService {
    private audio: HTMLAudioElement | null = null;

    constructor() {
        if (typeof window !== "undefined") {
            this.audio = new Audio(NOTIFICATION_SOUND_URL);
            this.audio.preload = "auto";
        }
    }

    play() {
        if (this.audio) {
            this.audio.currentTime = 0;
            this.audio.play().catch(err => {
                // Most browsers block auto-play until user interaction
                console.warn("[SoundService] Playback blocked or failed:", err);
            });
        }
    }
}

export const soundService = new SoundService();
