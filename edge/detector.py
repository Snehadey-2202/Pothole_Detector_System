import os
import time
import random
import json
from datetime import datetime
# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
from torchvision import transforms
# pyrefly: ignore [missing-import]
from PIL import Image

import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "ml"))
from model import PotholeCNN
from gps_sim import GPSSimulator
from db_setup import init_db, run_query
from env_utils import load_env_file

load_env_file()

MODEL_PATH = os.path.join(ROOT_DIR, "models", "pothole_cnn_best.pth")
DB_PATH = os.path.join(ROOT_DIR, "detections.db")
DATASET_PATH = os.path.join(ROOT_DIR, "dataset")
DETECTION_THRESHOLD = float(os.getenv("DETECTION_THRESHOLD", "0.5"))
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "").rstrip("/")
INGEST_TOKEN = os.getenv("INGEST_TOKEN")

# Classes based on alphabetical order of folders: 'normal', 'potholes'
CLASSES = ['normal', 'potholes']


def write_live_status(status_path, pred_class, confidence, image_path):
    status = {
        "frame_updated_at": datetime.now().isoformat(),
        "prediction": pred_class,
        "confidence": confidence,
        "image_path": image_path,
    }
    try:
        with open(status_path, "w", encoding="utf-8") as status_file:
            json.dump(status, status_file)
    except Exception as e:
        print(f"Failed to update live status locally: {e}")


def post_image(endpoint, image_path, data=None):
    if not BACKEND_API_URL:
        return

    try:
        import requests

        headers = {}
        if INGEST_TOKEN:
            headers["X-Ingest-Token"] = INGEST_TOKEN

        with open(image_path, "rb") as image_file:
            response = requests.post(
                f"{BACKEND_API_URL}{endpoint}",
                data=data or {},
                files={"image": (os.path.basename(image_path), image_file, "image/jpeg")},
                headers=headers,
                timeout=15,
            )
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to push frame to backend API: {e}")

def load_model(device):
    model = PotholeCNN(num_classes=2).to(device)
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        model.eval()
        print(f"Loaded trained model from {MODEL_PATH}")
        return model
    else:
        print("Warning: Model file not found. Inference will use random weights.")
        model.eval()
        return model

def process_frame(model, device, image_path):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(inputs)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)

        return CLASSES[predicted.item()], confidence.item()
        
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None, 0.0

def run_detection_cycle():
    """Simulates one cron job cycle: Process a batch of recent frames"""
    init_db()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device)
    gps = GPSSimulator()
    
    # Simulate picking random images from the dataset as if they were live frames
    all_images = []
    for cls in CLASSES:
        cls_path = os.path.join(DATASET_PATH, cls)
        if os.path.exists(cls_path):
            all_images.extend([os.path.join(cls_path, f) for f in os.listdir(cls_path) if f.endswith(('.jpg', '.png'))])
    
    if not all_images:
        print("No images found to simulate camera feed.")
        return

    # Process 5 random "frames"
    frames_to_process = random.sample(all_images, min(5, len(all_images)))
    
    dashboard_img_dir = os.path.join(ROOT_DIR, "dashboard", "public", "detections")
    os.makedirs(dashboard_img_dir, exist_ok=True)
    status_path = os.path.join(dashboard_img_dir, "status.json")
    
    for frame_path in frames_to_process:
        pred_class, confidence = process_frame(model, device, frame_path)
        lat, lon = gps.get_coordinates()
        
        # Always save the current frame for the live feed
        current_frame_path = os.path.join(dashboard_img_dir, "current_frame.jpg")
        try:
            Image.open(frame_path).save(current_frame_path)
        except Exception as e:
            print(f"Failed to update current frame locally: {e}")
        write_live_status(status_path, pred_class, confidence, "/detections/current_frame.jpg")
        post_image(
            "/api/live-frame",
            current_frame_path,
            data={"prediction": pred_class or "", "confidence": confidence},
        )
 
        # Log to DB if it's a pothole
        if pred_class == 'potholes' and confidence > DETECTION_THRESHOLD:
            timestamp = datetime.now().isoformat()
            new_img_name = f"det_{int(time.time()*1000)}.jpg"
            new_img_path = os.path.join(dashboard_img_dir, new_img_name)
            
            try:
                Image.open(frame_path).save(new_img_path)
            except Exception as e:
                print(f"Failed to save image locally: {e}")
            rel_img_path = f"/detections/{new_img_name}"
            post_image(
                "/api/detections",
                new_img_path,
                data={
                    "timestamp": timestamp,
                    "latitude": lat,
                    "longitude": lon,
                    "confidence": confidence,
                },
            )

            # Save to DB via run_query
            query = '''
                INSERT INTO detections (timestamp, latitude, longitude, confidence, image_path)
                VALUES (%s, %s, %s, %s, %s)
            '''
            run_query(query, (timestamp, lat, lon, confidence, rel_img_path), commit=True)
            print(f"POTHOLE DETECTED: {confidence:.2f} confidence at {lat:.5f}, {lon:.5f}")
        else:
            print(f"Frame processed: {pred_class} ({confidence:.2f})")
            
        time.sleep(1) # Simulate processing time

if __name__ == "__main__":
    run_detection_cycle()
