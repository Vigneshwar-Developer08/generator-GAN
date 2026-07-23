"""
DCGAN Generator architecture.

CRITICAL: This must be byte-for-byte identical to the architecture used
during training. torch.load(state_dict) will fail (or silently
mismatch) if layer shapes differ from the checkpoint in models/generator_final.pth.
Do not modify layer sizes without retraining the model.

Input:  latent vector z of shape (batch, LATENT_DIM, 1, 1)
Output: RGB image tensor of shape (batch, 3, 64, 64), values in [-1, 1]
"""

import torch
import torch.nn as nn


class Generator(nn.Module):
    """Standard DCGAN generator: 5 transposed-conv blocks, 1x1 -> 64x64."""

    def __init__(self, latent_dim: int = 100, ngf: int = 64, nc: int = 3) -> None:
        super().__init__()
        self.latent_dim = latent_dim

        self.main = nn.Sequential(
            # (latent_dim, 1, 1) -> (ngf*8, 4, 4)
            nn.ConvTranspose2d(latent_dim, ngf * 8, kernel_size=4, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(ngf * 8),
            nn.ReLU(inplace=True),
            # (ngf*8, 4, 4) -> (ngf*4, 8, 8)
            nn.ConvTranspose2d(ngf * 8, ngf * 4, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(ngf * 4),
            nn.ReLU(inplace=True),
            # (ngf*4, 8, 8) -> (ngf*2, 16, 16)
            nn.ConvTranspose2d(ngf * 4, ngf * 2, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(ngf * 2),
            nn.ReLU(inplace=True),
            # (ngf*2, 16, 16) -> (ngf, 32, 32)
            nn.ConvTranspose2d(ngf * 2, ngf, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(ngf),
            nn.ReLU(inplace=True),
            # (ngf, 32, 32) -> (nc, 64, 64)
            nn.ConvTranspose2d(ngf, nc, kernel_size=4, stride=2, padding=1, bias=False),
            nn.Tanh(),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        return self.main(z)
