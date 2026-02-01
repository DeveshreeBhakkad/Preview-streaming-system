def simple_stream():
    yield "Chunk 1"
    yield "Chunk 2"
    yield "Chunk 3"

if __name__ == "__main__":
    stream = simple_stream()

    print(next(stream))
    print(next(stream))
    print(next(stream))


import time 

def timed_stream():
    for i in range(1,6):
        time.sleep(1)
        yield f"Chunk {i}"

if __name__ == "__main__":
    for chunk in timed_stream():
        print(chunk)

def preview():
    for sec in range(3):
        yield f"Playing second {sec}"


