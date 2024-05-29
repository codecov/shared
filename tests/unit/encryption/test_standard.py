from shared.encryption.standard import StandardEncryptor


def test_standard_encryptor():
    se = StandardEncryptor(
        "part1", "part2", iv=b"\xe7\xdf\x12i&`\x9f:\xce\x97\x99\xdf\xd5\xe3\xcd\x8c"
    )
    word_to_encode = "mykey123456"
    res = se.encode(word_to_encode)
    assert res == b"598SaSZgnzrOl5nf1ePNjP9mdoj6hma717YLPiIxbCs="
    assert se.decode(res) == word_to_encode


def test_standard_encryptor_one_part():
    se = StandardEncryptor(
        "part1", iv=b"\xb5\xfa\xc7!\xd2\x8b\x1c\x06\xf0\x1c\xa2\\\xfe\x9e\xa8\x1d"
    )
    oe = StandardEncryptor(
        "part1", iv=b"\xb5\xfa\xc7!\xd2\x8b\x1c\x06\xf0\x1c\xa2\\\xfe\x9e\xa8\x1d"
    )
    word_to_encode = "somekey9865321"
    res = se.encode(word_to_encode)
    assert res == oe.encode(word_to_encode)
    assert se.decode(res) == word_to_encode
    assert se.decode(res) == oe.decode(res)


def test_standard_encryptor_three_parts():
    se = StandardEncryptor(
        "part1",
        "fnudbashbdsahbdahbcdcsc  cxcx",
        "dadsadbiyygweereeier",
        iv=b"\x14\x8c\x9e\xd8\xa1\xc5\xff\x1d\x9e[\xd7\x05K\t\xf4\x95",
    )
    word_to_encode = "mydsdbsdbebehbewbew123456"
    res = se.encode(word_to_encode)
    assert res == b"FIye2KHF/x2eW9cFSwn0lYV5MKCIr8o/Gr2/nBgat1Kb0D256PFNxphi5PfFXrCF"
    assert se.decode(res) == word_to_encode


def test_standard_encryptor_no_iv():
    se = StandardEncryptor("part1")
    assert se.decode(se.encode("mykey123456")) == "mykey123456"


def test_decrypt_token():
    value = "jd3ewr8cndsbc-0wr$"
    se = StandardEncryptor("aruba", "jamaica")
    encoded = se.encode(value)
    res = se.decrypt_token(encoded)
    assert res == {"key": "jd3ewr8cndsbc-0wr$", "secret": None}


def test_decrypt_token_key_secret_pair():
    value = "jd3ewr8cnd:sbc-0wr$"
    se = StandardEncryptor("aruba", "jamaica")
    encoded = se.encode(value)
    res = se.decrypt_token(encoded)
    assert res == {"key": "jd3ewr8cnd", "secret": "sbc-0wr$"}


def test_decrypt_token_key_secret_pair_refresh():
    value = "jd3ewr8cnd: :sbc-0wr$"
    se = StandardEncryptor("aruba", "jamaica")
    encoded = se.encode(value)
    res = se.decrypt_token(encoded)
    assert res == {"key": "jd3ewr8cnd", "refresh_token": "sbc-0wr$", "secret": None}
