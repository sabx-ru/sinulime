from application.cursors import make_cursor, read_cursor
import pytest
from application.errors import ResyncRequired

def test_cursor_binding_and_tamper_are_resync():
    token=make_cursor('event.list',{},3,consistency='event_log',installation='i',retention=2)
    assert read_cursor(token,'event.list',{},consistency='event_log',installation='i',retention=2)==3
    with pytest.raises(ResyncRequired): read_cursor(token,'event.list',{},consistency='event_log',installation='other',retention=2)
