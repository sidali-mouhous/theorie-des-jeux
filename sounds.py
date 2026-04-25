# ─────────────────────────────────────────────
#  Quoridor — Sons procéduraux (sans fichiers)
#  Généré avec numpy + pygame.mixer
# ─────────────────────────────────────────────
import numpy as np
import pygame

SAMPLE_RATE = 44100


def _make_sound(samples: np.ndarray) -> pygame.mixer.Sound:
    """Convertit un tableau float32 [-1,1] en pygame.mixer.Sound stéréo 16-bit."""
    samples = np.clip(samples, -1.0, 1.0)
    s16 = (samples * 32767).astype(np.int16)
    stereo = np.column_stack([s16, s16])   # stéréo
    return pygame.sndarray.make_sound(stereo)


def _envelope(t: np.ndarray, attack=0.005, decay=0.05, sustain=0.6,
              release=0.1, total=None) -> np.ndarray:
    """ADSR simple."""
    if total is None:
        total = t[-1]
    env = np.ones_like(t)
    # Attack
    a_end = attack
    env[t < a_end] = t[t < a_end] / attack
    # Decay
    d_end = a_end + decay
    mask = (t >= a_end) & (t < d_end)
    env[mask] = 1.0 - (1.0 - sustain) * (t[mask] - a_end) / decay
    # Sustain already = sustain
    env[(t >= d_end) & (t < total - release)] = sustain
    # Release
    r_start = total - release
    mask_r = t >= r_start
    env[mask_r] = sustain * (1.0 - (t[mask_r] - r_start) / release)
    return env


# ── Son : déplacement de pion ─────────────────
def _build_move() -> pygame.mixer.Sound:
    dur = 0.12
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Claquement doux : sin à 520 Hz + harmonique decroissante
    f0  = 520
    sig = 0.55 * np.sin(2 * np.pi * f0 * t)
    sig += 0.25 * np.sin(2 * np.pi * f0 * 2 * t)
    sig += 0.10 * np.sin(2 * np.pi * f0 * 3 * t)
    # Noise percussif au début
    noise = np.random.uniform(-1, 1, len(t))
    noise *= np.exp(-t * 80)
    sig   += 0.35 * noise
    # Enveloppe
    env = _envelope(t, attack=0.003, decay=0.04, sustain=0.0, release=0.07, total=dur)
    return _make_sound(sig * env * 0.7)


# ── Son : pose de barrière ────────────────────
def _build_wall() -> pygame.mixer.Sound:
    dur = 0.22
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Choc sourd basse fréquence
    f0  = 180
    sig = 0.6 * np.sin(2 * np.pi * f0 * t)
    sig += 0.3 * np.sin(2 * np.pi * f0 * 1.5 * t) * np.exp(-t * 25)
    # Bruit impulsif
    noise = np.random.uniform(-1, 1, len(t))
    noise *= np.exp(-t * 40)
    sig += 0.45 * noise
    env = _envelope(t, attack=0.002, decay=0.08, sustain=0.0, release=0.10, total=dur)
    return _make_sound(sig * env * 0.75)


# ── Son : victoire ────────────────────────────
def _build_win() -> pygame.mixer.Sound:
    dur   = 1.0
    t     = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    notes = [523.25, 659.25, 783.99, 1046.50]   # do mi sol do (arpège)
    sig   = np.zeros_like(t)
    step  = dur / len(notes)
    for i, freq in enumerate(notes):
        start = int(i * step * SAMPLE_RATE)
        end   = int((i + 1) * step * SAMPLE_RATE)
        tt    = t[start:end] - t[start]
        note  = np.sin(2 * np.pi * freq * tt)
        note += 0.3 * np.sin(2 * np.pi * freq * 2 * tt)
        env   = _envelope(tt, attack=0.01, decay=0.05, sustain=0.7,
                          release=0.08, total=step)
        sig[start:end] += note * env * 0.5
    return _make_sound(sig)


# ── Son : sélection / pop UI ──────────────────
def _build_pop() -> pygame.mixer.Sound:
    dur = 0.07
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    f0  = 900
    sig = np.sin(2 * np.pi * f0 * t)
    sig += 0.2 * np.sin(2 * np.pi * f0 * 1.5 * t)
    env = _envelope(t, attack=0.002, decay=0.03, sustain=0.0, release=0.03, total=dur)
    return _make_sound(sig * env * 0.55)


# ── Chargement global ─────────────────────────
class Sounds:
    def __init__(self):
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
        self.move = _build_move()
        self.wall = _build_wall()
        self.win  = _build_win()
        self.pop  = _build_pop()
        # Volume
        self.move.set_volume(0.8)
        self.wall.set_volume(0.9)
        self.win.set_volume(1.0)
        self.pop.set_volume(0.7)

    def play_move(self):  self.move.play()
    def play_wall(self):  self.wall.play()
    def play_win(self):   self.win.play()
    def play_pop(self):   self.pop.play()
