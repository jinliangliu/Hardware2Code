# CLI Debug Shell Commands

When `Internal_CLI` is enabled in your hardware YAML, hw2c generates a UART-based interactive debug shell. Connect via serial terminal (115200 bps default) to access the command prompt.

## Enabling CLI

```yaml
peripherals:
  - name: "uart_debug"
    type: "UART_Serial"
    extra:
      baudrate: 115200

  - name: "cli"
    type: "Internal_CLI"
    uart: "uart_debug"
    extra:
      prompt: "h2c> "
      stack_size: 512
      priority: 4
```

## Command Reference

### System Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `help` | List all available commands | Always |
| `version` | Show firmware version and build time | Always |
| `uptime` | Show system uptime in seconds | Always |
| `free` | Show free heap memory (bytes) | Always |
| `tasks` | List all FreeRTOS tasks with stack info | Always |
| `reset` | Trigger software reset of the MCU | Always |

### GPIO Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `gpio read <pin>` | Read GPIO pin level (0 or 1) | When pins configured |
| `gpio write <pin> <0\|1>` | Set GPIO output level | When pins configured |

Example:

```
h2c> gpio read PA0
PA0: 1
h2c> gpio write PC0 0
PC0 set to 0
```

### LED Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `led on` | Turn LED on | When LED pin exists |
| `led off` | Turn LED off | When LED pin exists |
| `led toggle` | Toggle LED state | When LED pin exists |

### RTC Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `rtc time` | Show current RTC time (HH:MM:SS) | When RTC enabled |
| `rtc set <HH:MM:SS>` | Set RTC time | When RTC enabled |

Example:

```
h2c> rtc time
RTC Time: 14:30:00
h2c> rtc set 08:00:00
RTC time set to 08:00:00
```

### Modbus Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `modbus read <addr> <count>` | Read holding registers | When Modbus enabled |
| `modbus write <addr> <value>` | Write single holding register | When Modbus enabled |

### Cellular Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `cellular status` | Show cellular connection status | When Cellular enabled |
| `cellular imei` | Show modem IMEI | When Cellular enabled |
| `cellular csq` | Show signal quality (CSQ) | When Cellular enabled |

### MQTT Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `mqtt status` | Show MQTT connection status | When MQTT enabled |
| `mqtt publish <topic> <payload>` | Publish a message to a topic | When MQTT enabled |

### FOTA Commands

| Command | Description | Availability |
|---------|-------------|-------------|
| `fota version` | Show current firmware version | When FOTA enabled |
| `fota start` | Enter FOTA receive mode | When FOTA enabled |

## Customization

CLI is generated via `templates/drivers/drv_cli.c.j2`. The following template variables control CLI behavior:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | `"> "` | Shell prompt string |
| `stack_size` | `512` | CLI task stack size in words |
| `priority` | `4` | CLI FreeRTOS task priority |
| `max_cmd_len` | `64` | Maximum command line length |
