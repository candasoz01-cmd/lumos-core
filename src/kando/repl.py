from kando.llm import llm

EXIT_WORDS = {"exit", "quit", "q", "çık", "cik"}

def main() -> None:
    while True:
        try:
            history = globals().get("_hist", [])
            user_input = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in EXIT_WORDS:
            print("OK")
            break

        history.append(user_input)
        history = history[-2:]
        globals()["_hist"] = history
        context = "\n".join(history)
        response = llm(context)
        print(response)

if __name__ == "__main__":
    main()
