# Solar-wind spectral index

**Author:** Zesen Huang (UCLA EPSS) · **Field:** physics / space plasma physics · **Class level:** 1 (a valid task) · **Agent budget:** 30 min

Estimate the inertial-range spectral index of solar-wind magnetic-field fluctuations from one hour of 4 Hz magnetometer data that has telemetry gaps and instrumental spikes.

This is the worked example for the class. It is a **level 1** task: correctly built and honestly graded, but not yet hard. Frontier agents should solve it. The last section lists what would make it harder.

## Difficulty

A space physicist does this routinely. It takes about half an hour, most of it cleaning the data. What makes it more than a textbook exercise:

- **The record is dirty.** `nan` gaps break naive FFT and Welch code, and eight single-sample spikes of 40–80 nT add white power that flattens the spectrum. A solver that skips despiking gets about −1.23, which fails.
- **The answer is not a famous number.** The data were generated with slope −1.30, away from Kolmogorov's −5/3 and Iroshnikov–Kraichnan's −3/2. Writing down a textbook value fails.
- **The frequency range matters.** Above about 0.5 Hz the spectrum steepens to the kinetic range. Fitting too wide a band gives about −1.86.

The data are synthetic: a random-phase Fourier series with a prescribed spectrum, plus a mean field, noise, gaps and spikes (`authoring/provenance/generate_data.py`). Real spacecraft data would be the level-3 version of this task.

## Reference solution

Fill the gaps by linear interpolation, and replace samples more than 10 nT from a 9-point running median. Then take the Welch power spectrum of each component (Hann window, 2048-sample segments), sum the three into the trace, and fit a straight line to log10(PSD) against log10(f) over 0.02–0.2 Hz. The result is −1.3465 (`solution/solve.py`).

## Verification

The verifier runs in a separate container with no network access. It sees only `/root/results/spectrum.json`, and it passes (reward 1) if `spectral_index` is a finite number in **[−1.39, −1.27]**.

The window is calibrated, not "truth ± tolerance". `authoring/evidence/calibrate.py` runs the shipped data through five defensible estimators and four wrong routes:

| Estimator | Slope | Result |
|---|---|---|
| The generating slope (a perfect method) | −1.300 | pass |
| Welch 2048, Hann (reference) | −1.347 | pass |
| Welch 1024 / 4096 | −1.324 / −1.334 | pass |
| Welch 2048, Blackman | −1.368 | pass |
| Periodogram, 12 log bins | −1.352 | pass |
| No despiking | −1.231 | fail |
| Fit over 0.02–1.5 Hz | −1.865 | fail |
| Guess −3/2 / −5/3 | −1.500 / −1.667 | fail |

Every defensible estimate is steeper than the generating slope, because interpolating across gaps removes high-frequency power. A window centered on −1.30 would have been unfair to good solutions. Every row sits at least 0.02 inside or 0.04 outside the window.

## How this could get harder (levels 2–4)

- **Level 2 (honest):** run a frontier agent, read its whole trajectory, and fix anything it exposed about the instruction or the verifier.
- **Level 3 (hard):** stop telling the solver the inertial range. Ask for the spectral break frequency and the kinetic-range slope as well. Use a real Parker Solar Probe interval, with its reaction-wheel noise lines and irregular gaps.
- **Level 4 (benchmark-ready):** ask for a quantity no textbook gives, such as the anisotropy of the fluctuations relative to the local mean field. That needs a scale-dependent analysis, and agents tend to fall back on a global mean field.

## Attempts

See `authoring/attempts.md`.
