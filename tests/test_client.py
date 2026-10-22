"""SPEC 7.1 (request), 7.2 (parsing) and 7.3 (errors)."""

import json
import math

import httpx
import pytest

from magic8.client import BackendError, parse_response

BAD_RESPONSE_MESSAGE = "The decision model sent a response the ball can't read."
DEFAULT_URL = "http://127.0.0.1:8000"


def wrap(probabilities, **extra):
    answer = {"type": "choice", "probabilities": probabilities, **extra}
    return {"answers": {"answer": answer}}


# --- request -------------------------------------------------------------------------------


def test_request_shape(run_cli, fake_server, answer_rows):
    code, _, _ = run_cli("Will it rain?", "--backend", fake_server.url)
    assert code == 0
    assert len(fake_server.requests) == 1
    req = fake_server.requests[0]
    assert req.method == "POST"
    assert req.path == "/v1/systemone"
    body = req.json
    assert "Will it rain?" in body["state"]
    assert len(body["questions"]) == 1
    (question,) = body["questions"].values()
    assert question["type"] == "choice"
    assert question["criteria"] == {key: text for key, text, _ in answer_rows}


def test_no_model_field_when_unset(run_cli, fake_server):
    run_cli("q?", "--backend", fake_server.url)
    assert "model" not in fake_server.requests[0].json


def test_model_from_env(run_cli, fake_server):
    run_cli("q?", "--backend", fake_server.url, env={"MAGIC8_MODEL": "jev-latest"})
    assert fake_server.requests[0].json["model"] == "jev-latest"


def test_model_from_flag(run_cli, fake_server):
    run_cli("q?", "--backend", fake_server.url, "--model", "jev-latest")
    assert fake_server.requests[0].json["model"] == "jev-latest"


def test_model_flag_overrides_env(run_cli, fake_server):
    run_cli("q?", "--backend", fake_server.url, "--model", "flag", env={"MAGIC8_MODEL": "env"})
    assert fake_server.requests[0].json["model"] == "flag"


def test_no_authorization_header_when_key_unset(run_cli, fake_server):
    run_cli("q?", "--backend", fake_server.url)
    assert "authorization" not in fake_server.requests[0].headers


def test_bearer_header_when_key_set(run_cli, fake_server):
    run_cli("q?", "--backend", fake_server.url, env={"MAGIC8_API_KEY": "sekrit"})
    assert fake_server.requests[0].headers["authorization"] == "Bearer sekrit"


def test_backend_flag_overrides_env(run_cli, fake_server, closed_port_url):
    code, _, _ = run_cli(
        "q?", "--backend", fake_server.url, env={"MAGIC8_BASE_URL": closed_port_url()}
    )
    assert code == 0
    assert len(fake_server.requests) == 1


def test_base_url_from_env(run_cli, fake_server):
    code, _, _ = run_cli("q?", env={"MAGIC8_BASE_URL": fake_server.url})
    assert code == 0
    assert len(fake_server.requests) == 1


def test_trailing_slash_base_url(run_cli, fake_server):
    code, _, _ = run_cli("q?", "--backend", fake_server.url + "/")
    assert code == 0
    assert fake_server.requests[0].path == "/v1/systemone"


# --- parse_response ------------------------------------------------------------------------


def test_unknown_keys_ignored(answer_rows):
    result = parse_response(wrap({"yes": 0.5, "maybe": 0.5}))
    assert "maybe" not in result.probabilities
    assert len(result.probabilities) == 20
    assert result.probabilities["yes"] == 1.0
    assert all(v == 0.0 for k, v in result.probabilities.items() if k != "yes")


def test_unknown_keys_ignored_whatever_their_value():
    result = parse_response(wrap({"yes": 1.0, "maybe": "junk", "other": -3, "x": True}))
    assert result.probabilities["yes"] == 1.0


def test_normalisation_and_order(answer_rows):
    result = parse_response(wrap({"yes": 2, "very_doubtful": 2}))
    assert result.probabilities["yes"] == pytest.approx(0.5)
    assert result.probabilities["very_doubtful"] == pytest.approx(0.5)
    assert list(result.probabilities) == [key for key, _, _ in answer_rows]
    assert sum(result.probabilities.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param([], id="not-a-dict-list"),
        pytest.param(None, id="not-a-dict-none"),
        pytest.param("text", id="not-a-dict-str"),
        pytest.param({}, id="missing-answers"),
        pytest.param({"answers": []}, id="answers-not-dict"),
        pytest.param({"answers": {}}, id="missing-answer"),
        pytest.param({"answers": {"answer": []}}, id="answer-not-dict"),
        pytest.param({"answers": {"answer": {}}}, id="missing-probabilities"),
        pytest.param(wrap([0.5, 0.5]), id="probabilities-not-dict"),
        pytest.param(wrap({}), id="empty-probabilities"),
        pytest.param(wrap({"maybe": 1.0}), id="no-known-key"),
        pytest.param(wrap({"yes": 0, "my_reply_is_no": 0.0}), id="all-zero"),
        pytest.param(wrap({"yes": "0.5"}), id="string-value"),
        pytest.param(wrap({"yes": 0.5, "my_reply_is_no": -0.1}), id="negative"),
        pytest.param(wrap({"yes": math.nan, "my_reply_is_no": 1.0}), id="nan"),
        pytest.param(wrap({"yes": math.inf}), id="inf"),
        pytest.param(wrap({"yes": True}), id="bool"),
        pytest.param(wrap({"yes": 0.5, "my_reply_is_no": None}), id="null-value"),
    ],
)
def test_bad_responses_raise(data):
    with pytest.raises(BackendError) as exc:
        parse_response(data)
    assert exc.value.code == "bad_response"
    assert exc.value.message == BAD_RESPONSE_MESSAGE
    assert str(exc.value) == BAD_RESPONSE_MESSAGE


def test_huge_int_probability_is_valid_and_normalised():
    result = parse_response(wrap({"yes": 10**400, "my_reply_is_no": 1}))
    assert result.probabilities["yes"] == 1.0
    assert result.probabilities["my_reply_is_no"] == 0.0
    assert sum(result.probabilities.values()) == pytest.approx(1.0)


def test_huge_float_probabilities_do_not_overflow():
    result = parse_response(wrap({"yes": 1e308, "my_reply_is_no": 1e308}))
    assert result.probabilities["yes"] == pytest.approx(0.5)
    assert result.probabilities["my_reply_is_no"] == pytest.approx(0.5)


def test_huge_int_probability_through_cli(run_cli, fake_server, answer_rows):
    fake_server.body = b'{"answers": {"answer": {"probabilities": {"yes": ' + b"9" * 400 + b"}}}}"
    code, out, err = run_cli("Will it rain?", "--backend", fake_server.url)
    text = next(t for k, t, _ in answer_rows if k == "yes")
    assert code == 0
    assert f"▲  {text}  ▲" in out


def _probabilities_body(probs):
    return b'{"answers": {"answer": {"probabilities": {' + probs + b"}}}}"


@pytest.mark.parametrize(
    "probs",
    [
        b'"yes": ' + b"9" * 4301,
        b'"yes": ' + b"9" * 5000 + b', "my_reply_is_no": 1',
        b'"yes": 1e400, "my_reply_is_no": 1',
        b'"yes": 9.9e999999, "my_reply_is_no": 1',
        b'"yes": 1e-1000000',
        b'"yes": 1, "my_reply_is_no": 0e99999999999999999999',
        b'"yes": 1, "my_reply_is_no": 0.0',
        b'"yes": 1, "my_reply_is_no": 0.0e99999999999999999999',
        b'"yes": 1, "my_reply_is_no": -0.0E-99999999999999999999',
    ],
    ids=[
        "int-4301-digits",
        "int-5000-digits",
        "1e400",
        "just-below-max",
        "min",
        "zero-huge-exponent",
        "zero-float",
        "zero-point-huge-exponent",
        "negative-zero-point-tiny-exponent",
    ],
)
def test_probability_of_any_size_in_range_is_valid(run_cli, fake_server, probs):
    fake_server.body = _probabilities_body(probs)
    code, out, err = run_cli("Will it rain?", "--backend", fake_server.url, "--json")
    assert code == 0
    result = json.loads(out)
    assert result["key"] == "yes"
    assert result["probabilities"]["yes"] == 1.0
    assert result["probabilities"]["my_reply_is_no"] == 0.0


@pytest.mark.parametrize("count", [4, 20], ids=["4-keys", "20-keys"])
def test_probabilities_near_max_are_summed_without_overflow(
    run_cli, fake_server, answer_rows, count
):
    keys = [key for key, _, _ in answer_rows][:count]
    entries = [b'"%s": 9.99e999999' % key.encode() for key in keys]
    fake_server.body = _probabilities_body(b", ".join(entries))
    code, out, err = run_cli("Will it rain?", "--backend", fake_server.url, "--json")
    assert code == 0
    result = json.loads(out)
    assert result["key"] in keys
    for key, _, _ in answer_rows:
        expected = 1 / count if key in keys else 0.0
        assert result["probabilities"][key] == expected


def test_normalisation_is_exact_to_float_precision(run_cli, fake_server):
    fake_server.body = _probabilities_body(b'"yes": 1, "my_reply_is_no": 2')
    code, out, err = run_cli("Will it rain?", "--backend", fake_server.url, "--json")
    assert code == 0
    result = json.loads(out)
    assert result["probabilities"]["yes"] == 1 / 3
    assert result["probabilities"]["my_reply_is_no"] == 2 / 3


@pytest.mark.parametrize(
    "probs",
    [
        b'"yes": 1e1000000',
        b'"yes": 1, "my_reply_is_no": 1e-1000001',
        b'"yes": 1, "my_reply_is_no": 1e99999999999999999999',
        b'"yes": 1, "my_reply_is_no": 1e-99999999999999999999',
        b'"yes": -1e400',
    ],
    ids=["max", "below-min", "huge-exponent", "tiny-exponent", "negative-huge"],
)
def test_probability_out_of_range_is_bad_response(run_cli, fake_server, probs):
    fake_server.body = _probabilities_body(probs)
    code, out, err = run_cli("Will it rain?", "--backend", fake_server.url, "--json")
    assert code == 2
    assert json.loads(out) == {"error": "bad_response", "message": BAD_RESPONSE_MESSAGE}


def test_model_choice_kept_when_known():
    result = parse_response(wrap({"yes": 1.0}, choice="very_doubtful"))
    assert result.model_choice == "very_doubtful"


def test_model_choice_none_when_unknown_or_missing():
    assert parse_response(wrap({"yes": 1.0}, choice="maybe")).model_choice is None
    assert parse_response(wrap({"yes": 1.0})).model_choice is None


def test_confidence_and_model_and_latency():
    data = wrap({"yes": 1.0}, confidence=0.25)
    data["model"] = "m-1"
    result = parse_response(data, latency_ms=17)
    assert result.confidence == 0.25
    assert result.model == "m-1"
    assert result.latency_ms == 17


def test_confidence_and_model_none_when_missing():
    result = parse_response(wrap({"yes": 1.0}))
    assert result.confidence is None
    assert result.model is None


def test_confidence_bool_is_not_a_number():
    assert parse_response(wrap({"yes": 1.0}, confidence=True)).confidence is None


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(10**400, id="huge-int"),
        pytest.param(math.nan, id="nan"),
        pytest.param(math.inf, id="inf"),
        pytest.param(-math.inf, id="-inf"),
    ],
)
def test_unusable_confidence_is_none(value):
    assert parse_response(wrap({"yes": 1.0}, confidence=value)).confidence is None


def _no_constants(name):
    raise ValueError(f"non-standard JSON constant {name}")


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            b'{"answers": {"answer": {"probabilities": {"yes": 1}, "confidence": '
            + b"9" * 400
            + b"}}}",
            id="huge-int",
        ),
        pytest.param(
            b'{"answers": {"answer": {"probabilities": {"yes": 1}, "confidence": NaN}}}',
            id="nan",
        ),
    ],
)
def test_unusable_confidence_through_cli_is_strict_json_null(run_cli, fake_server, body):
    fake_server.body = body
    code, out, _ = run_cli("Will it rain?", "--backend", fake_server.url, "--json")
    assert code == 0
    obj = json.loads(out, parse_constant=_no_constants)
    assert obj["confidence"] is None


# --- error cases through the CLI -----------------------------------------------------------


def _connect_refused(request):
    raise httpx.ConnectError("refused", request=request)


def _read_timeout(request):
    raise httpx.ReadTimeout("slow", request=request)


def make_scenario(kind, fake_server, closed_port_url):
    """Return (argv, env, transport, code, message) for one error kind."""
    argv = ["Will it rain?"]
    env = {}
    transport = None
    if kind == "unreachable-other":
        url = closed_port_url()
        argv += ["--backend", url]
        return argv, env, transport, "unreachable", f"Can't reach the decision model at {url}."
    if kind == "unreachable-default":
        transport = httpx.MockTransport(_connect_refused)
        message = (
            f"Can't reach the decision model at {DEFAULT_URL}. "
            "Start a local Laya server with: laya-serve"
        )
        return argv, env, transport, "unreachable", message
    if kind == "timeout-server":
        fake_server.delay = 1.0
        argv += ["--backend", fake_server.url]
        env["MAGIC8_TIMEOUT_MS"] = "200"
        return argv, env, transport, "timeout", "The decision model did not answer in 0.2 s."
    if kind == "timeout-mock":
        transport = httpx.MockTransport(_read_timeout)
        return argv, env, transport, "timeout", "The decision model did not answer in 5 s."
    if kind == "timeout-body":
        fake_server.body_stall_after = 10
        fake_server.body_stall = 1.0
        argv += ["--backend", fake_server.url]
        env["MAGIC8_TIMEOUT_MS"] = "200"
        return argv, env, transport, "timeout", "The decision model did not answer in 0.2 s."
    argv += ["--backend", fake_server.url]
    if kind.startswith("bad-encoding-"):
        # The status decides the case; a 2xx body that can't be decoded is a bad response.
        fake_server.status = int(kind[-3:])
        fake_server.headers = {"Content-Encoding": "gzip"}
        fake_server.body = b"not gzip"
        if fake_server.status == 401:
            message = "The decision model rejected the API key. Check MAGIC8_API_KEY."
            return argv, env, transport, "auth", message
        if fake_server.status == 500:
            message = "The decision model returned an error (HTTP 500)."
            return argv, env, transport, "http_error", message
        return argv, env, transport, "bad_response", BAD_RESPONSE_MESSAGE
    if kind in ("auth-401", "auth-403"):
        fake_server.status = int(kind[-3:])
        message = "The decision model rejected the API key. Check MAGIC8_API_KEY."
        return argv, env, transport, "auth", message
    if kind == "http-500":
        fake_server.status = 500
        fake_server.body = b"model exploded"
        message = "The decision model returned an error (HTTP 500)."
        return argv, env, transport, "http_error", message
    if kind == "bad-json":
        fake_server.body = b"this is not json"
    elif kind == "bad-shape":
        fake_server.body = {"answers": {}}
    elif kind == "deep-json":
        fake_server.body = b"[" * 100_000 + b"]" * 100_000
    else:  # pragma: no cover
        raise AssertionError(kind)
    return argv, env, transport, "bad_response", BAD_RESPONSE_MESSAGE


KINDS = [
    "unreachable-other",
    "unreachable-default",
    "timeout-server",
    "timeout-mock",
    "timeout-body",
    "auth-401",
    "auth-403",
    "http-500",
    "bad-json",
    "bad-shape",
    "deep-json",
    "bad-encoding-200",
    "bad-encoding-500",
    "bad-encoding-401",
]


@pytest.mark.parametrize("kind", KINDS)
def test_backend_errors(kind, run_cli, fake_server, closed_port_url, answer_rows):
    argv, env, transport, _, message = make_scenario(kind, fake_server, closed_port_url)
    code, out, err = run_cli(*argv, env=env, transport=transport)
    assert code == 2
    assert message in err
    for _, text, _ in answer_rows:
        assert text not in out
        assert text not in err


@pytest.mark.parametrize("kind", KINDS)
def test_backend_errors_json(kind, run_cli, fake_server, closed_port_url, answer_rows):
    argv, env, transport, error_code, message = make_scenario(kind, fake_server, closed_port_url)
    code, out, err = run_cli(*argv, "--json", env=env, transport=transport)
    assert code == 2
    assert len(out.strip().splitlines()) == 1
    assert json.loads(out) == {"error": error_code, "message": message}
    assert message in err
    for _, text, _ in answer_rows:
        assert text not in out
        assert text not in err


# Base URLs that pass the SPEC 6 rules but whose host or path can't be encoded.
UNENCODABLE_URLS = [
    pytest.param("http://xn--zz", id="bad-a-label"),
    pytest.param("http://xn--", id="empty-a-label"),
    pytest.param("http://a..b", id="empty-label"),
    pytest.param("http://.", id="dot"),
    pytest.param("http://..", id="two-dots"),
    pytest.param("http://a" + "b" * 70 + ".test", id="label-over-63"),
    pytest.param("http://a/\udcff", id="surrogate-in-path"),
]


@pytest.mark.parametrize("url", UNENCODABLE_URLS)
def test_unencodable_backend_url_is_unreachable(run_cli, url):
    code, out, err = run_cli("Will it rain?", "--backend", url, "--json")
    message = f"Can't reach the decision model at {url}."
    assert code == 2
    assert json.loads(out) == {"error": "unreachable", "message": message}
    assert message in err


@pytest.mark.parametrize("url", UNENCODABLE_URLS)
def test_unencodable_env_base_url_is_unreachable(run_cli, url):
    code, out, err = run_cli("Will it rain?", env={"MAGIC8_BASE_URL": url})
    assert code == 2
    assert out == ""
    assert f"Can't reach the decision model at {url}." in err


def test_server_detail_hidden_without_verbose(run_cli, fake_server):
    fake_server.status = 500
    fake_server.body = b"model exploded"
    _, _, err = run_cli("q?", "--backend", fake_server.url)
    assert "model exploded" not in err


def test_server_detail_shown_with_verbose(run_cli, fake_server):
    fake_server.status = 500
    fake_server.body = b"model exploded"
    code, _, err = run_cli("q?", "--backend", fake_server.url, "--verbose")
    assert code == 2
    assert "The decision model returned an error (HTTP 500)." in err
    assert "model exploded" in err
