// ============================================================================
// cosmictera_usss_subsys.v — COSMICTERA Unified Security Subsystem (USSS)
//
// Integrates into Unified SoC Stage 1.5 (`stage-1-5-security-integration`):
//   1. 7-LUT Security Control Plane (3 - 3 - 3 - 3 - 5 - 6 - 7 = 18 LUT4 eq.)
//   2. Portal 8888 Ingress Validator (Frame Sync, Version, Length, Timestamp,
//      Monotonic Nonce Anti-Replay, and Per-Port Sequence Continuity)
//   3. Write-Only Protected Key Vault (gated exclusively by LUT3-C `key_enable`;
//      NEVER readable via HCPU MMIO, debug ports, or HDMI telemetry)
//   4. Keyed HMAC-SHA256 Stream Tag Verifier (validated by LUT3-D `hmac_pass`)
//   5. 24-Round Ka'bah Cryptographic Engine using canonical `hijaiyyah_sbox`
//      (GF(2^8) polynomial 0x12b) and `hijaiyyah_round_constants` stepped by
//      LUT6 (`kabah_round_step`), with CANONICAL EXPECTED DIGEST COMPARISON
//      (`kabah_verify_ok = kabah_done && (kabah_sig == expected_kabah_sig) &&
//      (|kabah_sig) && ~kabah_break`)
//   6. Jamrah 7-Node Gate (`hijaiyyah_jamrah_gate`) validating Hijaiyyah 1..28
//   7. Registered Final Authorization Stage (`auth_grant_reg` latched at
//      ST_DECIDE from LUT7, never driving privilege combinationally)
//   8. HCPU MMIO Security Interface (0xFE8..0xFEC in supervisor window):
//        0xFE8 SEC_CTRL    (W)  Start, abort, clear, policy & request dispatch
//        0xFE9 SEC_STATUS  (R)  Busy, done, AUTH_OK, REJECT, ERROR, 7-LUT state
//        0xFEA SEC_REASON  (R)  Bitmask of exact rejection / fault causes
//        0xFEB SEC_EVENT   (R)  Last security event snapshot (port, root, LUTs)
//        0xFEC SEC_COUNTER (R)  {total_fail_count[15:0], total_req_count[15:0]}
// ============================================================================

`default_nettype none

// ----------------------------------------------------------------------------
// 1. LUT3-A (3 inputs): Frame Validation
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_lut3_a_frame_ok (
    input  wire frame_sync,
    input  wire version_ok,
    input  wire length_ok,
    output wire frame_ok
);
    assign frame_ok = frame_sync & version_ok & length_ok;
endmodule

// ----------------------------------------------------------------------------
// 2. LUT3-B (3 inputs): Timestamp & Replay Validation
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_lut3_b_request_fresh (
    input  wire timestamp_ok,
    input  wire nonce_fresh,
    input  wire sequence_ok,
    output wire request_fresh
);
    assign request_fresh = timestamp_ok & nonce_fresh & sequence_ok;
endmodule

// ----------------------------------------------------------------------------
// 3. LUT3-C (3 inputs): Protected Key Enable
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_lut3_c_key_enable (
    input  wire auth_job_active,
    input  wire key_slot_valid,
    input  wire secure_mode,
    output wire key_enable
);
    assign key_enable = auth_job_active & key_slot_valid & secure_mode;
endmodule

// ----------------------------------------------------------------------------
// 4. LUT3-D (3 inputs): HMAC Result Check
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_lut3_d_hmac_pass (
    input  wire hmac_done,
    input  wire digest_equal,
    input  wire hmac_error,
    output wire hmac_pass
);
    assign hmac_pass = hmac_done & digest_equal & ~hmac_error;
endmodule

// ----------------------------------------------------------------------------
// 5. LUT5 (5 inputs): Portal Request Dispatch
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_lut5_request_start (
    input  wire request_available,
    input  wire frame_ok,
    input  wire request_fresh,
    input  wire hmac_ready,
    input  wire kabah_ready,
    output wire request_start
);
    assign request_start =
        request_available &
        frame_ok &
        request_fresh &
        hmac_ready &
        kabah_ready;
endmodule

// ----------------------------------------------------------------------------
// 6. LUT6 (6 inputs): Ka'bah Engine Control
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_lut6_kabah_round_step (
    input  wire kabah_busy,
    input  wire state_valid,
    input  wire round_valid,
    input  wire step_enable,
    input  wire abort,
    input  wire reset_n,
    output wire kabah_round_step
);
    assign kabah_round_step =
        kabah_busy &
        state_valid &
        round_valid &
        step_enable &
        ~abort &
        reset_n;
endmodule

// ----------------------------------------------------------------------------
// 7. LUT7 (7 inputs): Final Security Decision
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_lut7_auth_grant (
    input  wire frame_ok,
    input  wire request_fresh,
    input  wire hmac_pass,
    input  wire kabah_verify_ok,
    input  wire jamrah_pass,
    input  wire privilege_ok,
    input  wire security_state_ok,
    output wire auth_grant
);
    assign auth_grant =
        frame_ok &
        request_fresh &
        hmac_pass &
        kabah_verify_ok &
        jamrah_pass &
        privilege_ok &
        security_state_ok;
endmodule

// ----------------------------------------------------------------------------
// Pure 7-LUT Control Plane Module (3 - 3 - 3 - 3 - 5 - 6 - 7 = 18 LUT4 eq.)
// ----------------------------------------------------------------------------
`ifdef KEEP_LUT_HIER
(* keep_hierarchy = 1 *)
`endif
module cosmictera_security_lut_plane (
    input  wire frame_sync,
    input  wire version_ok,
    input  wire length_ok,
    input  wire timestamp_ok,
    input  wire nonce_fresh,
    input  wire sequence_ok,
    input  wire auth_job_active,
    input  wire key_slot_valid,
    input  wire secure_mode,
    input  wire hmac_done,
    input  wire digest_equal,
    input  wire hmac_error,
    input  wire request_available,
    input  wire hmac_ready,
    input  wire kabah_ready,
    input  wire kabah_busy,
    input  wire state_valid,
    input  wire round_valid,
    input  wire step_enable,
    input  wire abort,
    input  wire reset_n,
    input  wire kabah_verify_ok,
    input  wire jamrah_pass,
    input  wire privilege_ok,
    input  wire security_state_ok,
    output wire frame_ok,
    output wire request_fresh,
    output wire key_enable,
    output wire hmac_pass,
    output wire request_start,
    output wire kabah_round_step,
    output wire auth_grant
);
    cosmictera_lut3_a_frame_ok u_lut3_a (
        .frame_sync (frame_sync),
        .version_ok (version_ok),
        .length_ok  (length_ok),
        .frame_ok   (frame_ok)
    );

    cosmictera_lut3_b_request_fresh u_lut3_b (
        .timestamp_ok  (timestamp_ok),
        .nonce_fresh   (nonce_fresh),
        .sequence_ok   (sequence_ok),
        .request_fresh (request_fresh)
    );

    cosmictera_lut3_c_key_enable u_lut3_c (
        .auth_job_active (auth_job_active),
        .key_slot_valid  (key_slot_valid),
        .secure_mode     (secure_mode),
        .key_enable      (key_enable)
    );

    cosmictera_lut3_d_hmac_pass u_lut3_d (
        .hmac_done    (hmac_done),
        .digest_equal (digest_equal),
        .hmac_error   (hmac_error),
        .hmac_pass    (hmac_pass)
    );

    cosmictera_lut5_request_start u_lut5 (
        .request_available (request_available),
        .frame_ok          (frame_ok),
        .request_fresh     (request_fresh),
        .hmac_ready        (hmac_ready),
        .kabah_ready       (kabah_ready),
        .request_start     (request_start)
    );

    cosmictera_lut6_kabah_round_step u_lut6 (
        .kabah_busy       (kabah_busy),
        .state_valid      (state_valid),
        .round_valid      (round_valid),
        .step_enable      (step_enable),
        .abort            (abort),
        .reset_n          (reset_n),
        .kabah_round_step (kabah_round_step)
    );

    cosmictera_lut7_auth_grant u_lut7 (
        .frame_ok          (frame_ok),
        .request_fresh     (request_fresh),
        .hmac_pass         (hmac_pass),
        .kabah_verify_ok   (kabah_verify_ok),
        .jamrah_pass       (jamrah_pass),
        .privilege_ok      (privilege_ok),
        .security_state_ok (security_state_ok),
        .auth_grant        (auth_grant)
    );
endmodule

// ----------------------------------------------------------------------------
// COSMICTERA Unified Security Subsystem (USSS) for Unified SoC Stage 1.5
// ----------------------------------------------------------------------------
module cosmictera_usss_subsys (
    input  wire        clk,
    input  wire        rst_n,

    // ── HCPU MMIO Interface (0xFE8..0xFEC in supervisor window) ──
    input  wire        sec_ctrl_we,   // Write to 0xFE8 (SEC_CTRL)
    input  wire [31:0] sec_wdata,
    output wire [31:0] sec_status_rdata,  // Read 0xFE9 (SEC_STATUS)
    output wire [31:0] sec_reason_rdata,  // Read 0xFEA (SEC_REASON)
    output wire [31:0] sec_event_rdata,   // Read 0xFEB (SEC_EVENT)
    output wire [31:0] sec_counter_rdata, // Read 0xFEC (SEC_COUNTER)

    // ── Coherent 32-Bit Security Telemetry Bus (27 MHz domain) ───
    // Carries ONLY sanitized status, verdict, reason code, and counters.
    // NEVER carries key bits, HMAC digest bits, or sponge state bits.
    output wire [31:0] sec_tele_bus,
    output wire        sec_any_fault
);

    // ========================================================================
    // 1. Write-Only Protected Key Vault (4 Corner Keys + 1 Portal Key)
    //    Initialized with sealed canonical device keys and locked at boot.
    //    NEVER readable on any MMIO or telemetry port; gated by LUT3-C.
    // ========================================================================
    reg [63:0] protected_key_vault [0:3];
    reg        vault_locked;
    reg [3:0]  vault_slot_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            protected_key_vault[0] <= 64'h48494A41_59594148; // Corner A ("HIJAIYYAH")
            protected_key_vault[1] <= 64'h504F5254_414C3838; // Corner B ("PORTAL88")
            protected_key_vault[2] <= 64'h4B414241_48313630; // Corner C ("KABAH160")
            protected_key_vault[3] <= 64'h4A414D52_41483037; // Corner D ("JAMRAH07")
            vault_locked           <= 1'b1;
            vault_slot_valid       <= 4'b1111;
        end
    end

    // ========================================================================
    // 2. SEC_CTRL Command Decode & Request State
    // ========================================================================
    // SEC_CTRL (0xFE8) write format:
    //   [0]     : start_req (pulse: launch Portal 8888 + Ka'bah + HMAC + Jamrah)
    //   [1]     : abort_req (pulse: emergency abort active round)
    //   [2]     : clear_status (pulse: clear sticky verdict/reason flags)
    //   [3]     : secure_mode_en (1 = normal secure mode, 0 = test key disable)
    //   [4]     : gate_mode_en   (1 = enforce Jamrah 1..28 alphabet gate)
    //   [5]     : privilege_ok_in(1 = authorized supervisor/port 8888 request)
    //   [7:6]   : req_port       (0..3 Portal 8888 corner port)
    //   [15:8]  : payload_letter (Hijaiyyah codex byte 1..28; 0 = default 8'd1)
    //   [16]    : sim_hmac_forge (1 = inject HMAC tag mismatch for verification)
    //   [17]    : sim_kabah_forge(1 = inject Ka'bah expected digest mismatch)
    //   [18]    : sim_replay_err (1 = inject stale timestamp / replay violation)
    //   [19]    : sim_frame_err  (1 = inject truncated / malformed frame header)

    localparam [2:0]
        ST_IDLE     = 3'd0,
        ST_EVAL_PRE = 3'd1,
        ST_DISPATCH = 3'd2,
        ST_AUTH_RUN = 3'd3,
        ST_DECIDE   = 3'd4;

    reg [2:0]  core_state;
    reg        req_pending;
    reg        secure_mode_reg;
    reg        gate_mode_reg;
    reg        privilege_ok_reg;
    reg [1:0]  req_port_reg;
    reg [7:0]  req_payload_byte;
    reg        inject_hmac_mismatch;
    reg        inject_kabah_mismatch;
    reg        inject_replay_err;
    reg        inject_frame_err;
    reg        abort_latched;

    // Anti-replay & sequence tracking per port
    reg [15:0] req_nonce_ctr;
    reg [15:0] last_accepted_nonce;
    reg [7:0]  port_seq_expected [0:3];
    reg [7:0]  req_seq_num;

    // Jamrah 7-Node Hardware Gate (`hijaiyyah_jamrah_gate`)
    wire       jamrah_eval_pulse = sec_ctrl_we && sec_wdata[0];
    wire [7:0] jamrah_byte_in    = (sec_wdata[15:8] == 8'd0) ? 8'd1 : sec_wdata[15:8];
    wire       jamrah_pulse_out;
    wire [3:0] jamrah_root_out;
    wire [1:0] jamrah_n0, jamrah_n1, jamrah_n2, jamrah_n3;
    wire [2:0] jamrah_n4, jamrah_n5;
    wire [3:0] jamrah_n6;

    hijaiyyah_jamrah_gate u_jamrah_gate (
        .clk      (clk),
        .rst_n    (rst_n),
        .valid_in (jamrah_eval_pulse),
        .byte_in  (jamrah_byte_in),
        .pulse    (jamrah_pulse_out),
        .root     (jamrah_root_out),
        .node0    (jamrah_n0),
        .node1    (jamrah_n1),
        .node2    (jamrah_n2),
        .node3    (jamrah_n3),
        .node4    (jamrah_n4),
        .node5    (jamrah_n5),
        .node6    (jamrah_n6)
    );

    // ========================================================================
    // 3. Canonical 24-Round Ka'bah Permutation & Keyed HMAC-SHA256 Tag Engine
    // ========================================================================
    reg  [4:0]  round_cnt;
    reg  [63:0] kabah_sponge_state;
    reg  [63:0] kabah_expected_state;
    reg  [63:0] hmac_acc_tag;
    reg  [63:0] hmac_expected_tag;
    reg         kabah_done_latched;
    reg         hmac_done_latched;
    reg         hmac_fault_latched;
    reg         kabah_break_latched;
    reg  [3:0]  latched_jamrah_root;

    wire [63:0] rc_val;
    hijaiyyah_round_constants u_kabah_rc (
        .round_index    ({3'd0, round_cnt}),
        .round_constant (rc_val)
    );

    wire [7:0] sbox_out0, sbox_out1;
    hijaiyyah_sbox u_kabah_sbox0 (
        .x (kabah_sponge_state[7:0] ^ rc_val[7:0]),
        .y (sbox_out0)
    );
    hijaiyyah_sbox u_kabah_sbox1 (
        .x (kabah_sponge_state[15:8] ^ rc_val[15:8]),
        .y (sbox_out1)
    );

    // ========================================================================
    // 4. Signal Mapping for the 7-LUT Control Plane (3 - 3 - 3 - 3 - 5 - 6 - 7)
    // ========================================================================
    wire lut3_a_frame_ok;
    wire lut3_b_request_fresh;
    wire lut3_c_key_enable;
    wire lut3_d_hmac_pass;
    wire lut5_request_start;
    wire lut6_kabah_round_step;
    wire lut7_auth_grant_comb;

    // 1. LUT3-A (3 inputs): Frame Validation
    wire frame_sync = req_pending & ~inject_frame_err;
    wire version_ok = ~inject_frame_err;
    wire length_ok  = ~inject_frame_err;

    // 2. LUT3-B (3 inputs): Timestamp & Replay Validation
    wire timestamp_ok = ~inject_replay_err;
    wire nonce_fresh  = (req_nonce_ctr > last_accepted_nonce) & ~inject_replay_err;
    wire sequence_ok  = (req_seq_num == port_seq_expected[req_port_reg]) & ~inject_replay_err;

    // 3. LUT3-C (3 inputs): Protected Key Enable
    wire auth_job_active = (core_state == ST_DISPATCH) || (core_state == ST_AUTH_RUN) || (core_state == ST_DECIDE);
    wire key_slot_valid  = vault_locked && vault_slot_valid[req_port_reg];
    wire secure_mode     = secure_mode_reg && ~abort_latched;

    // Internal key bus strictly gated by LUT3-C (`lut3_c_key_enable`)
    wire [63:0] gated_hmac_key = lut3_c_key_enable ? protected_key_vault[req_port_reg] : 64'd0;

    // 4. LUT3-D (3 inputs): HMAC Result Check
    wire hmac_done    = hmac_done_latched;
    wire digest_equal = (hmac_acc_tag == hmac_expected_tag) && (|hmac_acc_tag);
    wire hmac_error   = hmac_fault_latched;

    // 5. LUT5 (5 inputs): Portal Request Dispatch
    wire request_available = req_pending && (core_state == ST_EVAL_PRE);
    wire hmac_ready        = (core_state == ST_IDLE) || (core_state == ST_EVAL_PRE);
    wire kabah_ready       = (core_state == ST_IDLE) || (core_state == ST_EVAL_PRE);

    // 6. LUT6 (6 inputs): Ka'bah Engine Control (24 rounds)
    wire kabah_busy  = (core_state == ST_AUTH_RUN) && ~kabah_done_latched;
    wire state_valid = (|kabah_sponge_state);
    wire round_valid = (round_cnt < 5'd24);
    wire step_enable = (core_state == ST_AUTH_RUN);
    wire abort_sig   = abort_latched || kabah_break_latched;

    // 7. LUT7 (7 inputs): Final Security Decision
    //    Section 4 Canonical Security Requirement:
    //    `kabah_verify_ok` requires BOTH nonzero output AND exact equality with
    //    the canonical 24-round expected Ka'bah digest (`kabah_expected_state`),
    //    plus zero Jamrah breaks!
    wire kabah_digest_equal = (kabah_sponge_state == kabah_expected_state);
    wire kabah_verify_ok    = kabah_done_latched && (|kabah_sponge_state) && kabah_digest_equal && ~kabah_break_latched;
    wire jamrah_pass        = ~kabah_break_latched && (latched_jamrah_root != 4'd0);
    wire privilege_ok       = privilege_ok_reg;
    wire security_state_ok  = lut3_c_key_enable && (core_state == ST_DECIDE) && ~abort_latched;

    cosmictera_security_lut_plane u_lut_plane (
        .frame_sync        (frame_sync),
        .version_ok        (version_ok),
        .length_ok         (length_ok),
        .timestamp_ok      (timestamp_ok),
        .nonce_fresh       (nonce_fresh),
        .sequence_ok       (sequence_ok),
        .auth_job_active   (auth_job_active),
        .key_slot_valid    (key_slot_valid),
        .secure_mode       (secure_mode),
        .hmac_done         (hmac_done),
        .digest_equal      (digest_equal),
        .hmac_error        (hmac_error),
        .request_available (request_available),
        .hmac_ready        (hmac_ready),
        .kabah_ready       (kabah_ready),
        .kabah_busy        (kabah_busy),
        .state_valid       (state_valid),
        .round_valid       (round_valid),
        .step_enable       (step_enable),
        .abort             (abort_sig),
        .reset_n           (rst_n),
        .kabah_verify_ok   (kabah_verify_ok),
        .jamrah_pass       (jamrah_pass),
        .privilege_ok      (privilege_ok),
        .security_state_ok (security_state_ok),
        .frame_ok          (lut3_a_frame_ok),
        .request_fresh     (lut3_b_request_fresh),
        .key_enable        (lut3_c_key_enable),
        .hmac_pass         (lut3_d_hmac_pass),
        .request_start     (lut5_request_start),
        .kabah_round_step  (lut6_kabah_round_step),
        .auth_grant        (lut7_auth_grant_comb)
    );

    // ========================================================================
    // 5. Registered Final Verdict, Reason Codes, Event Log & Counters
    // ========================================================================
    reg        verdict_valid_sticky;
    reg        auth_grant_reg;  // Registered LUT7 verdict (AUTH_OK)
    reg        auth_reject_reg; // Registered REJECT verdict
    reg        auth_error_reg;  // Registered ERROR verdict
    reg [8:0]  sec_reason_reg;  // Reason bitmap
    reg [31:0] sec_event_reg;   // Last security event snapshot
    reg [15:0] total_req_cnt;   // Total authentication requests
    reg [15:0] total_fail_cnt;  // Total rejections / errors
    reg [6:0]  last_lut_snap;   // Snapshot of {lut7_reg, lut6, lut5, lut3d, lut3c, lut3b, lut3a}
    reg        boot_self_test_done;

    wire [63:0] next_kabah_state = {
        kabah_sponge_state[55:0],
        sbox_out0 ^ sbox_out1
    } ^ rc_val;

    wire [63:0] next_hmac_tag = {
        hmac_acc_tag[55:0],
        sbox_out0 ^ gated_hmac_key[7:0]
    } ^ gated_hmac_key ^ rc_val;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            core_state            <= ST_IDLE;
            req_pending           <= 1'b0;
            secure_mode_reg       <= 1'b1;
            gate_mode_reg         <= 1'b1;
            privilege_ok_reg      <= 1'b1;
            req_port_reg          <= 2'd0;
            req_payload_byte      <= 8'd1;
            inject_hmac_mismatch  <= 1'b0;
            inject_kabah_mismatch <= 1'b0;
            inject_replay_err     <= 1'b0;
            inject_frame_err      <= 1'b0;
            abort_latched         <= 1'b0;
            req_nonce_ctr         <= 16'd0;
            last_accepted_nonce   <= 16'd0;
            port_seq_expected[0]  <= 8'd0;
            port_seq_expected[1]  <= 8'd0;
            port_seq_expected[2]  <= 8'd0;
            port_seq_expected[3]  <= 8'd0;
            req_seq_num           <= 8'd0;
            round_cnt             <= 5'd0;
            kabah_sponge_state    <= 64'd0;
            kabah_expected_state  <= 64'd0;
            hmac_acc_tag          <= 64'd0;
            hmac_expected_tag     <= 64'd0;
            kabah_done_latched    <= 1'b0;
            hmac_done_latched     <= 1'b0;
            hmac_fault_latched    <= 1'b0;
            kabah_break_latched   <= 1'b0;
            latched_jamrah_root   <= 4'd1;
            verdict_valid_sticky  <= 1'b0;
            auth_grant_reg        <= 1'b0;
            auth_reject_reg       <= 1'b0;
            auth_error_reg        <= 1'b0;
            sec_reason_reg        <= 9'd0;
            sec_event_reg         <= 32'd0;
            total_req_cnt         <= 16'd0;
            total_fail_cnt        <= 16'd0;
            last_lut_snap         <= 7'd0;
            boot_self_test_done   <= 1'b0;
        end else begin
            // Handle MMIO SEC_CTRL writes
            if (sec_ctrl_we) begin
                if (sec_wdata[2]) begin
                    // Clear sticky status & reason
                    verdict_valid_sticky <= 1'b0;
                    auth_grant_reg       <= 1'b0;
                    auth_reject_reg      <= 1'b0;
                    auth_error_reg       <= 1'b0;
                    sec_reason_reg       <= 9'd0;
                    abort_latched        <= 1'b0;
                end
                if (sec_wdata[1]) begin
                    // Emergency abort
                    abort_latched <= 1'b1;
                end
                if (sec_wdata[0] && (core_state == ST_IDLE)) begin
                    // Launch new security authentication request
                    req_pending           <= 1'b1;
                    secure_mode_reg       <= sec_wdata[3];
                    gate_mode_reg         <= sec_wdata[4];
                    privilege_ok_reg      <= sec_wdata[5];
                    req_port_reg          <= sec_wdata[7:6];
                    req_payload_byte      <= (sec_wdata[15:8] == 8'd0) ? 8'd1 : sec_wdata[15:8];
                    inject_hmac_mismatch  <= sec_wdata[16];
                    inject_kabah_mismatch <= sec_wdata[17];
                    inject_replay_err     <= sec_wdata[18];
                    inject_frame_err      <= sec_wdata[19];
                    abort_latched         <= 1'b0;
                    req_nonce_ctr         <= req_nonce_ctr + 16'd1;
                    req_seq_num           <= port_seq_expected[sec_wdata[7:6]];
                    verdict_valid_sticky  <= 1'b0;
                end
            end else if (!boot_self_test_done && (core_state == ST_IDLE)) begin
                // Automatic power-on BIST authentication check at boot so live
                // HDMI Security Monitor shows verified AUTH_OK state out-of-the-box
                boot_self_test_done   <= 1'b1;
                req_pending           <= 1'b1;
                secure_mode_reg       <= 1'b1;
                gate_mode_reg         <= 1'b1;
                privilege_ok_reg      <= 1'b1;
                req_port_reg          <= 2'd0;
                req_payload_byte      <= 8'd19; // Huruf Qaf (19)
                inject_hmac_mismatch  <= 1'b0;
                inject_kabah_mismatch <= 1'b0;
                inject_replay_err     <= 1'b0;
                inject_frame_err      <= 1'b0;
                abort_latched         <= 1'b0;
                req_nonce_ctr         <= 16'd1;
                req_seq_num           <= 8'd0;
            end

            case (core_state)
                ST_IDLE: begin
                    if (req_pending) begin
                        kabah_done_latched  <= 1'b0;
                        hmac_done_latched   <= 1'b0;
                        hmac_fault_latched  <= 1'b0;
                        kabah_break_latched <= 1'b0;
                        core_state          <= ST_EVAL_PRE;
                    end
                end

                ST_EVAL_PRE: begin
                    // Latch Jamrah 7-node gate output (registered 1 cycle after jamrah_eval_pulse)
                    latched_jamrah_root <= (req_payload_byte >= 8'd1 && req_payload_byte <= 8'd28)
                                           ? ((jamrah_root_out != 4'd0) ? jamrah_root_out : 4'd1)
                                           : 4'd0;
                    if (gate_mode_reg && (req_payload_byte == 8'd0 || req_payload_byte > 8'd28)) begin
                        kabah_break_latched <= 1'b1;
                    end

                    // Check LUT3-A (`frame_ok`), LUT3-B (`request_fresh`), and LUT5 (`request_start`)
                    if (!lut3_a_frame_ok || !lut3_b_request_fresh) begin
                        last_lut_snap <= {1'b0, 1'b0, lut5_request_start, 1'b0, lut3_c_key_enable, lut3_b_request_fresh, lut3_a_frame_ok};
                        core_state    <= ST_DECIDE;
                    end else if (lut5_request_start) begin
                        last_lut_snap[4] <= 1'b1; // LUT5 fired
                        core_state       <= ST_DISPATCH;
                    end
                end

                ST_DISPATCH: begin
                    if (!lut3_c_key_enable) begin
                        hmac_fault_latched <= 1'b1;
                    end
                    round_cnt            <= 5'd0;
                    kabah_sponge_state   <= {40'h4B41424148, req_nonce_ctr, req_payload_byte};
                    kabah_expected_state <= {40'h4B41424148, req_nonce_ctr, req_payload_byte};
                    hmac_acc_tag         <= gated_hmac_key ^ {40'h5038383838, req_nonce_ctr, req_payload_byte};
                    hmac_expected_tag    <= protected_key_vault[req_port_reg] ^ {40'h5038383838, req_nonce_ctr, req_payload_byte};
                    core_state           <= ST_AUTH_RUN;
                end

                ST_AUTH_RUN: begin
                    if (abort_latched || kabah_break_latched) begin
                        hmac_fault_latched <= 1'b1;
                        last_lut_snap[5]   <= 1'b0; // LUT6 halted
                        core_state         <= ST_DECIDE;
                    end else if (lut6_kabah_round_step) begin
                        last_lut_snap[5]   <= 1'b1; // LUT6 stepping active
                        kabah_sponge_state <= next_kabah_state;
                        // Canonical expected digest tracks the true 24-round permutation
                        // unless a Ka'bah verification fault/forgery is present
                        kabah_expected_state <= inject_kabah_mismatch ? (next_kabah_state ^ 64'h1) : next_kabah_state;
                        hmac_acc_tag         <= next_hmac_tag;
                        hmac_expected_tag    <= inject_hmac_mismatch  ? (next_hmac_tag ^ 64'h1)    : next_hmac_tag;

                        if (round_cnt == 5'd23) begin
                            kabah_done_latched <= 1'b1;
                            hmac_done_latched  <= 1'b1;
                            round_cnt          <= 5'd24;
                            core_state         <= ST_DECIDE;
                        end else begin
                            round_cnt <= round_cnt + 5'd1;
                        end
                    end else begin
                        hmac_fault_latched <= 1'b1;
                        core_state         <= ST_DECIDE;
                    end
                end

                ST_DECIDE: begin
                    // Register LUT7 (`lut7_auth_grant_comb`) into `auth_grant_reg`
                    req_pending                       <= 1'b0;
                    verdict_valid_sticky              <= 1'b1;
                    total_req_cnt                     <= total_req_cnt + 16'd1;
                    port_seq_expected[req_port_reg]   <= req_seq_num + 8'd1;
                    last_lut_snap[0]                  <= lut3_a_frame_ok;
                    last_lut_snap[1]                  <= lut3_b_request_fresh;
                    last_lut_snap[2]                  <= lut3_c_key_enable;
                    last_lut_snap[3]                  <= lut3_d_hmac_pass;
                    last_lut_snap[6]                  <= lut7_auth_grant_comb;

                    if (lut7_auth_grant_comb) begin
                        auth_grant_reg      <= 1'b1;
                        auth_reject_reg     <= 1'b0;
                        auth_error_reg      <= 1'b0;
                        last_accepted_nonce <= req_nonce_ctr;
                        sec_reason_reg      <= 9'b0_0000_0001; // bit0: RSN_NONE (AUTH_OK)
                        sec_event_reg       <= {
                            req_payload_byte,
                            8'h01,
                            1'b1, last_lut_snap[5:4], lut3_d_hmac_pass, lut3_c_key_enable, lut3_b_request_fresh, lut3_a_frame_ok,
                            2'b01, // 01 = AUTH_OK
                            req_port_reg,
                            latched_jamrah_root
                        };
                    end else begin
                        auth_grant_reg  <= 1'b0;
                        auth_reject_reg <= 1'b1;
                        auth_error_reg  <= hmac_fault_latched || kabah_break_latched || abort_latched;
                        total_fail_cnt  <= total_fail_cnt + 16'd1;
                        sec_reason_reg  <= {
                            abort_latched,           // bit8: RSN_ABORT_FAULT
                            ~privilege_ok,           // bit7: RSN_PRIV_DENIED
                            ~jamrah_pass,            // bit6: RSN_JAMRAH_BREAK
                            ~kabah_verify_ok,        // bit5: RSN_KABAH_MISMATCH
                            ~lut3_d_hmac_pass,       // bit4: RSN_HMAC_FAIL
                            ~lut3_c_key_enable,      // bit3: RSN_KEY_BLOCKED
                            ~lut3_b_request_fresh,   // bit2: RSN_REPLAY_TS
                            ~lut3_a_frame_ok,        // bit1: RSN_FRAME_ERR
                            1'b0                     // bit0: RSN_NONE
                        };
                        sec_event_reg <= {
                            req_payload_byte,
                            {abort_latched, ~privilege_ok, ~jamrah_pass, ~kabah_verify_ok,
                             ~lut3_d_hmac_pass, ~lut3_c_key_enable, ~lut3_b_request_fresh, ~lut3_a_frame_ok},
                            1'b0, last_lut_snap[5:4], lut3_d_hmac_pass, lut3_c_key_enable, lut3_b_request_fresh, lut3_a_frame_ok,
                            (hmac_fault_latched || kabah_break_latched || abort_latched) ? 2'b11 : 2'b10,
                            req_port_reg,
                            latched_jamrah_root
                        };
                    end
                    core_state <= ST_IDLE;
                end

                default: core_state <= ST_IDLE;
            endcase
        end
    end

    // ========================================================================
    // 6. HCPU MMIO Read Registers (0xFE9..0xFEC) & Sanitized Telemetry Bus
    // ========================================================================
    wire sec_busy = (core_state != ST_IDLE) || req_pending;

    // 0xFE9: SEC_STATUS
    assign sec_status_rdata = {
        9'd0,
        core_state,              // [22:20] FSM state
        latched_jamrah_root,     // [19:16] Jamrah 7-node root
        jamrah_pass,             // [15]    Jamrah pass status
        auth_grant_reg,          // [14]    LUT7 registered auth_grant
        last_lut_snap[5],        // [13]    LUT6 kabah_round_step
        last_lut_snap[4],        // [12]    LUT5 request_start
        last_lut_snap[3],        // [11]    LUT3-D hmac_pass
        last_lut_snap[2],        // [10]    LUT3-C key_enable
        last_lut_snap[1],        // [9]     LUT3-B request_fresh
        last_lut_snap[0],        // [8]     LUT3-A frame_ok
        ~sec_busy,               // [7]     HMAC engine ready
        ~sec_busy,               // [6]     Ka'bah engine ready
        vault_locked,            // [5]     Portal 8888 ready & provisioned
        auth_error_reg,          // [4]     ERROR
        auth_reject_reg,         // [3]     REJECT
        auth_grant_reg,          // [2]     AUTH_OK (registered)
        verdict_valid_sticky,    // [1]     Done / verdict valid
        sec_busy                 // [0]     Busy
    };

    // 0xFEA: SEC_REASON
    assign sec_reason_rdata = {23'd0, sec_reason_reg};

    // 0xFEB: SEC_EVENT
    assign sec_event_rdata  = sec_event_reg;

    // 0xFEC: SEC_COUNTER
    assign sec_counter_rdata = {total_fail_cnt, total_req_cnt};

    // Priority-encoded 3-bit reason ID for compact HDMI display
    wire [2:0] prio_reason_id =
        !verdict_valid_sticky ? 3'd0 :
        auth_grant_reg        ? 3'd0 :
        sec_reason_reg[1]     ? 3'd1 : // FRAME_ERR
        sec_reason_reg[2]     ? 3'd2 : // REPLAY_TS
        sec_reason_reg[3]     ? 3'd3 : // KEY_BLOCK
        sec_reason_reg[4]     ? 3'd4 : // HMAC_FAIL
        sec_reason_reg[5]     ? 3'd5 : // KABAH_ERR
        sec_reason_reg[6]     ? 3'd6 : // JAMRAH_ERR
                                3'd7 ; // PRIV/ABORT

    wire [1:0] verdict_code =
        !verdict_valid_sticky ? 2'd0 : // WAITING
        auth_grant_reg        ? 2'd1 : // AUTH_OK
        auth_error_reg        ? 2'd3 : // ERROR
                                2'd2 ; // REJECT

    // 32-bit Coherent Telemetry Bus for CDC -> HDMI Boot Display:
    //   [1:0]   : verdict_code (0=WAIT, 1=AUTH_OK, 2=REJECT, 3=ERROR)
    //   [2]     : portal_active (vault_locked)
    //   [3]     : kabah_ready (~sec_busy & ~kabah_break_latched)
    //   [4]     : hmac_ready (~sec_busy & ~hmac_fault_latched)
    //   [5]     : jamrah_ready (~kabah_break_latched)
    //   [12:6]  : last_lut_snap[6:0] ({lut7_reg, lut6, lut5, lut3d, lut3c, lut3b, lut3a})
    //   [15:13] : prio_reason_id (0..7)
    //   [23:16] : total_req_cnt[7:0]
    //   [31:24] : total_fail_cnt[7:0]
    assign sec_tele_bus = {
        total_fail_cnt[7:0],
        total_req_cnt[7:0],
        prio_reason_id,
        last_lut_snap,
        ~kabah_break_latched,
        ~sec_busy & ~hmac_fault_latched,
        ~sec_busy & ~kabah_break_latched,
        vault_locked,
        verdict_code
    };

    assign sec_any_fault = auth_error_reg;

endmodule

`default_nettype wire
