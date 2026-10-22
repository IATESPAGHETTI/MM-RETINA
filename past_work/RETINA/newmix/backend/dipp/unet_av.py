import torch
import torch.nn as nn

class UNetAV(nn.Module):
    # You can use any U-Net implementation, just set output channels to 3
    def __init__(self):
        super().__init__()
        # ... [Define your U-Net encoder-decoder layers here]
        self.final = nn.Conv2d(64, 3, kernel_size=1)  # 3 output classes

    def forward(self, x):
        # ... [Implement forward pass]
        out = self.final(x)
        return out
