import os
import torch
import torch.nn as nn
import torch.optim as optim
from dataset import get_data_loaders
from model import PotholeCNN

def train_model(data_dir, num_epochs=10, batch_size=32, learning_rate=0.001):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Ensure dataset directory exists
    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found.")
        return

    # Get data loaders
    try:
        train_loader, val_loader, class_names = get_data_loaders(data_dir, batch_size=batch_size)
        print(f"Classes found: {class_names}")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    # Initialize model, loss function, and optimizer
    model = PotholeCNN(num_classes=len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    best_val_accuracy = 0.0

    print("Starting training...")
    for epoch in range(num_epochs):
        # Training Phase
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        train_loss = running_loss / len(train_loader)
        train_accuracy = 100 * correct / total

        # Validation Phase
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        val_loss = val_loss / len(val_loader)
        val_accuracy = 100 * correct / total

        print(f"Epoch [{epoch+1}/{num_epochs}] "
              f"Train Loss: {train_loss:.4f}, Train Acc: {train_accuracy:.2f}% | "
              f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.2f}%")

        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
            os.makedirs(models_dir, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(models_dir, "pothole_cnn_best.pth"))
            print("  --> Saved improved model!")

    print("Training complete.")

if __name__ == "__main__":
    # The dataset directory should be one level up from the ml folder
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "dataset")
    train_model(dataset_path, num_epochs=5)
