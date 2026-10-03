"""Ethernet/IP packet builder + reference header parser (what the FPGA ingress must extract)."""
import random, struct, ipaddress
OK, NOT_IP, TRUNC, UNSUP = 0, 1, 2, 3
def eth(dst, src, ethertype, vlan=None):
    h = dst + src
    if vlan is not None: h += struct.pack(">HH", 0x8100, vlan)
    return h + struct.pack(">H", ethertype)
def ipv4(src, dst, proto, payload, opts=b""):
    ihl = 5 + len(opts)//4; tot = ihl*4 + len(payload)
    hdr = struct.pack(">BBHHHBBH4s4s", (4<<4)|ihl, 0, tot, 0, 0, 64, proto, 0, src, dst) + opts
    return hdr + payload
def ipv6(src, dst, nh, payload):
    return struct.pack(">IHBB16s16s", 6<<28, len(payload), nh, 64, src, dst) + payload
def l4(sport, dport, proto):
    if proto == 6:  return struct.pack(">HHIIBBHHH", sport, dport, 0, 0, 5<<4, 0x02, 1024, 0, 0)
    return struct.pack(">HHHH", sport, dport, 8, 0)
def parse(frame):
    """returns (status, ver, src_ip(16B, v4-mapped), sport, dport, proto, src_mac)"""
    z = (bytes(16), 0, 0, 0)
    if len(frame) < 14: return (TRUNC, 0, *z, b"")
    smac = frame[6:12]; i = 12; et = struct.unpack(">H", frame[i:i+2])[0]; i += 2
    if et == 0x8100:
        if len(frame) < i+4: return (TRUNC, 0, *z, smac)
        et = struct.unpack(">H", frame[i+2:i+4])[0]; i += 4
    if et == 0x0800:
        if len(frame) < i+20: return (TRUNC, 4, *z, smac)
        ihl = (frame[i] & 15)*4; proto = frame[i+9]; src = frame[i+12:i+16]
        if ihl < 20: return (UNSUP, 4, *z, smac)
        l = i+ihl; ip16 = bytes(10)+b"\xff\xff"+src
    elif et == 0x86DD:
        if len(frame) < i+40: return (TRUNC, 6, *z, smac)
        proto = frame[i+6]; ip16 = frame[i+8:i+24]; l = i+40
    else:
        return (NOT_IP, 0, *z, smac)
    ver = 4 if et == 0x0800 else 6
    if proto not in (6, 17): return (UNSUP, ver, ip16, 0, 0, proto, smac)
    if len(frame) < l+4: return (TRUNC, ver, ip16, 0, 0, proto, smac)
    sp, dp = struct.unpack(">HH", frame[l:l+4])
    return (OK, ver, ip16, sp, dp, proto, smac)
def random_frames(n, rng):
    out = []
    for k in range(n):
        dmac, smac = rng.randbytes(6), rng.randbytes(6)
        kind = rng.choice(["v4tcp","v4udp","v6udp","v6tcp","vlan4","v4opt","arp","trunc","v6ext","icmp"])
        sp, dp = rng.randrange(65536), rng.randrange(65536)
        s4, d4 = rng.randbytes(4), rng.randbytes(4); s6, d6 = rng.randbytes(16), rng.randbytes(16)
        if kind=="v4tcp":  f = eth(dmac,smac,0x0800)+ipv4(s4,d4,6,l4(sp,dp,6))
        elif kind=="v4udp":f = eth(dmac,smac,0x0800)+ipv4(s4,d4,17,l4(sp,dp,17)+rng.randbytes(20))
        elif kind=="v6udp":f = eth(dmac,smac,0x86DD)+ipv6(s6,d6,17,l4(sp,dp,17))
        elif kind=="v6tcp":f = eth(dmac,smac,0x86DD)+ipv6(s6,d6,6,l4(sp,dp,6))
        elif kind=="vlan4":f = eth(dmac,smac,0x0800,vlan=rng.randrange(4096))+ipv4(s4,d4,17,l4(sp,dp,17))
        elif kind=="v4opt":f = eth(dmac,smac,0x0800)+ipv4(s4,d4,6,l4(sp,dp,6),opts=rng.randbytes(8))
        elif kind=="arp":  f = eth(dmac,smac,0x0806)+rng.randbytes(28)
        elif kind=="trunc":f = (eth(dmac,smac,0x0800)+ipv4(s4,d4,6,l4(sp,dp,6)))[:rng.randrange(10,36)]
        elif kind=="v6ext":f = eth(dmac,smac,0x86DD)+ipv6(s6,d6,0,rng.randbytes(16))   # hop-by-hop: unsupported
        else:              f = eth(dmac,smac,0x0800)+ipv4(s4,d4,1,rng.randbytes(8))
        out.append((kind, f))
    return out
