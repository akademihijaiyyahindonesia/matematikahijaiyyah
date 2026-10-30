"""Phase 3.3 — Native `.hcell` Parser and `.hc` Compatibility Bridge into Shared Cell IR.

Implements Owner Engineering Decision 1, Priority 2 Backend Correctness, and
Wave 2 System-Programming Operators:
- Parses native `.hcell` programs (Option 2: Hijaiyyah letters + approved
  mathematical & system symbols, zero Latin keywords) into `CellIRGraph`,
  including comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`, including
  18-component `HYBIT_EQ`), conditional branches (`?`), bounded loops (`↻`),
  subroutines (`ƒ` / `⇐`), dynamic HAR lookup (`§(idx)`), official HOS
  syscalls (`⏣(sys, arg [, hybit])`), and HFS hybit reads (`⛁(file_id)`).
- Bridges `.hc` (HC v1.0) programs into the exact same `CellIRGraph`.
"""

from __future__ import annotations

from typing import Any

from hijaiyyah.cells.dataset_engine import MASTER_TABLE_ENGINE
from hijaiyyah.cells.ir import (
    CellBasicBlock,
    CellIRGraph,
    CellIRNode,
    CellOp,
    CellSubroutineDef,
    CellValueType,
    SourceSpan,
)
from hijaiyyah.cells.lexer import (
    HCellToken,
    HCellTokenType,
    tokenize_hcell,
)
from hijaiyyah.cells.spec import HC_COMPAT_VERSION, HCELL_LANGUAGE_VERSION
from hijaiyyah.core.exceptions import HijaiyyahError
from hijaiyyah.language.ast_nodes import (
    AssignStmt,
    BinaryExpr,
    Block,
    CallExpr,
    ExpressedStmt,
    FnDecl,
    IfExpr,
    IndexExpr,
    LetStmt,
    Literal,
    MethodCall,
    Program,
    ReturnStmt,
    VarRef,
    WhileStmt,
)
from hijaiyyah.language.grammar import SLOT_INDEX
from hijaiyyah.language.lexer import Lexer as HCLexer
from hijaiyyah.language.parser import Parser as HCParser


class HCellParseError(HijaiyyahError):
    """Raised when a native `.hcell` source program has invalid syntax."""

    def __init__(self, message: str, token: HCellToken) -> None:
        self.token = token
        super().__init__(
            f"L{token.line}:{token.col}: {message} "
            f"(got {token.type.name} {token.value!r})"
        )


class HCellParser:
    """Recursive-descent parser for native `.hcell` programs into `CellIRGraph`."""

    def __init__(self, tokens: list[HCellToken]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._graph = CellIRGraph(source_language=HCELL_LANGUAGE_VERSION)
        self._counter = 0
        self._env: dict[str, str] = {}
        self._in_nested_block = False
        self._current_block = "entry"
        self._active_node_sink: list[str] | None = None

    def _new_id(self, prefix: str = "c") -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def _add_node(self, node: CellIRNode) -> str:
        top = self._active_node_sink is None
        cid = self._graph.add_node(node, block_id=self._current_block, top_level=top)
        if self._active_node_sink is not None:
            self._active_node_sink.append(cid)
        return cid

    def _cur(self) -> HCellToken:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._tokens[-1]

    def _peek(self, offset: int = 1) -> HCellToken:
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return self._tokens[-1]

    def _advance(self) -> HCellToken:
        tok = self._cur()
        self._pos += 1
        return tok

    def _expect(self, ttype: HCellTokenType, msg: str) -> HCellToken:
        tok = self._cur()
        if tok.type == ttype:
            return self._advance()
        raise HCellParseError(msg, tok)

    def _skip_separators(self) -> None:
        while self._cur().type in (HCellTokenType.NEWLINE, HCellTokenType.SEMICOLON):
            self._advance()

    def parse(self) -> CellIRGraph:
        self._skip_separators()
        while self._cur().type != HCellTokenType.EOF:
            self._parse_statement()
            self._skip_separators()
        return self._graph

    def _parse_statement(self) -> None:
        tok = self._cur()

        if tok.type == HCellTokenType.FN_HOOK:
            self._parse_fn_decl()
            return

        if tok.type == HCellTokenType.QUESTION:
            self._parse_cond_stmt()
            return

        if tok.type == HCellTokenType.LOOP_CYCLE:
            self._parse_loop_stmt()
            return

        if tok.type == HCellTokenType.GUARD_TURNSTILE:
            self._advance()
            target_id = self._parse_expr()
            cid = self._new_id("grd")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.GUARD_CHECK,
                    source_glyphs=f"⊢ {self._graph.nodes[target_id].source_glyphs}",
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[target_id],
                    output_type=CellValueType.BOOL,
                )
            )
            return

        if tok.type == HCellTokenType.EMIT_ARROW:
            self._advance()
            target_id = self._parse_expr()
            cid = self._new_id("out")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.EMIT_OUTPUT,
                    source_glyphs=f"↦ {self._graph.nodes[target_id].source_glyphs}",
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[target_id],
                    output_type=CellValueType.VOID,
                )
            )
            return

        if tok.type in (HCellTokenType.CELL_ID, HCellTokenType.HIJAIYYAH_LETTER) and (
            self._peek(1).type == HCellTokenType.ASSIGN
        ):
            name_tok = self._advance()
            self._advance()
            val_id = self._parse_expr()
            if self._in_nested_block and name_tok.value in self._env:
                cid = self._new_id("asn")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.VAR_ASSIGN,
                        source_glyphs=(
                            f"{name_tok.value} := {self._graph.nodes[val_id].source_glyphs}"
                        ),
                        span=SourceSpan(name_tok.line, name_tok.col),
                        inputs=[val_id],
                        output_type=self._graph.nodes[val_id].output_type,
                        binding_name=name_tok.value,
                    )
                )
                return
            node = self._graph.nodes[val_id]
            node.binding_name = name_tok.value
            self._graph.bindings[name_tok.value] = val_id
            self._env[name_tok.value] = val_id
            return

        self._parse_expr()

    def _parse_fn_decl(self) -> None:
        fn_tok = self._advance()
        name_tok = self._cur()
        if name_tok.type not in (HCellTokenType.CELL_ID, HCellTokenType.HIJAIYYAH_LETTER):
            raise HCellParseError("Expected Hijaiyyah subroutine name after 'ƒ'", name_tok)
        self._advance()
        self._expect(HCellTokenType.LPAREN, "Expected '(' after subroutine name")
        params: list[str] = []
        if self._cur().type != HCellTokenType.RPAREN:
            p_tok = self._cur()
            if p_tok.type not in (HCellTokenType.CELL_ID, HCellTokenType.HIJAIYYAH_LETTER):
                raise HCellParseError("Expected Hijaiyyah parameter name", p_tok)
            params.append(self._advance().value)
            while self._cur().type == HCellTokenType.COMMA:
                self._advance()
                p_tok = self._cur()
                if p_tok.type not in (HCellTokenType.CELL_ID, HCellTokenType.HIJAIYYAH_LETTER):
                    raise HCellParseError("Expected Hijaiyyah parameter name", p_tok)
                params.append(self._advance().value)
        self._expect(HCellTokenType.RPAREN, "Expected ')' after subroutine parameters")

        saved_env = dict(self._env)
        saved_sink = self._active_node_sink
        saved_block = self._current_block
        fn_block = f"fn_{name_tok.value}"
        self._graph.blocks[fn_block] = CellBasicBlock(block_id=fn_block)
        self._current_block = fn_block
        body_nodes: list[str] = []
        param_nodes: list[str] = []
        self._active_node_sink = body_nodes

        for idx, pname in enumerate(params):
            pid = self._new_id("prm")
            self._add_node(
                CellIRNode(
                    cell_id=pid,
                    op=CellOp.FN_PARAM,
                    source_glyphs=pname,
                    span=SourceSpan(fn_tok.line, fn_tok.col),
                    output_type=CellValueType.SCALAR,
                    binding_name=pname,
                    imm_param=idx,
                )
            )
            param_nodes.append(pid)
            self._env[pname] = pid

        ret_id = ""
        if self._cur().type == HCellTokenType.ASSIGN:
            self._advance()
            ret_id = self._parse_expr()
        elif self._cur().type == HCellTokenType.LBRACE:
            self._advance()
            self._skip_separators()
            while self._cur().type not in (HCellTokenType.RBRACE, HCellTokenType.EOF):
                if self._cur().type == HCellTokenType.RETURN_ARROW:
                    self._advance()
                    ret_id = self._parse_expr()
                else:
                    self._parse_statement()
                self._skip_separators()
            self._expect(HCellTokenType.RBRACE, "Expected '}' closing subroutine body")
        else:
            raise HCellParseError("Expected ':=' or '{' in subroutine definition", self._cur())

        if not ret_id and body_nodes:
            ret_id = body_nodes[-1]
        self._graph.subroutines[name_tok.value] = CellSubroutineDef(
            name=name_tok.value,
            params=params,
            param_node_ids=param_nodes,
            body_node_ids=body_nodes,
            return_node_id=ret_id,
            return_type=self._graph.nodes[ret_id].output_type if ret_id else CellValueType.SCALAR,
        )
        self._env = saved_env
        self._active_node_sink = saved_sink
        self._current_block = saved_block

    def _parse_block_nodes(self, block_label: str) -> list[str]:
        self._expect(HCellTokenType.LBRACE, "Expected '{' starting block")
        saved_sink = self._active_node_sink
        saved_nested = self._in_nested_block
        saved_block = self._current_block
        if block_label not in self._graph.blocks:
            self._graph.blocks[block_label] = CellBasicBlock(block_id=block_label)
        self._graph.blocks[saved_block].successors.append(block_label)
        self._current_block = block_label
        self._in_nested_block = True
        collected: list[str] = []
        self._active_node_sink = collected
        self._skip_separators()
        while self._cur().type not in (HCellTokenType.RBRACE, HCellTokenType.EOF):
            self._parse_statement()
            self._skip_separators()
        self._expect(HCellTokenType.RBRACE, "Expected '}' closing block")
        self._active_node_sink = saved_sink
        self._in_nested_block = saved_nested
        self._current_block = saved_block
        return collected

    def _parse_cond_stmt(self) -> None:
        q_tok = self._advance()
        has_paren = self._cur().type == HCellTokenType.LPAREN
        if has_paren:
            self._advance()
        cond_id = self._parse_expr()
        if has_paren:
            self._expect(HCellTokenType.RPAREN, "Expected ')' after branch condition")
        self._skip_separators()
        cid = self._new_id("if")
        then_nodes = self._parse_block_nodes(f"{cid}_then")
        else_nodes: list[str] = []
        self._skip_separators()
        if self._cur().type == HCellTokenType.COLON:
            self._advance()
            self._skip_separators()
            else_nodes = self._parse_block_nodes(f"{cid}_else")
        self._add_node(
            CellIRNode(
                cell_id=cid,
                op=CellOp.COND_BRANCH,
                source_glyphs=f"? ({self._graph.nodes[cond_id].source_glyphs})",
                span=SourceSpan(q_tok.line, q_tok.col),
                inputs=[cond_id],
                output_type=CellValueType.VOID,
                then_node_ids=then_nodes,
                else_node_ids=else_nodes,
            )
        )

    def _parse_loop_stmt(self) -> None:
        lp_tok = self._advance()
        cid = self._new_id("loop")
        saved_sink = self._active_node_sink
        cond_nodes: list[str] = []
        self._active_node_sink = cond_nodes
        has_paren = self._cur().type == HCellTokenType.LPAREN
        if has_paren:
            self._advance()
        cond_id = self._parse_expr()
        if has_paren:
            self._expect(HCellTokenType.RPAREN, "Expected ')' after loop condition")
        self._active_node_sink = saved_sink
        self._skip_separators()
        body_nodes = self._parse_block_nodes(f"{cid}_body")
        self._add_node(
            CellIRNode(
                cell_id=cid,
                op=CellOp.WHILE_LOOP,
                source_glyphs=f"↻ ({self._graph.nodes[cond_id].source_glyphs})",
                span=SourceSpan(lp_tok.line, lp_tok.col),
                inputs=[cond_id],
                output_type=CellValueType.VOID,
                loop_cond_node_ids=cond_nodes,
                loop_body_node_ids=body_nodes,
            )
        )

    def _parse_expr(self) -> str:
        return self._parse_comparison()

    def _parse_comparison(self) -> str:
        left_id = self._parse_additive()
        cmp_map = {
            HCellTokenType.EQ: (CellOp.CMP_EQ, "=="),
            HCellTokenType.NE: (CellOp.CMP_NE, "!="),
            HCellTokenType.LT: (CellOp.CMP_LT, "<"),
            HCellTokenType.GT: (CellOp.CMP_GT, ">"),
            HCellTokenType.LE: (CellOp.CMP_LE, "<="),
            HCellTokenType.GE: (CellOp.CMP_GE, ">="),
        }
        if self._cur().type in cmp_map:
            op_tok = self._advance()
            right_id = self._parse_additive()
            cell_op, sym = cmp_map[op_tok.type]
            lnode = self._graph.nodes[left_id]
            rnode = self._graph.nodes[right_id]
            if (
                cell_op == CellOp.CMP_EQ
                and lnode.output_type == CellValueType.HYBIT
                and rnode.output_type == CellValueType.HYBIT
            ):
                cell_op = CellOp.HYBIT_EQ
            cid = self._new_id("cmp")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=cell_op,
                    source_glyphs=f"{lnode.source_glyphs} {sym} {rnode.source_glyphs}",
                    span=SourceSpan(op_tok.line, op_tok.col),
                    inputs=[left_id, right_id],
                    output_type=CellValueType.SCALAR,
                )
            )
            return cid
        return left_id

    def _parse_additive(self) -> str:
        left_id = self._parse_multiplicative()
        while self._cur().type in (HCellTokenType.PLUS, HCellTokenType.MINUS):
            op_tok = self._advance()
            right_id = self._parse_multiplicative()
            left_node = self._graph.nodes[left_id]
            right_node = self._graph.nodes[right_id]

            if op_tok.type == HCellTokenType.PLUS:
                is_scalar = (
                    left_node.output_type == CellValueType.SCALAR
                    and right_node.output_type == CellValueType.SCALAR
                )
                cell_op = CellOp.SCALAR_ADD if is_scalar else CellOp.HYBIT_ADD
                out_type = CellValueType.SCALAR if is_scalar else CellValueType.HYBIT
                seq: tuple[str, ...] = ()
                if not is_scalar and left_node.letter_sequence and right_node.letter_sequence:
                    seq = (*left_node.letter_sequence, *right_node.letter_sequence)
                cid = self._new_id("add")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=cell_op,
                        source_glyphs=f"{left_node.source_glyphs} + {right_node.source_glyphs}",
                        span=SourceSpan(op_tok.line, op_tok.col),
                        inputs=[left_id, right_id],
                        output_type=out_type,
                        letter_sequence=seq,
                    )
                )
                left_id = cid
            else:
                is_scalar = (
                    left_node.output_type == CellValueType.SCALAR
                    and right_node.output_type == CellValueType.SCALAR
                )
                cell_op = CellOp.SCALAR_SUB if is_scalar else CellOp.HYBIT_DELTA
                out_type = CellValueType.SCALAR if is_scalar else CellValueType.DELTA14
                cid = self._new_id("sub")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=cell_op,
                        source_glyphs=f"{left_node.source_glyphs} - {right_node.source_glyphs}",
                        span=SourceSpan(op_tok.line, op_tok.col),
                        inputs=[left_id, right_id],
                        output_type=out_type,
                    )
                )
                left_id = cid
        return left_id

    def _parse_multiplicative(self) -> str:
        left_id = self._parse_postfix()
        while self._cur().type == HCellTokenType.STAR:
            op_tok = self._advance()
            right_id = self._parse_postfix()
            left_node = self._graph.nodes[left_id]
            right_node = self._graph.nodes[right_id]
            cid = self._new_id("mul")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.SCALAR_MUL,
                    source_glyphs=f"{left_node.source_glyphs} * {right_node.source_glyphs}",
                    span=SourceSpan(op_tok.line, op_tok.col),
                    inputs=[left_id, right_id],
                    output_type=CellValueType.SCALAR,
                )
            )
            left_id = cid
        return left_id

    def _parse_postfix(self) -> str:
        base_id = self._parse_primary()
        while self._cur().type == HCellTokenType.LBRACKET:
            brk_tok = self._advance()
            idx_tok = self._expect(
                HCellTokenType.INTEGER, "Expected integer component index 0..17 inside [...]"
            )
            self._expect(HCellTokenType.RBRACKET, "Expected ']' after component index")
            idx_val = int(idx_tok.value)
            base_node = self._graph.nodes[base_id]
            cid = self._new_id("cget")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.PROJ_COMPONENT,
                    source_glyphs=f"{base_node.source_glyphs}[{idx_val}]",
                    span=SourceSpan(brk_tok.line, brk_tok.col),
                    inputs=[base_id],
                    output_type=CellValueType.SCALAR,
                    imm_param=idx_val,
                )
            )
            base_id = cid
        return base_id

    def _parse_primary(self) -> str:
        tok = self._cur()

        if tok.type == HCellTokenType.HIJAIYYAH_LETTER:
            self._advance()
            if self._cur().type == HCellTokenType.LPAREN and tok.value in self._graph.subroutines:
                return self._parse_fn_call(tok)
            if tok.value in self._env:
                return self._env[tok.value]
            rec = MASTER_TABLE_ENGINE.get_by_char(tok.value)
            if rec is None:
                raise HCellParseError(f"Unknown Hijaiyyah letter {tok.value!r}", tok)
            cid = self._new_id("ltr")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.LETTER_CONST,
                    source_glyphs=rec.char,
                    span=SourceSpan(tok.line, tok.col),
                    output_type=CellValueType.HYBIT,
                    master_table_id=rec.har_ref,
                    imm_param=rec.index,
                    letter_sequence=(rec.char,),
                )
            )
            return cid

        if tok.type == HCellTokenType.WORD_LITERAL:
            self._advance()
            letters = tuple(tok.value.split())
            cid = self._new_id("wrd")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.WORD_ACCUM,
                    source_glyphs=f"⟪{tok.value}⟫",
                    span=SourceSpan(tok.line, tok.col),
                    output_type=CellValueType.HYBIT,
                    letter_sequence=letters,
                )
            )
            return cid

        if tok.type == HCellTokenType.CELL_ID:
            self._advance()
            if self._cur().type == HCellTokenType.LPAREN:
                return self._parse_fn_call(tok)
            if tok.value not in self._env:
                raise HCellParseError(
                    f"Undefined Hijaiyyah cell reference {tok.value!r}", tok
                )
            return self._env[tok.value]

        if tok.type == HCellTokenType.INTEGER:
            self._advance()
            val = int(tok.value)
            cid = self._new_id("num")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.SCALAR_CONST,
                    source_glyphs=tok.value,
                    span=SourceSpan(tok.line, tok.col),
                    output_type=CellValueType.SCALAR,
                    imm_param=val,
                    static_scalar=val,
                )
            )
            return cid

        if tok.type == HCellTokenType.NORM_BAR:
            self._advance()
            inner_id = self._parse_expr()
            self._expect(HCellTokenType.NORM_BAR, "Expected closing '‖' in norm expression")
            self._expect(HCellTokenType.SUP_TWO, "Expected '²' after closing '‖'")
            inner_node = self._graph.nodes[inner_id]
            cid = self._new_id("nrm")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.NORM2_V14,
                    source_glyphs=f"‖{inner_node.source_glyphs}‖²",
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[inner_id],
                    output_type=CellValueType.SCALAR,
                )
            )
            return cid

        if tok.type == HCellTokenType.LANGLE:
            self._advance()
            a_id = self._parse_expr()
            self._expect(HCellTokenType.COMMA, "Expected ',' inside ⟨a, b⟩")
            b_id = self._parse_expr()
            self._expect(HCellTokenType.RANGLE, "Expected '⟩' closing inner product")
            cid = self._new_id("dot")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.INNER_V14,
                    source_glyphs=(
                        f"⟨{self._graph.nodes[a_id].source_glyphs}, "
                        f"{self._graph.nodes[b_id].source_glyphs}⟩"
                    ),
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[a_id, b_id],
                    output_type=CellValueType.SCALAR,
                )
            )
            return cid

        # Official HOS Syscall: ⏣(sys_num, arg [, hybit_payload])
        if tok.type == HCellTokenType.OP_SYSCALL:
            self._advance()
            self._expect(HCellTokenType.LPAREN, "Expected '(' after '⏣'")
            args = [self._parse_expr()]
            while self._cur().type == HCellTokenType.COMMA:
                self._advance()
                args.append(self._parse_expr())
            self._expect(HCellTokenType.RPAREN, "Expected ')' closing '⏣(...)'")
            arg_glyphs = ", ".join(self._graph.nodes[a].source_glyphs for a in args)
            cid = self._new_id("sys")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.HOS_SYSCALL,
                    source_glyphs=f"⏣({arg_glyphs})",
                    span=SourceSpan(tok.line, tok.col),
                    inputs=args,
                    output_type=CellValueType.SCALAR,
                )
            )
            return cid

        # Official HFS Read Hybit (SYSCALL 7 -> H0): ⛁(file_id)
        if tok.type == HCellTokenType.OP_HFS_READ_HYBIT:
            self._advance()
            self._expect(HCellTokenType.LPAREN, "Expected '(' after '⛁'")
            fid_id = self._parse_expr()
            self._expect(HCellTokenType.RPAREN, "Expected ')' after '⛁(file_id)'")
            cid = self._new_id("hfsr")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.HFS_READ_HYBIT,
                    source_glyphs=f"⛁({self._graph.nodes[fid_id].source_glyphs})",
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[fid_id],
                    output_type=CellValueType.HYBIT,
                )
            )
            return cid

        # HAR lookup: §(idx) -> CellOp.LOAD_ID
        if tok.type == HCellTokenType.OP_HAR_LOOKUP:
            self._advance()
            self._expect(HCellTokenType.LPAREN, "Expected '(' after '§'")
            idx_id = self._parse_expr()
            self._expect(HCellTokenType.RPAREN, "Expected ')' after '§(idx)'")
            idx_node = self._graph.nodes[idx_id]
            cid = self._new_id("har")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.LOAD_ID,
                    source_glyphs=f"§({idx_node.source_glyphs})",
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[idx_id],
                    output_type=CellValueType.HYBIT,
                    imm_param=idx_node.static_scalar,
                )
            )
            return cid

        unary_ops: dict[HCellTokenType, tuple[CellOp, CellValueType]] = {
            HCellTokenType.OP_THETA: (CellOp.PROJ_THETA, CellValueType.SCALAR),
            HCellTokenType.OP_U: (CellOp.TURNING_U, CellValueType.SCALAR),
            HCellTokenType.OP_RHO: (CellOp.TURNING_RHO, CellValueType.SCALAR),
            HCellTokenType.OP_THETA4: (CellOp.MOD4_GATE, CellValueType.SCALAR),
            HCellTokenType.OP_N: (CellOp.PROJ_GROUP_N, CellValueType.VECTOR3),
            HCellTokenType.OP_K: (CellOp.PROJ_GROUP_K, CellValueType.VECTOR5),
            HCellTokenType.OP_Q: (CellOp.PROJ_GROUP_Q, CellValueType.VECTOR5),
            HCellTokenType.OP_A: (CellOp.PROJ_GROUP_A, CellValueType.VECTOR3),
            HCellTokenType.OP_HSTAR: (CellOp.PROJ_HSTAR, CellValueType.SCALAR),
            HCellTokenType.OP_PHI: (CellOp.EXOMATRIX_PHI, CellValueType.SCALAR),
        }
        if tok.type in unary_ops:
            self._advance()
            self._expect(HCellTokenType.LPAREN, f"Expected '(' after {tok.value}")
            arg_id = self._parse_expr()
            self._expect(HCellTokenType.RPAREN, f"Expected ')' after {tok.value} argument")
            cell_op, out_type = unary_ops[tok.type]
            cid = self._new_id("op")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=cell_op,
                    source_glyphs=f"{tok.value}({self._graph.nodes[arg_id].source_glyphs})",
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[arg_id],
                    output_type=out_type,
                    imm_param=0 if cell_op == CellOp.PROJ_THETA else (
                        17 if cell_op == CellOp.PROJ_HSTAR else None
                    ),
                )
            )
            return cid

        if tok.type in (HCellTokenType.OP_DELTA, HCellTokenType.OP_DIST2):
            self._advance()
            self._expect(HCellTokenType.LPAREN, f"Expected '(' after {tok.value}")
            a_id = self._parse_expr()
            self._expect(HCellTokenType.COMMA, f"Expected ',' in {tok.value}(a, b)")
            b_id = self._parse_expr()
            self._expect(HCellTokenType.RPAREN, f"Expected ')' closing {tok.value}(a, b)")
            is_dist = (tok.type == HCellTokenType.OP_DIST2)
            cid = self._new_id("dst" if is_dist else "dlt")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.DIST2_V14 if is_dist else CellOp.HYBIT_DELTA,
                    source_glyphs=(
                        f"{tok.value}({self._graph.nodes[a_id].source_glyphs}, "
                        f"{self._graph.nodes[b_id].source_glyphs})"
                    ),
                    span=SourceSpan(tok.line, tok.col),
                    inputs=[a_id, b_id],
                    output_type=CellValueType.SCALAR if is_dist else CellValueType.DELTA14,
                )
            )
            return cid

        if tok.type == HCellTokenType.LPAREN:
            self._advance()
            inner_id = self._parse_expr()
            self._expect(HCellTokenType.RPAREN, "Expected ')' after parenthesized expression")
            return inner_id

        raise HCellParseError("Unexpected token in .hcell expression", tok)

    def _parse_fn_call(self, name_tok: HCellToken) -> str:
        self._expect(HCellTokenType.LPAREN, "Expected '(' in subroutine call")
        args: list[str] = []
        if self._cur().type != HCellTokenType.RPAREN:
            args.append(self._parse_expr())
            while self._cur().type == HCellTokenType.COMMA:
                self._advance()
                args.append(self._parse_expr())
        self._expect(HCellTokenType.RPAREN, "Expected ')' closing subroutine call")
        arg_glyphs = ", ".join(self._graph.nodes[a].source_glyphs for a in args)
        cid = self._new_id("call")
        self._add_node(
            CellIRNode(
                cell_id=cid,
                op=CellOp.FN_CALL,
                source_glyphs=f"{name_tok.value}({arg_glyphs})",
                span=SourceSpan(name_tok.line, name_tok.col),
                inputs=args,
                output_type=CellValueType.SCALAR,
                callee_name=name_tok.value,
            )
        )
        return cid


def parse_hcell(source: str) -> CellIRGraph:
    """Lex and parse a native `.hcell` source string into a `CellIRGraph`."""
    tokens = tokenize_hcell(source)
    return HCellParser(tokens).parse()


# ── HC v1.0 (.hc) Compatibility Frontend Bridge ──────────────────────────────


class HCCompatBridge:
    """Lowers an HC v1.0 AST (`Program`) into the shared `CellIRGraph`."""

    def __init__(self) -> None:
        self._graph = CellIRGraph(source_language=HC_COMPAT_VERSION)
        self._counter = 0
        self._env: dict[str, str] = {}
        self._in_nested_block = False
        self._active_sink: list[str] | None = None

    def _new_id(self, prefix: str = "hc") -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def _add_node(self, node: CellIRNode) -> str:
        top = self._active_sink is None
        cid = self._graph.add_node(node, top_level=top)
        if self._active_sink is not None:
            self._active_sink.append(cid)
        return cid

    def lower(self, program: Program) -> CellIRGraph:
        for stmt in program.body:
            self._lower_stmt(stmt)
        return self._graph

    def _lower_block(self, block: Any) -> list[str]:
        saved_sink = self._active_sink
        saved_nested = self._in_nested_block
        self._in_nested_block = True
        collected: list[str] = []
        self._active_sink = collected
        stmts = block.statements if isinstance(block, Block) else [block]
        for s in stmts:
            self._lower_stmt(s)
        self._active_sink = saved_sink
        self._in_nested_block = saved_nested
        return collected

    def _lower_stmt(self, stmt: Any) -> None:
        if isinstance(stmt, FnDecl):
            saved_env = dict(self._env)
            saved_sink = self._active_sink
            body_nodes: list[str] = []
            param_nodes: list[str] = []
            self._active_sink = body_nodes
            params = [p[0] for p in stmt.params]
            for idx, pname in enumerate(params):
                pid = self._new_id("prm")
                self._add_node(
                    CellIRNode(
                        cell_id=pid,
                        op=CellOp.FN_PARAM,
                        source_glyphs=pname,
                        span=SourceSpan(1, 1),
                        output_type=CellValueType.SCALAR,
                        binding_name=pname,
                        imm_param=idx,
                    )
                )
                param_nodes.append(pid)
                self._env[pname] = pid

            ret_id = ""
            stmts = stmt.body.statements if isinstance(stmt.body, Block) else [stmt.body]
            for s in stmts:
                if isinstance(s, ReturnStmt):
                    ret_id = self._lower_expr(s.value)
                elif isinstance(s, ExpressedStmt):
                    ret_id = self._lower_expr(s.expr)
                else:
                    self._lower_stmt(s)
            if not ret_id and body_nodes:
                ret_id = body_nodes[-1]
            self._graph.subroutines[stmt.name] = CellSubroutineDef(
                name=stmt.name,
                params=params,
                param_node_ids=param_nodes,
                body_node_ids=body_nodes,
                return_node_id=ret_id,
                return_type=CellValueType.SCALAR,
            )
            self._env = saved_env
            self._active_sink = saved_sink
            return

        if isinstance(stmt, LetStmt):
            cid = self._lower_expr(stmt.value)
            node = self._graph.nodes[cid]
            node.binding_name = stmt.name
            self._graph.bindings[stmt.name] = cid
            self._env[stmt.name] = cid
            return

        if isinstance(stmt, AssignStmt):
            val_id = self._lower_expr(stmt.value)
            cid = self._new_id("asn")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.VAR_ASSIGN,
                    source_glyphs=f"{stmt.name} = {self._graph.nodes[val_id].source_glyphs}",
                    span=SourceSpan(1, 1),
                    inputs=[val_id],
                    output_type=self._graph.nodes[val_id].output_type,
                    binding_name=stmt.name,
                )
            )
            return

        if isinstance(stmt, WhileStmt):
            cid = self._new_id("loop")
            saved_sink = self._active_sink
            cond_nodes: list[str] = []
            self._active_sink = cond_nodes
            cond_id = self._lower_expr(stmt.condition)
            self._active_sink = saved_sink
            body_nodes = self._lower_block(stmt.body)
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.WHILE_LOOP,
                    source_glyphs=f"while ({self._graph.nodes[cond_id].source_glyphs})",
                    span=SourceSpan(1, 1),
                    inputs=[cond_id],
                    output_type=CellValueType.VOID,
                    loop_cond_node_ids=cond_nodes,
                    loop_body_node_ids=body_nodes,
                )
            )
            return

        if isinstance(stmt, IfExpr):
            cond_id = self._lower_expr(stmt.condition)
            then_nodes = self._lower_block(stmt.then_branch)
            else_nodes = (
                self._lower_block(stmt.else_branch) if stmt.else_branch is not None else []
            )
            cid = self._new_id("if")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.COND_BRANCH,
                    source_glyphs=f"if ({self._graph.nodes[cond_id].source_glyphs})",
                    span=SourceSpan(1, 1),
                    inputs=[cond_id],
                    output_type=CellValueType.VOID,
                    then_node_ids=then_nodes,
                    else_node_ids=else_nodes,
                )
            )
            return

        if isinstance(stmt, ExpressedStmt):
            expr = stmt.expr
            if isinstance(expr, IfExpr):
                cond_id = self._lower_expr(expr.condition)
                then_nodes = self._lower_block(expr.then_branch)
                else_nodes = (
                    self._lower_block(expr.else_branch) if expr.else_branch is not None else []
                )
                cid = self._new_id("if")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.COND_BRANCH,
                        source_glyphs=f"if ({self._graph.nodes[cond_id].source_glyphs})",
                        span=SourceSpan(1, 1),
                        inputs=[cond_id],
                        output_type=CellValueType.VOID,
                        then_node_ids=then_nodes,
                        else_node_ids=else_nodes,
                    )
                )
                return

            if isinstance(expr, MethodCall) and expr.method == "guard":
                obj_id = self._lower_expr(expr.obj)
                cid = self._new_id("grd")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.GUARD_CHECK,
                        source_glyphs=f"{self._graph.nodes[obj_id].source_glyphs}.guard()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.BOOL,
                    )
                )
                return

            if isinstance(expr, CallExpr) and expr.callee in ("println", "print"):
                if len(expr.args) != 1:
                    raise HijaiyyahError(f"{expr.callee} takes 1 argument in Cell IR")
                arg_id = self._lower_expr(expr.args[0])
                cid = self._new_id("out")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.EMIT_OUTPUT,
                        source_glyphs=f"{expr.callee}({self._graph.nodes[arg_id].source_glyphs})",
                        span=SourceSpan(1, 1),
                        inputs=[arg_id],
                        output_type=CellValueType.VOID,
                    )
                )
                return

            self._lower_expr(expr)
            return

        raise HijaiyyahError(
            f"Unsupported HC v1.0 statement in Cell IR bridge: {type(stmt).__name__}"
        )

    def _lower_expr(self, expr: Any) -> str:
        if isinstance(expr, Literal):
            if expr.lit_type == "hybit_ref":
                rec = MASTER_TABLE_ENGINE.get_by_char(str(expr.value))
                if rec is None:
                    raise HijaiyyahError(f"Unknown Hijaiyyah literal: {expr.value!r}")
                cid = self._new_id("ltr")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.LETTER_CONST,
                        source_glyphs=rec.char,
                        span=SourceSpan(1, 1),
                        output_type=CellValueType.HYBIT,
                        master_table_id=rec.har_ref,
                        imm_param=rec.index,
                        letter_sequence=(rec.char,),
                    )
                )
                return cid

            if isinstance(expr.value, int) and not isinstance(expr.value, bool):
                cid = self._new_id("num")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.SCALAR_CONST,
                        source_glyphs=str(expr.value),
                        span=SourceSpan(1, 1),
                        output_type=CellValueType.SCALAR,
                        imm_param=int(expr.value),
                        static_scalar=int(expr.value),
                    )
                )
                return cid

        if isinstance(expr, VarRef):
            if expr.name not in self._env:
                raise HijaiyyahError(f"Unbound variable in HC source: {expr.name!r}")
            return self._env[expr.name]

        if isinstance(expr, BinaryExpr):
            left_id = self._lower_expr(expr.left)
            right_id = self._lower_expr(expr.right)
            lnode = self._graph.nodes[left_id]
            rnode = self._graph.nodes[right_id]

            if (
                lnode.output_type == CellValueType.HYBIT
                and rnode.output_type == CellValueType.HYBIT
            ):
                if expr.op == "+":
                    seq: tuple[str, ...] = ()
                    if lnode.letter_sequence and rnode.letter_sequence:
                        seq = (*lnode.letter_sequence, *rnode.letter_sequence)
                    cid = self._new_id("add")
                    self._add_node(
                        CellIRNode(
                            cell_id=cid,
                            op=CellOp.HYBIT_ADD,
                            source_glyphs=f"{lnode.source_glyphs} + {rnode.source_glyphs}",
                            span=SourceSpan(1, 1),
                            inputs=[left_id, right_id],
                            output_type=CellValueType.HYBIT,
                            letter_sequence=seq,
                        )
                    )
                    return cid
                if expr.op == "-":
                    cid = self._new_id("dlt")
                    self._add_node(
                        CellIRNode(
                            cell_id=cid,
                            op=CellOp.HYBIT_DELTA,
                            source_glyphs=f"{lnode.source_glyphs} - {rnode.source_glyphs}",
                            span=SourceSpan(1, 1),
                            inputs=[left_id, right_id],
                            output_type=CellValueType.DELTA14,
                        )
                    )
                    return cid
                if expr.op == "==":
                    cid = self._new_id("ceq")
                    self._add_node(
                        CellIRNode(
                            cell_id=cid,
                            op=CellOp.HYBIT_EQ,
                            source_glyphs=f"{lnode.source_glyphs} == {rnode.source_glyphs}",
                            span=SourceSpan(1, 1),
                            inputs=[left_id, right_id],
                            output_type=CellValueType.SCALAR,
                        )
                    )
                    return cid

            cmp_map = {
                "==": CellOp.CMP_EQ,
                "!=": CellOp.CMP_NE,
                "<": CellOp.CMP_LT,
                ">": CellOp.CMP_GT,
                "<=": CellOp.CMP_LE,
                ">=": CellOp.CMP_GE,
            }
            if expr.op in cmp_map:
                cid = self._new_id("cmp")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=cmp_map[expr.op],
                        source_glyphs=f"{lnode.source_glyphs} {expr.op} {rnode.source_glyphs}",
                        span=SourceSpan(1, 1),
                        inputs=[left_id, right_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid

            op_map = {
                "+": CellOp.SCALAR_ADD,
                "-": CellOp.SCALAR_SUB,
                "*": CellOp.SCALAR_MUL,
            }
            if expr.op in op_map:
                cid = self._new_id("sop")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=op_map[expr.op],
                        source_glyphs=f"{lnode.source_glyphs} {expr.op} {rnode.source_glyphs}",
                        span=SourceSpan(1, 1),
                        inputs=[left_id, right_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid

        if isinstance(expr, CallExpr):
            if expr.callee == "zero" and not expr.args:
                cid = self._new_id("zro")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.ZERO_HYBIT,
                        source_glyphs="zero()",
                        span=SourceSpan(1, 1),
                        output_type=CellValueType.HYBIT,
                    )
                )
                return cid
            if expr.callee == "load_id" and len(expr.args) == 1:
                arg_id = self._lower_expr(expr.args[0])
                arg_node = self._graph.nodes[arg_id]
                cid = self._new_id("lid")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.LOAD_ID,
                        source_glyphs=f"load_id({arg_node.source_glyphs})",
                        span=SourceSpan(1, 1),
                        inputs=[arg_id],
                        output_type=CellValueType.HYBIT,
                        imm_param=arg_node.static_scalar,
                    )
                )
                return cid
            if expr.callee in self._graph.subroutines:
                args = [self._lower_expr(a) for a in expr.args]
                arg_glyphs = ", ".join(self._graph.nodes[a].source_glyphs for a in args)
                cid = self._new_id("call")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.FN_CALL,
                        source_glyphs=f"{expr.callee}({arg_glyphs})",
                        span=SourceSpan(1, 1),
                        inputs=args,
                        output_type=CellValueType.SCALAR,
                        callee_name=expr.callee,
                    )
                )
                return cid

        if isinstance(expr, IndexExpr):
            obj_id = self._lower_expr(expr.obj)
            idx_id = self._lower_expr(expr.index)
            idx_node = self._graph.nodes[idx_id]
            cid = self._new_id("idx")
            self._add_node(
                CellIRNode(
                    cell_id=cid,
                    op=CellOp.PROJ_COMPONENT,
                    source_glyphs=(
                        f"{self._graph.nodes[obj_id].source_glyphs}[{idx_node.source_glyphs}]"
                    ),
                    span=SourceSpan(1, 1),
                    inputs=[obj_id],
                    output_type=CellValueType.SCALAR,
                    imm_param=idx_node.static_scalar,
                )
            )
            return cid

        if isinstance(expr, MethodCall):
            obj_id = self._lower_expr(expr.obj)
            obj_glyphs = self._graph.nodes[obj_id].source_glyphs
            m = expr.method
            if m == "theta":
                cid = self._new_id("tht")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.PROJ_THETA,
                        source_glyphs=f"{obj_glyphs}.theta()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                        imm_param=0,
                    )
                )
                return cid
            if m in SLOT_INDEX:
                slot = SLOT_INDEX[m]
                cid = self._new_id("cget")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.PROJ_COMPONENT,
                        source_glyphs=f"{obj_glyphs}.{m}()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                        imm_param=slot,
                    )
                )
                return cid
            if m == "U":
                cid = self._new_id("u")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.TURNING_U,
                        source_glyphs=f"{obj_glyphs}.U()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid
            if m == "rho":
                cid = self._new_id("rho")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.TURNING_RHO,
                        source_glyphs=f"{obj_glyphs}.rho()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid
            if m == "norm2":
                cid = self._new_id("nrm")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.NORM2_V14,
                        source_glyphs=f"{obj_glyphs}.norm2()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid
            if m == "dist2" and len(expr.args) == 1:
                other_id = self._lower_expr(expr.args[0])
                cid = self._new_id("dst")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.DIST2_V14,
                        source_glyphs=(
                            f"{obj_glyphs}.dist2({self._graph.nodes[other_id].source_glyphs})"
                        ),
                        span=SourceSpan(1, 1),
                        inputs=[obj_id, other_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid
            if m == "dot" and len(expr.args) == 1:
                other_id = self._lower_expr(expr.args[0])
                cid = self._new_id("dot")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.INNER_V14,
                        source_glyphs=(
                            f"{obj_glyphs}.dot({self._graph.nodes[other_id].source_glyphs})"
                        ),
                        span=SourceSpan(1, 1),
                        inputs=[obj_id, other_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid
            if m == "pack" and len(expr.args) == 1:
                idx_id = self._lower_expr(expr.args[0])
                idx_node = self._graph.nodes[idx_id]
                cid = self._new_id("pck")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.HISAB_PACK,
                        source_glyphs=f"{obj_glyphs}.pack({idx_node.source_glyphs})",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                        imm_param=idx_node.static_scalar,
                    )
                )
                return cid
            if m == "crc" and not expr.args:
                cid = self._new_id("crc")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.HISAB_CRC,
                        source_glyphs=f"{obj_glyphs}.crc()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid
            if m == "phi" and not expr.args:
                cid = self._new_id("phi")
                self._add_node(
                    CellIRNode(
                        cell_id=cid,
                        op=CellOp.EXOMATRIX_PHI,
                        source_glyphs=f"{obj_glyphs}.phi()",
                        span=SourceSpan(1, 1),
                        inputs=[obj_id],
                        output_type=CellValueType.SCALAR,
                    )
                )
                return cid

        raise HijaiyyahError(f"Unsupported HC v1.0 expression in Cell IR bridge: {expr!r}")


def parse_hc_to_cell_ir(source: str) -> CellIRGraph:
    """Parse an HC v1.0 `.hc` source string and lower it into a `CellIRGraph`."""
    tokens = HCLexer(source).tokenize()
    ast = HCParser(tokens).parse()
    return HCCompatBridge().lower(ast)


__all__ = [
    "HCCompatBridge",
    "HCellParseError",
    "HCellParser",
    "parse_hc_to_cell_ir",
    "parse_hcell",
]
