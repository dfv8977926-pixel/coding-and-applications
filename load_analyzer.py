from pathlib import Path
import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CSV_PATH = Path(__file__).with_name("load_data.csv")
RESULT_PATH = Path(__file__).with_name("load_result.csv")
PLOT_PATH = Path(__file__).with_name("stress_plot.png")
REQUIRED_COLUMNS = {"time_s", "force_N"}


def analyze_load_data(
    csv_path: Path, result_path: Path, area_mm2: float
) -> tuple[int, float, float, float, float]:
    """Save stress results and return count, maximum load and stress with times."""
    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"필수 열이 없습니다: {missing}")

        fieldnames = reader.fieldnames
        result_rows = []
        data_count = 0
        maximum_force = float("-inf")
        maximum_force_time = 0.0
        maximum_stress = float("-inf")
        maximum_stress_time = 0.0
        for row in reader:
            time = float(row["time_s"])
            force = float(row["force_N"])
            stress = force / area_mm2
            row["stress_MPa"] = stress
            result_rows.append(row)
            data_count += 1
            if force > maximum_force:
                maximum_force = force
                maximum_force_time = time
            if stress > maximum_stress:
                maximum_stress = stress
                maximum_stress_time = time

    if data_count == 0:
        raise ValueError("CSV 파일에 데이터가 없습니다.")

    with result_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=[*fieldnames, "stress_MPa"]
        )
        writer.writeheader()
        writer.writerows(result_rows)

    return (
        data_count,
        maximum_force,
        maximum_force_time,
        maximum_stress,
        maximum_stress_time,
    )


def save_stress_plot(result_path: Path, plot_path: Path) -> None:
    with result_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        time_values = [float(row["time_s"]) for row in reader]

    with result_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        stress_values = [float(row["stress_MPa"]) for row in reader]

    figure, axis = plt.subplots()
    axis.plot(time_values, stress_values, marker="o")
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Stress (MPa)")
    figure.savefig(plot_path)
    plt.close(figure)


def main() -> None:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}")

    area_mm2 = 200
    (
        data_count,
        maximum_force,
        maximum_force_time,
        maximum_stress,
        maximum_stress_time,
    ) = analyze_load_data(CSV_PATH, RESULT_PATH, area_mm2)
    save_stress_plot(RESULT_PATH, PLOT_PATH)
    print(f"데이터 개수: {data_count}개")
    print(f"최대 하중: {maximum_force:g} N")
    print(f"최대 하중 해당 시간: {maximum_force_time:g} s")
    print(f"최대 응력: {maximum_stress:g} MPa")
    print(f"최대 응력 해당 시간: {maximum_stress_time:g} s")
    print(f"응력 결과 저장: {RESULT_PATH}")
    print(f"응력 그래프 저장: {PLOT_PATH}")


if __name__ == "__main__":
    main()
