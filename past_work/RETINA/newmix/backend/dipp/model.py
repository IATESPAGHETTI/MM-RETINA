import torch
import torch.nn as nn

class UNet(nn.Module):
    def __init__(self):
        super(UNet, self).__init__()

        def conv_block(in_c, out_c):
            return nn.Sequential(
                nn.Conv2d(in_c, out_c, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
                nn.BatchNorm2d(out_c),
                nn.Conv2d(out_c, out_c, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
                nn.BatchNorm2d(out_c)
            )

        self.pool = nn.MaxPool2d(2)

        self.enc1 = conv_block(3, 64)
        self.enc2 = conv_block(64, 128)
        self.enc3 = conv_block(128, 256)
        self.middle = conv_block(256, 512)

        self.up3 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.dec3 = conv_block(512, 256)  # 256 (up) + 256 (enc)

        self.up2 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec2 = conv_block(256, 128)  # 128 (up) + 128 (enc)

        self.up1 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec1 = conv_block(128, 64)   # 64 (up) + 64 (enc)

        self.final = nn.Conv2d(64, 1, kernel_size=1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # Encoder
        e1 = self.enc1(x)           # [B, 64, 256, 256]
        e2 = self.enc2(self.pool(e1))  # [B, 128, 128, 128]
        e3 = self.enc3(self.pool(e2))  # [B, 256, 64, 64]

        # Bottleneck
        m = self.middle(self.pool(e3)) # [B, 512, 32, 32]

        # Decoder
        d3 = self.up3(m)               # [B, 256, 64, 64]
        d3 = self.dec3(torch.cat([d3, e3], dim=1))

        d2 = self.up2(d3)              # [B, 128, 128, 128]
        d2 = self.dec2(torch.cat([d2, e2], dim=1))

        d1 = self.up1(d2)              # [B, 64, 256, 256]
        d1 = self.dec1(torch.cat([d1, e1], dim=1))

        out = self.final(d1)
        return self.sigmoid(out)