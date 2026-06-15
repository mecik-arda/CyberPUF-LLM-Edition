import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tensorflow.keras.datasets import cifar10
from PIL import Image

def generate_images():
    print("CIFAR-10 veriseti yukleniyor...")
    (_, _), (x_test, y_test) = cifar10.load_data()
    
    classes = ["Ucak", "Otomobil", "Kus", "Kedi", "Geyik", "Kopek", "Kurbaga", "At", "Gemi", "Kamyon"]
    
    output_dir = os.path.join("static", "test_images")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Ornek gorseller {output_dir} dizinine kaydediliyor...")
    
    # Her siniftan 1 ornek kaydedelim
    saved_classes = set()
    count = 0
    
    for i in range(len(x_test)):
        cls_idx = y_test[i][0]
        if cls_idx not in saved_classes:
            img_array = x_test[i]
            img = Image.fromarray(img_array)
            
            filename = f"cifar_{classes[cls_idx].lower()}_{i}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath)
            
            saved_classes.add(cls_idx)
            count += 1
            print(f"Kaydedildi: {filename}")
            
            if count >= 10:
                break
                
    print("Test gorselleri hazir.")

if __name__ == "__main__":
    generate_images()
