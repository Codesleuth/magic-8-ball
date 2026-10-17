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


def test_valid_timeout():
    assert load_config({"MAGIC8_TIMEOUT_MS": "1"}, None).timeout_ms == 1


@pytest.mark.parametrize("raw", ["abc", "0", "-5", "1.5"])
def test_bad_timeout_raises(raw):
    with pytest.raises(ConfigError) as exc:
        load_config({"MAGIC8_TIMEOUT_MS": raw}, None)
    assert str(exc.value) == (
        f"MAGIC8_TIMEOUT_MS must be a positive whole number of milliseconds, got {raw!r}."
    )


@pytest.mark.parametrize("raw", ["abc", "0", "-5"])
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
    "raw", ["99999999999999999999", "2147483647", "2147483648"], ids=["huge", "max", "max-plus-1"]
)
def test_timeout_above_max_is_clamped(raw):
    assert load_config({"MAGIC8_TIMEOUT_MS": raw}, None).timeout_ms == 2147483647


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


API_KEY_MESSAGE = "MAGIC8_API_KEY must hold only printable ASCII characters."


@pytest.mark.parametrize(
    "key",
    ["clé", "tok\nen", "tok\ten", "\x7f"],
    ids=["non-ascii", "newline", "tab", "del"],
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
