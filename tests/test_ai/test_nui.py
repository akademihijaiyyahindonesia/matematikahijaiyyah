"""hijaiyyah.nui: features, dataset, model, and a fast end-to-end check.

The full experiment (`python3 -m hijaiyyah.nui.train`, 4000 sequences, 500
epochs, ~15s) is documented and reproducible in
src/hijaiyyah/nui/README.md rather than re-run here on every test pass; what
runs here is scaled down to stay fast while still exercising real code, not
mocks. Everything in this module needs torch, which is an optional extra
(`pip install .[nui]`) precisely because the rest of this project does not
need it -- skip the whole file if it is not installed, rather than fail.
"""
from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from hijaiyyah.core.exomatrix import matrix_order  # noqa: E402
from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.nui.dataset import (  # noqa: E402
    Example,
    build_dataset,
    is_primitive,
    random_examples,
    real_corpus_examples,
)
from hijaiyyah.nui.features import (  # noqa: E402
    all_letter_features,
    feature_matrix,
    vector_features,
)
from hijaiyyah.nui.model import LetterAccumulatorNet, labels, multihot  # noqa: E402
from hijaiyyah.nui.train import evaluate, prior_correction, train_one  # noqa: E402

# ── features.py ────────────────────────────────────────────────


def test_exomatrix_period_matches_the_established_jim_facts():
    """cosmic-codex-jim/'s own numbers, recomputed through the lifted
    function rather than the test file's former private copy."""
    jim = MASTER_TABLE.get_by_char("ج")
    kha = MASTER_TABLE.get_by_char("خ")
    assert matrix_order(jim.vector, 2) == (1, 31)
    assert matrix_order(jim.vector, 5) == (1, 3124)
    assert matrix_order(kha.vector, 2)[1] == 31


def test_letter_features_match_hand_computed_values():
    jim = vector_features(MASTER_TABLE.get_by_char("ج").vector)
    assert jim == (1, 1, 1, 3, 3)  # titik, garis, lengkung, theta, rho

    alif = vector_features(MASTER_TABLE.get_by_char("ا").vector)
    assert alif == (0, 1, 0, 0, 0)  # pure line, zero turning


def test_jims_theta_is_not_its_curve_component():
    """The precision note features.py's docstring exists for: 270 degrees
    is Jim's TOTAL turning (theta), not what its curve component explains
    (U = theta - rho = 0)."""
    jim = MASTER_TABLE.get_by_char("ج")
    f = vector_features(jim.vector)
    assert f.theta == 3 and f.theta * 90 == 270
    assert f.rho == f.theta, "none of Jim's turning is curve-explained"


def test_all_letter_features_and_matrix_agree():
    features = all_letter_features()
    matrix = feature_matrix()
    assert len(features) == len(matrix) == 28
    ordered = [features[e.char] for e in MASTER_TABLE.all_entries()]
    assert [list(f.as_tuple()) for f in ordered] == matrix


# ── dataset.py ─────────────────────────────────────────────────


def test_is_primitive_matches_direct_matrix_order():
    jim_vec = list(MASTER_TABLE.get_by_char("ج").vector)
    assert is_primitive(jim_vec) is True
    alif_vec = list(MASTER_TABLE.get_by_char("ا").vector)
    assert is_primitive(alif_vec) is False


def test_random_examples_labels_are_independently_verifiable():
    """Spot-check every example's label against a fresh accumulation and
    matrix_order call, not against dataset.py's own bookkeeping."""
    examples = random_examples(20, seed=1)
    assert examples
    entries = MASTER_TABLE.all_entries()
    for ex in examples:
        acc = [0] * 18
        for idx in ex.letter_indices:
            acc = [a + b for a, b in zip(acc, entries[idx].vector, strict=True)]
        _, period = matrix_order(acc, 2, cap=64)
        assert ex.label == (period == 31), ex


def test_real_corpus_examples_is_the_actual_letters_hasm_order():
    """The prefixes must be Alif..Ya in Master Table order -- the same
    accumulation rtl/programs/letters.hasm performs -- not a shuffled or
    reordered stand-in."""
    examples = real_corpus_examples()
    assert len(examples) == 28
    assert list(examples[-1].letter_indices) == list(range(28))
    for i, ex in enumerate(examples):
        assert list(ex.letter_indices) == list(range(i + 1))


def test_build_dataset_is_class_balanced_for_training_and_natural_for_eval():
    ds = build_dataset(sequences=300, seed=2)
    assert sum(e.label for e in ds.train) == sum(not e.label for e in ds.train)
    natural_rate = sum(e.label for e in ds.natural) / len(ds.natural)
    assert 0.0 < natural_rate < 0.3, "the natural split should stay rare-positive"
    assert ds.real_corpus == real_corpus_examples()


# ── model.py ───────────────────────────────────────────────────


def test_physics_embedding_is_frozen_and_matches_feature_matrix():
    net = LetterAccumulatorNet(kind="physics")
    assert not net.embedding.weight.requires_grad
    expected = torch.tensor(feature_matrix(), dtype=torch.float32)
    assert torch.equal(net.embedding.weight, expected)


def test_exomatrix_embedding_is_frozen_and_matches_build_exomatrix():
    """The 25-dim embedding is exactly what src/hijaiyyah/crypto/cube.py's
    build_cube() stacks over all 28 letters and cube_digest() hashes to seed
    the Ka'bah S-box -- not a new representation invented for this
    comparison. Cross-checked against build_exomatrix directly, not against
    exomatrix_matrix()'s own bookkeeping."""
    from hijaiyyah.core.exomatrix import build_exomatrix
    from hijaiyyah.core.master_table import MASTER_TABLE as MT

    net = LetterAccumulatorNet(kind="exomatrix")
    assert not net.embedding.weight.requires_grad
    assert net.embedding.weight.shape == (28, 25)

    jim = MT.get_by_char("ج")
    jim_row = net.embedding.weight[jim.index - 1]
    expected = [x for row in build_exomatrix(jim.vector) for x in row]
    assert jim_row.tolist() == [float(x) for x in expected]


def test_baseline_embedding_is_trainable_at_the_requested_dimension():
    net = LetterAccumulatorNet(kind="baseline", embed_dim=25)
    assert net.embedding.weight.requires_grad
    assert net.embedding.weight.shape == (28, 25)


def test_baseline_without_embed_dim_is_rejected():
    with pytest.raises(ValueError, match="embed_dim"):
        LetterAccumulatorNet(kind="baseline")


def test_multihot_and_forward_shapes():
    examples = random_examples(5, seed=3)
    batch = multihot(examples)
    assert batch.shape == (len(examples), 28)
    net = LetterAccumulatorNet(kind="physics")
    out = net(batch)
    assert out.shape == (len(examples),)


def test_multihot_sums_match_manual_accumulation():
    """The model's `multihot @ embedding` really does compute the same sum
    dataset.py accumulates by hand -- not merely something shaped right."""
    ex = Example(letter_indices=(0, 4, 6), label=False)  # Alif, Jim, Kha
    net = LetterAccumulatorNet(kind="physics")
    summed = multihot([ex]) @ net.embedding.weight
    entries = MASTER_TABLE.all_entries()
    expected = vector_features(
        [sum(x) for x in zip(entries[0].vector, entries[4].vector, entries[6].vector, strict=True)]
    )
    assert torch.allclose(summed[0], torch.tensor(expected.as_tuple(), dtype=torch.float32))


# ── train.py ───────────────────────────────────────────────────


def test_prior_correction_shifts_toward_the_rarer_class():
    """Correcting from a 50% training prior to a rare ~4.5% natural prior
    must shift the decision boundary AGAINST predicting positive -- a
    positive bias here would mean the sign is backwards."""
    bias = prior_correction(0.045)
    assert bias < 0


def test_prior_correction_is_zero_when_priors_match():
    assert prior_correction(0.5) == pytest.approx(0.0, abs=1e-9)


def test_training_beats_the_naive_baseline_on_a_small_scale_run():
    """Scaled down for test speed (300 sequences, 60 epochs versus the
    documented 4000/500) -- not the rigorous numbers in README.md, just a
    real, fast check that the training loop actually learns something."""
    ds = build_dataset(sequences=300, seed=0)
    natural_rate = sum(e.label for e in ds.natural) / len(ds.natural)
    bias = prior_correction(natural_rate)

    model = train_one(kind="physics", dataset=ds, epochs=60, seed=0)
    calibrated = evaluate(model, ds.natural, logit_bias=bias)
    assert calibrated.accuracy >= calibrated.baseline_accuracy, (
        "a trained model should not do worse than always predicting "
        "not-primitive once calibrated to the true prior"
    )


def test_labels_tensor_matches_example_order():
    examples = random_examples(4, seed=5)
    y = labels(examples)
    assert y.tolist() == [1.0 if e.label else 0.0 for e in examples]
