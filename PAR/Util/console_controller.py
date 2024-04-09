import os
import time

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_large_text():
    large_text = [
        "██████╗ ███████╗     ██████╗ █████╗ ██████╗ ███████╗███████╗██╗   ██╗██╗     ██╗     ",
        "██╔══██╗██╔════╝    ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██║   ██║██║     ██║     ",
        "██████╔╝█████╗      ██║     ███████║██████╔╝█████╗  █████╗  ██║   ██║██║     ██║     ",
        "██╔══██╗██╔══╝      ██║     ██╔══██║██╔══██╗██╔══╝  ██╔══╝  ██║   ██║██║     ██║     ",
        "██████╔╝███████╗    ╚██████╗██║  ██║██║  ██║███████╗██║     ╚██████╔╝███████╗███████╗",
        "╚═════╝ ╚══════╝     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚══════╝╚══════╝"
    ]

    for line in large_text:
        print(line)


def print_see_you_again():
    see_you_again_text = [
        " ██████╗███████╗███████╗    ██╗   ██╗ ██████╗ ██╗   ██╗     █████╗  ██████╗  █████╗ ██╗███╗   ██╗",
        "██╔════╝██╔════╝██╔════╝    ╚██╗ ██╔╝██╔═══██╗██║   ██║    ██╔══██╗██╔════╝ ██╔══██╗██║████╗  ██║",
        "███████╗█████╗  █████╗       ╚████╔╝ ██║   ██║██║   ██║    ███████║██║  ███╗███████║██║██╔██╗ ██║",
        "╚════██║██╔══╝  ██╔══╝        ╚██╔╝  ██║   ██║██║   ██║    ██╔══██║██║   ██║██╔══██║██║██║╚██╗██║",
        "███████║███████╗███████╗       ██║   ╚██████╔╝╚██████╔╝    ██║  ██║╚██████╔╝██║  ██║██║██║ ╚████║",
        "╚══════╝╚══════╝╚══════╝       ╚═╝    ╚═════╝  ╚═════╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝"
    ]

    for line in see_you_again_text:
        print(line)


def print_warning_text(text):
    print("=" * 80)
    print("|" + " " * 78 + "|")
    print("|" + text.center(78) + "|")
    print("|" + " " * 78 + "|")
    print("=" * 80)

def print_warning_message():
    clear_console()
    print("\033[91m")  # ANSI escape code for red color
    print_large_text()
    print("\033[0m")  # ANSI escape code to reset color
    print()
    print("\033[93m")
    print_warning_text("THIS PROJECT IS USING SO MANY TOKENS")
    print("\033[0m")

    print("\033[93m")
    print_warning_text("YOUR ANTHROPIC ACCOUNT TIER MUST BE OVER THAN TIER 2")
    print("\033[0m")

    # print_warning_text("MAKE SURE YOU KNOW WHAT YOU ARE DOING.")
    print()
    time.sleep(1)
    print("\033[93m")  # ANSI escape code for yellow color
    print_warning_text("ARE YOU SURE YOU WANT TO RUN THIS PROJECT?")
    print("\033[0m")  # ANSI escape code to reset color
    print()