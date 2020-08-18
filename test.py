t = int(input())
for i in range(t):
    n = int(input())
    res = []
    arr = input("")    
    nums = [int(n) for n in arr.split()] 
    for num in nums:
        cnt = 0
        while num:
            num = num & (num - 1)
            cnt += 1
        res.append(cnt)
    print(len(set(res)))