def test_folder_overlap(count_a, count_b, mtime_a, mtime_b):
    min_c = min(count_a, count_b)
    max_c = max(count_a, count_b)
    if max_c > 0 and (min_c / max_c) >= 0.8:
        print("Similar count -> earliest")
        if mtime_a <= mtime_b:
            print("Delete A")
        else:
            print("Delete B")
    else:
        print("Different count -> fewest")
        if count_a < count_b:
            print("Delete A")
        elif count_b < count_a:
            print("Delete B")
        else:
            print("Delete earliest")
            if mtime_a <= mtime_b:
                print("Delete A")
            else:
                print("Delete B")

test_folder_overlap(10, 20, 100, 200) # A has 10, B has 20. Diff count -> delete fewest -> Delete A
test_folder_overlap(18, 20, 100, 200) # A has 18, B has 20. Similar count (0.9) -> delete earliest (100) -> Delete A
test_folder_overlap(18, 20, 200, 100) # Similar -> delete earliest -> Delete B
