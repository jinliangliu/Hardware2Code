#include "drv_mpu6050.h"

static I2C_HandleTypeDef *i2c_handle = NULL;

/* MPU6050 register definitions */
#define MPU6050_PWR_MGMT_1   107
#define MPU6050_GYRO_CONFIG  27
#define MPU6050_ACCEL_CONFIG 28
#define MPU6050_SMPLRT_DIV   25
#define MPU6050_ACCEL_XOUT_H 59

void mpu6050_init(I2C_HandleTypeDef *hi2c) {
    i2c_handle = hi2c;

    /* Wake up the sensor */
    uint8_t init_data[2] = { MPU6050_PWR_MGMT_1, 0x00 };
    HAL_I2C_Master_Transmit(i2c_handle, 104 << 1, init_data, 2, 100);

    /* Configure gyroscope full scale */
    uint8_t gyro_fs_val;
    gyro_fs_val = 0x00;
    uint8_t gyro_data[2] = { MPU6050_GYRO_CONFIG, gyro_fs_val };
    HAL_I2C_Master_Transmit(i2c_handle, 104 << 1, gyro_data, 2, 100);

    /* Configure accelerometer full scale */
    uint8_t accel_fs_val;
    accel_fs_val = 0x00;
    uint8_t accel_data[2] = { MPU6050_ACCEL_CONFIG, accel_fs_val };
    HAL_I2C_Master_Transmit(i2c_handle, 104 << 1, accel_data, 2, 100);

    /* Set sample rate divider */
    uint8_t rate_data[2] = { MPU6050_SMPLRT_DIV, 0 };
    HAL_I2C_Master_Transmit(i2c_handle, 104 << 1, rate_data, 2, 100);
}

void mpu6050_read(mpu6050_data_t *data) {
    uint8_t buffer[14];
    HAL_I2C_Mem_Read(i2c_handle, 104 << 1, MPU6050_ACCEL_XOUT_H,
                    I2C_MEMADD_SIZE_8BIT, buffer, 14, 100);

    /* Extract raw values */
    int16_t ax = (buffer[0] << 8) | buffer[1];
    int16_t ay = (buffer[2] << 8) | buffer[3];
    int16_t az = (buffer[4] << 8) | buffer[5];
    int16_t gx = (buffer[8] << 8) | buffer[9];
    int16_t gy = (buffer[10] << 8) | buffer[11];
    int16_t gz = (buffer[12] << 8) | buffer[13];

    /* Scale factors (match full-scale configuration) */
    float accel_scale = 16384.0f;  /* ±2g */
    float gyro_scale = 131.0f;     /* ±250°/s */
    data->accel_x = ax / accel_scale;
    data->accel_y = ay / accel_scale;
    data->accel_z = az / accel_scale;
    data->gyro_x = gx / gyro_scale;
    data->gyro_y = gy / gyro_scale;
    data->gyro_z = gz / gyro_scale;
}