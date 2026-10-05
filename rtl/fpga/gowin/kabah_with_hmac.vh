// Read before hijaiyyah_kabah_gowin_top.v, this turns layer 3 on: the wrapper
// then signs each reply with HMAC-SHA256 under its public test key. Only the
// UART slot's own targets read it (KABAH_L3_DEFINE in the Makefile); Ka'bah
// over HDMI and the combined top do not, and build the wrapper as it was.
`define KABAH_WITH_HMAC
