   #ifndef __DRV_MPU6050_H
   #define __DRV_MPU6050_H
   
   #include "stm32g0xx_hal.h"
   
   typedef struct {
       float accel_x, accel_y, accel_z;
       float gyro_x, gyro_y, gyro_z;
   } mpu6050_data_t;
   
   void mpu6050_init(I2C_HandleTypeDef *hi2c);
   void mpu6050_read(mpu6050_data_t *data);
   
   #endif