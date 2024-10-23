import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.optimizers import Adam

# Set paths
DATASET_DIR = "../images-resized"
MODEL_DIR = "../"
TFLITE_MODEL_FILE = os.path.join(MODEL_DIR, "mobilenet_v2_recycle.tflite")
EDGETPU_COMPILATION_OUTPUT = os.path.join(MODEL_DIR, "mobilenet_v2_recycle_edgetpu.tflite")

# Parameters
IMG_HEIGHT = 224
IMG_WIDTH = 224
BATCH_SIZE = 32
EPOCHS = 20

def load_dataset_from_directory(dataset_dir, batch_size, img_height, img_width):
    """Load dataset from directory and preprocess images."""
    dataset = tf.keras.preprocessing.image_dataset_from_directory(
        dataset_dir,
        labels="inferred",
        label_mode="int",  # Labels will be integers (class indices)
        image_size=(img_height, img_width),
        batch_size=batch_size,
        shuffle=True
    )
    
    # Normalize the dataset
    normalization_layer = layers.Rescaling(1./255)
    dataset = dataset.map(lambda x, y: (normalization_layer(x), y))
    
    return dataset

def build_model(num_classes):
    print("\n===== [1/4] Building model =====")
    # Load the MobileNetV2 model pre-trained on ImageNet
    base_model = MobileNetV2(input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
                             include_top=False,
                             weights='imagenet')

    # Freeze the base model
    base_model.trainable = False

    # Add classification layers
    model = models.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.2),
        layers.Dense(num_classes, activation='softmax')
    ])

    # Compile the model
    model.compile(optimizer=Adam(),
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    
    return model

def fine_tune_model(model, num_fine_tune_layers=100):
    print("\n===== [2/4] Fine-tuning model =====")
    # Unfreeze the base model for fine-tuning
    base_model = model.layers[0]
    base_model.trainable = True

    # Fine-tune only the last num_fine_tune_layers layers of MobileNetV2
    for layer in base_model.layers[:-num_fine_tune_layers]:
        layer.trainable = False

    # Recompile the model
    model.compile(optimizer=Adam(learning_rate=1e-5),
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])

    return model

def convert_to_tflite(model, train_dataset, tflite_model_file):
    print("\n===== [3/4] Converting model =====")
    # Convert to TFLite model
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    def representative_dataset():
        for images, _ in train_dataset.take(100):  # Use 100 samples for quantization
            yield [tf.dtypes.cast(images, tf.float32)]

    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.uint8  # Post-training quantization to uint8
    converter.inference_output_type = tf.uint8
    
    tflite_model = converter.convert()
    
    # Save the model
    with open(tflite_model_file, 'wb') as f:
        f.write(tflite_model)
    print(f'TFLite model saved at: {tflite_model_file}')

def compile_for_edgetpu(tflite_model_file, edgetpu_output_file):
    print("\n===== [4/4] Compiling model =====")
    # Run EdgeTPU Compiler
    os.system(f"edgetpu_compiler {tflite_model_file} -o {MODEL_DIR}")
    log_path = edgetpu_output_file.replace(".tflite", ".log")
    os.remove(log_path)
    print(f'EdgeTPU model saved at: {edgetpu_output_file}')

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Load the dataset from the directory
    train_dataset = load_dataset_from_directory(DATASET_DIR, BATCH_SIZE, IMG_HEIGHT, IMG_WIDTH)

    # Get the number of classes from the dataset (it infers from folder structure)
    num_classes = train_dataset.cardinality().numpy()  # Automatically inferred from folder structure

    # Build and train the model
    model = build_model(num_classes)
    model.fit(train_dataset, epochs=EPOCHS)

    # Fine-tune the model (optional)
    model = fine_tune_model(model)
    model.fit(train_dataset, epochs=EPOCHS)

    # Convert to TFLite
    convert_to_tflite(model, train_dataset, TFLITE_MODEL_FILE)

    # Compile for EdgeTPU
    compile_for_edgetpu(TFLITE_MODEL_FILE, EDGETPU_COMPILATION_OUTPUT)

if __name__ == '__main__':
    main()

