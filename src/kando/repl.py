from kando.llm import llm

EXIT_WORDS = {"exit", "quit", "q", "çık", "cik"}

def main() -> None:
    while True:
        try:
            user_input = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in EXIT_WORDS:
            print("OK")
            break

        response = llm(user_input)
        print(response)

if __name__ == "__main__":
    main()
