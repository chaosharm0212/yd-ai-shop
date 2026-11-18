"""可复用的业务工具：订单号（雪花算法）等。"""
import os
import time

_EPOCH = 1735689600000  # 2025-01-01 00:00:00 UTC，压缩时间戳位数


class Snowflake:
    """64 位：1 位符号 | 41 位毫秒时间 | 5 位机房/机架 | 12 位序列号。"""

    def __init__(self, worker_id: int = 1) -> None:
        self.worker_id = worker_id & 0x1F
        self.seq = 0
        self.last_ts = -1

    def next_id(self) -> int:
        ts = int(time.time() * 1000)
        if ts == self.last_ts:
            self.seq = (self.seq + 1) & 0xFFF
            while self.seq == 0 and ts <= self.last_ts:  # 同一毫秒序列号用尽，等下一毫秒
                ts = int(time.time() * 1000)
        else:
            self.seq = 0
        self.last_ts = ts
        return ((ts - _EPOCH) << 22) | (self.worker_id << 17) | self.seq


_snowflake = Snowflake(int(os.getenv("WORKER_ID", "1")))


def gen_order_no() -> str:
    """对外订单号：不暴露自增 id，避免别人推算出日单量、防止遍历。"""
    return f"YD{_snowflake.next_id()}"
