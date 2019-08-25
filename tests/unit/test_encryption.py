from covreports.encryption import StandardEncryptor
from covreports.encryption.old_encryptor import OldEncryptor


def test_standard_encryptor():
    se = StandardEncryptor(
        'part1', 'part2', iv=b'\xe7\xdf\x12i&`\x9f:\xce\x97\x99\xdf\xd5\xe3\xcd\x8c'
    )
    oe = OldEncryptor(
        'part1', 'part2', iv=b'\xe7\xdf\x12i&`\x9f:\xce\x97\x99\xdf\xd5\xe3\xcd\x8c'
    )
    word_to_encode = 'mykey123456'
    res = se.encode(word_to_encode)
    assert res == oe.encode(word_to_encode)
    assert se.decode(res) == word_to_encode
    assert se.decode(res) == oe.decode(res)


def test_standard_encryptor_one_part():
    se = StandardEncryptor('part1', iv=b'\xb5\xfa\xc7!\xd2\x8b\x1c\x06\xf0\x1c\xa2\\\xfe\x9e\xa8\x1d')
    oe = StandardEncryptor('part1', iv=b'\xb5\xfa\xc7!\xd2\x8b\x1c\x06\xf0\x1c\xa2\\\xfe\x9e\xa8\x1d')
    word_to_encode = 'somekey9865321'
    res = se.encode(word_to_encode)
    assert res == oe.encode(word_to_encode)
    assert se.decode(res) == word_to_encode
    assert se.decode(res) == oe.decode(res)


def test_standard_encryptor_three_parts():
    se = StandardEncryptor(
        'part1', 'fnudbashbdsahbdahbcdcsc  cxcx', 'dadsadbiyygweereeier',
        iv=b'\x14\x8c\x9e\xd8\xa1\xc5\xff\x1d\x9e[\xd7\x05K\t\xf4\x95'
    )
    oe = OldEncryptor(
        'part1', 'fnudbashbdsahbdahbcdcsc  cxcx', 'dadsadbiyygweereeier',
        iv=b'\x14\x8c\x9e\xd8\xa1\xc5\xff\x1d\x9e[\xd7\x05K\t\xf4\x95'
    )
    word_to_encode = 'mydsdbsdbebehbewbew123456'
    res = se.encode(word_to_encode)
    assert res == oe.encode(word_to_encode)
    assert se.decode(res) == word_to_encode
    assert se.decode(res) == oe.decode(res)


def test_standard_encryptor_no_iv():
    se = StandardEncryptor('part1')
    assert se.decode(se.encode('mykey123456')) == 'mykey123456'
