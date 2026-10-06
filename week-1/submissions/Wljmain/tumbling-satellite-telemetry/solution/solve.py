import json
from pathlib import Path

import numpy as np
from scipy import signal


FS = 125_000.0
SYMBOL_RATE = 2400.0
RRC_ROLLOFF = 0.35

FC = 437.5e6
C = 299_792_458.0
V_REL = 7.5e3
H_CLOSE = 150e3

F_OSC0 = 1.3e3
F_OSC_DRIFT = 4.0
F_OSC_MOD = 0.35
F_OSC_MOD_DEPTH = 18.0

TARGET_START = 1.1
TARGET_DURATION = 7.2

RESULT = Path("/root/results/answer.json")
INPUT = Path("/root/data/recording.npy")


def crc16_ccitt(data):
    crc = 0xFFFF

    for byte in data:
        crc ^= byte << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return crc


def bits_to_bytes(bits):
    bits = np.asarray(bits, dtype=np.uint8)

    if len(bits) % 8:
        raise ValueError("bit count is not divisible by 8")

    return np.packbits(bits).tobytes()


def rrc_impulse_response(sample_rate, symbol_rate, alpha,
                         span_symbols=10):

    sps = sample_rate / symbol_rate
    half_span = span_symbols / 2
    n = int(np.ceil(half_span * sps))

    t = np.arange(-n, n + 1) / sample_rate
    T = 1.0 / symbol_rate

    h = np.zeros_like(t)

    for i, ti in enumerate(t):

        if abs(ti) < 1e-12:
            h[i] = 1 + alpha * (4 / np.pi - 1)

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

    h /= np.sqrt(np.sum(h ** 2))

    return h


def doppler_frequency(t):
    vr = (
        V_REL ** 2 * t
        / np.sqrt(H_CLOSE ** 2 + (V_REL * t) ** 2)
    )

    return -FC / C * vr


def oscillator_frequency(t):
    return (
        F_OSC0
        + F_OSC_DRIFT * t
        + F_OSC_MOD_DEPTH
        * np.sin(2 * np.pi * F_OSC_MOD * t)
    )


def remove_frequency_error(iq):
    """
    Remove the exact frequency trajectory used by the generator.
    """

    n = len(iq)
    t = np.arange(n) / FS

    t_rel = t - TARGET_START - TARGET_DURATION / 2

    frequency = (
        doppler_frequency(t_rel)
        + oscillator_frequency(t_rel)
    )

    phase = np.zeros(n)

    phase[1:] = (
        2 * np.pi
        * np.cumsum(frequency[:-1])
        / FS
    )

    return iq * np.exp(-1j * phase)


def viterbi_decode(received):
    """
    Hard-decision Viterbi decoder for the exact encoder:

        K = 7
        G0 = 171 octal
        G1 = 133 octal

    The encoder is nonterminated.
    """

    g0 = 0o171
    g1 = 0o133

    received = np.asarray(received, dtype=np.uint8)

    if len(received) % 2:
        raise ValueError("coded bit count must be even")

    n = len(received) // 2

    INF = 10**12

    # Encoder state is the previous six input bits.
    metrics = np.full(64, INF, dtype=np.int64)
    metrics[0] = 0

    prev_state = np.zeros((n, 64), dtype=np.uint8)
    prev_bit = np.zeros((n, 64), dtype=np.uint8)

    for k in range(n):

        r0 = int(received[2 * k])
        r1 = int(received[2 * k + 1])

        new_metrics = np.full(64, INF, dtype=np.int64)

        for state in range(64):

            metric = metrics[state]

            if metric >= INF:
                continue

            for bit in (0, 1):

                reg = (state << 1) | bit

                out0 = (reg & g0).bit_count() & 1
                out1 = (reg & g1).bit_count() & 1

                branch = (out0 != r0) + (out1 != r1)

                next_state = reg & 0x3F

                candidate = metric + branch

                if candidate < new_metrics[next_state]:
                    new_metrics[next_state] = candidate
                    prev_state[k, next_state] = state
                    prev_bit[k, next_state] = bit

        metrics = new_metrics

    # Nonterminated encoder: select best final state.
    state = int(np.argmin(metrics))

    decoded = np.empty(n, dtype=np.uint8)

    for k in range(n - 1, -1, -1):
        decoded[k] = prev_bit[k, state]
        state = int(prev_state[k, state])

    return decoded


def descramble(bits, seed=0x5D):
    state = seed & 0x7F

    out = np.empty_like(bits)

    for i, bit in enumerate(bits):

        feedback = ((state >> 6) ^ (state >> 3)) & 1

        out[i] = bit ^ feedback

        state = ((state << 1) | feedback) & 0x7F

    return out


def score_preamble(bits):
    """
    Score a candidate bitstream against the known 64-bit
    alternating preamble.
    """

    preamble = np.tile(
        np.array([1, 0], dtype=np.uint8),
        32,
    )

    if len(bits) < len(preamble):
        return -1

    a = np.sum(bits[:64] == preamble)
    b = np.sum(bits[:64] == (1 - preamble))

    return max(a, b)


def recover_symbols(iq):
    """
    Matched filter and search fractional symbol timing.

    The generator creates the waveform using a 100x intermediate
    grid and interpolates it to 125 kS/s, so blindly assuming
    an integer 52-sample symbol period is undesirable.
    """

    h = rrc_impulse_response(
        FS,
        SYMBOL_RATE,
        RRC_ROLLOFF,
        span_symbols=10,
    )

    filtered = signal.fftconvolve(
        iq,
        h,
        mode="same",
    )

    sps = FS / SYMBOL_RATE

    # Search a set of timing offsets.
    best = None

    # The target contains 64 preamble bits followed by
    # 16 sync bits and 8*(2 + payload + 2)*2 coded bits.
    # We search around the target start and allow several
    # samples of timing uncertainty.
    target_start = int(TARGET_START * FS)

    for timing in np.linspace(0, sps, 128, endpoint=False):

        first = target_start + int(5 * sps + timing)

        count = int(
            (TARGET_DURATION - 0.2) * SYMBOL_RATE
        )

        positions = first + np.arange(count) * sps

        valid = (
            (positions >= 0)
            & (positions < len(filtered))
        )

        if np.sum(valid) < 500:
            continue

        positions = positions[valid]

        samples = np.interp(
            positions,
            np.arange(len(filtered)),
            filtered.real,
        )

        bits = (samples < 0).astype(np.uint8)

        score = score_preamble(bits)

        if best is None or score > best[0]:
            best = (score, timing, positions, samples)

    if best is None:
        raise RuntimeError("could not recover symbol timing")

    return best


def find_frame(symbol_samples):
    """
    Search around the beginning of the target for the frame.

    Because the exact target start is known to the reference
    solution, this is deliberately much less exploratory than
    the student's blind task.
    """

    samples = symbol_samples

    # Try both BPSK polarities.
    candidates = []

    for polarity in (1, -1):

        vals = samples * polarity
        bits = (vals < 0).astype(np.uint8)

        # Search for the 64-bit alternating preamble.
        preamble = np.tile(
            np.array([1, 0], dtype=np.uint8),
            32,
        )

        for offset in range(0, min(100, len(bits) - 80)):

            a = bits[offset:offset + 64]

            if np.array_equal(a, preamble):
                candidates.append(
                    (offset, polarity, bits)
                )

            elif np.array_equal(a, 1 - preamble):
                candidates.append(
                    (offset, -polarity, bits)
                )

    if not candidates:
        # Fall back to maximum correlation.
        preamble_pm = np.tile(
            np.array([1, -1]),
            32,
        )

        x = 1 - 2 * (samples < 0).astype(np.int8)

        corr = np.correlate(
            x.astype(float),
            preamble_pm.astype(float),
            mode="valid",
        )

        offset = int(np.argmax(np.abs(corr)))

        polarity = (
            1 if corr[offset] > 0 else -1
        )

        bits = (
            ((samples * polarity) < 0)
            .astype(np.uint8)
        )

        candidates.append(
            (offset, polarity, bits)
        )

    return candidates[0]


def decode_frame(bits, offset):
    """
    Decode:

        64-bit preamble
        16-bit DDAA sync
        convolutionally coded LENGTH + PAYLOAD + CRC
    """

    sync = np.unpackbits(
        np.frombuffer(bytes.fromhex("DDAA"), dtype=np.uint8)
    )

    pos = offset + 64

    if not np.array_equal(
        bits[pos:pos + 16],
        sync,
    ):
        raise RuntimeError("sync word not found")

    pos += 16

    # The remainder is coded at rate 1/2.
    coded = bits[pos:]

    # The frame should contain at least length + CRC.
    if len(coded) < 64:
        raise RuntimeError("insufficient coded data")

    # Decode a range of possible coded lengths.
    decoded = viterbi_decode(coded)

    # Descramble the information bits.
    info = descramble(decoded)

    # First two bytes are the payload length.
    if len(info) < 32:
        raise RuntimeError("insufficient decoded information")

    length = int.from_bytes(
        bits_to_bytes(info[:16]),
        "big",
    )

    total_bytes = 2 + length + 2
    total_bits = total_bytes * 8

    if total_bits > len(info):
        raise RuntimeError(
            f"decoded length {length} exceeds available data"
        )

    frame = bits_to_bytes(
        info[:total_bits]
    )

    payload = frame[2:2 + length]

    received_crc = int.from_bytes(
        frame[2 + length:2 + length + 2],
        "big",
    )

    calculated_crc = crc16_ccitt(
        frame[:2 + length]
    )

    if received_crc != calculated_crc:
        raise RuntimeError(
            f"CRC mismatch: received "
            f"{received_crc:04X}, calculated "
            f"{calculated_crc:04X}"
        )

    return {
        "length": length,
        "payload": payload.decode("ascii"),
        "crc_valid": True,
    }


def main():

    iq = np.load(INPUT)

    if iq.dtype != np.complex64:
        iq = iq.astype(np.complex64)

    corrected = remove_frequency_error(iq)

    # Work only on the target region.
    start = int((TARGET_START - 0.05) * FS)
    end = int(
        (TARGET_START + TARGET_DURATION + 0.05)
        * FS
    )

    corrected = corrected[start:end]

    # Use the known target start after trimming.
    best = recover_symbols(
        np.pad(
            corrected,
            (int(TARGET_START * FS), 0),
        )
    )

    _, timing, positions, samples = best

    offset, polarity, bits = find_frame(samples)

    frame = decode_frame(bits, offset)

    # Estimate carrier offset at beginning of recovered frame.
    #
    # The frequency correction model is known, so evaluate the
    # generated instantaneous frequency at the recovered frame.
    #
    # `offset` is relative to the sampled target waveform.
    sample_index = int(
        TARGET_START * FS
        + offset * FS / SYMBOL_RATE
    )

    t = sample_index / FS

    t_rel = (
        t
        - TARGET_START
        - TARGET_DURATION / 2
    )

    carrier_offset = (
        doppler_frequency(t_rel)
        + oscillator_frequency(t_rel)
    )

    result = {
        "carrier_offset_hz": float(carrier_offset),
        "symbol_rate_baud": float(SYMBOL_RATE),
        "payload": frame["payload"],
        "crc_valid": bool(frame["crc_valid"]),
    }

    RESULT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(RESULT, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()