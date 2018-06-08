def zfill(lst, index, value):
    ll = len(lst)
    if len(lst) <= index:
        lst.extend([None] * (index - ll + 1))
    lst[index] = value
    return lst
