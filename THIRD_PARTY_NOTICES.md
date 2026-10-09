# Third-party data

Original RunLens code is MIT licensed. The following test data retains its own
license and is not relicensed under MIT:

| Files | Source / creators | License |
| --- | --- | --- |
| `tests/fixtures/robot_execution_failures/lp1.data` | Luis Seabra Lopes and Luis M. Camarinha-Matos, UCI Robot Execution Failures, LP1 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

Citation: Lopes, L. & Camarinha-Matos, L. (1998). Robot Execution Failures [Dataset].
UCI Machine Learning Repository. https://doi.org/10.24432/C5M89N.

[Official metadata and license](https://archive.ics.uci.edu/dataset/138/robot+execution+failures)
and [fixture provenance](tests/fixtures/robot_execution_failures/README.md).
The original fixture is unchanged. Converted examples retain original measurements,
add an explicitly constructed plotting clock, and separate whole trial IDs into
reference and detection splits. Injected test perturbations are identified as modifications.
No hardware-fault certification or endorsement by the original authors is implied.

Installed libraries retain their respective licenses; their source/binaries are not
bundled in this repository.
