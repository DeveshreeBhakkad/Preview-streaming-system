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

