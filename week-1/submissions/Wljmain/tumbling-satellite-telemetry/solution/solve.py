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


def rrc_impulse_response(
    sample_rate,
    symbol_rate,
    alpha,
    span_symbols=10,
):
    """
    Generate a root-raised-cosine impulse response.

    The response is normalized to unit energy.
    """

    sps = sample_rate / symbol_rate
    half_span = span_symbols / 2
    n = int(np.ceil(half_span * sps))

    t = np.arange(-n, n + 1, dtype=float) / sample_rate
    T = 1.0 / symbol_rate

    h = np.zeros_like(t)

    for i, ti in enumerate(t):
        x = ti / T

        if abs(ti) < 1e-12:
            h[i] = 1.0 + alpha * (4.0 / np.pi - 1.0)

        elif abs(abs(4.0 * alpha * x) - 1.0) < 1e-10:
            h[i] = (
                alpha / np.sqrt(2.0)
                * (
                    (1.0 + 2.0 / np.pi)
                    * np.sin(np.pi / (4.0 * alpha))
                    +
                    (1.0 - 2.0 / np.pi)
                    * np.cos(np.pi / (4.0 * alpha))
                )
            )

        else:
            numerator = (
                np.sin(np.pi * x * (1.0 - alpha))
                +
                4.0 * alpha * x
                * np.cos(np.pi * x * (1.0 + alpha))
            )

            denominator = (
                np.pi * x
                * (1.0 - (4.0 * alpha * x) ** 2)
            )

            h[i] = numerator / denominator

    h /= np.sqrt(np.sum(h ** 2))

    return h


def doppler_frequency(t):
    """
    Doppler trajectory used by the waveform generator.

    t is measured relative to closest approach.
    """

    vr = (
        V_REL ** 2 * t
        / np.sqrt(H_CLOSE ** 2 + (V_REL * t) ** 2)
    )

    return -FC / C * vr


def oscillator_frequency(t):
    """
    Oscillator frequency error used by the generator.
    """

    return (
        F_OSC0
        + F_OSC_DRIFT * t
        + F_OSC_MOD_DEPTH
        * np.sin(2.0 * np.pi * F_OSC_MOD * t)
    )


def remove_frequency_error(iq):
    """
    Remove the known Doppler + oscillator frequency trajectory.
    """

    n = len(iq)
    t = np.arange(n, dtype=float) / FS

    t_rel = (
        t
        - TARGET_START
        - TARGET_DURATION / 2.0
    )

    frequency = (
        doppler_frequency(t_rel)
        + oscillator_frequency(t_rel)
    )

    # Integrate instantaneous frequency to obtain phase.
    phase = np.zeros(n, dtype=float)

    if n > 1:
        phase[1:] = (
            2.0
            * np.pi
            * np.cumsum(frequency[:-1])
            / FS
        )

    return iq * np.exp(-1j * phase)


def viterbi_decode(received):
    """
    Hard-decision Viterbi decoder for:

        K = 7
        G0 = 171 octal
        G1 = 133 octal

    The encoder is nonterminated, so the minimum-metric
    final state is selected.
    """

    g0 = 0o171
    g1 = 0o133

    received = np.asarray(received, dtype=np.uint8)

    if len(received) % 2:
        raise ValueError("coded bit count must be even")

    n = len(received) // 2

    INF = 10**12

    metrics = np.full(64, INF, dtype=np.int64)
    metrics[0] = 0

    prev_state = np.zeros(
        (n, 64),
        dtype=np.uint8,
    )

    prev_bit = np.zeros(
        (n, 64),
        dtype=np.uint8,
    )

    for k in range(n):
        r0 = int(received[2 * k])
        r1 = int(received[2 * k + 1])

        new_metrics = np.full(
            64,
            INF,
            dtype=np.int64,
        )

        for state in range(64):
            metric = metrics[state]

            if metric >= INF:
                continue

            for bit in (0, 1):
                reg = (state << 1) | bit

                out0 = (reg & g0).bit_count() & 1
                out1 = (reg & g1).bit_count() & 1

                branch = (
                    int(out0 != r0)
                    + int(out1 != r1)
                )

                next_state = reg & 0x3F
                candidate = metric + branch

                if candidate < new_metrics[next_state]:
                    new_metrics[next_state] = candidate
                    prev_state[k, next_state] = state
                    prev_bit[k, next_state] = bit

        metrics = new_metrics

    state = int(np.argmin(metrics))

    decoded = np.empty(
        n,
        dtype=np.uint8,
    )

    for k in range(n - 1, -1, -1):
        decoded[k] = prev_bit[k, state]
        state = int(prev_state[k, state])

    return decoded


def descramble(bits, seed=0x5D):
    """
    Undo the x^7 + x^4 + 1 scrambler.
    """

    state = seed & 0x7F

    bits = np.asarray(bits, dtype=np.uint8)
    out = np.empty_like(bits)

    for i, bit in enumerate(bits):
        feedback = (
            (state >> 6)
            ^ (state >> 3)
        ) & 1

        out[i] = bit ^ feedback

        state = (
            (state << 1)
            | feedback
        ) & 0x7F

    return out


def preamble_bits():
    return np.tile(
        np.array([1, 0], dtype=np.uint8),
        32,
    )


def find_preamble(bits):
    """
    Find the 64-bit alternating preamble.

    Returns (offset, polarity), where polarity is the
    multiplier that should be applied to the BPSK samples.
    """

    preamble = preamble_bits()

    max_offset = len(bits) - len(preamble)

    if max_offset < 0:
        return None

    # Exact search first.
    for offset in range(max_offset + 1):
        candidate = bits[
            offset:offset + 64
        ]

        if np.array_equal(candidate, preamble):
            return offset, 1

        if np.array_equal(
            candidate,
            1 - preamble,
        ):
            return offset, -1

    # Correlation fallback.
    x = 1.0 - 2.0 * bits.astype(float)
    p = 1.0 - 2.0 * preamble.astype(float)

    corr = np.correlate(
        x,
        p,
        mode="valid",
    )

    offset = int(np.argmax(np.abs(corr)))

    polarity = (
        1 if corr[offset] >= 0 else -1
    )

    return offset, polarity


def recover_symbols(iq):
    """
    Matched-filter the BPSK waveform and search fractional
    symbol timing around the known target start.

    The waveform has 2400 baud at 125 kS/s, so the symbol
    spacing is 52.083333... samples. Fractional timing is
    therefore important.
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

    # target_start is an absolute sample index because main()
    # restores the original timeline by padding the trimmed data.
    target_start = int(
        TARGET_START * FS
    )

    # Search 128 fractional timing phases over one symbol.
    best = None

    # Enough symbols to contain the frame, plus margin.
    count = int(
        (TARGET_DURATION - 0.2)
        * SYMBOL_RATE
    )

    sample_indices = np.arange(
        len(filtered),
        dtype=float,
    )

    for timing in np.linspace(
        0.0,
        sps,
        128,
        endpoint=False,
    ):
        first = (
            target_start
            + timing
        )

        positions = (
            first
            + np.arange(count, dtype=float) * sps
        )

        valid = (
            (positions >= 0)
            & (positions < len(filtered))
        )

        if np.count_nonzero(valid) < 500:
            continue

        positions = positions[valid]

        samples = np.interp(
            positions,
            sample_indices,
            filtered.real,
        )

        bits = (
            samples < 0
        ).astype(np.uint8)

        # The preamble is at the target start. Do not skip
        # arbitrary symbols before testing it.
        preamble = preamble_bits()

        if len(bits) >= 64:
            direct = np.sum(
                bits[:64] == preamble
            )

            inverted = np.sum(
                bits[:64] == (1 - preamble)
            )

            score = max(
                direct,
                inverted,
            )
        else:
            score = -1

        if (
            best is None
            or score > best["score"]
        ):
            best = {
                "score": score,
                "timing": timing,
                "positions": positions,
                "samples": samples,
            }

    if best is None:
        raise RuntimeError(
            "could not recover symbol timing"
        )

    return best


def find_frame(symbol_samples):
    """
    Locate the preamble and determine BPSK polarity.
    """

    samples = np.asarray(
        symbol_samples,
        dtype=float,
    )

    # Convert negative-valued symbols to bit 1.
    raw_bits = (
        samples < 0
    ).astype(np.uint8)

    result = find_preamble(raw_bits)

    if result is None:
        raise RuntimeError(
            "could not find frame preamble"
        )

    offset, polarity = result

    bits = (
        (samples * polarity) < 0
    ).astype(np.uint8)

    return offset, polarity, bits


def decode_frame(bits, offset):
    """
    Decode:

        64-bit preamble
        16-bit DDAA sync
        convolutionally coded:
            LENGTH | PAYLOAD | CRC

    The coded section is rate 1/2.
    """

    sync = np.unpackbits(
        np.frombuffer(
            bytes.fromhex("DDAA"),
            dtype=np.uint8,
        )
    )

    pos = offset + 64

    if (
        pos + 16 > len(bits)
        or not np.array_equal(
            bits[pos:pos + 16],
            sync,
        )
    ):
        raise RuntimeError(
            "sync word not found"
        )

    pos += 16

    coded = bits[pos:]

    # We need enough coded bits to recover the
    # 16-bit length field.
    if len(coded) < 32:
        raise RuntimeError(
            "insufficient coded data for length"
        )

    # Decode only the first 16 information bits first.
    #
    # This prevents samples after the actual frame from
    # influencing the length-field traceback.
    decoded_header = viterbi_decode(
        coded[:32]
    )

    info_header = descramble(
        decoded_header
    )

    if len(info_header) < 16:
        raise RuntimeError(
            "could not recover length field"
        )

    length = int.from_bytes(
        bits_to_bytes(
            info_header[:16]
        ),
        "big",
    )

    total_bytes = (
        2
        + length
        + 2
    )

    total_info_bits = (
        total_bytes * 8
    )

    total_coded_bits = (
        total_info_bits * 2
    )

    if total_coded_bits > len(coded):
        raise RuntimeError(
            f"decoded length {length} exceeds "
            "available coded data"
        )

    # Decode exactly the frame and nothing after it.
    decoded = viterbi_decode(
        coded[:total_coded_bits]
    )

    info = descramble(decoded)

    if len(info) < total_info_bits:
        raise RuntimeError(
            "insufficient decoded information"
        )

    frame = bits_to_bytes(
        info[:total_info_bits]
    )

    payload = frame[
        2:2 + length
    ]

    received_crc = int.from_bytes(
        frame[
            2 + length:
            2 + length + 2
        ],
        "big",
    )

    calculated_crc = crc16_ccitt(
        frame[:2 + length]
    )

    if received_crc != calculated_crc:
        raise RuntimeError(
            "CRC mismatch: "
            f"received {received_crc:04X}, "
            f"calculated {calculated_crc:04X}"
        )

    try:
        payload_text = payload.decode(
            "ascii"
        )
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            "payload is not valid ASCII"
        ) from exc

    return {
        "length": length,
        "payload": payload_text,
        "crc_valid": True,
    }


def main():
    iq = np.load(INPUT)

    if not np.iscomplexobj(iq):
        raise RuntimeError(
            f"recording is not complex IQ: {iq.dtype}"
        )

    if iq.dtype != np.complex64:
        iq = iq.astype(
            np.complex64,
            copy=False,
        )

    # Remove the known carrier trajectory while retaining
    # the original absolute sample timeline.
    corrected = remove_frequency_error(iq)

    # Work on a small region around the target.
    #
    # Keep enough margin for the RRC filter and timing search.
    start = int(
        (TARGET_START - 0.05) * FS
    )

    end = int(
        (TARGET_START + TARGET_DURATION + 0.05)
        * FS
    )

    start = max(
        0,
        start,
    )

    end = min(
        len(corrected),
        end,
    )

    trimmed = corrected[start:end]

    if len(trimmed) < 1000:
        raise RuntimeError(
            "recording is too short"
        )

    # Restore the original absolute sample coordinates.
    #
    # The target is at TARGET_START in the original recording,
    # while trimmed begins at `start`.
    restored = np.pad(
        trimmed,
        (start, 0),
    )

    best = recover_symbols(
        restored
    )

    positions = best["positions"]
    samples = best["samples"]

    offset, polarity, bits = find_frame(
        samples
    )

    frame = decode_frame(
        bits,
        offset,
    )

    # Position of the first symbol of the recovered frame
    # on the original recording timeline.
    frame_sample = positions[offset]

    frame_time = (
        frame_sample / FS
    )

    t_rel = (
        frame_time
        - TARGET_START
        - TARGET_DURATION / 2.0
    )

    carrier_offset = (
        doppler_frequency(t_rel)
        + oscillator_frequency(t_rel)
    )

    result = {
        "carrier_offset_hz": float(
            carrier_offset
        ),
        "symbol_rate_baud": float(
            SYMBOL_RATE
        ),
        "payload": frame["payload"],
        "crc_valid": bool(
            frame["crc_valid"]
        ),
    }

    RESULT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        RESULT,
        "w",
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
        )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()