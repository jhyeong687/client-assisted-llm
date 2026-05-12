# Phase 0B Sensitivity Summary

This experiment checks how fragile the toy-model benefit is when local draft speed and network RTT change.

## Best Case

- local_ms_per_token: 1.5
- network_rtt_ms: 3.0
- latency_reduction_pct: 64.5

## Worst Case

- local_ms_per_token: 12.0
- network_rtt_ms: 100.0
- latency_reduction_pct: -119.4

## Product Read

- viable_cells: 14 / 36
- client-assisted inference looks most promising when the local draft model is fast and the client/server round trip is low.
- high RTT hurts because every draft verification window pays the network cost.
