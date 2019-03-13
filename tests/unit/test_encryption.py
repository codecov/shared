from covreports.encryption import StandardEncryptor


def test_standard_encryptor():
    se = StandardEncryptor('part1', 'part2')
    res = se.encode('mykey123456')
    assert se.decode(res) == 'mykey123456'


def test_standard_encryptor_one_part():
    se = StandardEncryptor('part1')
    res = se.encode('mykey123456')
    assert se.decode(res) == 'mykey123456'


def test_standard_encryptor_three_parts():
    se = StandardEncryptor('part1', 'fnudbashbdsahbdahbcdcsc  cxcx', 'dadsadbiyygweereeier')
    res = se.encode('mykey123456')
    assert se.decode(res) == 'mykey123456'
