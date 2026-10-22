"""SPEC section 6: configuration."""

from pathlib import Path

import pytest

from magic8.config import ConfigError, load_config, read_dotenv


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_without_env_or_dotenv(tmp_path):
    for dotenv in (None, tmp_path / ".env"):
        cfg = load_config({}, dotenv)
        assert cfg.base_url == "http://127.0.0.1:8000"
        assert cfg.api_key is None
        assert cfg.model is None
        assert cfg.timeout_ms == 5000


def test_env_vars_are_read():
    cfg = load_config(
        {
            "MAGIC8_BASE_URL": "http://example.test:9",
            "MAGIC8_API_KEY": "k",
            "MAGIC8_MODEL": "m",
            "MAGIC8_TIMEOUT_MS": "2500",
        },
        None,
    )
    assert (cfg.base_url, cfg.api_key, cfg.model, cfg.timeout_ms) == (
        "http://example.test:9",
        "k",
        "m",
        2500,
    )


def test_dotenv_file_is_read(tmp_path):
    path = write_env(
        tmp_path,
        "MAGIC8_BASE_URL=http://dotenv.test\nMAGIC8_API_KEY=dk\n"
        "MAGIC8_MODEL=dm\nMAGIC8_TIMEOUT_MS=1234\n",
    )
    cfg = load_config({}, path)
    assert (cfg.base_url, cfg.api_key, cfg.model, cfg.timeout_ms) == (
        "http://dotenv.test",
        "dk",
        "dm",
        1234,
    )


def test_real_env_wins_over_dotenv(tmp_path):
    path = write_env(tmp_path, "MAGIC8_MODEL=from-dotenv\nMAGIC8_API_KEY=dotenv-key\n")
    cfg = load_config({"MAGIC8_MODEL": "from-env"}, path)
    assert cfg.model == "from-env"
    assert cfg.api_key == "dotenv-key"


def test_kwargs_win_over_env_and_dotenv(tmp_path):
    path = write_env(tmp_path, "MAGIC8_BASE_URL=http://dotenv.test\nMAGIC8_MODEL=dm\n")
    env = {"MAGIC8_BASE_URL": "http://env.test", "MAGIC8_MODEL": "em"}
    cfg = load_config(env, path, base_url="http://flag.test", model="fm")
    assert cfg.base_url == "http://flag.test"
    assert cfg.model == "fm"


def test_empty_or_none_kwargs_fall_back(tmp_path):
    env = {"MAGIC8_BASE_URL": "http://env.test", "MAGIC8_MODEL": "em"}
    cfg = load_config(env, None, base_url="", model=None)
    assert cfg.base_url == "http://env.test"
    assert cfg.model == "em"


def test_empty_values_mean_unset(tmp_path):
    path = write_env(tmp_path, "MAGIC8_API_KEY=\n")
    env = {"MAGIC8_MODEL": "", "MAGIC8_BASE_URL": "", "MAGIC8_TIMEOUT_MS": ""}
    cfg = load_config(env, path)
    assert cfg.model is None
    assert cfg.api_key is None
    assert cfg.base_url == "http://127.0.0.1:8000"
    assert cfg.timeout_ms == 5000


def test_empty_env_value_shadows_dotenv_as_unset(tmp_path):
    # The real environment wins even when its value is empty ("not set").
    path = write_env(tmp_path, "MAGIC8_MODEL=dm\n")
    assert load_config({"MAGIC8_MODEL": ""}, path).model is None


@pytest.mark.parametrize(
    ("name", "dotenv_value", "attr", "expected"),
    [
        ("MAGIC8_BASE_URL", "http://dotenv.test", "base_url", "http://127.0.0.1:8000"),
        ("MAGIC8_API_KEY", "dotenv-key", "api_key", None),
        ("MAGIC8_MODEL", "dm", "model", None),
        ("MAGIC8_TIMEOUT_MS", "1234", "timeout_ms", 5000),
    ],
)
def test_empty_env_value_hides_dotenv(tmp_path, name, dotenv_value, attr, expected):
    path = write_env(tmp_path, f"{name}={dotenv_value}\n")
    cfg = load_config({name: ""}, path)
    assert getattr(cfg, attr) == expected


@pytest.mark.parametrize(
    ("name", "bad_value"),
    [
        ("MAGIC8_BASE_URL", "ftp://x"),
        ("MAGIC8_API_KEY", "clé"),
        ("MAGIC8_TIMEOUT_MS", "abc"),
    ],
)
def test_empty_env_value_hides_invalid_dotenv_value(tmp_path, name, bad_value):
    path = write_env(tmp_path, f"{name}={bad_value}\n")
    assert load_config({name: ""}, path) is not None


def test_empty_env_base_url_hides_dotenv_via_cli(run_cli, tmp_path):
    write_env(tmp_path, "MAGIC8_BASE_URL=ftp://from-dotenv\nMAGIC8_TIMEOUT_MS=abc\n")
    code, _, err = run_cli(
        "Will it rain?",
        env={"MAGIC8_BASE_URL": "", "MAGIC8_TIMEOUT_MS": ""},
    )
    assert code != 1
    assert "MAGIC8_BASE_URL" not in err
    assert "MAGIC8_TIMEOUT_MS" not in err


def test_dotenv_parsing(tmp_path):
    path = write_env(
        tmp_path,
        "# a comment\n"
        "\n"
        "   \n"
        'MAGIC8_API_KEY="quoted key"\n'
        "MAGIC8_MODEL='single'\n"
        "export MAGIC8_BASE_URL=http://exported.test\n"
        "  MAGIC8_TIMEOUT_MS = 777  \n"
        "no equals sign here\n"
        "WITH_EQ=a=b\n"
        "INLINE=value # not a comment\n"
        "MISMATCH=\"oops'\n",
    )
    values = read_dotenv(path)
    assert values["MAGIC8_API_KEY"] == "quoted key"
    assert values["MAGIC8_MODEL"] == "single"
    assert values["MAGIC8_BASE_URL"] == "http://exported.test"
    assert values["MAGIC8_TIMEOUT_MS"] == "777"
    assert values["WITH_EQ"] == "a=b"
    assert values["INLINE"] == "value # not a comment"
    assert values["MISMATCH"] == "\"oops'"
    assert "no equals sign here" not in values
    assert not any(k.startswith("#") for k in values)
    assert "" not in values


def test_read_dotenv_missing_file(tmp_path):
    assert read_dotenv(tmp_path / "nope.env") == {}


def test_trailing_slash_stripped():
    assert load_config({"MAGIC8_BASE_URL": "http://x.test/"}, None).base_url == "http://x.test"
    assert load_config({}, None, base_url="http://y.test/").base_url == "http://y.test"


def url_message(rule, name, raw):
    messages = {
        "R1": f"{name} must not hold spaces or control characters, got {raw!r}.",
        "R2": f"{name} must start with http:// or https://, got {raw!r}.",
        "R3": f"{name} must not hold a query (?) or a fragment (#), got {raw!r}.",
        "R4": f"{name} must have a host, got {raw!r}.",
        "R5": f"{name} must have a port from 1 to 65535, got {raw!r}.",
    }
    return messages[rule]


@pytest.mark.parametrize(
    ("raw", "rule"),
    [
        (" http://x.test", "R1"),
        ("http://x.test ", "R1"),
        ("http://x test", "R1"),
        ("http://x.test\n", "R1"),
        ("http://x.test\t", "R1"),
        ("http://x.test\x00", "R1"),
        ("http://x.test\x7f", "R1"),
        ("localhost:8000", "R2"),
        ("127.0.0.1:8000", "R2"),
        ("x.test", "R2"),
        ("ftp://x.test", "R2"),
        ("file:///etc", "R2"),
        ("mailto:a@b.test", "R2"),
        ("http:x.test", "R2"),
        ("http:/x.test", "R2"),
        ("http//x.test", "R2"),
        ("//x.test", "R2"),
        ("httpx://x.test", "R2"),
        ("http://x.test?q=1", "R3"),
        ("http://x.test/#frag", "R3"),
        ("http://?q", "R3"),
        ("http://", "R4"),
        ("https://", "R4"),
        ("http:///path", "R4"),
        ("https://:80", "R4"),
        ("http://user@", "R4"),
        ("http://u@:9", "R4"),
        ("http://[::1", "R4"),
        ("http://[]:80", "R4"),
        ("http://[::1]x", "R4"),
        ("http://::1", "R4"),
        ("http://x.test:abc", "R5"),
        ("http://x.test:0", "R5"),
        ("http://x.test:65536", "R5"),
        ("http://x.test:99999999999999999999", "R5"),
        ("http://x.test:-1", "R5"),
        ("http://x.test:+80", "R5"),
        ("http://x.test:\u0668\u0660", "R5"),
        ("http://x.test:1:2", "R5"),
        ("http://[::1]:0", "R5"),
    ],
    ids=[
        "leading-space",
        "trailing-space",
        "inner-space",
        "newline",
        "tab",
        "nul",
        "del",
        "no-scheme-host-port",
        "no-scheme-ip-port",
        "bare-host",
        "ftp",
        "file",
        "mailto",
        "no-slashes",
        "one-slash",
        "no-colon",
        "scheme-relative",
        "other-scheme",
        "query",
        "fragment",
        "query-no-host",
        "nothing-after-slashes",
        "https-nothing",
        "empty-host-with-path",
        "port-only",
        "userinfo-only",
        "userinfo-port-no-host",
        "ipv6-no-close",
        "ipv6-empty",
        "ipv6-junk-after-bracket",
        "ipv6-no-brackets",
        "port-letters",
        "port-zero",
        "port-too-big",
        "port-huge",
        "port-negative",
        "port-plus",
        "port-arabic-indic",
        "two-colons",
        "ipv6-port-zero",
    ],
)
def test_malformed_base_url_raises(raw, rule):
    with pytest.raises(ConfigError) as exc:
        load_config({}, None, base_url=raw)
    assert str(exc.value) == url_message(rule, "--backend", raw)
    with pytest.raises(ConfigError) as exc:
        load_config({"MAGIC8_BASE_URL": raw}, None)
    assert str(exc.value) == url_message(rule, "MAGIC8_BASE_URL", raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://127.0.0.1:8000", "http://127.0.0.1:8000"),
        ("https://api.example.test", "https://api.example.test"),
        ("HTTPS://X.TEST", "HTTPS://X.TEST"),
        ("HtTp://x.test", "HtTp://x.test"),
        ("http://x.test/", "http://x.test"),
        ("http://x.test///", "http://x.test"),
        ("https://example.test/magic", "https://example.test/magic"),
        ("http://x.test:", "http://x.test:"),
        ("http://x.test:1", "http://x.test:1"),
        ("http://x.test:65535", "http://x.test:65535"),
        ("http://x.test:080", "http://x.test:080"),
        ("http://user:pw@x.test:9", "http://user:pw@x.test:9"),
        ("http://[::1]:8000", "http://[::1]:8000"),
        ("http://[::1]", "http://[::1]"),
        ("http://[::1]:", "http://[::1]:"),
        ("http://\u00e9.test", "http://\u00e9.test"),
    ],
    ids=[
        "ip-port",
        "https",
        "upper-case",
        "mixed-case",
        "trailing-slash",
        "trailing-slashes",
        "path",
        "empty-port",
        "port-min",
        "port-max",
        "port-leading-zero",
        "userinfo",
        "ipv6-port",
        "ipv6",
        "ipv6-empty-port",
        "non-ascii-host",
    ],
)
def test_valid_base_url_is_accepted(raw, expected):
    assert load_config({}, None, base_url=raw).base_url == expected
    assert load_config({"MAGIC8_BASE_URL": raw}, None).base_url == expected


def test_malformed_base_url_from_dotenv_raises(tmp_path):
    path = write_env(tmp_path, "MAGIC8_BASE_URL=ftp://x.test\n")
    with pytest.raises(ConfigError) as exc:
        load_config({}, path)
    assert str(exc.value) == url_message("R2", "MAGIC8_BASE_URL", "ftp://x.test")


def test_flag_wins_so_bad_env_url_is_not_checked():
    cfg = load_config({"MAGIC8_BASE_URL": "ftp://x.test"}, None, base_url="http://ok.test")
    assert cfg.base_url == "http://ok.test"


def test_malformed_flag_url_raises_even_with_good_env():
    with pytest.raises(ConfigError) as exc:
        load_config({"MAGIC8_BASE_URL": "http://ok.test"}, None, base_url="ftp://x.test")
    assert str(exc.value) == url_message("R2", "--backend", "ftp://x.test")


@pytest.mark.parametrize(
    "raw",
    [
        "localhost:8000",
        "ftp://x.test",
        "http://",
        "http://x.test:abc",
        "http://x.test?q=1",
        " http://x.test",
    ],
)
def test_malformed_backend_flag_via_cli_exits_1_without_request(run_cli, raw):
    code, out, err = run_cli("Will it rain?", "--backend", raw)
    assert code == 1
    assert out == ""
    assert "--backend" in err
    assert "Can't reach" not in err


def test_malformed_backend_flag_with_json_exits_1_without_json_error(run_cli):
    code, out, err = run_cli("Will it rain?", "--json", "--backend", "ftp://x.test")
    assert code == 1
    assert out == ""
    assert "--backend" in err


@pytest.mark.parametrize("raw", ["localhost:8000", "https://"])
def test_malformed_env_base_url_via_cli_exits_1(run_cli, raw):
    code, out, err = run_cli("Will it rain?", env={"MAGIC8_BASE_URL": raw})
    assert code == 1
    assert out == ""
    assert "MAGIC8_BASE_URL" in err
    assert "Can't reach" not in err


def test_valid_backend_flag_reaches_server(run_cli, fake_server):
    code, _, _ = run_cli("Will it rain?", "--backend", fake_server.url + "/")
    assert code == 0
    assert len(fake_server.requests) == 1


def test_well_formed_unreachable_url_is_backend_error(run_cli, closed_port_url):
    url = closed_port_url()
    code, _, err = run_cli("Will it rain?", "--backend", "HTTP://" + url[len("http://") :])
    assert code == 2
    assert "Can't reach the decision model at" in err


def test_valid_timeout():
    assert load_config({"MAGIC8_TIMEOUT_MS": "1"}, None).timeout_ms == 1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", 1), ("007", 7), ("5000", 5000), ("2147483646", 2147483646)],
)
def test_timeout_accepts_ascii_digits(raw, expected):
    assert load_config({"MAGIC8_TIMEOUT_MS": raw}, None).timeout_ms == expected


def test_quoted_dotenv_timeout_keeps_spaces_and_is_rejected(tmp_path):
    path = write_env(tmp_path, 'MAGIC8_TIMEOUT_MS=" 5000 "\n')
    with pytest.raises(ConfigError):
        load_config({}, path)


def test_unquoted_dotenv_timeout_spaces_are_not_part_of_value(tmp_path):
    path = write_env(tmp_path, "MAGIC8_TIMEOUT_MS= 5000 \n")
    assert load_config({}, path).timeout_ms == 5000


@pytest.mark.parametrize(
    "raw",
    [
        "abc",
        "0",
        "-5",
        "1.5",
        "-" + "9" * 5000,
        "0" * 5000,
        "9" * 5000 + "x",
        "9_" * 4300 + "_9",
        "9_" * 4301,
        "_" + "9" * 4301,
        "5_000",
        "1_0",
        "+5",
        "-0",
        " 5000",
        "5000 ",
        " 5000 ",
        "5000\n",
        "\t5000",
        "\u0665\u0660\u0660\u0660",
        "\uff15\uff10\uff10\uff10",
        "\U0001d7d3",
        "\u00b2",
        "000",
        "0x10",
        "1e3",
        "9" * 4301 + " ",
    ],
    ids=[
        "letters",
        "zero",
        "negative",
        "fraction",
        "negative-5001-digits",
        "zero-5000-digits",
        "5000-digits-then-letter",
        "double-underscore-4301-digits",
        "trailing-underscore-4301-digits",
        "leading-underscore-4301-digits",
        "underscore",
        "underscore-short",
        "plus-sign",
        "minus-zero",
        "leading-space",
        "trailing-space",
        "spaces-both-ends",
        "trailing-newline",
        "leading-tab",
        "arabic-indic-digits",
        "fullwidth-digits",
        "math-bold-digit-5",
        "superscript-two",
        "zeros",
        "hex",
        "exponent",
        "4301-digits-trailing-space",
    ],
)
def test_bad_timeout_raises(raw):
    with pytest.raises(ConfigError) as exc:
        load_config({"MAGIC8_TIMEOUT_MS": raw}, None)
    assert str(exc.value) == (
        f"MAGIC8_TIMEOUT_MS must be digits 0-9 only, with a value above 0, got {raw!r}."
    )


@pytest.mark.parametrize(
    "raw", ["abc", "0", "-5", "5_000", "+5", " 5000 ", "\u0665\u0660\u0660\u0660"]
)
def test_bad_timeout_via_cli_exits_1(run_cli, closed_port_url, raw):
    code, out, err = run_cli(
        "Will it rain?",
        "--backend",
        closed_port_url(),
        env={"MAGIC8_TIMEOUT_MS": raw},
    )
    assert code == 1
    assert out == ""
    assert "MAGIC8_TIMEOUT_MS" in err


@pytest.mark.parametrize(
    "raw",
    [
        "99999999999999999999",
        "2147483647",
        "2147483648",
        "9" * 4301,
        "1" + "0" * 5000,
    ],
    ids=["huge", "max", "max-plus-1", "4301-digits", "5001-digits"],
)
def test_timeout_above_max_is_clamped(raw):
    assert load_config({"MAGIC8_TIMEOUT_MS": raw}, None).timeout_ms == 2147483647


def test_timeout_with_many_leading_zeros():
    assert load_config({"MAGIC8_TIMEOUT_MS": "0" * 5000 + "7"}, None).timeout_ms == 7


def test_huge_timeout_via_cli_is_clamped_not_rejected(run_cli, closed_port_url):
    url = closed_port_url()
    code, _, err = run_cli(
        "Will it rain?",
        "--backend",
        url,
        env={"MAGIC8_TIMEOUT_MS": "99999999999999999999"},
    )
    assert code == 2
    assert f"Can't reach the decision model at {url}." in err


@pytest.mark.parametrize("raw", ["9" * 4301], ids=["4301-digits"])
def test_timeout_beyond_int_digit_limit_via_cli_is_clamped_not_rejected(
    run_cli, closed_port_url, raw
):
    url = closed_port_url()
    code, _, err = run_cli(
        "Will it rain?",
        "--backend",
        url,
        env={"MAGIC8_TIMEOUT_MS": raw},
    )
    assert code == 2
    assert f"Can't reach the decision model at {url}." in err


API_KEY_MESSAGE = (
    "MAGIC8_API_KEY must hold only printable ASCII characters, with no space at the start or end."
)


@pytest.mark.parametrize(
    "key",
    ["clé", "tok\nen", "tok\ten", "\x7f", "abc ", " abc", "   "],
    ids=["non-ascii", "newline", "tab", "del", "trailing-space", "leading-space", "only-spaces"],
)
def test_api_key_must_be_printable_ascii(key):
    with pytest.raises(ConfigError) as exc:
        load_config({"MAGIC8_API_KEY": key}, None)
    assert str(exc.value) == API_KEY_MESSAGE


def test_api_key_from_dotenv_must_be_printable_ascii(tmp_path):
    path = write_env(tmp_path, "MAGIC8_API_KEY=clé\n")
    with pytest.raises(ConfigError) as exc:
        load_config({}, path)
    assert str(exc.value) == API_KEY_MESSAGE


def test_api_key_with_space_and_punctuation_is_valid():
    key = "abc DEF-123._~+/="
    assert load_config({"MAGIC8_API_KEY": key}, None).api_key == key


def test_bad_api_key_via_cli_exits_1_without_request(run_cli, fake_server):
    code, out, err = run_cli(
        "Will it rain?",
        "--backend",
        fake_server.url,
        env={"MAGIC8_API_KEY": "clé-secret"},
    )
    assert code == 1
    assert out == ""
    assert "MAGIC8_API_KEY" in err
    assert "clé-secret" not in err
    assert fake_server.requests == []


def test_api_key_with_trailing_space_via_cli_exits_1_without_request(run_cli, fake_server):
    code, out, err = run_cli(
        "Will it rain?",
        "--backend",
        fake_server.url,
        env={"MAGIC8_API_KEY": "abc "},
    )
    assert code == 1
    assert out == ""
    assert "MAGIC8_API_KEY" in err
    assert "Can't reach" not in err
    assert fake_server.requests == []
