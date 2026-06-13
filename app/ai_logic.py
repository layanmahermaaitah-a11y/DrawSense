import os
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import asyncio
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
# Global variable to hold the model instance
model_container = {"model": None}

def load_drawsense_model():
    # Point to the root of the model folder
    model_path = r"C:\Users\Admin\Desktop\DrawSense\app\models\MobileNetV2_best.keras"

    try:
        if not os.path.exists(model_path):
            print(f"ERROR: Model folder not found at {model_path}")
            return

        # Load the model. compile=False is vital because the training script 
        # used custom Adam optimizers that the backend doesn't need to 're-compile'.
        model_container["model"] = tf.keras.models.load_model(model_path, compile=False)
        print(f"SUCCESS: AI Model Loaded from {model_path}")
        
    except Exception as e:
        print(f"Error loading model: {e}")
        # Fallback: Pointing specifically to the weights if the folder load fails
        try:
            weights_path = os.path.join(model_path, "model.weights.h5")
            # This requires you to have the model architecture defined, 
            # so the folder-level load_model is much preferred.
        except:
            pass

async def run_ai_analysis(image_path: str):
    model = model_container["model"]
    
    if model is None:
        return {"error": "AI Model not loaded"}

    # Image Preprocessing
    # Using a thread for loading the image to keep things async-friendly
    img = await asyncio.to_thread(image.load_img, image_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0  # Rescale

    # Prediction
    # model.predict is also wrapped in to_thread to prevent blocking the event loop
    prediction = await asyncio.to_thread(model.predict, img_array)
    score = float(prediction[0][0]) 

    # Interpretation
    label = "Positive/Expressive" if score > 0.5 else "Neutral/Quiet"
    confidence = score if score > 0.5 else (1 - score)

    return {
        "prediction_label": label,
        "confidence_score": round(confidence * 100, 2),
        "raw_score": score,
        "analysis_details": {
            "model_used": "MobileNetV2",
            "message": "Analysis completed based on emotional patterns in drawing."
        }
    }