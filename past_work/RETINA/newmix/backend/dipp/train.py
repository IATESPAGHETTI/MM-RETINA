import os
import torch
from torch.utils.data import Dataset, DataLoader, Subset
from torchvision import transforms
import torch.nn as nn
import torch.optim as optim
from model import UNet
from PIL import Image
from sklearn.model_selection import train_test_split
import numpy as np
import random

# --------------------------
# Set Seeds for Reproducibility
# --------------------------
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

# --------------------------
# Dataset
# --------------------------
class DriveDataset(Dataset):
    def __init__(self, image_dir, mask_dir, transform=None):
        self.image_dir = image_dir
        self.mask_dir = mask_dir
        self.transform = transform
        self.images = sorted([f for f in os.listdir(image_dir) if f.endswith('.tif')])

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_filename = self.images[idx]
        img_path = os.path.join(self.image_dir, img_filename)

        base_number = img_filename.split('_')[0]
        mask_filename = f"{base_number}_manual1.gif"
        mask_path = os.path.join(self.mask_dir, mask_filename)

        image = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")

        if self.transform:
            seed = np.random.randint(2147483647)
            random.seed(seed)
            torch.manual_seed(seed)
            image = self.transform(image)

            random.seed(seed)
            torch.manual_seed(seed)
            mask = self.transform(mask)

        # 🔥 Minimal fix: make sure mask is binary (0 or 1), as float
        mask = (mask > 0.5).float()

        return image, mask

# --------------------------
# Metric Functions
# --------------------------
def compute_metrics(preds, masks, threshold=0.5):
    preds = (preds > threshold).float()
    intersection = (preds * masks).sum(dim=(1, 2, 3))
    union = preds.sum(dim=(1, 2, 3)) + masks.sum(dim=(1, 2, 3))
    dice = (2. * intersection + 1e-8) / (union + 1e-8)
    iou = (intersection + 1e-8) / ((preds + masks - preds * masks).sum(dim=(1, 2, 3)) + 1e-8)
    acc = ((preds == masks).float().mean(dim=(1, 2, 3)))
    return dice.mean().item(), iou.mean().item(), acc.mean().item()

# --------------------------
# Transformations
# --------------------------
transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor()
])

# --------------------------
# Dataset & Data Loaders
# --------------------------
dataset = DriveDataset(
    image_dir = "segmentation_dataset/training/training/images",
mask_dir = "segmentation_dataset/training/training/1st_manual",

    transform=transform
)

train_idx, val_idx = train_test_split(list(range(len(dataset))), test_size=0.2, random_state=42)
train_dataset = Subset(dataset, train_idx)
val_dataset = Subset(dataset, val_idx)

train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=2, shuffle=False)

# --------------------------
# Model, Loss, Optimizer
# --------------------------
model = UNet()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

def dice_loss(pred, target):
    smooth = 1e-8
    pred = pred.contiguous()
    target = target.contiguous()
    intersection = (pred * target).sum(dim=(2, 3))
    loss = 1 - ((2. * intersection + smooth) / (pred.sum(dim=(2,3)) + target.sum(dim=(2,3)) + smooth))
    return loss.mean()

criterion = lambda pred, target: nn.BCELoss()(pred, target) + dice_loss(pred, target)
optimizer = optim.Adam(model.parameters(), lr=0.0005)

# --------------------------
# Training Loop
# --------------------------
best_val_dice = 0.0
epochs = 50

for epoch in range(epochs):
    model.train()
    epoch_loss = 0
    total_dice = 0
    total_iou = 0
    total_acc = 0

    for imgs, masks in train_loader:
        imgs = imgs.to(device)
        masks = masks.to(device)

        preds = model(imgs)
        loss = criterion(preds, masks)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()
        dice, iou, acc = compute_metrics(preds, masks)
        total_dice += dice
        total_iou += iou
        total_acc += acc

    batches = len(train_loader)
    avg_train_dice = total_dice / batches

    # Validation
    model.eval()
    val_dice = 0
    val_iou = 0
    val_acc = 0
    with torch.no_grad():
        for imgs, masks in val_loader:
            imgs = imgs.to(device)
            masks = masks.to(device)
            preds = model(imgs)
            dice, iou, acc = compute_metrics(preds, masks)
            val_dice += dice
            val_iou += iou
            val_acc += acc
    val_batches = len(val_loader)
    avg_val_dice = val_dice / val_batches

    print(f"Epoch {epoch+1}/{epochs} | "
          f"Train Loss: {epoch_loss:.4f} | Train Dice: {avg_train_dice:.4f} | "
          f"Val Dice: {avg_val_dice:.4f} | Val IoU: {val_iou/val_batches:.4f} | Val Acc: {val_acc/val_batches:.4f}")

    # Save best model
    if avg_val_dice > best_val_dice:
        best_val_dice = avg_val_dice
        os.makedirs("saved_model", exist_ok=True)
        torch.save(model.state_dict(), "saved_model/unet_drive.pth")
        print(f"✅ Model saved (Val Dice: {best_val_dice:.4f})")

print(f"\n✅ Training complete. Best validation Dice: {best_val_dice:.4f}")