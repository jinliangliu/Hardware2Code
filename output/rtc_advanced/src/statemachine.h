#ifndef __STATEMACHINE_H
#define __STATEMACHINE_H

#include <stdint.h>
#include "event_mgr.h"


void statemachine_init(void);
void statemachine_process(event_t *evt);
#endif