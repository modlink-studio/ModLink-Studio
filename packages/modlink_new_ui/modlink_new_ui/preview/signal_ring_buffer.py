from __future__ import annotations

import numpy as np


class SignalRingBuffer:
    def __init__(self, channels: int, max_samples: int) -> None:
        self.channels = channels
        self.max_samples = max_samples
        self.data = np.zeros((channels, max_samples), dtype=np.float32)
        self.ptr = 0
        self.full = False

    def extend(self, new_data: np.ndarray) -> None:
        chunk_size = new_data.shape[1]
        if chunk_size == 0:
            return
        if chunk_size >= self.max_samples:
            self.data[:, :] = new_data[:, -self.max_samples:]
            self.ptr = 0
            self.full = True
            return
        end = self.ptr + chunk_size
        if end <= self.max_samples:
            self.data[:, self.ptr:end] = new_data
            self.ptr = end
            if self.ptr == self.max_samples:
                self.ptr = 0
                self.full = True
        else:
            overflow = end - self.max_samples
            self.data[:, self.ptr:] = new_data[:, :self.max_samples - self.ptr]
            self.data[:, :overflow] = new_data[:, self.max_samples - self.ptr:]
            self.ptr = overflow
            self.full = True

    def get_linear(self) -> np.ndarray:
        if not self.full:
            return self.data[:, :self.ptr]
        return np.concatenate((self.data[:, self.ptr:], self.data[:, :self.ptr]), axis=1)

    def clear(self) -> None:
        self.ptr = 0
        self.full = False

    def resize(self, new_max_samples: int) -> None:
        new_data = np.zeros((self.channels, new_max_samples), dtype=np.float32)
        old_linear = self.get_linear()
        valid_len = old_linear.shape[1]
        if valid_len > new_max_samples:
            new_data[:, :] = old_linear[:, -new_max_samples:]
            self.ptr = 0
            self.full = True
        else:
            new_data[:, :valid_len] = old_linear
            self.ptr = valid_len % new_max_samples
            self.full = valid_len == new_max_samples
        self.data = new_data
        self.max_samples = new_max_samples
