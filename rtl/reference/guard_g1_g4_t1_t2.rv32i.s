# Guard G1-G4 + T1-T2 atas satu codex v18 di RV32I.
# a0 = alamat basis, 18 word (32-bit) berurutan comp[0..17].
# Hasil: a1 = 1 bila lolos, 0 bila gagal.
        li      a1, 0
# --- G1: A_N == Na+Nb+Nd
        lw      t0, 4(a0)        # Na
        lw      t1, 8(a0)        # Nb
        lw      t2, 12(a0)       # Nd
        lw      t3, 56(a0)       # A_N
        add     t4, t0, t1
        add     t4, t4, t2
        bne     t4, t3, fail
# --- G2: A_K == Kp+Kx+Ks+Ka+Kc
        lw      t0, 16(a0)       # Kp
        lw      t1, 20(a0)       # Kx
        lw      t2, 24(a0)       # Ks
        lw      t3, 28(a0)       # Ka
        lw      t5, 32(a0)       # Kc
        lw      t6, 60(a0)       # A_K
        add     t4, t0, t1
        add     t4, t4, t2
        add     t4, t4, t3
        add     t4, t4, t5
        bne     t4, t6, fail
# --- simpan Ks dan Kc utk T1/T2
        mv      s0, t2           # Ks
        mv      s1, t5           # Kc
# --- G3: A_Q == Qp+Qx+Qs+Qa+Qc
        lw      t0, 36(a0)       # Qp
        lw      t1, 40(a0)       # Qx
        lw      t2, 44(a0)       # Qs
        lw      t3, 48(a0)       # Qa
        lw      t5, 52(a0)       # Qc
        lw      t6, 64(a0)       # A_Q
        add     t4, t0, t1
        add     t4, t4, t2
        add     t4, t4, t3
        add     t4, t4, t5
        bne     t4, t6, fail
# --- G4: theta >= Qx+Qs+Qa+4*Qc
        lw      t0, 0(a0)        # theta
        slli    t6, t5, 2        # 4*Qc
        add     t4, t1, t2
        add     t4, t4, t3
        add     t4, t4, t6
        blt     t0, t4, fail
# --- T1: Ks>0 -> Qc>=1
        beqz    s0, t2check
        beqz    t5, fail
t2check:
# --- T2: Kc>0 -> Qc>=1
        beqz    s1, pass
        beqz    t5, fail
pass:
        li      a1, 1
fail:
        ret
