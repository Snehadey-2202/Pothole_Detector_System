import os
import time
import random
from datetime import datetime
# pyrefly: ignore [missing-import]
import torch
# pyrefly: ignore [missing-import]
from torchvision import transforms
# pyrefly: ignore [missing-import]
from PIL import Image

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ml"))
from model import PotholeCNN
from gps_sim import GPSSimulator
from db_setup import init_db, run_query

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "pothole_cnn_best.pth")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "detections.db")
DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset")
DETECTION_THRESHOLD = float(os.getenv("DETECTION_THRESHOLD", "0.6"))

# Classes based on alphabetical order of folders: 'normal', 'potholes'
CLASSES = ['normal', 'potholes']

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
    
    dashboard_img_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard", "public", "detections")
    os.makedirs(dashboard_img_dir, exist_ok=True)
    
    for frame_path in frames_to_process:
        pred_class, confidence = process_frame(model, device, frame_path)
        lat, lon = gps.get_coordinates()
        
        # Always save the current frame for the live feed
        current_frame_path = os.path.join(dashboard_img_dir, "current_frame.jpg")
        try:
            Image.open(frame_path).save(current_frame_path)
        except Exception as e:
            print(f"Failed to update current frame locally: {e}")
            
        if os.getenv("CLOUDINARY_URL"):
            try:
                import cloudinary
                import cloudinary.uploader
                cloudinary.uploader.upload(
                    frame_path,
                    public_id="current_frame",
                    overwrite=True,
                    invalidate=True
                )
                print("Uploaded live feed frame to Cloudinary.")
            except Exception as e:
                print(f"Failed to upload live feed frame to Cloudinary: {e}")
 
        # Log to DB if it's a pothole
        if pred_class == 'potholes' and confidence > DETECTION_THRESHOLD:
            timestamp = datetime.now().isoformat()
            new_img_name = f"det_{int(time.time()*1000)}.jpg"
            new_img_path = os.path.join(dashboard_img_dir, new_img_name)
            
            if os.getenv("CLOUDINARY_URL"):
                try:
                    import cloudinary
                    import cloudinary.uploader
                    upload_result = cloudinary.uploader.upload(frame_path, folder="detections")
                    rel_img_path = upload_result["secure_url"]
                    print(f"Pothole image uploaded to Cloudinary: {rel_img_path}")
                except Exception as e:
                    print(f"Cloudinary upload failed, falling back to local: {e}")
                    try:
                        Image.open(frame_path).save(new_img_path)
                    except Exception as err:
                        print(f"Failed to save image locally: {err}")
                    rel_img_path = f"/detections/{new_img_name}"
            else:
                try:
                    Image.open(frame_path).save(new_img_path)
                except Exception as e:
                    print(f"Failed to save image locally: {e}")
                rel_img_path = f"/detections/{new_img_name}"

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
