"""Reproduce the XGBoost result and test strict verifier rejection."""

from benchmarks.embench.run import (
    HERE,
    command,
    path_parser,
    prepare_paths,
    read_yaml,
    write_json,
)


def main() -> None:
    """Check the native result and reject incorrect results."""
    parser = path_parser(__doc__)
    args = prepare_paths(parser)
    source = args.upstream.resolve() / "src/xgboost"
    expected = read_yaml(HERE / "suite.yaml")["exact_results"]["xgboost"]
    executable = args.output / "xgboost-reference"
    log = args.output / "oracle.log"
    command(
        [
            "gcc",
            "-O2",
            "-std=gnu17",
            "-DGLOBAL_SCALE_FACTOR=1",
            "-DEMBENCH_EXPECTED_CORRECT=" + str(expected),
            "-Wl,--wrap=verify_benchmark",
            str(source / "testbench.c"),
            str(source / "xgboost.c"),
            str(HERE / "xgboost_guard.c"),
            str(HERE / "xgboost_reference.c"),
            "-o",
            str(executable),
        ],
        args.output,
        log,
    )
    command([str(executable)], args.output, log)
    write_json(
        args.output / "oracle-check.json",
        {
            "status": "pass",
            "correct_classifications": expected,
            "samples": 128,
            "zero_and_off_by_one_rejected": True,
            "host_timing_used_for_score": False,
        },
    )


if __name__ == "__main__":
    main()
