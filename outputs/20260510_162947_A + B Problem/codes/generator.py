import random
import sys

def generate():
    # 生成在范围内的随机整数 A 和 B
    A = random.randint(-1000, 1000)
    B = random.randint(-1000, 1000)
    # 输出到标准输出,可直接重定向为输入文件
    print(A, B)

if __name__ == "__main__":
    generate()
