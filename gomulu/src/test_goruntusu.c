#include "test_goruntusu.h"
// Test amaçlı minimal veri, production'da gerçek CIFAR-10 görüntüsü kullanılmalıdır.

const float test_goruntusu_cifar10[32 * 32 * 3] = {
    0.1f, -0.2f, 0.5f, -0.1f, 0.9f, 0.3f,
    // (In a real system, this array would contain the 3072 normalized pixel float values)
    // Here we put 0.0f for remaining to compile cleanly
    0.0f
};
