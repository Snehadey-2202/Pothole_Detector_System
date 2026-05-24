import torch
import torch.nn as nn
import torch.nn.functional as F

class PotholeCNN(nn.Module):
    def __init__(self, num_classes=2):
        super(PotholeCNN, self).__init__()
        
        # Convolutional layers with Batch Normalization to stabilize training
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        
        self.conv3 = nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        
        # Max pooling layer
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # Global Average Pooling to reduce dimensions to 1x1 per channel
        # This prevents the massive parameter explosion of flattening the whole image
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        
        # Fully connected layers
        self.fc1 = nn.Linear(128, 64)
        self.dropout = nn.Dropout(0.5)
        self.fc2 = nn.Linear(64, num_classes)

    def forward(self, x):
        # Layer 1
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        # Layer 2
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        # Layer 3
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        
        # Global Average Pooling
        x = self.gap(x)
        
        # Flatten
        x = x.view(x.size(0), -1)
        
        # Fully connected layers
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x

