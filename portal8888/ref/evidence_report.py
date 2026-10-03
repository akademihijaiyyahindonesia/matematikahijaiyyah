"""Evidence report for one sealed record: what is PROVEN by the Portal, what is OBSERVED on the wire,
and what is only ENRICHMENT (outside the Portal, approximate)."""
import ipaddress, json, random, provenance as V, packets as P
STATUS = {0: "OK", 1: "NOT_IP", 2: "TRUNCATED", 3: "UNSUPPORTED"}
def ip_text(b16, ver):
    a = ipaddress.IPv6Address(b16); return str(a.ipv4_mapped) if ver == 4 and a.ipv4_mapped else str(a)
def report(portal, ctr):
    flags = V.verify(portal.log, portal.K, portal.anchor())
    rec = next(x for x in portal.log if x.get("ctr") == ctr)
    pos = sum(1 for x in portal.log if x.get("port") == rec["port"] and x.get("ctr", 0) < ctr)
    st, ver, ip, sp, dp, pr, mac = rec["obs"]
    return {
      "verdict": "INTACT" if not flags else "TAMPERED", "flags": [list(f) for f in flags],
      "PROVEN_by_portal_hardware": {
        "portal_device": rec["dev"].decode(), "ingress_port": rec["port"], "arrival_counter": rec["ctr"],
        "chain_position": f"sudut {rec['port']}, catatan ke-{pos}", "frame_sha256": rec["fhash"].hex(),
        "sealed_tag": rec["tag"].hex()[:32]+"…", "anchored_head_matches": not any(f[0]=="head-anchor" for f in flags)},
      "OBSERVED_on_wire_sealed_as_seen": {
        "parse_status": STATUS[st], "ip_version": ver or None,
        "source_ip_claimed": ip_text(ip, ver) if st in (0, 3) and ver else None,
        "source_port": sp if st == 0 else None, "dest_port": dp if st == 0 else None,
        "l4_protocol": {6: "TCP", 17: "UDP"}.get(pr, pr or None), "source_mac_last_hop": mac.hex(":") if len(mac)==6 else None},
      "NOT_PROVEN": [
        "IP sumber bisa dipalsukan di asal (terutama UDP); Portal membuktikan apa yang TIBA, bukan siapa yang MENGIRIM.",
        "MAC hanya lompatan terakhir (router/switch lokal), bukan perangkat asal di internet.",
        "Lokasi geografis dari IP (GeoIP/ASN) adalah perkiraan dari basis data luar; VPN/Tor/proxy/NAT menyembunyikan asal.",
        "Identitas pelaku memerlukan catatan ISP lewat proses hukum."]}
rng = random.Random(42); pt = V.Portal(b"TN20K-01", rng.randbytes(32))
attack = P.eth(rng.randbytes(6), bytes.fromhex("02005e0010aa"), 0x0800) + P.ipv4(bytes([203,0,113,77]), bytes([10,0,0,5]), 6, P.l4(51515, 22, 6))
pt.ingress("B", attack); [pt.ingress(p, P.random_frames(1, rng)[0][1]) for p in "ACD"]
print(json.dumps(report(pt, 1), indent=2, ensure_ascii=False))
