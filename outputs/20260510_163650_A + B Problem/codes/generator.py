import random

A = random.randint(-1000, 1000)
B = random.randint(-1000, 1000)
# 以一定概率产生边界值
if random.random() < 0.2:
    A = random.choice([-1000, 0, 1000])
    B = random.choice([-1000, 0, 1000])
print(A, B)