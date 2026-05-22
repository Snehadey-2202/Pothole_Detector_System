import os
import torch
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "ml"))
from ml.model import PotholeCNN

os.makedirs("models", exist_ok=True)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = PotholeCNN(num_classes=2).to(device)
torch.save(model.state_dict(), "models/pothole_cnn_best.pth")
print("Saved initialized model weights to models/pothole_cnn_best.pth")
