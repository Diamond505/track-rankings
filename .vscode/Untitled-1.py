def countdown(n):
    # Base case – when to stop
    if n == 0:
        print("Blast off!")
    else:
        print(n)
        countdown(n - 1)  # Recursive call

countdown(5)