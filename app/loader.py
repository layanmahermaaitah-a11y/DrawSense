import tensorflow as tf
from PIL import Image
import numpy as np
import io


MODEL_PATH = "MobileNetV2_best.keras"
model = tf.keras.models.load_model(MODEL_PATH)


def predict_drawing(image_bytes):

    image = Image.open(io.BytesIO(image_bytes))


    image = image.resize((224, 224))
    image_array = np.array(image) / 255.0  # Normalization


    image_array = np.expand_dims(image_array, axis=0)


    predictions = model.predict(image_array)


    #  افتراض إنه يرجع رقم الكلاس الأعلى
    result_index = np.argmax(predictions[0])

    return int(result_index)