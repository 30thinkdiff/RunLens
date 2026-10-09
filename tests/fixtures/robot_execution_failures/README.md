# Real robot fixture: UCI Robot Execution Failures, LP1

`lp1.data` is the unchanged LP1 file from the official UCI archive. It contains
88 robot execution trials, each with 15 real six-axis force/torque measurements;
columns are Fx, Fy, Fz, Tx, Ty, Tz. Labels describe entire trials.

Creators: Luis Seabra Lopes and Luis M. Camarinha-Matos, Universidade Nova de Lisboa.
Citation: Lopes, L. & Camarinha-Matos, L. (1998). Robot Execution Failures [Dataset].
UCI Machine Learning Repository. DOI: https://doi.org/10.24432/C5M89N.

Official metadata and license:
https://archive.ics.uci.edu/dataset/138/robot+execution+failures

Official download (only lp1.data is redistributed here):
https://archive.ics.uci.edu/static/public/138/robot+execution+failures.zip

Retrieved 2026-10-09. Size: 27,345 bytes.
SHA-256: `e146de5aeaffd864f0e57ce2fe0b58e98582c3e808e6c0e8deb9b25a54ef0cb5`.

## License and modifications

The dataset has its own **CC BY 4.0** license, not the project's MIT license.
License: https://creativecommons.org/licenses/by/4.0/
Legal text: https://creativecommons.org/licenses/by/4.0/legalcode
Keep attribution and license information when redistributing this fixture.
The fixture is unmodified; converted examples and explicit injected perturbations
are derived versions and must be identified as such. No additional restrictions
are imposed on the dataset. Other archive files/programs are not included or run.

## Honest interpretation

No per-sample measured timestamps are supplied. The source describes regularly
sampled 15-point trials with a 315 ms observation window. Our example uses a
declared **constructed** 0.021 s step (315 ms / 15), with trials starting 1 s apart
to preserve boundaries. This is a plotting/import convention, not a measured
sampling clock or confirmation of the source's endpoint convention.
Do not derive physical frequency or real timing-defect claims from this clock.
Original measurement units are not specified in the file; values are kept unchanged.

The first ten normal-labeled trials form the reference split. All remaining trials
form the detection split, retaining original trial IDs and within-trial order.
No trial occurs in both splits. Event class labels are not point-level outlier
truth and do not validate hardware-fault inference or sample-level accuracy.

Tests retain small known-signal examples for numerical contracts and also run on
these real measurements, both unchanged and in separately identified copies with
known injected spikes/missing samples. Tests never download data from the network.
