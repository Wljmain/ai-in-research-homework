# Tumbling Satellite Telemetry

**Author:** William Johnson (UCLA) · **Field:** Physics · **Class level:** Undergraduate · **Agent budget:** 60 min

The solver is given a 10-second complex IQ recording sampled at 125 kS/s containing a weak BPSK spacecraft telemetry signal, several interfering signals, impulsive interference, and noise. The solver must identify and decode the spacecraft signal and produce its carrier-frequency offset, symbol rate, decoded telemetry payload, and CRC validation in `/root/results/answer.json`.

## Difficulty

The spacecraft signal is deliberately weaker than several interfering signals and has a time-varying carrier caused by realistic LEO Doppler, oscillator drift, and satellite tumbling. The solver must therefore distinguish the target from stronger interference, determine the modulation and symbol timing, recover the packet structure, compensate for a changing carrier, and validate the recovered frame with its CRC.

This is representative of work performed by satellite communications engineers and researchers using software-defined radio and digital signal-processing techniques. The recording is synthetic, but its signal-processing challenges and channel impairments are designed to resemble a realistic satellite telemetry reception problem.

## Reference solution

The reference solution uses spectral and time-frequency analysis to identify the weak BPSK signal among the stronger interferers. It estimates the target's frequency evolution, recovers the 2400-baud symbol timing, demodulates the BPSK waveform, and reverses the known packet-processing chain including the scrambler and convolutional coding. It then parses the telemetry frame and independently verifies its CRC before writing the required JSON output.

## Verification

The tests require `/root/results/answer.json` to contain exactly the four fields specified in the task: `carrier_offset_hz`, `symbol_rate_baud`, `payload`, and `crc_valid`. The numerical estimates must be finite, the symbol rate must be within 25 baud of the known 2400-baud transmission rate, the decoded payload must exactly match the telemetry frame contained in the recording, and `crc_valid` must be the JSON boolean `true`.

The ±25-baud symbol-rate tolerance allows for small differences in timing estimation while rejecting substantially incorrect symbol-rate estimates. The carrier-frequency estimate is allowed a ±100-Hz tolerance because the signal has time-varying Doppler and oscillator frequency, so reasonable frequency estimators can differ somewhat depending on their observation interval and interpolation method. The payload and CRC have no tolerance because they provide the strongest evidence that the solver actually recovered and decoded the spacecraft frame rather than identifying the signal parameters or guessing the telemetry contents.

## Attempts

See `authoring/attempts.md`.