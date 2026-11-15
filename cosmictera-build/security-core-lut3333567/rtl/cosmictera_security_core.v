// ============================================================================
// COSMICTERA SECURITY CORE — Ka'bah Cryptographic Engine + Portal 8888
// Architecture: 7-Function Cascaded LUT Control Plane (3 - 3 - 3 - 3 - 5 - 6 - 7)
// Target FPGA : Gowin GW2AR-LV18QN88C8/I7 (Tang Nano 20K)
// ============================================================================
//
// Security & Architectural Principles:
//   1. Non-destructive wrapper: Integrates existing unmodified RTL modules:
//        - hijaiyyah_portal8888  (Portal 8888 ingress, UTC/PPS time, chain seal)
//        - hijaiyyah_kabah_top   (Ka'bah 1600-bit sponge, 7-node Jamrah, Ramal)
//        - hijaiyyah_hmac        (Layer-3 HMAC-SHA256 verification engine)
//        - hijaiyyah_jamrah_gate (7-node combinatorial residue & alphabet gate)
//   2. 7-Block LUT Hierarchy (3 - 3 - 3 - 3 - 5 - 6 - 7):
//        - LUT3-A (3-input): Frame sync, IP version, and length/parse validation
//        - LUT3-B (3-input): Timestamp window, anti-replay nonce, and port sequence
//        - LUT3-C (3-input): Protected internal key enable (never exposes keys)
//        - LUT3-D (3-input): HMAC completion, 256-bit tag match, and no fault
//        - LUT5   (5-input): Portal 8888 request dispatch to crypto engines
//        - LUT6   (6-input): Ka'bah 1600-bit sponge & round stepping control
//        - LUT7   (7-input): Final security authorization decision (AUTH_OK)
//   3. Strict Key Isolation:
//        - Provisioned 512-bit keys live inside an internal write-only vault.
//        - No output port, debug signal, or MMIO register can ever read key bits.
//        - LUT3-C (`key_enable`) strictly gates internal key delivery to HMAC.
// ============================================================================

`default_nettype none

// ----------------------------------------------------------------------------
// 1. LUT3-A (3 inputs): Frame Validation
// ----------------------------------------------------------------------------
(* keep_hierarchy = 1 *)
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
(* keep_hierarchy = 1 *)
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
(* keep_hierarchy = 1 *)
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
(* keep_hierarchy = 1 *)
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
(* keep_hierarchy = 1 *)
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
(* keep_hierarchy = 1 *)
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
(* keep_hierarchy = 1 *)
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
// Pure 7-LUT Control Plane Module (3 - 3 - 3 - 3 - 5 - 6 - 7)
// Allows standalone synthesis inspection of the exact 18-LUT4 equivalent plane
// as well as hierarchical instantiation inside cosmictera_security_core.
// ----------------------------------------------------------------------------
(* keep_hierarchy = 1 *)
module cosmictera_security_lut_plane (
    // LUT3-A inputs
    input  wire frame_sync,
    input  wire version_ok,
    input  wire length_ok,
    // LUT3-B inputs
    input  wire timestamp_ok,
    input  wire nonce_fresh,
    input  wire sequence_ok,
    // LUT3-C inputs
    input  wire auth_job_active,
    input  wire key_slot_valid,
    input  wire secure_mode,
    // LUT3-D inputs
    input  wire hmac_done,
    input  wire digest_equal,
    input  wire hmac_error,
    // LUT5 additional inputs
    input  wire request_available,
    input  wire hmac_ready,
    input  wire kabah_ready,
    // LUT6 inputs
    input  wire kabah_busy,
    input  wire state_valid,
    input  wire round_valid,
    input  wire step_enable,
    input  wire abort,
    input  wire reset_n,
    // LUT7 additional inputs
    input  wire kabah_verify_ok,
    input  wire jamrah_pass,
    input  wire privilege_ok,
    input  wire security_state_ok,
    // 7 LUT outputs
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
// Top-Level Integrated Security Core:
// Portal 8888 + Ka'bah Engine + HMAC-SHA256 + Jamrah 7-Node Gate + 7-LUT Plane
// ----------------------------------------------------------------------------
module cosmictera_security_core #(
    parameter [63:0] DEV_ID = 64'h48494A41_59594148, // "HIJAIYYAH"
    parameter integer TPS   = 27_000_000,
    parameter integer ANCHOR_PERIOD = 4
) (
    input  wire          clk,
    input  wire          rst_n,

    // --- Portal 8888 Time & Key Provisioning Interface ---
    input  wire          pps,
    input  wire          provision_time,
    input  wire [31:0]   provision_utc_sec,
    input  wire [31:0]   provision_uncert_ns,
    input  wire          prov_valid,
    input  wire [2:0]    prov_slot,
    input  wire [7:0]    prov_byte,
    input  wire          prov_lock,

    // --- Portal 8888 PHY Ingress Interface ---
    input  wire [1:0]    phy_port,
    input  wire          phy_byte_valid,
    input  wire [7:0]    phy_byte,
    input  wire          phy_last,

    // --- Security Policy & Verification Parameters ---
    input  wire          secure_mode_en,
    input  wire          privilege_req_ok,
    input  wire          security_abort,
    input  wire          kabah_gate_mode,
    input  wire [2:0]    kabah_phase,
    input  wire [31:0]   min_utc_sec,
    input  wire [31:0]   max_uncert_ns,
    input  wire          use_external_expected_tag,
    input  wire [255:0]  external_expected_tag,

    // --- Hijaiyyah Letter Payload Stream for Ka'bah & Jamrah Verification ---
    input  wire          payload_byte_valid,
    input  wire [7:0]    payload_byte_in,

    // --- Direct LUT Truth-Table Verification Mode (for exhaustive unit tests) ---
    input  wire          direct_lut_test_mode,
    input  wire [21:0]   direct_lut_test_vec,

    // --- Exposed 7-LUT Signals (Read-only status telemetry; NO key bits) ---
    output wire          lut3_a_frame_ok,
    output wire          lut3_b_request_fresh,
    output wire          lut3_c_key_enable,
    output wire          lut3_d_hmac_pass,
    output wire          lut5_request_start,
    output wire          lut6_kabah_round_step,
    output wire          lut7_auth_grant,

    // --- Final Security Verdict Outputs ---
    output reg           verdict_valid,
    output reg           auth_ok,      // Authorized (AUTH_OK)
    output reg           auth_reject,  // Denied (REJECT)
    output reg           auth_error,   // Hardware/Protocol Fault (ERROR)

    // --- Portal 8888 & Ka'bah Status Telemetry ---
    output wire          portal_provisioned,
    output wire          portal_provision_locked,
    output wire [4:0]    portal_provision_written,
    output wire          portal_busy,
    output wire          portal_ready,
    output wire          portal_record_done,
    output wire          portal_record_dropped,
    output wire          portal_overflow_drop,
    output wire [999:0]  portal_sealed_body,
    output wire [255:0]  portal_sealed_tag,
    output wire [31:0]   portal_anc_round,
    output wire [255:0]  portal_anc_root,
    output wire          kabah_break_valid,
    output wire [31:0]   kabah_break_at,
    output wire [15:0]   kabah_break_count,
    output wire [3:0]    jamrah_root_out,
    output wire [2:0]    security_fsm_state
);

    // ========================================================================
    // A. Internal Write-Only Protected Key Vault (NEVER readable externally)
    // ========================================================================
    reg [511:0] protected_key_vault [0:4];
    reg [5:0]   vault_byte_idx;
    reg [2:0]   vault_last_slot;
    integer     k_idx;

    wire vault_key_we = prov_valid && !portal_provision_locked && !prov_lock &&
                        (prov_slot < 3'd5) && !portal_provision_written[prov_slot];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k_idx = 0; k_idx < 5; k_idx = k_idx + 1)
                protected_key_vault[k_idx] <= 512'd0;
            vault_byte_idx  <= 6'd0;
            vault_last_slot <= 3'd7;
        end else if (vault_key_we) begin
            protected_key_vault[prov_slot] <= {protected_key_vault[prov_slot][503:0], prov_byte};
            vault_byte_idx  <= vault_byte_idx + 6'd1;
            vault_last_slot <= prov_slot;
        end
    end

    // ========================================================================
    // B. Portal 8888 Instantiation (Unmodified hijaiyyah_portal8888)
    // ========================================================================
    wire [255:0] portal_tagA, portal_tagB, portal_tagC, portal_tagD;

    hijaiyyah_portal8888 u_portal8888 (
        .clk                 (clk),
        .rst_n               (rst_n),
        .pps                 (pps),
        .provision_time      (provision_time),
        .provision_utc_sec   (provision_utc_sec),
        .provision_uncert_ns (provision_uncert_ns),
        .phy_port            (phy_port),
        .phy_byte_valid      (phy_byte_valid),
        .phy_byte            (phy_byte),
        .phy_last            (phy_last),
        .prov_valid          (prov_valid),
        .prov_slot           (prov_slot),
        .prov_byte           (prov_byte),
        .prov_lock           (prov_lock),
        .provisioned         (portal_provisioned),
        .provision_locked    (portal_provision_locked),
        .provision_written   (portal_provision_written),
        .busy                (portal_busy),
        .ready               (portal_ready),
        .record_done         (portal_record_done),
        .record_dropped      (portal_record_dropped),
        .overflow_drop       (portal_overflow_drop),
        .sealed_body         (portal_sealed_body),
        .sealed_tag          (portal_sealed_tag),
        .anc_round           (portal_anc_round),
        .anc_root            (portal_anc_root),
        .tagA                (portal_tagA),
        .tagB                (portal_tagB),
        .tagC                (portal_tagC),
        .tagD                (portal_tagD)
    );

    // ========================================================================
    // C. Unpack Sealed Record Fields from Portal 8888 (125 Bytes / 1000 Bits)
    // ========================================================================
    reg  [999:0] latched_body;
    reg  [255:0] latched_portal_tag;
    reg          record_latched;
    reg          overflow_fault_latched;
    reg          dropped_fault_latched;

    wire [1:0]   rec_port       = latched_body[929:928];
    wire [31:0]  rec_tsec       = latched_body[927:896];
    wire [31:0]  rec_uncert     = latched_body[855:824];
    wire [63:0]  rec_ctr        = latched_body[823:760];
    wire [1:0]   rec_status     = latched_body[753:752];
    wire [3:0]   rec_ver        = latched_body[747:744];
    wire [15:0]  rec_dport      = latched_body[599:584];
    wire [255:0] rec_sha_digest = latched_body[527:272];
    wire [15:0]  rec_idx        = latched_body[271:256];

    // Anti-replay state per Security Core
    reg  [63:0]  last_accepted_ctr;
    reg  [15:0]  expected_port_idx [0:3];

    // ========================================================================
    // D. Standalone Jamrah 7-Node Gate Monitor & Coordinator FSM Declarations
    // ========================================================================
    localparam [2:0]
        ST_IDLE     = 3'd0,
        ST_EVAL_PRE = 3'd1,
        ST_DISPATCH = 3'd2,
        ST_AUTH_RUN = 3'd3,
        ST_DECIDE   = 3'd4;

    reg [2:0] core_state;
    assign security_fsm_state = core_state;

    wire         jamrah_pulse;
    wire [3:0]   jamrah_root;
    wire [1:0]   jamrah_n0, jamrah_n1, jamrah_n2, jamrah_n3;
    wire [2:0]   jamrah_n4, jamrah_n5;
    wire [3:0]   jamrah_n6;

    hijaiyyah_jamrah_gate u_jamrah_monitor (
        .clk      (clk),
        .rst_n    (rst_n),
        .valid_in (payload_byte_valid),
        .byte_in  (payload_byte_in),
        .pulse    (jamrah_pulse),
        .root     (jamrah_root),
        .node0    (jamrah_n0),
        .node1    (jamrah_n1),
        .node2    (jamrah_n2),
        .node3    (jamrah_n3),
        .node4    (jamrah_n4),
        .node5    (jamrah_n5),
        .node6    (jamrah_n6)
    );
    assign jamrah_root_out = jamrah_root;

    reg          jamrah_seen_valid;
    reg          jamrah_violation;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            jamrah_seen_valid <= 1'b0;
            jamrah_violation  <= 1'b0;
        end else if (core_state == ST_DECIDE) begin
            jamrah_violation  <= 1'b0;
        end else if (payload_byte_valid) begin
            if ((payload_byte_in >= 8'd1) && (payload_byte_in <= 8'd28)) begin
                jamrah_seen_valid <= 1'b1;
            end else if (kabah_gate_mode) begin
                jamrah_violation  <= 1'b1;
            end
        end
    end

    // ========================================================================
    // E. Layer-3 HMAC + Ka'bah Cryptographic Engine Instantiation
    // ========================================================================

    // Layer-3 Independent HMAC Verification Engine (hijaiyyah_hmac)
    reg          verify_hmac_start;
    reg          verify_hmac_byte_valid;
    reg  [7:0]   verify_hmac_byte_in;
    reg          verify_hmac_finish;
    wire         verify_hmac_byte_ready;
    wire         verify_hmac_idle;
    wire         verify_hmac_done;
    wire [255:0] verify_hmac_mac;

    // Internal key bus strictly gated by LUT3-C (`lut3_c_key_enable`)
    wire [2:0]   active_key_slot      = {1'b0, rec_port};
    wire [511:0] gated_hmac_key       = lut3_c_key_enable ? protected_key_vault[active_key_slot] : 512'd0;
    wire         crypto_cleanup_pulse = verdict_valid;
    wire         crypto_sub_rst_n     = rst_n & ~crypto_cleanup_pulse;

    hijaiyyah_hmac u_verify_hmac (
        .clk        (clk),
        .rst_n      (crypto_sub_rst_n),
        .start      (verify_hmac_start),
        .key        (gated_hmac_key),
        .byte_valid (verify_hmac_byte_valid),
        .byte_in    (verify_hmac_byte_in),
        .byte_ready (verify_hmac_byte_ready),
        .finish     (verify_hmac_finish),
        .idle       (verify_hmac_idle),
        .done       (verify_hmac_done),
        .mac        (verify_hmac_mac)
    );

    // Ka'bah Cryptographic Engine (hijaiyyah_kabah_top)
    reg           kabah_load;
    wire          kabah_bit_valid;
    wire          kabah_bit_in;
    wire          kabah_gate_pulse;
    wire [3:0]    kabah_gate_root;
    wire          kabah_class_valid;
    wire [1:0]    kabah_class_out;
    wire [7:0]    kabah_xor_key_out;
    wire          kabah_bits_ready;
    wire          kabah_absorbing;
    wire          kabah_permuting;
    wire [1599:0] kabah_out_state;

    // Bit serialiser feeding Ka'bah during ST_AUTH_RUN gated by LUT6 (`lut6_kabah_round_step`)
    reg  [7:0]    kabah_cur_byte;
    reg  [2:0]    kabah_bit_idx;
    reg  [5:0]    kabah_step_cnt;
    reg           kabah_state_seeded;
    reg           kabah_step_en;
    reg           kabah_done_latched;

    // Map digest byte into valid Hijaiyyah 1..28 alphabet (or inject raw payload byte if gate_mode violation test)
    wire [7:0]    digest_letter_byte   = ((rec_sha_digest[255 - (kabah_step_cnt[4:0]*8) -: 8] % 8'd28) + 8'd1);
    wire [7:0]    effective_kabah_byte = (kabah_gate_mode && jamrah_violation) ? 8'd0 : digest_letter_byte;

    // Note: hijaiyyah_deserialiser shifts {bit_in, shifter[7:1]} (LSB-first)
    assign kabah_bit_valid = lut6_kabah_round_step && kabah_bits_ready;
    assign kabah_bit_in    = effective_kabah_byte[kabah_bit_idx];

    hijaiyyah_kabah_top #(
        .SLICE_BYTES (25)
    ) u_kabah_top (
        .clk         (clk),
        .rst_n       (crypto_sub_rst_n),
        .standby     (1'b0),
        .load        (kabah_load),
        .gate_mode   (kabah_gate_mode),
        .phase       (kabah_phase),
        .bit_valid   (kabah_bit_valid),
        .bit_in      (kabah_bit_in),
        .gate_pulse  (kabah_gate_pulse),
        .gate_root   (kabah_gate_root),
        .break_valid (kabah_break_valid),
        .break_at    (kabah_break_at),
        .break_count (kabah_break_count),
        .class_valid (kabah_class_valid),
        .class_out   (kabah_class_out),
        .xor_key_out (kabah_xor_key_out),
        .bits_ready  (kabah_bits_ready),
        .absorbing   (kabah_absorbing),
        .permuting   (kabah_permuting),
        .out_state   (kabah_out_state)
    );

    // ========================================================================
    // F. Signal Extraction for the 7 LUT Functions
    // ========================================================================
    reg  [6:0]   hmac_byte_idx;
    reg          verify_hmac_done_latched;
    reg  [255:0] verify_hmac_mac_latched;
    reg          hmac_fault_latched;
    reg          kabah_break_latched;

    // 1. LUT3-A candidate signals
    wire live_frame_sync  = record_latched & ~overflow_fault_latched & ~dropped_fault_latched;
    wire live_version_ok  = (rec_ver == 4'd4) || (rec_ver == 4'd6);
    wire live_length_ok   = (rec_status == 2'b00);

    // 2. LUT3-B candidate signals
    wire live_timestamp_ok = (rec_tsec >= min_utc_sec) && (rec_uncert <= max_uncert_ns);
    wire live_nonce_fresh  = (rec_ctr > last_accepted_ctr);
    wire live_sequence_ok  = (rec_idx == expected_port_idx[rec_port]);

    // 3. LUT3-C candidate signals
    wire live_auth_job_active = (core_state == ST_DISPATCH) || (core_state == ST_AUTH_RUN) || (core_state == ST_DECIDE);
    wire live_key_slot_valid  = portal_provisioned && portal_provision_written[active_key_slot];
    wire live_secure_mode     = portal_provision_locked && secure_mode_en && ~security_abort;

    // 4. LUT3-D candidate signals
    wire [255:0] expected_tag_mux = use_external_expected_tag ? external_expected_tag : latched_portal_tag;
    wire live_hmac_done    = verify_hmac_done_latched;
    wire live_digest_equal = (verify_hmac_mac_latched == expected_tag_mux);
    wire live_hmac_error   = hmac_fault_latched;

    // 5. LUT5 additional candidate signals
    wire live_request_available = record_latched && (core_state == ST_EVAL_PRE);
    wire live_hmac_ready        = verify_hmac_idle;
    wire live_kabah_ready       = ~kabah_permuting && kabah_bits_ready;

    // 6. LUT6 candidate signals
    wire live_kabah_busy  = (core_state == ST_AUTH_RUN) && ~kabah_done_latched;
    wire live_state_valid = kabah_state_seeded;
    wire live_round_valid = (kabah_step_cnt < 6'd25);
    wire live_step_enable = kabah_step_en;
    wire live_abort       = security_abort || kabah_break_latched;
    wire live_reset_n     = rst_n;

    // 7. LUT7 additional candidate signals
    wire live_kabah_verify_ok   = kabah_done_latched && (|kabah_out_state[255:0]) && ~kabah_break_latched;
    wire live_jamrah_pass       = ~jamrah_violation && ~kabah_break_latched;
    wire live_privilege_ok      = privilege_req_ok && ((rec_dport == 16'd8888) || (rec_dport == 16'd0));
    wire live_security_state_ok = lut3_c_key_enable && (core_state == ST_DECIDE) && ~security_abort && ~overflow_fault_latched && ~dropped_fault_latched;

    // Multiplex between live hardware operation and direct truth-table verification mode
    wire mux_frame_sync        = direct_lut_test_mode ? direct_lut_test_vec[0]  : live_frame_sync;
    wire mux_version_ok        = direct_lut_test_mode ? direct_lut_test_vec[1]  : live_version_ok;
    wire mux_length_ok         = direct_lut_test_mode ? direct_lut_test_vec[2]  : live_length_ok;

    wire mux_timestamp_ok      = direct_lut_test_mode ? direct_lut_test_vec[3]  : live_timestamp_ok;
    wire mux_nonce_fresh       = direct_lut_test_mode ? direct_lut_test_vec[4]  : live_nonce_fresh;
    wire mux_sequence_ok       = direct_lut_test_mode ? direct_lut_test_vec[5]  : live_sequence_ok;

    wire mux_auth_job_active   = direct_lut_test_mode ? direct_lut_test_vec[6]  : live_auth_job_active;
    wire mux_key_slot_valid    = direct_lut_test_mode ? direct_lut_test_vec[7]  : live_key_slot_valid;
    wire mux_secure_mode       = direct_lut_test_mode ? direct_lut_test_vec[8]  : live_secure_mode;

    wire mux_hmac_done         = direct_lut_test_mode ? direct_lut_test_vec[9]  : live_hmac_done;
    wire mux_digest_equal      = direct_lut_test_mode ? direct_lut_test_vec[10] : live_digest_equal;
    wire mux_hmac_error        = direct_lut_test_mode ? direct_lut_test_vec[11] : live_hmac_error;

    wire mux_request_available = direct_lut_test_mode ? direct_lut_test_vec[12] : live_request_available;
    wire mux_hmac_ready        = direct_lut_test_mode ? direct_lut_test_vec[13] : live_hmac_ready;
    wire mux_kabah_ready       = direct_lut_test_mode ? direct_lut_test_vec[14] : live_kabah_ready;

    wire mux_kabah_busy        = direct_lut_test_mode ? direct_lut_test_vec[15] : live_kabah_busy;
    wire mux_state_valid       = direct_lut_test_mode ? direct_lut_test_vec[16] : live_state_valid;
    wire mux_round_valid       = direct_lut_test_mode ? direct_lut_test_vec[17] : live_round_valid;
    wire mux_step_enable       = direct_lut_test_mode ? direct_lut_test_vec[18] : live_step_enable;
    wire mux_abort             = direct_lut_test_mode ? direct_lut_test_vec[19] : live_abort;
    wire mux_reset_n           = direct_lut_test_mode ? direct_lut_test_vec[20] : live_reset_n;

    wire mux_kabah_verify_ok   = direct_lut_test_mode ? direct_lut_test_vec[21] : live_kabah_verify_ok;
    wire mux_jamrah_pass       = direct_lut_test_mode ? direct_lut_test_vec[12] : live_jamrah_pass;
    wire mux_privilege_ok      = direct_lut_test_mode ? direct_lut_test_vec[13] : live_privilege_ok;
    wire mux_security_state_ok = direct_lut_test_mode ? direct_lut_test_vec[14] : live_security_state_ok;

    // Instantiate the 7-LUT Security Control Plane (3 - 3 - 3 - 3 - 5 - 6 - 7)
    cosmictera_security_lut_plane u_lut_plane (
        .frame_sync        (mux_frame_sync),
        .version_ok        (mux_version_ok),
        .length_ok         (mux_length_ok),
        .timestamp_ok      (mux_timestamp_ok),
        .nonce_fresh       (mux_nonce_fresh),
        .sequence_ok       (mux_sequence_ok),
        .auth_job_active   (mux_auth_job_active),
        .key_slot_valid    (mux_key_slot_valid),
        .secure_mode       (mux_secure_mode),
        .hmac_done         (mux_hmac_done),
        .digest_equal      (mux_digest_equal),
        .hmac_error        (mux_hmac_error),
        .request_available (mux_request_available),
        .hmac_ready        (mux_hmac_ready),
        .kabah_ready       (mux_kabah_ready),
        .kabah_busy        (mux_kabah_busy),
        .state_valid       (mux_state_valid),
        .round_valid       (mux_round_valid),
        .step_enable       (mux_step_enable),
        .abort             (mux_abort),
        .reset_n           (mux_reset_n),
        .kabah_verify_ok   (mux_kabah_verify_ok),
        .jamrah_pass       (mux_jamrah_pass),
        .privilege_ok      (mux_privilege_ok),
        .security_state_ok (mux_security_state_ok),
        .frame_ok          (lut3_a_frame_ok),
        .request_fresh     (lut3_b_request_fresh),
        .key_enable        (lut3_c_key_enable),
        .hmac_pass         (lut3_d_hmac_pass),
        .request_start     (lut5_request_start),
        .kabah_round_step  (lut6_kabah_round_step),
        .auth_grant        (lut7_auth_grant)
    );

    // ========================================================================
    // G. Sequential Control State Machine (Portal -> HMAC & Ka'bah -> Decision)
    // ========================================================================
    wire [7:0] body_byte_at_idx = latched_body[999 - (hmac_byte_idx * 8) -: 8];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            core_state               <= ST_IDLE;
            latched_body             <= 1000'd0;
            latched_portal_tag       <= 256'd0;
            record_latched           <= 1'b0;
            overflow_fault_latched   <= 1'b0;
            dropped_fault_latched    <= 1'b0;
            last_accepted_ctr        <= 64'd0;
            expected_port_idx[0]     <= 16'd0;
            expected_port_idx[1]     <= 16'd0;
            expected_port_idx[2]     <= 16'd0;
            expected_port_idx[3]     <= 16'd0;
            verify_hmac_start        <= 1'b0;
            verify_hmac_byte_valid   <= 1'b0;
            verify_hmac_byte_in      <= 8'd0;
            verify_hmac_finish       <= 1'b0;
            hmac_byte_idx            <= 7'd0;
            verify_hmac_done_latched <= 1'b0;
            verify_hmac_mac_latched  <= 256'd0;
            hmac_fault_latched       <= 1'b0;
            kabah_load               <= 1'b0;
            kabah_cur_byte           <= 8'd1;
            kabah_bit_idx            <= 3'd0;
            kabah_step_cnt           <= 6'd0;
            kabah_state_seeded       <= 1'b0;
            kabah_step_en            <= 1'b0;
            kabah_done_latched       <= 1'b0;
            kabah_break_latched      <= 1'b0;
            verdict_valid            <= 1'b0;
            auth_ok                  <= 1'b0;
            auth_reject              <= 1'b0;
            auth_error               <= 1'b0;
        end else begin
            verify_hmac_start      <= 1'b0;
            verify_hmac_byte_valid <= 1'b0;
            verify_hmac_finish     <= 1'b0;
            kabah_load             <= 1'b0;
            verdict_valid          <= 1'b0;

            if (portal_overflow_drop)
                overflow_fault_latched <= 1'b1;
            if (portal_record_dropped)
                dropped_fault_latched <= 1'b1;
            if (kabah_break_valid)
                kabah_break_latched <= 1'b1;

            case (core_state)
                ST_IDLE: begin
                    if (portal_overflow_drop || portal_record_dropped) begin
                        verdict_valid          <= 1'b1;
                        auth_ok                <= 1'b0;
                        auth_error             <= 1'b1;
                        auth_reject            <= 1'b1;
                        overflow_fault_latched <= 1'b0;
                        dropped_fault_latched  <= 1'b0;
                    end else if (portal_record_done) begin
                        latched_body             <= portal_sealed_body;
                        latched_portal_tag       <= portal_sealed_tag;
                        record_latched           <= 1'b1;
                        verify_hmac_done_latched <= 1'b0;
                        hmac_fault_latched       <= 1'b0;
                        kabah_done_latched       <= 1'b0;
                        kabah_break_latched      <= 1'b0;
                        auth_ok                  <= 1'b0;
                        auth_reject              <= 1'b0;
                        auth_error               <= 1'b0;
                        core_state               <= ST_EVAL_PRE;
                    end
                end

                ST_EVAL_PRE: begin
                    // Evaluate LUT3-A (frame_ok), LUT3-B (request_fresh), and LUT5 (request_start)
                    if (!lut3_a_frame_ok || !lut3_b_request_fresh) begin
                        // Early pre-filter rejection before waking crypto engines
                        core_state <= ST_DECIDE;
                    end else if (lut5_request_start) begin
                        core_state <= ST_DISPATCH;
                    end
                end

                ST_DISPATCH: begin
                    // LUT3-C (`lut3_c_key_enable`) is now active if key_slot_valid & secure_mode
                    if (!lut3_c_key_enable) begin
                        hmac_fault_latched <= 1'b1;
                    end
                    verify_hmac_start  <= 1'b1;
                    hmac_byte_idx      <= 7'd0;
                    kabah_load         <= 1'b1;
                    kabah_bit_idx      <= 3'd0;
                    kabah_step_cnt     <= 6'd0;
                    kabah_state_seeded <= 1'b1;
                    kabah_step_en      <= 1'b1;
                    core_state         <= ST_AUTH_RUN;
                end

                ST_AUTH_RUN: begin
                    if (security_abort || kabah_break_latched) begin
                        hmac_fault_latched <= 1'b1;
                        core_state         <= ST_DECIDE;
                    end else begin
                        // 1. Feed 125-byte sealed_body to Layer-3 HMAC verifier
                        if (!verify_hmac_done_latched) begin
                            if (verify_hmac_done) begin
                                verify_hmac_done_latched <= 1'b1;
                                verify_hmac_mac_latched  <= verify_hmac_mac;
                            end else if (verify_hmac_byte_ready && !verify_hmac_byte_valid && !verify_hmac_finish) begin
                                if (hmac_byte_idx < 7'd125) begin
                                    verify_hmac_byte_in    <= body_byte_at_idx;
                                    verify_hmac_byte_valid <= 1'b1;
                                    hmac_byte_idx          <= hmac_byte_idx + 7'd1;
                                end else begin
                                    verify_hmac_finish     <= 1'b1;
                                end
                            end
                        end

                        // 2. Step Ka'bah 1600-bit sponge via LUT6 (`lut6_kabah_round_step`)
                        if (!kabah_done_latched) begin
                            if (kabah_step_cnt == 6'd25) begin
                                // Wait 4 pipeline cycles for 25th byte to enter sponge & trigger permutation,
                                // then wait for 24-round permutation (!kabah_permuting) to complete
                                if (kabah_bit_idx < 3'd4) begin
                                    kabah_bit_idx <= kabah_bit_idx + 3'd1;
                                end else if (!kabah_permuting) begin
                                    kabah_done_latched <= 1'b1;
                                    kabah_step_en      <= 1'b0;
                                end
                            end else if (kabah_bit_valid) begin
                                if (kabah_bit_idx == 3'd7) begin
                                    kabah_bit_idx  <= 3'd0;
                                    kabah_step_cnt <= kabah_step_cnt + 6'd1;
                                end else begin
                                    kabah_bit_idx  <= kabah_bit_idx + 3'd1;
                                end
                            end
                        end

                        // Transition to ST_DECIDE when both HMAC and Ka'bah complete
                        if (verify_hmac_done_latched && kabah_done_latched) begin
                            core_state <= ST_DECIDE;
                        end
                    end
                end

                ST_DECIDE: begin
                    // LUT7 (`lut7_auth_grant`) evaluates all 7 security conditions
                    verdict_valid               <= 1'b1;
                    record_latched              <= 1'b0;
                    expected_port_idx[rec_port] <= rec_idx + 16'd1;
                    if (lut7_auth_grant) begin
                        auth_ok           <= 1'b1;
                        auth_reject       <= 1'b0;
                        auth_error        <= 1'b0;
                        last_accepted_ctr <= rec_ctr;
                    end else begin
                        auth_ok     <= 1'b0;
                        auth_reject <= 1'b1;
                        auth_error  <= overflow_fault_latched ||
                                       dropped_fault_latched  ||
                                       hmac_fault_latched     ||
                                       kabah_break_latched    ||
                                       security_abort;
                    end
                    overflow_fault_latched <= 1'b0;
                    dropped_fault_latched  <= 1'b0;
                    core_state             <= ST_IDLE;
                end

                default: core_state <= ST_IDLE;
            endcase
        end
    end

endmodule
`default_nettype wire
