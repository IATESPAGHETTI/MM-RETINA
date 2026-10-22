import torch
import torch.optim as optim
import torch.nn as nn
from torch.utils.data import DataLoader
from dataset import RetinalAVSegmentationDataset
from unet_av import UNetAV

# Set paths to images and masks
image_dir = "path/to/images"
mask_dir = "path/to/av_masks"

train_dataset = RetinalAVSegmentationDataset(image_dir, mask_dir)
train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True)

model = UNetAV()
model = model.to("cuda" if torch.cuda.is_available() else "cpu")

optimizer = optim.Adam(model.parameters(), lr=1e-4)
loss_fn = nn.CrossEntropyLoss()

for epoch in range(30):  # Change as needed
    for images, masks in train_loader:
        images = images.to("cuda")
        masks = masks.to("cuda")

        outputs = model(images)
        loss = loss_fn(outputs, masks)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print(f"Epoch {epoch}, Loss: {loss.item()}")

# Save model
torch.save(model.state_dict(), "models/av_model.pth")
