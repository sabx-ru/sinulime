#!/usr/bin/env python3
"""Small bounded S7comm/COTP **read-only** transport for SINUMERIK NCK.

Only S7 0xF0 SetupCommunication and 0x04 ReadVar are implemented.
NCK VarSpec: 12 08 82 (area<<5 | unit) column:u16 row:u16 module:u8 count:1.
No WriteVar or drive-control function exists here.

The on-controller support and addressing of specific drive params depends on
firmware. Refused/unsupported items are results, not evidence of zero values.
"""
from __future__ import annotations
import socket
import struct

class NckProtocolError(Exception):
    """Protocol parsing failure with a bounded hex sample for diagnostics."""
    def __init__(self, message, response=None):
        self.response_length = len(response) if response is not None else None
        self.response_hex = response[:256].hex() if response is not None else None
        super().__init__(message)

class NckTransportError(Exception):
    pass

BLOCKS = {'CU':0x80,'SERVO':0x82,'INFEED':0x83,'GENERAL_MD':0x1a,'AXIS_MD':0x1a}


def pack_tpkt(payload: bytes) -> bytes:
    total=len(payload)+4
    if not 4 <= total <= 8192:
        raise ValueError('TPKT length exceeds conservative bound')
    return b'\x03\x00'+struct.pack('>H',total)+payload


def nck_varspec(area:int,unit:int,column:int,row:int,block:int)->bytes:
    if not (0<=area<=7 and 0<=unit<=31 and 0<=column<=65535 and 1<=row<=65535 and block in BLOCKS.values()):
        raise ValueError('Out-of-bounds NCK read-only address')
    return b'\x12\x08\x82'+bytes([(area<<5)|unit])+struct.pack('>HH',column,row)+bytes([block,1])


def s7_job(ref:int,param:bytes)->bytes:
    return (b'\x32\x01\x00\x00'+struct.pack('>HHH',ref,len(param),0)+param)


def request_setup(ref:int=1)->bytes:
    return pack_tpkt(b'\x02\xf0\x80'+s7_job(ref,b'\xf0\x00\x00\x01\x00\x01\x00\xf0'))


def request_read(ref:int,area:int,unit:int,column:int,row:int,block:int)->bytes:
    param=b'\x04\x01'+nck_varspec(area,unit,column,row,block)
    return pack_tpkt(b'\x02\xf0\x80'+s7_job(ref,param))


def request_cotp(src_tsap:bytes=b'\x01\x00',dst_tsap:bytes=b'\x01\x03')->bytes:
    if len(src_tsap)!=2 or len(dst_tsap)!=2:
        raise ValueError('TSAP must be 2 bytes')
    return pack_tpkt(b'\x11\xe0\x00\x00\x00\x01\x00'+b'\xc0\x01\x0a'+b'\xc1\x02'+src_tsap+b'\xc2\x02'+dst_tsap)


def parse_s7(pdu:bytes, expected_ref:int, *, expected_function:int):
    if len(pdu)<12 or pdu[0]!=0x32 or pdu[1]!=0x03:
        rosctr = f'0x{pdu[1]:02x}' if len(pdu)>1 and pdu[0]==0x32 else 'unknown'
        raise NckProtocolError(f'Expected S7 AckData frame (ROSCTR={rosctr}, '
                               f'length={len(pdu)})', response=pdu)
    ref=int.from_bytes(pdu[4:6],'big')
    if ref!=expected_ref:
        raise NckProtocolError('PDU reference mismatch', response=pdu)
    param_len=int.from_bytes(pdu[6:8],'big')
    data_len=int.from_bytes(pdu[8:10],'big')
    if len(pdu)!=12+param_len+data_len:
        raise NckProtocolError('S7 response parameter/data length mismatch', response=pdu)
    err=pdu[10:12]
    if err!=b'\x00\x00':
        return dict(status='s7_header_error',code='0x'+err.hex(),raw_hex=None,
                    error=f'S7 header class/code 0x{err.hex()}')
    param=pdu[12:12+param_len]
    data=pdu[12+param_len:]
    if len(param)<1 or param[0]!=expected_function:
        raise NckProtocolError('Unexpected S7 function', response=pdu)
    return dict(status='ok',param=param,data=data,code='0xff')


def parse_read_ack(pdu:bytes,expected_ref:int):
    response=parse_s7(pdu,expected_ref,expected_function=0x04)
    if response['status']!='ok':return response
    param=response['param']; data=response['data']
    if len(param)<2 or param[1]!=1:
        raise NckProtocolError('Unexpected ReadVar item count', response=pdu)
    if len(data)<4:
        raise NckProtocolError('Truncated ReadVar response item', response=pdu)
    code,transport=data[0],data[1]
    count=int.from_bytes(data[2:4],'big')
    if code!=0xff:
        return dict(status='item_error',code=f'0x{code:02x}',raw_hex=None,
                    transport_size=transport,reported_length=count,
                    error=f'ReadVar item status 0x{code:02x}')
    buf=data[4:]
    # S7 transport size 0x04 often reports a BIT length. Real SINUMERIK NCK
    # 0x05/0x06/0x07 return the length directly in bytes on tested machines.
    if transport in (0x03,0x04):
        if count%8:raise NckProtocolError('Non-byte-aligned response', response=pdu)
        n=count//8
    elif transport in (0x05,0x06,0x07,0x09):
        n=count
    else:
        raise NckProtocolError(f'Unknown S7 response transport size 0x{transport:02x}', response=pdu)
    if n<1 or n>4096 or len(buf)<n:
        raise NckProtocolError(f'Invalid response size: reported={n}, available={len(buf)}', response=pdu)
    if len(buf)>n+1:
        raise NckProtocolError('Excess data in single-item ReadVar response', response=pdu)
    return dict(status='ok',code='0xff',raw_hex=buf[:n].hex(),
                transport_size=transport,reported_length=count)


def decode(raw_hex:str,dtype:str):
    b=bytes.fromhex(raw_hex)
    formats={'u8':(1,'>B'),'u16be':(2,'>H'),'i16be':(2,'>h'),
             'u32be':(4,'>I'),'u32le':(4,'<I'),'i32be':(4,'>i'),
             'f32be':(4,'>f')}
    if dtype=='raw':return raw_hex
    if dtype not in formats:raise ValueError('Unknown decode type')
    expected,fmt=formats[dtype]
    if len(b)!=expected:raise ValueError(f'{dtype} requires {expected} bytes, received {len(b)}')
    return struct.unpack(fmt,b)[0]


class NckClient:
    def __init__(self,host:str,port:int=102,timeout:float=4.,local_tsap:bytes=b'\x01\x00',
                 nck_tsap:bytes=b'\x01\x03',trace=None):
        if not (0<port<65536 and 0.2<=timeout<=30):raise ValueError('Invalid socket settings')
        self.host=host;self.port=port;self.timeout=timeout
        self.local_tsap=local_tsap;self.nck_tsap=nck_tsap
        self.trace=trace
        self.sock=None;self.ref=0

    def _rx_exact(self,n):
        data=bytearray()
        while len(data)<n:
            block=self.sock.recv(n-len(data))
            if not block:raise NckTransportError('Socket closed before full response')
            data.extend(block)
        return bytes(data)

    def _recv(self)->bytes:
        head=self._rx_exact(4)
        if head[:2]!=b'\x03\x00':raise NckProtocolError('Invalid TPKT signature')
        n=int.from_bytes(head[2:],'big')
        if not 7<=n<=8192:raise NckProtocolError('TPKT invalid size')
        content=self._rx_exact(n-4)
        if self.trace:self.trace('rx',head+content)
        return content

    def _send(self,payload):
        if self.trace:self.trace('tx',payload)
        self.sock.sendall(payload)

    def _next_ref(self):
        self.ref=1 if self.ref>=65535 else self.ref+1
        return self.ref

    def connect(self):
        if self.sock:return
        try:
            self.sock=socket.create_connection((self.host,self.port),timeout=self.timeout)
            self.sock.settimeout(self.timeout)
            self._send(request_cotp(self.local_tsap,self.nck_tsap))
            cc=self._recv()
            if len(cc)<2 or cc[1]!=0xd0:raise NckProtocolError('COTP connection confirmation missing')
            ref=self._next_ref()
            self._send(request_setup(ref))
            resp=self._recv()
            if resp[:3]!=b'\x02\xf0\x80':raise NckProtocolError('COTP Data TPDU expected')
            out=parse_s7(resp[3:],ref,expected_function=0xf0)
            if out['status']!='ok':raise NckProtocolError(f'S7 SetupCommunication error {out["code"]}')
            if len(out['param'])<8:raise NckProtocolError('Incomplete S7 SetupCommunication response')
            return int.from_bytes(out['param'][-2:],'big')
        except (OSError,NckProtocolError,NckTransportError) as e:
            self.close()
            if isinstance(e,OSError):raise NckTransportError(str(e)) from e
            raise

    def read(self,area:int,unit:int,column:int,index:int=0,block:int=0x80):
        if not self.sock:raise NckTransportError('Not connected')
        if not 0<=index<=65534:raise ValueError('NCK index out of range')
        ref=self._next_ref()
        self._send(request_read(ref,area,unit,column,index+1,block))
        try:
            tpdu=self._recv()
            if tpdu[:3]!=b'\x02\xf0\x80':raise NckProtocolError('COTP Data TPDU expected', response=tpdu)
            return parse_read_ack(tpdu[3:],ref)
        except OSError as e:
            raise NckTransportError(str(e)) from e

    def close(self):
        s=self.sock;self.sock=None
        if s:
            try:s.close()
            except OSError:pass

    def __enter__(self):self.connect();return self
    def __exit__(self,*a):self.close()
