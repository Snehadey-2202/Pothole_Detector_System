import torch
import torch.nn as nn
import torch.nn.functional as F

class PotholeCNN(nn.Module):
    def __init__(self, num_classes=2):
        super(PotholeCNN, self).__init__()
        
        # Convolutional layers
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, padding=1)
        
        # Max pooling layer
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # Fully connected layers
        # Input image size: 224x224
        # After 3 pooling layers: 224 -> 112 -> 56 -> 28
        # Flattened size: 128 channels * 28 * 28
        self.fc1 = nn.Linear(128 * 28 * 28, 512)
        self.dropout = nn.Dropout(0.5)
        self.fc2 = nn.Linear(512, num_classes)

    def forward(self, x):
        # Layer 1
        x = self.pool(F.relu(self.conv1(x)))
        # Layer 2
        x = self.pool(F.relu(self.conv2(x)))
        # Layer 3
        x = self.pool(F.relu(self.conv3(x)))
        
        # Flatten
        x = x.view(x.size(0), -1)
        
        # Fully connected layers
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x
