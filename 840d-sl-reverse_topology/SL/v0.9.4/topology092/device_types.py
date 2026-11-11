"""Independent read-only labels for observed Topo 4.6 component type ranges.

These are classification hints, not a firmware compatibility guarantee.
Unknown codes stay UNKNOWN rather than being assigned a convenient class.
"""

# More specific overlapping categories precede their general class.
RANGES = (
    ('SENSOR_MODULE', ((512, 607), (3004, 3004))),
    ('MOTOR', ((3801, 3801), (4000, 4000), (3070, 3070))),
    ('ENCODER', ((3800, 3800), (4001, 4001), (3060, 3060))),
    ('HF_MOTOR_MODULE', ((264, 264),)),
    ('MOTOR_MODULE', ((256, 263), (265, 341), (343, 343),
                      (345, 367), (3002, 3002))),
    ('NCU', ((31, 31), (41, 69), (100, 102))),
    ('NX', ((20, 21), (23, 24))),
    ('CU', ((1, 1), (11, 11), (17, 17), (70, 79), (104, 104))),
    ('CONTROL_UNIT', ((3001, 3001),)),
    ('LINE_MODULE', ((368, 511), (342, 342), (344, 344), (3003, 3003))),
    ('VOLTAGE_SENSING_MODULE', ((608, 639), (3005, 3005))),
    ('TERMINAL_MODULE', ((768, 879), (3006, 3006))),
    ('HUB_MODULE', ((896, 911), (3007, 3007))),
    ('DAMPING_MODULE', ((1010, 1010), (3009, 3009))),
    ('SINE_FILTER_MODULE', ((4011, 4011), (3040, 3040))),
    ('TERMINAL_BOARD', ((3830, 3869),)),
    ('OPTION_BOARD', ((3804, 3873), (3050, 3050))),
)


def classify_device(code):
    if not isinstance(code, int):
        return 'UNKNOWN'
    for name, ranges in RANGES:
        if any(low <= code <= high for low, high in ranges):
            return name
    return 'UNKNOWN'
