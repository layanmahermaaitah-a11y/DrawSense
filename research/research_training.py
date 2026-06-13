import os
import json
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping

BASE_DIR = os.getcwd()
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

train_dir = os.path.join(BASE_DIR, "Dataset", "Images", "Emotion", "train")
test_dir = os.path.join(BASE_DIR, "Dataset", "Images", "Emotion", "test")

IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 20

train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=15,
    zoom_range=0.1,
    horizontal_flip=True
)

test_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
    train_dir,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode='binary',
    shuffle=True
)

test_generator = test_datagen.flow_from_directory(
    test_dir,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode='binary',
    shuffle=False
)

class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(train_generator.classes),
    y=train_generator.classes
)

class_weights = dict(enumerate(class_weights))

def plot_history(history, name):
    plt.figure()
    plt.plot(history.history['accuracy'])
    plt.plot(history.history['val_accuracy'])
    plt.title(f"{name} Accuracy")
    plt.legend(['Train', 'Validation'])
    plt.savefig(os.path.join(RESULTS_DIR, f"{name}_accuracy.png"))
    plt.close()

    plt.figure()
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title(f"{name} Loss")
    plt.legend(['Train', 'Validation'])
    plt.savefig(os.path.join(RESULTS_DIR, f"{name}_loss.png"))
    plt.close()

def evaluate_model(model, name):
    y_true = test_generator.classes
    y_pred_prob = model.predict(test_generator)
    y_pred = (y_pred_prob > 0.5).astype(int).reshape(-1)

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)

    plt.figure()
    plt.imshow(cm, cmap='Blues')
    plt.title(f"{name} Confusion Matrix")
    plt.colorbar()
    plt.savefig(os.path.join(RESULTS_DIR, f"{name}_confusion_matrix.png"))
    plt.close()

    misclassified = np.where(y_true != y_pred)[0]
    mis_list = misclassified.tolist()

    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "confusion_matrix": cm.tolist(),
        "misclassified_indices": mis_list[:20]
    }

def build_baseline_cnn():
    model = models.Sequential([
        layers.Conv2D(32, (3,3), activation='relu', input_shape=(224,224,3)),
        layers.MaxPooling2D(),
        layers.Conv2D(64, (3,3), activation='relu'),
        layers.MaxPooling2D(),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer=Adam(0.0001),
                  loss='binary_crossentropy',
                  metrics=['accuracy'])
    return model

def build_mobilenet():
    base = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224,224,3))
    base.trainable = False
    model = models.Sequential([
        base,
        layers.GlobalAveragePooling2D(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer=Adam(0.0001),
                  loss='binary_crossentropy',
                  metrics=['accuracy'])
    return model, base

results = {}

for name in ["Baseline_CNN", "MobileNetV2"]:
    if name == "Baseline_CNN":
        model = build_baseline_cnn()
        base_model = None
    else:
        model, base_model = build_mobilenet()

    checkpoint_path = os.path.join(RESULTS_DIR, f"{name}_best.keras")

    checkpoint = ModelCheckpoint(
        checkpoint_path,
        monitor="val_accuracy",
        save_best_only=True,
        mode="max"
    )

    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True
    )

    history = model.fit(
        train_generator,
        validation_data=test_generator,
        epochs=EPOCHS,
        class_weight=class_weights,
        callbacks=[checkpoint, early_stop]
    )

    plot_history(history, name)

    if base_model is not None:
        base_model.trainable = True
        model.compile(optimizer=Adam(1e-5),
                      loss='binary_crossentropy',
                      metrics=['accuracy'])

        model.fit(
            train_generator,
            validation_data=test_generator,
            epochs=5
        )

    best_model = tf.keras.models.load_model(checkpoint_path)
    results[name] = evaluate_model(best_model, name)

with open(os.path.join(RESULTS_DIR, "final_results.json"), "w") as f:
    json.dump(results, f, indent=4)

print(json.dumps(results, indent=4))