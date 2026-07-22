#ifndef __STATEMACHINE_H
#define __STATEMACHINE_H

#include <stdint.h>
#include "event_mgr.h"

#define REGION_LED_CONTROL 0
#define REGION_COUNTER 1

void statemachine_init(void);
void statemachine_process(event_t *evt);
#endif