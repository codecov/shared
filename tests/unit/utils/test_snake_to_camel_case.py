from shared.utils.snake_to_camel_case import snake_to_camel_case


def test_single_word():
    assert snake_to_camel_case("hello") == "hello"


def test_empty_string():
    assert snake_to_camel_case("") == ""


def test_two_words():
    assert snake_to_camel_case("hello_world") == "helloWorld"


def test_many_words():
    assert (
        snake_to_camel_case("hello_world_codecov_is_cool") == "helloWorldCodecovIsCool"
    )
