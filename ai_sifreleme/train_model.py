import os
import sys
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, regularizers, callbacks


def build_cyberpuf_cnn(input_shape=(32, 32, 3), num_classes=10):
    model = keras.Sequential()

    model.add(layers.Input(shape=input_shape))

    model.add(layers.Conv2D(
        filters=64,
        kernel_size=(3, 3),
        padding='same',
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.Conv2D(
        filters=64,
        kernel_size=(3, 3),
        padding='same',
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))
    model.add(layers.Dropout(0.25))

    model.add(layers.Conv2D(
        filters=128,
        kernel_size=(3, 3),
        padding='same',
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.Conv2D(
        filters=128,
        kernel_size=(3, 3),
        padding='same',
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))
    model.add(layers.Dropout(0.30))

    model.add(layers.Conv2D(
        filters=256,
        kernel_size=(3, 3),
        padding='same',
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.Conv2D(
        filters=256,
        kernel_size=(3, 3),
        padding='same',
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))
    model.add(layers.Dropout(0.35))

    model.add(layers.Flatten())

    model.add(layers.Dense(
        512,
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.Dropout(0.5))

    model.add(layers.Dense(
        256,
        kernel_regularizer=regularizers.l2(1e-4)
    ))
    model.add(layers.BatchNormalization())
    model.add(layers.Activation('relu'))
    model.add(layers.Dropout(0.5))

    model.add(layers.Dense(num_classes, activation='softmax'))

    return model


def load_and_preprocess_cifar10():
    (x_egitim, y_egitim), (x_test, y_test) = keras.datasets.cifar10.load_data()

    x_egitim = x_egitim.astype('float32') / 255.0
    x_test = x_test.astype('float32') / 255.0

    kanal_ortalamasi = np.mean(x_egitim, axis=(0, 1, 2))
    kanal_std = np.std(x_egitim, axis=(0, 1, 2))

    x_egitim = (x_egitim - kanal_ortalamasi) / (kanal_std + 1e-7)
    x_test = (x_test - kanal_ortalamasi) / (kanal_std + 1e-7)

    y_egitim = keras.utils.to_categorical(y_egitim, 10)
    y_test = keras.utils.to_categorical(y_test, 10)

    normalizasyon_parametreleri = {
        'kanal_ortalamasi': kanal_ortalamasi.tolist(),
        'kanal_std': kanal_std.tolist()
    }

    return (x_egitim, y_egitim), (x_test, y_test), normalizasyon_parametreleri


def create_data_augmentation():
    veri_ureticisi = keras.preprocessing.image.ImageDataGenerator(
        rotation_range=15,
        width_shift_range=0.1,
        height_shift_range=0.1,
        horizontal_flip=True,
        fill_mode='nearest'
    )
    return veri_ureticisi
class SyslogCallback(callbacks.Callback):
    def on_epoch_begin(self, epoch, logs=None):
        print(f"--- Epoch {epoch+1} Basladi ---")
    def on_batch_end(self, batch, logs=None):
        if batch > 0 and batch % 50 == 0:
            acc = logs.get('accuracy', 0)
            loss = logs.get('loss', 0)
            print(f"Step {batch:03d} -> loss: {loss:.4f}, acc: {acc:.4f}")

def setup_callbacks(cikis_dizini):
    kontrol_noktasi_yolu = os.path.join(cikis_dizini, 'best_model.weights.h5')

    geri_cagri_listesi = [SyslogCallback()]

    geri_cagri_listesi.append(callbacks.ModelCheckpoint(
        filepath=kontrol_noktasi_yolu,
        monitor='val_accuracy',
        save_best_only=True,
        save_weights_only=True,
        mode='max',
        verbose=1
    ))

    geri_cagri_listesi.append(callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-6,
        verbose=1
    ))

    geri_cagri_listesi.append(callbacks.EarlyStopping(
        monitor='val_accuracy',
        patience=15,
        restore_best_weights=True,
        verbose=1
    ))

    csv_log_yolu = os.path.join(cikis_dizini, 'training_log.csv')
    geri_cagri_listesi.append(callbacks.CSVLogger(
        csv_log_yolu,
        separator=',',
        append=False
    ))

    return geri_cagri_listesi


def train_model(epochs=100, batch_size=128, learning_rate=0.001):
    cikis_dizini = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output', 'model')
    os.makedirs(cikis_dizini, exist_ok=True)

    print("=" * 70)
    print("CyberPUF - Faz 1: CIFAR-10 CNN Model Egitimi")
    print("Gelistirici: Arda Mecik")
    print("=" * 70)

    print("\n[1/6] CIFAR-10 veri seti yukleniyor ve on isleniyor...")
    (x_egitim, y_egitim), (x_test, y_test), norm_parametreleri = load_and_preprocess_cifar10()
    print(f"  Egitim seti boyutu  : {x_egitim.shape}")
    print(f"  Test seti boyutu    : {x_test.shape}")
    print(f"  Kanal ortalamasi    : {norm_parametreleri['kanal_ortalamasi']}")
    print(f"  Kanal std sapmasi   : {norm_parametreleri['kanal_std']}")

    norm_param_yolu = os.path.join(cikis_dizini, 'normalization_params.json')
    with open(norm_param_yolu, 'w') as f:
        json.dump(norm_parametreleri, f, indent=2)
    print(f"  Normalizasyon parametreleri kaydedildi: {norm_param_yolu}")

    print("\n[2/6] CNN modeli olusturuluyor...")
    model = build_cyberpuf_cnn(input_shape=(32, 32, 3), num_classes=10)
    model.summary()

    print("\n[3/6] Model derleniyor...")
    optimizer = keras.optimizers.Adam(
        learning_rate=learning_rate,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-07
    )

    model.compile(
        optimizer=optimizer,
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    print("\n[4/6] Veri artirma (data augmentation) hazirlaniyor...")
    veri_ureticisi = create_data_augmentation()
    veri_ureticisi.fit(x_egitim)

    print("\n[5/6] Egitim basliyor...")
    print(f"  Epoch sayisi        : {epochs}")
    print(f"  Batch boyutu        : {batch_size}")
    print(f"  Baslangic ogrenme h.: {learning_rate}")
    print("-" * 70)

    geri_cagri_listesi = setup_callbacks(cikis_dizini)

    gecmis = model.fit(
        veri_ureticisi.flow(x_egitim, y_egitim, batch_size=batch_size),
        epochs=epochs,
        validation_data=(x_test, y_test),
        callbacks=geri_cagri_listesi,
        verbose=2
    )

    print("\n[6/6] Egitim tamamlandi. Sonuclar degerlendiriliyor...")
    test_kaybi, test_dogrulugu = model.evaluate(x_test, y_test, verbose=0)
    print(f"  Test kaybi (loss)   : {test_kaybi:.4f}")
    print(f"  Test dogrulugu (acc): {test_dogrulugu:.4f}")

    tam_model_yolu = os.path.join(cikis_dizini, 'cyberpuf_cifar10_model.keras')
    model.save(tam_model_yolu)
    print(f"  Tam model kaydedildi: {tam_model_yolu}")

    sadece_agirlik_yolu = os.path.join(cikis_dizini, 'cyberpuf_cifar10_weights.weights.h5')
    model.save_weights(sadece_agirlik_yolu)
    print(f"  Agirliklar kaydedildi: {sadece_agirlik_yolu}")

    egitim_ozeti = {
        'proje': 'CyberPUF',
        'gelistirici': 'Arda Mecik',
        'faz': 'Faz 1 - AI Model Egitimi',
        'veri_seti': 'CIFAR-10',
        'giris_boyutu': [32, 32, 3],
        'sinif_sayisi': 10,
        'tamamlanan_epoch': len(gecmis.history.get('loss', [])),
        'son_egitim_kaybi': float(gecmis.history.get('loss', [0.0])[-1]),
        'son_egitim_dogrulugu': float(gecmis.history.get('accuracy', [0.0])[-1]),
        'son_dogrulama_kaybi': float(gecmis.history.get('val_loss', [0.0])[-1]),
        'son_dogrulama_dogrulugu': float(gecmis.history.get('val_accuracy', [0.0])[-1]),
        'test_kaybi': float(test_kaybi),
        'test_dogrulugu': float(test_dogrulugu),
        'yigin_boyutu': batch_size,
        'baslangic_ogrenme_orani': learning_rate,
        'optimizasyon': 'Adam',
        'regularization': 'L2(1e-4) + Dropout',
        'data_augmentation': True,
        'model_dosyasi': tam_model_yolu,
        'agirlik_dosyasi': sadece_agirlik_yolu,
        'normalizasyon_parametreleri': norm_parametreleri
    }

    ozet_yolu = os.path.join(cikis_dizini, 'training_summary.json')
    with open(ozet_yolu, 'w') as f:
        json.dump(egitim_ozeti, f, indent=2)
    print(f"  Egitim ozeti kaydedildi: {ozet_yolu}")

    toplam_parametre = int(sum(np.prod(w.shape) for w in model.weights))
    egitilebilir_parametre = int(sum(
        np.prod(w.shape) for w in model.trainable_weights
    ))
    dondurulan_parametre = toplam_parametre - egitilebilir_parametre

    print("\n" + "=" * 70)
    print("MODEL ISTATISTIKLERI")
    print("=" * 70)
    print(f"  Toplam parametre    : {toplam_parametre:,}")
    print(f"  Egitilebilir param. : {egitilebilir_parametre:,}")
    print(f"  Dondurulan param.   : {dondurulan_parametre:,}")
    print(f"  Tahm. bellek (MB)   : {(toplam_parametre * 4) / (1024 * 1024):.2f}")
    print("=" * 70)

    katman_bilgisi = []
    for katman in model.layers:
        katman_agirliklari = katman.get_weights()
        if len(katman_agirliklari) > 0:
            katman_detayi = {
                'isim': katman.name,
                'tip': katman.__class__.__name__,
                'dizi_sayisi': len(katman_agirliklari),
                'sekiller': [w.shape for w in katman_agirliklari],
                'toplam_parametre': sum(np.prod(w.shape) for w in katman_agirliklari),
                'veri_tipleri': [str(w.dtype) for w in katman_agirliklari]
            }
            katman_bilgisi.append(katman_detayi)
            print(f"  Katman: {katman.name:30s} | Tip: {katman.__class__.__name__:20s} | Parametre: {katman_detayi['toplam_parametre']:>10,}")

    serilestirilebilir_katman_bilgisi = []
    for bilgi in katman_bilgisi:
        serilestirilebilir = {
            'isim': bilgi['isim'],
            'tip': bilgi['tip'],
            'dizi_sayisi': bilgi['dizi_sayisi'],
            'sekiller': [list(s) for s in bilgi['sekiller']],
            'toplam_parametre': int(bilgi['toplam_parametre']),
            'veri_tipleri': bilgi['veri_tipleri']
        }
        serilestirilebilir_katman_bilgisi.append(serilestirilebilir)

    katman_bilgisi_yolu = os.path.join(cikis_dizini, 'layer_info.json')
    with open(katman_bilgisi_yolu, 'w') as f:
        json.dump(serilestirilebilir_katman_bilgisi, f, indent=2)
    print(f"\n  Katman bilgileri kaydedildi: {katman_bilgisi_yolu}")

    print("\n" + "=" * 70)
    print("FAZ 1 - ADIM 1 TAMAMLANDI: Model egitildi ve kaydedildi.")
    print("Sonraki adim: export_weights.py ile agirliklari disa aktarin.")
    print("=" * 70)

    return model, gecmis


if __name__ == '__main__':
    custom_epochs = 100
    custom_batch_size = 128
    custom_lr = 0.001

    try:
        if len(sys.argv) > 1:
            custom_epochs = int(sys.argv[1])
            if custom_epochs <= 0: raise ValueError("Epochs > 0 olmali")
        if len(sys.argv) > 2:
            custom_batch_size = int(sys.argv[2])
            if custom_batch_size <= 0: raise ValueError("Batch size > 0 olmali")
        if len(sys.argv) > 3:
            custom_lr = float(sys.argv[3])
            if custom_lr <= 0: raise ValueError("Learning rate > 0 olmali")
    except ValueError as e:
        print(f"HATA: Gecersiz arguman: {e}")
        sys.exit(1)

    trained_model, training_history = train_model(
        epochs=custom_epochs,
        batch_size=custom_batch_size,
        learning_rate=custom_lr
    )
