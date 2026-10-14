import csv
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


REQUIRED_COLUMNS = {"time_s", "force_N"}
SECTION_FIELDS = {
    "사각형": (("b", "폭 b (mm)"), ("h", "높이 h (mm)")),
    "원형봉": (("d", "지름 d (mm)"),),
    "원형관": (("D", "외경 D (mm)"), ("t", "두께 t (mm)")),
    "사각형관": (
        ("B", "외측폭 B (mm)"),
        ("H", "외측높이 H (mm)"),
        ("t", "두께 t (mm)"),
    ),
    "H형강": (
        ("H", "전체높이 H (mm)"),
        ("B", "플랜지폭 B (mm)"),
        ("tw", "웨브두께 tw (mm)"),
        ("tf", "플랜지두께 tf (mm)"),
    ),
}


def read_load_data(
    csv_path: Path,
) -> tuple[list[float], list[float], int]:
    time_values = []
    force_values = []
    excluded_count = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"필수 열이 없습니다: {missing}")

        for row in reader:
            try:
                time = float(row["time_s"])
                force = float(row["force_N"])
            except (TypeError, ValueError, OverflowError):
                excluded_count += 1
                continue

            if not math.isfinite(time) or not math.isfinite(force):
                excluded_count += 1
                continue

            time_values.append(time)
            force_values.append(force)

    return time_values, force_values, excluded_count


def calculate_stress(
    force_values: list[float], area_mm2: float
) -> tuple[list[float], float, int]:
    if area_mm2 <= 0 or not math.isfinite(area_mm2):
        raise ValueError("단면적은 0보다 큰 유한한 값이어야 합니다.")

    stress_values = [force / area_mm2 for force in force_values]
    maximum_index = max(range(len(stress_values)), key=stress_values.__getitem__)
    return stress_values, stress_values[maximum_index], maximum_index


def calculate_section_area(section_type: str, dimensions: dict[str, float]) -> float:
    if section_type not in SECTION_FIELDS:
        raise ValueError("지원하지 않는 단면 종류입니다.")

    if any(not math.isfinite(value) or value <= 0 for value in dimensions.values()):
        raise ValueError("모든 치수는 0보다 큰 유한한 값이어야 합니다.")

    if section_type == "사각형":
        area = dimensions["b"] * dimensions["h"]
    elif section_type == "원형봉":
        area = math.pi * dimensions["d"] ** 2 / 4
    elif section_type == "원형관":
        outer_diameter = dimensions["D"]
        thickness = dimensions["t"]
        if 2 * thickness >= outer_diameter:
            raise ValueError("원형관은 2t < D 조건을 만족해야 합니다.")
        inner_diameter = outer_diameter - 2 * thickness
        area = math.pi * (outer_diameter**2 - inner_diameter**2) / 4
    elif section_type == "사각형관":
        outer_width = dimensions["B"]
        outer_height = dimensions["H"]
        thickness = dimensions["t"]
        if 2 * thickness >= outer_width or 2 * thickness >= outer_height:
            raise ValueError("사각형관은 2t < B, 2t < H 조건을 만족해야 합니다.")
        area = outer_width * outer_height - (outer_width - 2 * thickness) * (
            outer_height - 2 * thickness
        )
    else:
        total_height = dimensions["H"]
        flange_width = dimensions["B"]
        web_thickness = dimensions["tw"]
        flange_thickness = dimensions["tf"]
        if 2 * flange_thickness >= total_height:
            raise ValueError("H형강은 2tf < H 조건을 만족해야 합니다.")
        if web_thickness >= flange_width:
            raise ValueError("H형강은 tw < B 조건을 만족해야 합니다.")
        area = (
            2 * flange_width * flange_thickness
            + (total_height - 2 * flange_thickness) * web_thickness
        )

    if not math.isfinite(area) or area <= 0:
        raise ValueError("계산된 단면적이 유효하지 않습니다.")
    return area


class LoadAnalyzerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("하중 데이터 분석")
        self.root.geometry("900x700")
        self.root.minsize(680, 520)

        self.csv_path = tk.StringVar()
        self.data_count = tk.StringVar(value="유효 데이터: -")
        self.section_type = tk.StringVar(value="사각형")
        self.section_dimensions = {
            name: tk.StringVar() for fields in SECTION_FIELDS.values() for name, _ in fields
        }
        self.area_text = tk.StringVar(value="단면적: -")
        self.analysis_status = tk.StringVar(value="분석 필요")
        self.maximum_stress_text = tk.StringVar(value="최대 응력: -")
        self.maximum_time_text = tk.StringVar(value="해당 시간: -")
        self.time_values: list[float] = []
        self.force_values: list[float] = []

        self.build()

    def build(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        file_panel = ttk.Frame(main)
        file_panel.pack(fill="x", pady=(0, 10))

        ttk.Button(file_panel, text="CSV 찾아보기", command=self.select_csv).pack(
            side="left", padx=(0, 8)
        )
        ttk.Entry(
            file_panel,
            textvariable=self.csv_path,
            state="readonly",
        ).pack(side="left", fill="x", expand=True)
        ttk.Label(file_panel, textvariable=self.data_count, width=18).pack(
            side="right", padx=(10, 0)
        )

        section_panel = ttk.LabelFrame(main, text="단면 입력", padding=10)
        section_panel.pack(fill="x", pady=(0, 10))

        ttk.Label(section_panel, text="단면 종류").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        ttk.Combobox(
            section_panel,
            textvariable=self.section_type,
            values=tuple(SECTION_FIELDS),
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="w", padx=(0, 16))
        self.section_type.trace_add("write", self.update_section_fields)
        self.dimension_panel = ttk.Frame(section_panel)
        self.dimension_panel.grid(row=0, column=2, columnspan=6, sticky="ew")
        self.dimension_panel.columnconfigure(0, weight=1)
        self.build_dimension_fields()
        for dimension in self.section_dimensions.values():
            dimension.trace_add("write", self.dimensions_changed)

        ttk.Label(section_panel, textvariable=self.area_text).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )
        ttk.Button(section_panel, text="분석", command=self.analyze).grid(
            row=1, column=7, sticky="e", pady=(8, 0)
        )
        section_panel.columnconfigure(6, weight=1)

        summary_panel = ttk.Frame(main)
        summary_panel.pack(fill="x", pady=(0, 8))
        ttk.Label(summary_panel, textvariable=self.maximum_stress_text).pack(
            side="left", padx=(0, 24)
        )
        ttk.Label(summary_panel, textvariable=self.maximum_time_text).pack(
            side="left"
        )
        ttk.Label(summary_panel, textvariable=self.analysis_status).pack(side="right")

        graph_panel = ttk.LabelFrame(main, text="시간–응력 그래프", padding=8)
        graph_panel.pack(fill="both", expand=True)

        self.figure = Figure(figsize=(7, 4), dpi=100, tight_layout=True)
        self.axis = self.figure.add_subplot(111)
        self.configure_axes()
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def configure_axes(self) -> None:
        self.axis.set_xlabel("Time (s)")
        self.axis.set_ylabel("Stress (MPa)")
        self.axis.grid(True, alpha=0.3)

    def update_area_display(self, *_args: str) -> None:
        try:
            dimensions = self.get_dimensions()
            area = calculate_section_area(self.section_type.get(), dimensions)
        except ValueError:
            self.area_text.set("단면적: -")
            return

        self.area_text.set(f"단면적: {area:g} mm²")

    def build_dimension_fields(self) -> None:
        for child in self.dimension_panel.winfo_children():
            child.destroy()

        for column, (name, label) in enumerate(
            SECTION_FIELDS[self.section_type.get()]
        ):
            ttk.Label(self.dimension_panel, text=label).grid(
                row=0, column=column * 2, sticky="w", padx=(0, 5)
            )
            ttk.Entry(
                self.dimension_panel,
                textvariable=self.section_dimensions[name],
                width=8,
            ).grid(row=0, column=column * 2 + 1, sticky="w", padx=(0, 12))

    def update_section_fields(self, *_args: str) -> None:
        self.build_dimension_fields()
        self.invalidate_analysis("조건 변경됨: 다시 분석 필요")

    def dimensions_changed(self, *_args: str) -> None:
        self.invalidate_analysis("조건 변경됨: 다시 분석 필요")

    def get_dimensions(self) -> dict[str, float]:
        return {
            name: float(self.section_dimensions[name].get())
            for name, _ in SECTION_FIELDS[self.section_type.get()]
        }

    def clear_analysis(self) -> None:
        self.maximum_stress_text.set("최대 응력: -")
        self.maximum_time_text.set("해당 시간: -")
        self.axis.clear()
        self.configure_axes()
        self.canvas.draw_idle()

    def invalidate_analysis(self, status: str) -> None:
        self.clear_analysis()
        self.update_area_display()
        self.analysis_status.set(status)

    def analyze(self) -> None:
        self.clear_analysis()
        self.area_text.set("단면적: -")
        self.analysis_status.set("분석 중")

        if not self.time_values:
            self.analysis_status.set("분석 실패: CSV를 확인하세요")
            messagebox.showwarning("분석할 데이터 없음", "먼저 CSV 파일을 선택하세요.", parent=self.root)
            return

        try:
            dimensions = self.get_dimensions()
            area_mm2 = calculate_section_area(self.section_type.get(), dimensions)
            stress_values, maximum_stress, maximum_index = calculate_stress(
                self.force_values, area_mm2
            )
        except ValueError as error:
            self.analysis_status.set("분석 실패: 입력값을 확인하세요")
            messagebox.showerror("치수 또는 계산 오류", str(error), parent=self.root)
            return

        maximum_time = self.time_values[maximum_index]
        self.area_text.set(f"단면적: {area_mm2:g} mm²")
        self.maximum_stress_text.set(f"최대 응력: {maximum_stress:g} MPa")
        self.maximum_time_text.set(f"해당 시간: {maximum_time:g} s")
        self.axis.clear()
        self.axis.plot(self.time_values, stress_values, marker="o")
        self.axis.scatter([maximum_time], [maximum_stress], color="red", zorder=3)
        self.configure_axes()
        self.canvas.draw_idle()
        self.analysis_status.set("분석 완료")

    def select_csv(self) -> None:
        selected_path = filedialog.askopenfilename(
            title="하중 데이터 CSV 선택",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
        )
        if not selected_path:
            return

        self.csv_path.set(selected_path)
        self.time_values = []
        self.force_values = []
        self.data_count.set("유효 데이터: -")
        self.invalidate_analysis("CSV 변경됨: 다시 분석 필요")
        try:
            time_values, force_values, excluded_count = read_load_data(
                Path(selected_path)
            )
        except (OSError, UnicodeError, csv.Error, ValueError, KeyError) as error:
            self.analysis_status.set("CSV 오류: 분석할 수 없음")
            messagebox.showerror("CSV 읽기 오류", str(error), parent=self.root)
            return

        self.data_count.set(
            f"유효 데이터: {len(time_values)}개 / 제외: {excluded_count}개"
        )
        if not time_values:
            self.analysis_status.set("CSV 오류: 유효 데이터 없음")
            messagebox.showerror(
                "유효 데이터 없음",
                "숫자로 된 time_s와 force_N 데이터가 없어 분석할 수 없습니다.",
                parent=self.root,
            )
            return

        self.time_values = time_values
        self.force_values = force_values
        self.analysis_status.set("CSV 변경됨: 다시 분석 필요")


def main() -> None:
    root = tk.Tk()
    LoadAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()