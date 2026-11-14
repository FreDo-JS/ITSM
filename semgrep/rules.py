# ai-generated: 75% - Claude Code wrote the annotated cases for the two rules; I checked each ruleid/ok pair against svcdesk's code
import sqlite3
import time
from datetime import datetime, timezone


def handler_reads_the_wall_clock():
    # ruleid: svcdesk-direct-clock-read
    return datetime.now(timezone.utc)


def handler_reads_the_naive_wall_clock():
    # ruleid: svcdesk-direct-clock-read
    return datetime.utcnow()


def handler_reads_the_epoch():
    # ruleid: svcdesk-direct-clock-read
    return time.time()


def parses_the_request_clock(header):
    # ok: svcdesk-direct-clock-read
    return datetime.fromisoformat(header)


def builds_a_fixed_instant():
    # ok: svcdesk-direct-clock-read
    return datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)


def measures_a_duration():
    # ok: svcdesk-direct-clock-read
    return time.monotonic()


def store_shares_its_connection(path):
    # ruleid: svcdesk-sqlite-shared-connection
    return sqlite3.connect(path, check_same_thread=False)


def store_shares_its_connection_by_keyword(path):
    # ruleid: svcdesk-sqlite-shared-connection
    return sqlite3.connect(database=path, check_same_thread=False)


def connection_keeps_the_thread_check(path):
    # ok: svcdesk-sqlite-shared-connection
    return sqlite3.connect(path)


def connection_checks_the_thread_explicitly(path):
    # ok: svcdesk-sqlite-shared-connection
    return sqlite3.connect(path, check_same_thread=True)
