"""Person 3 (<name>): run all tasks under each memory condition, log results and cost, and plot them."""


def run_condition(condition: str, memory, tasks: list[dict]) -> list[dict]:
    raise NotImplementedError


def plot_results(results_dir: str, out_path: str) -> None:
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
