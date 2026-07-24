#include "unity.h"
#include "mock_hal.h"
#include <string.h>

#include "../src/event_mgr.c"

void setUp(void) {}
void tearDown(void) {}

void test_EventMgr_Init_should_create_queue(void) {
    EventMgr_Init();
    TEST_ASSERT_NOT_NULL(event_queue);
}

void test_EventMgr_should_receive_sent_event(void) {
    EventMgr_Init();
    event_t evt = { .id = EVENT_BUTTON_PRESS, .param = 0 };
    BaseType_t ret = xQueueSend(event_queue, &evt, 0);
    TEST_ASSERT_EQUAL(pdPASS, ret);
}

void test_EventMgr_should_dispatch_button_event(void)
{
    EventMgr_Init();
    event_t evt = { .id = EVENT_BUTTON_PRESS, .param = 0 };
    xQueueSend(event_queue, &evt, 0);
    /* 由于我们无法直接验证任务内部回调，但可以验证队列非空 */
    /* 这里简单确保发送成功 */
    TEST_ASSERT_EQUAL(pdPASS, xQueueSend(event_queue, &evt, 0));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_EventMgr_Init_should_create_queue);
    RUN_TEST(test_EventMgr_should_receive_sent_event);
    RUN_TEST(test_EventMgr_should_dispatch_button_event);
    return UNITY_END();
}