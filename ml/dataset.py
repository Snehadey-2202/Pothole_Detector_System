import copy
import os
import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, random_split

def get_data_loaders(data_dir: str, batch_size: int = 32, train_split: float = 0.8, seed: int = 42):
    """
    Creates PyTorch DataLoaders for the pothole dataset.
    Assumes the data_dir contains two subfolders: 'normal' and 'potholes'.
    """
    if not 0 < train_split < 1:
        raise ValueError("train_split must be between 0 and 1.")

    # Image transformations for data augmentation and normalization
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Load the dataset
    full_dataset = datasets.ImageFolder(root=data_dir)

    # Calculate split sizes
    train_size = int(train_split * len(full_dataset))
    val_size = len(full_dataset) - train_size

    # Split dataset deterministically so validation metrics are comparable between runs.
    generator = torch.Generator().manual_seed(seed)
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size], generator=generator)

    # Apply respective transforms
    train_dataset.dataset.transform = transform
    
    # We create a shallow copy to apply a different transform for validation.
    val_dataset.dataset = copy.copy(full_dataset)
    val_dataset.dataset.transform = val_transform

    # Create DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=2)

    return train_loader, val_loader, full_dataset.classes
