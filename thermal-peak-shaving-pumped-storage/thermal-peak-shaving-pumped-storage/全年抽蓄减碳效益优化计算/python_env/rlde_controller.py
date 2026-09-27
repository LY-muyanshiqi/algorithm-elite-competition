"""Individual-level RLDE-F controller adapted from the RLDE-PV reference.

The reference algorithm uses one Q table and one differential scale factor F
per individual.  This module keeps that credit assignment, but exposes a small
stable API for the multi-objective NSLDE environment:

 * state 0/1: the previous trial improved / did not improve.  The controller
   stores the failure state initially, matching the paper's initial state 2
   (MATLAB uses one-based state indexes).
* actions: decrease, keep, or increase F by ``delta``;
* reward: supplied by the caller and expected to be scale-normalized;
* softmax selection uses a temperature and a numerically stable logit shift.
"""

import numpy as np


class RLDEFController:
    """Per-individual Q-learning controller for the DE scale factor."""

    ACTION_DELTAS = np.array([-1.0, 0.0, 1.0], dtype=float)
    SUCCESS_STATE = 0
    FAILURE_STATE = 1

    def __init__(self, n_individuals, f_init=0.5, f_std=0.3, f_delta=0.1,
                 f_min=0.05, f_max=1.0, alpha=0.1, gamma=0.9,
                 temperature=1.0, temperature_min=0.15,
                 temperature_decay=0.995, seed=42):
        if (not isinstance(n_individuals, (int, np.integer)) or
                int(n_individuals) < 1):
            raise ValueError("n_individuals must be positive")
        values = (f_init, f_std, f_delta, f_min, f_max, alpha, gamma,
                  temperature, temperature_min, temperature_decay)
        if not np.all(np.isfinite(values)):
            raise ValueError("RLDE controller parameters must be finite")
        if f_std < 0 or f_delta <= 0 or f_min >= f_max or not f_min <= f_init <= f_max:
            raise ValueError("invalid F bounds or delta")
        if not 0 < alpha <= 1 or not 0 <= gamma <= 1:
            raise ValueError("alpha must be in (0, 1] and gamma in [0, 1]")
        if temperature <= 0 or temperature_min <= 0 or temperature_decay <= 0:
            raise ValueError("temperature parameters must be positive")
        self.n_individuals = int(n_individuals)
        self.f_delta = float(f_delta)
        self.f_init = float(f_init)
        self.f_std = float(f_std)
        self.f_min = float(f_min)
        self.f_max = float(f_max)
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        # Keep the configured episode-start temperature separate from the
        # mutable annealed value.  ``reset`` must not leak exploration decay
        # from one episode into the next.
        self.initial_temperature = float(temperature)
        self.temperature = self.initial_temperature
        self.temperature_min = float(temperature_min)
        self.temperature_decay = float(temperature_decay)
        self.rng = np.random.default_rng(seed)
        self.q = np.zeros((self.n_individuals, 2, 3), dtype=float)
        # RLDE-PV initializes every agent in state 2 (failure).  State 1 is
        # represented by index 0 here and state 2 by index 1.
        self.states = np.full(
            self.n_individuals, self.FAILURE_STATE, dtype=np.int64)
        self.f = np.full(self.n_individuals, self.f_init, dtype=float)
        self.f += self.rng.normal(0.0, self.f_std, self.n_individuals)
        self.f = np.clip(self.f, self.f_min, self.f_max)
        self.action_counts = np.zeros(3, dtype=np.int64)
        self.update_count = 0

    def reset(self, seed=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.q.fill(0.0)
        self.states.fill(self.FAILURE_STATE)
        self.f[:] = np.clip(
            self.f_init + self.rng.normal(0.0, self.f_std, self.n_individuals),
            self.f_min, self.f_max,
        )
        self.temperature = self.initial_temperature
        self.action_counts.fill(0)
        self.update_count = 0

    def _probabilities(self, q_values):
        temperature = max(self.temperature, 1e-8)
        logits = np.nan_to_num(
            np.asarray(q_values, dtype=float), nan=0.0,
            posinf=60.0 * temperature, neginf=-60.0 * temperature,
        ) / temperature
        logits -= np.max(logits)
        weights = np.exp(np.clip(logits, -60.0, 60.0))
        total = weights.sum()
        return weights / total if total > 0 else np.full(3, 1.0 / 3.0)

    def select(self, individual_indices, states=None):
        """Select actions before mutation and return ``(actions, F_values)``."""
        indices = np.asarray(individual_indices, dtype=np.int64)
        if np.any(indices < 0) or np.any(indices >= self.n_individuals):
            raise IndexError("individual index outside controller")
        if states is None:
            states = self.states[indices]
        states = np.asarray(states, dtype=np.int64)
        actions = np.empty(len(indices), dtype=np.int64)
        values = np.empty(len(indices), dtype=float)
        for row, (idx, state) in enumerate(zip(indices, states)):
            state = int(np.clip(state, 0, 1))
            probabilities = self._probabilities(self.q[idx, state])
            action = int(self.rng.choice(3, p=probabilities))
            actions[row] = action
            self.f[idx] = np.clip(
                self.f[idx] + self.ACTION_DELTAS[action] * self.f_delta,
                self.f_min, self.f_max,
            )
            values[row] = self.f[idx]
            self.action_counts[action] += 1
        return actions, values

    def update(self, individual_indices, actions, rewards, next_states):
        """Apply one-step Q-learning updates after trial evaluation."""
        indices = np.asarray(individual_indices, dtype=np.int64)
        actions = np.asarray(actions, dtype=np.int64)
        rewards = np.asarray(rewards, dtype=float)
        next_states = np.asarray(next_states, dtype=np.int64)
        if not (len(indices) == len(actions) == len(rewards) == len(next_states)):
            raise ValueError("RLDE update arrays must have equal length")
        if np.any(indices < 0) or np.any(indices >= self.n_individuals):
            raise IndexError("individual index outside controller")
        if not np.all(np.isfinite(rewards)):
            raise ValueError("RLDE rewards must be finite")
        if np.any((actions < 0) | (actions > 2)):
            raise ValueError("RLDE actions must be in [0, 2]")
        for idx, action, reward, next_state in zip(indices, actions, rewards, next_states):
            idx = int(idx); action = int(action); next_state = int(np.clip(next_state, 0, 1))
            old = self.q[idx, self.states[idx], action]
            target = float(reward) + self.gamma * np.max(self.q[idx, next_state])
            self.q[idx, self.states[idx], action] = old + self.alpha * (target - old)
            self.states[idx] = next_state
        self.temperature = max(self.temperature_min, self.temperature * self.temperature_decay)
        self.update_count += len(indices)

    def summary(self):
        return {
            "action_counts": self.action_counts.astype(int).tolist(),
            "f_min": float(np.min(self.f)),
            "f_max": float(np.max(self.f)),
            "f_mean": float(np.mean(self.f)),
            "q_min": float(np.min(self.q)),
            "q_max": float(np.max(self.q)),
            "temperature": float(self.temperature),
            "updates": int(self.update_count),
        }
