# Demo: Real-time table output with tabulate and prettytable
import time
import os
from tabulate import tabulate
from prettytable import PrettyTable

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def tabulate_demo():
    headers = ["Sheet", "Row", "Host", "Result", "Reason"]
    table_data = []
    tests = [
        ("Sheet1", 1, "host1", "PASS", ""),
        ("Sheet1", 2, "host2", "FAIL", "Pattern not found"),
        ("Sheet2", 1, "host1", "PASS", ""),
        ("Sheet2", 2, "host2", "PASS", ""),
    ]
    def on_test_complete(row):
        table_data.append(row)
        clear()
        print("TABULATE DEMO (real-time update)")
        print(tabulate(table_data, headers=headers, tablefmt="github"))
    for row in tests:
        # Simulate test completion event
        on_test_complete(row)

def prettytable_demo():
    x = PrettyTable()
    x.field_names = ["Sheet", "Row", "Host", "Result", "Reason"]
    tests = [
        ("Sheet1", 1, "host1", "PASS", ""),
        ("Sheet1", 2, "host2", "FAIL", "Pattern not found"),
        ("Sheet2", 1, "host1", "PASS", ""),
        ("Sheet2", 2, "host2", "PASS", ""),
    ]
    def on_test_complete(row):
        x.add_row(row)
        clear()
        print("PRETTYTABLE DEMO (real-time update)")
        print(x)
    for row in tests:
        # Simulate test completion event
        on_test_complete(row)

if __name__ == "__main__":
    print("Testing tabulate...")
    tabulate_demo()
    print("Testing prettytable...")
    prettytable_demo()
