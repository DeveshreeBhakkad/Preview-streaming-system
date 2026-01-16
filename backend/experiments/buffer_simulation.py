from collections import deque

#buffer config
BACKWARD_LIMIT = 2
FORWARD_LIMIT = 2

#this deque will store chunk id
buffer = deque()

current_chunk = 1

#initial buffer fill
buffer.append(1) #current
buffer.append(2) #forward
buffer.append(3) #forward

print("Initial buffer:",list(buffer))

def move_to_next_chunk():
    global current_chunk

    current_chunk +=1
    buffer.append(current_chunk + FORWARD_LIMIT)

    #enforce backward buffer limit

    while len(buffer) > (BACKWARD_LIMIT + 1 + FORWARD_LIMIT):
        removed = buffer.popleft()
        print(f"Removed old chunk: C{removed}")

    print(f"Now playing : C{current_chunk}")
    print("Buffer state:",list(buffer))
    print("-" * 40)

for _ in range(5):
    move_to_next_chunk()
        
