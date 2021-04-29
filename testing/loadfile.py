from ribs import parse_report, SimpleAnalyzer
from time import time
import random
import string
import statistics
chars = string.ascii_uppercase + string.digits


def random_string():
    return ''.join(random.choice(chars) for _ in range(10))


if __name__ == "__main__":
    filenames_array = [random_string() for i in range(4004)]
    filenames = {name: i for (i, name) in enumerate(filenames_array)}
    session_mapping = {1: ["flagone"]}
    filename = "/chunks.txt"
    with open(filename, "r") as file:
        chunks = file.read()
    took_array = []
    print(len(chunks))
    print("Starting parsing")
    for i in range(30):
        now = time()
        res = parse_report(filenames, chunks, session_mapping)
        took_array.append(time() - now)
    print(took_array)
    print("Mean", statistics.mean(took_array))
    print("Stdev", statistics.stdev(took_array))
    print("Quantiles", statistics.quantiles(took_array))
    s = SimpleAnalyzer()
    print(s.get_totals(res).asdict())
