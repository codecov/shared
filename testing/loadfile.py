from ribs import parse_report
from time import time
import random
import string

chars = string.ascii_uppercase + string.digits


def random_string():
    return ''.join(random.choice(chars) for _ in range(10))


if __name__ == "__main__":
    print("HAHAAHAHA")
    filenames_array = [random_string() for i in range(4004)]
    filenames = {name: i for (i, name) in enumerate(filenames_array)}
    session_mapping = {1: ["flagone"]}
    filename = "/chunks.txt"
    with open(filename, "r") as file:
        chunks = file.read()
    print(len(chunks))
    now = time()
    print("starting")
    res = parse_report(filenames, chunks, session_mapping)
    print("took", time() - now)
    print(res)
