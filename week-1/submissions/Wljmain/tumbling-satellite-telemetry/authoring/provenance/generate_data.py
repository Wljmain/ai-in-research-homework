# authoring/provenance/generate_data.py

from pathlib import Path
import json
import zlib

import numpy as np
from scipy import signal


# ============================================================
# Configuration
# ============================================================

SEED = 0x4375_2400

FS = 125_000.0
DURATION = 10.0
N = int(FS * DURATION)

FC = 437.5e6
SYMBOL_RATE = 2400.0
RRC_ROLLOFF = 0.35

TARGET_SNR_DB = 5.0

# LEO relative-motion model
V_REL = 7.5e3                 # m/s
C = 299_792_458.0

# Closest approach geometry.
# This controls the curvature of the Doppler trajectory.
H_CLOSE = 150e3               # m

# Oscillator
F_OSC0 = 1.3e3                # Hz
F_OSC_DRIFT = 4.0             # Hz/s
F_OSC_MOD = 0.35              # Hz
F_OSC_MOD_DEPTH = 18.0        # Hz

# Tumbling
F_TUMBLE = 0.20               # Hz
TUMBLE_PHASE = 1.17

# Target location in recording
TARGET_START = 1.1
TARGET_DURATION = 7.2

# Interferers
CW_FREQ = -17_500.0
AFSK_FREQ = 11_500.0
DIGITAL_FREQ = 29_000.0

# Output
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "environment" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE = OUT_DIR / "recording.npy"
PROVENANCE_FILE = Path(__file__).resolve().parent / "generation_metadata.json"


# ============================================================
# Utilities
# ============================================================

def crc16_ccitt(data: bytes) -> int:
    """
    CRC-16-CCITT:
        polynomial = 0x1021
        initial    = 0xFFFF
    """
    crc = 0xFFFF

    for byte in data:
        crc ^= byte << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return crc


def bytes_to_bits(data: bytes) -> np.ndarray:
    """MSB-first bit representation."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """MSB-first bit representation."""
    bits = np.asarray(bits, dtype=np.uint8)

    if len(bits) % 8:
        raise ValueError("Number of bits must be divisible by 8")

    return np.packbits(bits).tobytes()


# ============================================================
# Telemetry
# ============================================================

def generate_telemetry(frame_number: int) -> bytes:
    """
    Generate deterministic but nontrivial telemetry.

    The values are deliberately plausible rather than corresponding
    to a real spacecraft.
    """

    t = frame_number / 4.0

    lat = 34.217 + 0.015 * np.sin(0.13 * t)
    lon = -118.431 + 0.025 * np.cos(0.11 * t)

    alt = 612.7 + 2.8 * np.sin(0.19 * t)
    temp = 274.82 + 3.1 * np.sin(0.07 * t + 0.4)

    pressure = 982.4 + 5.5 * np.cos(0.09 * t)
    solar = 713.2 + 45.0 * np.sin(0.17 * t)
    battery = 7.82 + 0.08 * np.cos(0.05 * t)
    current = 0.417 + 0.025 * np.sin(0.23 * t)

    timestamp = f"2026-09-14T03:{17 + frame_number // 240:02d}:{42 + frame_number % 60:02d}Z"

    text = (
        f"SAT=042\n"
        f"FRAME={frame_number:04d}\n"
        f"TIME={timestamp}\n"
        f"LAT={lat:+08.3f}\n"
        f"LON={lon:+09.3f}\n"
        f"ALT={alt:06.1f}\n"
        f"TEMP={temp:06.2f}\n"
        f"PRESS={pressure:06.1f}\n"
        f"SOLAR={solar:06.1f}\n"
        f"BATT={battery:05.2f}\n"
        f"CURRENT={current:05.3f}"
    )

    return text.encode("ascii")


# ============================================================
# Convolutional encoder
# ============================================================

def convolutional_encode(bits: np.ndarray) -> np.ndarray:
    """
    Rate-1/2, K=7 convolutional code.

    G0 = 171 octal
    G1 = 133 octal

    No tail bits are added because the packet itself is protected
    by CRC and the decoder can use a terminated or nonterminated
    trellis.
    """

    g0 = 0o171
    g1 = 0o133

    state = 0
    encoded = np.empty(len(bits) * 2, dtype=np.uint8)

    for i, bit in enumerate(bits):
        bit = int(bit)

        # 7-bit shift-register state including current input.
        reg = (state << 1) | bit

        out0 = (reg & g0).bit_count() & 1
        out1 = (reg & g1).bit_count() & 1

        encoded[2 * i] = out0
        encoded[2 * i + 1] = out1

        state = reg & 0x3F

    return encoded


# ============================================================
# 7-bit scrambler
# ============================================================

def scramble(bits: np.ndarray, seed: int = 0x5D) -> np.ndarray:
    """
    Self-synchronizing-ish 7-bit XOR scrambler.

    Polynomial:
        x^7 + x^4 + 1

    The state is represented MSB-first.
    """

    state = seed & 0x7F

    out = np.empty_like(bits)

    for i, bit in enumerate(bits):
        # taps corresponding to x^7 + x^4 + 1
        feedback = ((state >> 6) ^ (state >> 3)) & 1

        out[i] = bit ^ feedback

        state = ((state << 1) | feedback) & 0x7F

    return out


# ============================================================
# RRC filter
# ============================================================

def rrc_impulse_response(
    sample_rate: float,
    symbol_rate: float,
    alpha: float,
    span_symbols: int = 10,
) -> np.ndarray:

    samples_per_symbol = sample_rate / symbol_rate

    half_span = span_symbols / 2

    # Enough samples to cover the desired span.
    n = int(np.ceil(half_span * samples_per_symbol))

    t = np.arange(-n, n + 1) / sample_rate

    T = 1.0 / symbol_rate

    h = np.zeros_like(t)

    for i, ti in enumerate(t):

        if abs(ti) < 1e-12:
            h[i] = (
                1
                + alpha * (4 / np.pi - 1)
            )

        elif abs(abs(4 * alpha * ti / T) - 1.0) < 1e-10:

            h[i] = (
                alpha / np.sqrt(2)
                * (
                    (1 + 2 / np.pi)
                    * np.sin(np.pi / (4 * alpha))
                    +
                    (1 - 2 / np.pi)
                    * np.cos(np.pi / (4 * alpha))
                )
            )

        else:

            numerator = (
                np.sin(np.pi * ti / T * (1 - alpha))
                +
                4 * alpha * ti / T
                * np.cos(np.pi * ti / T * (1 + alpha))
            )

            denominator = (
                np.pi * ti / T
                * (1 - (4 * alpha * ti / T) ** 2)
            )

            h[i] = numerator / denominator

    # Normalize to unit energy.
    h /= np.sqrt(np.sum(h ** 2))

    return h


def rrc_bpsk(bits: np.ndarray) -> np.ndarray:
    """
    Generate a BPSK waveform directly on the 125 kS/s grid.
    """

    symbols = 1.0 - 2.0 * bits.astype(np.float64)

    h = rrc_impulse_response(
        FS,
        SYMBOL_RATE,
        RRC_ROLLOFF,
        span_symbols=10,
    )

    # Use scipy's resample_poly-like fractional timing approach
    # by constructing an impulse train and resampling the symbol
    # sequence onto the requested sample grid.
    #
    # First create a high-resolution symbol waveform.
    oversample = 100
    fs_hi = SYMBOL_RATE * oversample

    up = np.zeros(len(symbols) * oversample)
    up[::oversample] = symbols

    h_hi = rrc_impulse_response(
        fs_hi,
        SYMBOL_RATE,
        RRC_ROLLOFF,
        span_symbols=10,
    )

    waveform_hi = signal.fftconvolve(up, h_hi, mode="same")

    duration = len(symbols) / SYMBOL_RATE

    n_out = int(np.ceil(duration * FS))

    t_hi = np.arange(len(waveform_hi)) / fs_hi
    t_out = np.arange(n_out) / FS

    waveform = np.interp(
        t_out,
        t_hi,
        waveform_hi,
    )

    return waveform


# ============================================================
# Doppler
# ============================================================

def doppler_frequency(t: np.ndarray) -> np.ndarray:
    """
    LEO Doppler from local straight-line geometry.

    r(t) = [h, vt]

    vr(t) = v^2 t / sqrt(h^2 + (vt)^2)

    fD = -(fc/c) vr
    """

    radial_velocity = (
        V_REL ** 2 * t
        / np.sqrt(H_CLOSE ** 2 + (V_REL * t) ** 2)
    )

    return -FC / C * radial_velocity


def oscillator_frequency(t: np.ndarray) -> np.ndarray:

    return (
        F_OSC0
        + F_OSC_DRIFT * t
        + F_OSC_MOD_DEPTH
        * np.sin(2 * np.pi * F_OSC_MOD * t)
    )


# ============================================================
# Target generation
# ============================================================

def generate_target(rng: np.random.Generator):

    # --------------------------------------------------------
    # Build packet
    # --------------------------------------------------------

    frame_number = 187

    payload = generate_telemetry(frame_number)

    length = len(payload)

    length_bytes = length.to_bytes(2, "big")

    crc_input = length_bytes + payload
    crc = crc16_ccitt(crc_input)

    crc_bytes = crc.to_bytes(2, "big")

    information = (
        length_bytes
        + payload
        + crc_bytes
    )

    info_bits = bytes_to_bits(information)

    scrambled = scramble(info_bits)

    coded = convolutional_encode(scrambled)

    preamble = np.tile(
        np.array([1, 0], dtype=np.uint8),
        32,
    )

    sync = bytes_to_bits(
        bytes.fromhex("DDAA")
    )

    frame_bits = np.concatenate([
        preamble,
        sync,
        coded,
    ])

    # --------------------------------------------------------
    # BPSK + RRC
    # --------------------------------------------------------

    waveform = rrc_bpsk(frame_bits)

    # Normalize.
    waveform /= np.sqrt(np.mean(waveform ** 2))

    # --------------------------------------------------------
    # Insert into recording
    # --------------------------------------------------------

    start = int(TARGET_START * FS)
    end = min(start + len(waveform), N)

    waveform = waveform[:end - start]

    target = np.zeros(N, dtype=np.complex128)

    target[start:end] = waveform

    # --------------------------------------------------------
    # Doppler and oscillator phase
    # --------------------------------------------------------

    t = np.arange(N) / FS

    active = np.zeros(N, dtype=bool)
    active[start:end] = True

    # Time relative to target center/closest approach.
    t_rel = t - TARGET_START - TARGET_DURATION / 2

    fd = doppler_frequency(t_rel)
    fosc = oscillator_frequency(t_rel)

    instantaneous_frequency = fd + fosc

    phase = np.zeros(N)

    # Integrate frequency into phase.
    phase[1:] = (
        2 * np.pi
        * np.cumsum(instantaneous_frequency[:-1])
        / FS
    )

    # Tumbling envelope.
    amplitude = (
        0.35
        + 0.65
        * np.abs(
            np.cos(
                2 * np.pi * F_TUMBLE * t_rel
                + TUMBLE_PHASE
            )
        )
    )

    # Slow correlated fading.
    fade_noise = rng.normal(0, 1, N)

    b, a = signal.butter(
        2,
        0.5 / (FS / 2),
    )

    fade = signal.filtfilt(
        b,
        a,
        fade_noise,
    )

    fade /= np.std(fade)

    fade_factor = np.exp(0.055 * fade)

    envelope = amplitude * fade_factor

    target *= envelope * np.exp(1j * phase)

    return target, {
        "frame_number": frame_number,
        "payload": payload.decode("ascii"),
        "payload_length": length,
        "crc": f"{crc:04X}",
        "raw_bits": len(info_bits),
        "coded_bits": len(coded),
        "frame_bits": len(frame_bits),
        "doppler_start_hz": float(fd[start]),
        "doppler_end_hz": float(fd[end - 1]),
    }


# ============================================================
# CW interferer
# ============================================================

def generate_cw():

    t = np.arange(N) / FS

    # Keyed CW bursts.
    keying = (
        (np.sin(2 * np.pi * 0.8 * t) > 0.2)
        .astype(float)
    )

    # Smooth the keying edges slightly.
    keying = signal.savgol_filter(
        keying,
        101,
        2,
    )

    phase = (
        2 * np.pi * CW_FREQ * t
    )

    cw = keying * np.exp(1j * phase)

    return cw


# ============================================================
# AFSK interferer
# ============================================================

def generate_afsk(rng):

    baud = 1200.0

    mark = 1200.0
    space = 2200.0

    n_symbols = int(DURATION * baud) + 2

    bits = rng.integers(
        0,
        2,
        n_symbols,
    )

    samples_per_symbol = FS / baud

    symbol_index = np.floor(
        np.arange(N) / samples_per_symbol
    ).astype(int)

    symbol_index = np.minimum(
        symbol_index,
        n_symbols - 1,
    )

    bit_stream = bits[symbol_index]

    freq = np.where(
        bit_stream,
        mark,
        space,
    )

    # Continuous-phase FSK.
    phase = np.zeros(N)

    phase[1:] = (
        2 * np.pi
        * np.cumsum(freq[:-1])
        / FS
    )

    afsk = np.exp(
        1j * (2 * np.pi * AFSK_FREQ * np.arange(N) / FS + phase)
    )

    # Add modest envelope shaping.
    envelope = 0.75

    return envelope * afsk


# ============================================================
# Strong digital interferer
# ============================================================

def generate_digital(rng):

    baud = 4800.0

    n_symbols = int(DURATION * baud) + 2

    bits_i = rng.integers(
        0,
        2,
        n_symbols,
    )

    bits_q = rng.integers(
        0,
        2,
        n_symbols,
    )

    symbols = (
        (1 - 2 * bits_i)
        + 1j * (1 - 2 * bits_q)
    ) / np.sqrt(2)

    samples_per_symbol = FS / baud

    symbol_index = np.floor(
        np.arange(N) / samples_per_symbol
    ).astype(int)

    symbol_index = np.minimum(
        symbol_index,
        n_symbols - 1,
    )

    waveform = symbols[symbol_index]

    # Mild RRC-like bandwidth limitation.
    sos = signal.butter(
        4,
        5000 / (FS / 2),
        output="sos",
    )

    i = signal.sosfilt(sos, waveform.real)
    q = signal.sosfilt(sos, waveform.imag)

    return 1.5 * (i + 1j * q)


# ============================================================
# Impulsive interference
# ============================================================

def generate_impulsive(rng):

    impulsive = np.zeros(N, dtype=np.complex128)

    # A handful of broadband bursts.
    for _ in range(8):

        center = rng.integers(
            0,
            N,
        )

        width = rng.integers(
            int(0.0005 * FS),
            int(0.004 * FS),
        )

        lo = max(0, center - width // 2)
        hi = min(N, center + width // 2)

        burst = (
            rng.normal(0, 1, hi - lo)
            + 1j * rng.normal(0, 1, hi - lo)
        )

        burst *= 3.0

        impulsive[lo:hi] += burst

    return impulsive


# ============================================================
# AWGN
# ============================================================

def add_awgn(
    signal_in,
    snr_db,
    rng,
):
    power = np.mean(
        np.abs(signal_in) ** 2
    )

    noise_power = (
        power
        / 10 ** (snr_db / 10)
    )

    sigma = np.sqrt(
        noise_power / 2
    )

    noise = sigma * (
        rng.normal(size=len(signal_in))
        + 1j * rng.normal(size=len(signal_in))
    )

    return signal_in + noise


# ============================================================
# Main
# ============================================================

def main():

    rng = np.random.default_rng(SEED)

    target, target_info = generate_target(rng)

    cw = generate_cw()

    afsk = generate_afsk(rng)

    digital = generate_digital(rng)

    impulsive = generate_impulsive(rng)

    # --------------------------------------------------------
    # Relative amplitudes
    # --------------------------------------------------------

    # Target is intentionally NOT the strongest signal.
    target *= 1.0
    cw *= 1.8
    afsk *= 1.25
    digital *= 2.0

    combined_clean = (
        target
        + cw
        + afsk
        + digital
        + impulsive
    )

    recording = add_awgn(
        combined_clean,
        TARGET_SNR_DB,
        rng,
    )

    recording = recording.astype(
        np.complex64
    )

    np.save(
        OUT_FILE,
        recording,
    )

    # --------------------------------------------------------
    # Author-side provenance
    # --------------------------------------------------------

    metadata = {
        "seed": SEED,

        "sample_rate_hz": FS,
        "duration_s": DURATION,
        "num_samples": N,
        "dtype": "complex64",

        "carrier_hz": FC,

        "target": {
            "modulation": "BPSK",
            "symbol_rate_baud": SYMBOL_RATE,
            "rrc_rolloff": RRC_ROLLOFF,
            "snr_db": TARGET_SNR_DB,

            "preamble_bits": 64,
            "sync_word": "DDAA",
            "sync_bits": 16,

            "fec": {
                "type": "convolutional",
                "constraint_length": 7,
                "rate": "1/2",
                "g0_octal": "171",
                "g1_octal": "133",
            },

            "scrambler": {
                "polynomial": "x^7 + x^4 + 1",
                "seed": "0x5D",
            },

            "crc": {
                "type": "CRC-16-CCITT",
                "polynomial": "0x1021",
                "initial": "0xFFFF",
                "coverage": "LENGTH + PAYLOAD",
            },

            "doppler": {
                "relative_velocity_mps": V_REL,
                "closest_approach_m": H_CLOSE,
                "formula": (
                    "-fc/c * v^2*t / "
                    "sqrt(h^2+(v*t)^2)"
                ),
            },

            "oscillator": {
                "offset_hz": F_OSC0,
                "drift_hz_per_s": F_OSC_DRIFT,
                "modulation_hz": F_OSC_MOD,
                "modulation_depth_hz": F_OSC_MOD_DEPTH,
            },

            "tumbling": {
                "frequency_hz": F_TUMBLE,
                "phase_rad": TUMBLE_PHASE,
            },

            **target_info,
        },

        "interferers": {
            "cw": {
                "offset_hz": CW_FREQ,
            },
            "afsk": {
                "offset_hz": AFSK_FREQ,
                "baud": 1200,
                "mark_hz": 1200,
                "space_hz": 2200,
            },
            "digital": {
                "offset_hz": DIGITAL_FREQ,
                "baud": 4800,
                "type": "QPSK-like",
            },
        },

        "output": str(OUT_FILE),
    }

    with open(PROVENANCE_FILE, "w") as f:
        json.dump(
            metadata,
            f,
            indent=2,
        )

    print(f"Generated: {OUT_FILE}")
    print(f"Samples:   {N:,}")
    print(f"Duration:  {DURATION:.1f} s")
    print(f"Dtype:     complex64")
    print()
    print("Target:")
    print(f"  payload: {target_info['payload_length']} bytes")
    print(f"  coded bits: {target_info['coded_bits']}")
    print(f"  total bits: {target_info['frame_bits']}")
    print(
        f"  Doppler: "
        f"{target_info['doppler_start_hz']:.1f} → "
        f"{target_info['doppler_end_hz']:.1f} Hz"
    )


if __name__ == "__main__":
    main()