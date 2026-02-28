# ─────────────────────────────────────────────
#  neural_net.py  –  Retea neuronala cu NumPy
#
#  Drop-in replacement pentru versiunea cu Python pur.
#  API identic: forward(), predict(), backward(), get_params(), set_params(), copy_from()
#  Viteza: 10-50x mai rapida datorita operatiilor vectorizate NumPy.
# ─────────────────────────────────────────────

import math
import random
import copy
import numpy as np


class NeuralNet:
    """
    Retea neuronala fully-connected, implementata cu NumPy.

    Parametri:
        layer_sizes – ex: [34, 32, 24, 2]
    Activare: ReLU pe layere ascunse, liniara pe output.
    """

    def __init__(self, layer_sizes: list):
        self.layer_sizes = layer_sizes
        self.weights: list[np.ndarray] = []
        self.biases:  list[np.ndarray] = []

        # Initializare He – optima pentru ReLU
        for i in range(len(layer_sizes) - 1):
            fan_in = layer_sizes[i]
            scale  = math.sqrt(2.0 / fan_in)
            W = np.random.randn(layer_sizes[i + 1], layer_sizes[i]) * scale
            b = np.zeros(layer_sizes[i + 1])
            self.weights.append(W)
            self.biases.append(b)

    # ── Forward pass ──────────────────────────────────────────

    def forward(self, inputs: list) -> list:
        x = np.array(inputs, dtype=np.float32)
        self._activations  = [x]
        self._pre_acts     = []

        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            pre = W @ x + b
            self._pre_acts.append(pre)
            is_last = (i == len(self.weights) - 1)
            x = pre if is_last else np.maximum(0.0, pre)   # ReLU sau liniar
            self._activations.append(x)

        return self._activations[-1].tolist()

    def predict(self, inputs: list) -> list:
        """Forward fara stocarea activarilor (mai rapid pentru inferenta)."""
        x = np.array(inputs, dtype=np.float32)
        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            x = W @ x + b
            if i < len(self.weights) - 1:
                np.maximum(x, 0.0, out=x)   # ReLU in-place
        return x.tolist()

    # ── Backward pass ────────────────────────────────────────

    def backward(self, targets: list, lr: float = 0.001):
        """Backpropagation cu MSE loss. Apeleaza dupa forward()."""
        targets = np.array(targets, dtype=np.float32)
        n       = len(self.weights)
        deltas  = [None] * n

        # Delta output (activare liniara)
        deltas[n - 1] = self._activations[-1] - targets

        # Propagare inapoi prin layere ascunse (ReLU)
        for i in range(n - 2, -1, -1):
            d_next    = deltas[i + 1]
            W_next    = self.weights[i + 1]
            relu_mask = (self._pre_acts[i] > 0).astype(np.float32)
            deltas[i] = (W_next.T @ d_next) * relu_mask

        # Actualizare ponderi
        for i in range(n):
            act_in = self._activations[i]
            self.weights[i] -= lr * np.outer(deltas[i], act_in)
            self.biases[i]  -= lr * deltas[i]

    # ── Batch forward (pentru antrenament rapid pe batch-uri) ─

    def forward_batch(self, X: np.ndarray) -> np.ndarray:
        """
        Forward pe un batch intreg de o data.
        X shape: (batch_size, input_size)
        Returneaza: (batch_size, output_size)
        """
        x = X.T  # (input_size, batch_size)
        self._batch_activations = [x]
        self._batch_pre_acts    = []

        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            pre = W @ x + b[:, None]
            self._batch_pre_acts.append(pre)
            is_last = (i == len(self.weights) - 1)
            x = pre if is_last else np.maximum(0.0, pre)
            self._batch_activations.append(x)

        return x.T  # (batch_size, output_size)

    def backward_batch(self, targets: np.ndarray, lr: float = 0.001):
        """
        Backprop pe batch intreg.
        targets shape: (batch_size, output_size)
        """
        batch_size = targets.shape[0]
        n          = len(self.weights)
        deltas     = [None] * n

        out     = self._batch_activations[-1]          # (out_size, batch)
        deltas[n - 1] = out - targets.T                # (out_size, batch)

        for i in range(n - 2, -1, -1):
            d_next    = deltas[i + 1]
            W_next    = self.weights[i + 1]
            relu_mask = (self._batch_pre_acts[i] > 0).astype(np.float32)
            deltas[i] = (W_next.T @ d_next) * relu_mask

        for i in range(n):
            act_in = self._batch_activations[i]        # (in_size, batch)
            self.weights[i] -= (lr / batch_size) * (deltas[i] @ act_in.T)
            self.biases[i]  -= (lr / batch_size) * deltas[i].sum(axis=1)

    # ── Serializare ───────────────────────────────────────────

    def get_params(self) -> dict:
        return {
            "layer_sizes": self.layer_sizes,
            "weights":     [w.tolist() for w in self.weights],
            "biases":      [b.tolist() for b in self.biases],
        }

    def set_params(self, params: dict):
        self.layer_sizes = params["layer_sizes"]
        self.weights     = [np.array(w, dtype=np.float32) for w in params["weights"]]
        self.biases      = [np.array(b, dtype=np.float32) for b in params["biases"]]

    def copy_from(self, other: "NeuralNet"):
        self.weights = [w.copy() for w in other.weights]
        self.biases  = [b.copy() for b in other.biases]
