"""
Скрипт строит графики по исходным данным датасета acct_0921-0923
для подраздела 1.3 отчёта (распределение Tфакт и распределение tau).

Использование:
    python3 plot_dataset_stats.py <путь_к_файлу_acct> [--uid 50430] [--jobname run_bwa.sh] [--outdir figures]
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

COLUMNS = [
    "JobIDRaw", "UID", "GID", "JobName", "Partition",
    "ReqNodes", "ReqCPUS", "AllocNodes", "AllocCPUS", "NodeList",
    "Timelimit", "Submit", "Reserved", "Start", "End", "Elapsed",
    "CPUTimeRAW", "ElapsedRaw", "TimelimitRaw", "Priority", "State",
]


def load_data(path: str) -> pd.DataFrame:
    """Читает файл учётных записей SLURM с разделителем '|'."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            parts = line.split("|")
            # убираем пустое поле, образующееся из-за завершающего '|' в строке
            if parts and parts[-1] == "":
                parts = parts[:-1]
            if len(parts) != len(COLUMNS):
                print(f"[предупреждение] строка {line_num}: "
                      f"ожидалось {len(COLUMNS)} полей, получено {len(parts)} — пропущена",
                      file=sys.stderr)
                continue
            rows.append(parts)

    if not rows:
        raise ValueError("Не удалось прочитать ни одной корректной строки из файла")

    return pd.DataFrame(rows, columns=COLUMNS)


def filter_variant(df: pd.DataFrame, uid: int, job_name: str) -> pd.DataFrame:
    """Фильтрует записи по UID и JobName, приводит числовые поля к нужному типу
    и вычисляет Tфакт / Tзаявки в секундах."""
    sub = df.copy()
    sub["UID"] = sub["UID"].astype(int)
    sub = sub[(sub["UID"] == uid) & (sub["JobName"] == job_name)].copy()

    if sub.empty:
        raise ValueError(f"Не найдено записей для UID={uid}, JobName={job_name}")

    sub["ElapsedRaw"] = sub["ElapsedRaw"].astype(float)
    sub["TimelimitRaw"] = sub["TimelimitRaw"].astype(float)

    # Tфакт — фактическое время выполнения, секунды
    sub["T_fact"] = sub["ElapsedRaw"]
    # Tзаявки — запрошенный пользователем лимит времени, секунды
    # (TimelimitRaw указан в минутах согласно описанию атрибутов датасета)
    sub["T_req"] = sub["TimelimitRaw"] * 60.0

    # упрощённое состояние без доп. деталей (например "CANCELLED by 50430" -> "CANCELLED")
    sub["State_clean"] = sub["State"].str.split(" by ").str[0]

    return sub


def compute_statistics(sub: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Вычисляет границы диапазона Tфакт и параметры mu, sigma логарифма tau.

    Ожидается, что на вход уже подан набор без FAILED-записей (см. main):
    задачи, прервавшиеся аварийно, не несут полезной информации об ошибке
    пользовательской оценки времени выполнения."""
    # исключаем записи с некорректным (нулевым/отрицательным) временем
    valid = sub[(sub["T_fact"] > 0) & (sub["T_req"] > 0)].copy()
    excluded = len(sub) - len(valid)

    t_min = valid["T_fact"].min()
    t_max = valid["T_fact"].max()

    valid["Tau"] = valid["T_req"] / valid["T_fact"]
    ln_tau = np.log(valid["Tau"])

    mu = ln_tau.mean()
    sigma = ln_tau.std(ddof=1)  # выборочное стандартное отклонение

    stats_dict = {
        "n_total": len(sub),
        "n_valid": len(valid),
        "n_excluded": excluded,
        "T_min": t_min,
        "T_max": t_max,
        "T_median": valid["T_fact"].median(),
        "mu": mu,
        "sigma": sigma,
        "quantiles": valid["T_fact"].quantile([0.05, 0.25, 0.5, 0.75, 0.95]),
    }
    return stats_dict, valid


def plot_status_distribution(sub: pd.DataFrame, outpath: str):
    """Столбчатая диаграмма распределения заявок по статусам (COMPLETED, FAILED,
    TIMEOUT, CANCELLED и т.д.) — строится на ПОЛНОМ наборе записей по варианту,
    без каких-либо исключений, чтобы дать представление о качестве исходных данных."""
    counts = sub["State_clean"].value_counts()
    total = counts.sum()
    percentages = counts / total * 100

    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(counts), 1)))
    bars = ax.bar(counts.index, counts.values, color=colors, edgecolor="black")

    for bar, count, pct in zip(bars, counts.values, percentages.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{count}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Статус задания")
    ax.set_ylabel("Количество заявок")
    ax.set_title(f"Распределение заявок по статусам\n(исходные данные acct_0921-0923, всего: {total})")
    ax.set_ylim(0, counts.max() * 1.18)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)

    fig.tight_layout()
    fig.savefig(outpath, dpi=300)
    plt.close(fig)
    print(f"Сохранено: {outpath}")


def plot_elapsed_distribution(valid: pd.DataFrame, stats_dict: dict, outpath: str):
    """Гистограмма фактического времени выполнения (Tфакт) — иллюстрирует диапазон [Tmin, Tmax]."""
    fig, ax = plt.subplots(figsize=(7, 4.5))

    data = valid["T_fact"].values
    # логарифмические по ширине бины, т.к. диапазон охватывает порядки величин (секунды..часы)
    lo = max(data.min(), 1)
    bins = np.logspace(np.log10(lo), np.log10(data.max()), 40)

    ax.hist(data, bins=bins, color="#4C72B0", edgecolor="black", alpha=0.85)
    ax.set_xscale("log")
    ax.axvline(stats_dict["T_min"], color="red", linestyle="--", linewidth=1,
               label=f"Tmin = {stats_dict['T_min']:.0f} с")
    ax.axvline(stats_dict["T_max"], color="darkred", linestyle="--", linewidth=1,
               label=f"Tmax = {stats_dict['T_max']:.0f} с")
    ax.axvline(stats_dict["T_median"], color="green", linestyle=":", linewidth=1.2,
               label=f"медиана = {stats_dict['T_median']:.0f} с")

    ax.set_xlabel("Tфакт, с (логарифмическая шкала)")
    ax.set_ylabel("Количество заявок")
    ax.set_title(f"Распределение фактического времени выполнения\n"
                 f"(выборка acct_0921-0923)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, which="both", linestyle=":", alpha=0.4)

    fig.tight_layout()
    fig.savefig(outpath, dpi=300)
    plt.close(fig)
    print(f"Сохранено: {outpath}")


def plot_tau_distribution(valid: pd.DataFrame, stats_dict: dict, outpath: str):
    """Гистограмма коэффициента ошибки tau с наложенной кривой логнормального закона
    (параметры mu, sigma) — иллюстрирует значения, вводимые в тексте подраздела 1.3."""
    fig, ax = plt.subplots(figsize=(7, 4.5))

    tau = valid["Tau"].values
    mu, sigma = stats_dict["mu"], stats_dict["sigma"]

    # ограничиваем отображаемый диапазон, чтобы редкие выбросы не "сжимали" гистограмму
    upper = np.percentile(tau, 99)
    tau_plot = tau[tau <= upper]

    bins = np.linspace(0, upper, 40)
    ax.hist(tau_plot, bins=bins, density=True, color="#4C9A6A",
            edgecolor="black", alpha=0.8, label="Исторические данные")

    x = np.linspace(0.01, upper, 500)
    pdf = stats.lognorm.pdf(x, s=sigma, scale=np.exp(mu))
    ax.plot(x, pdf, color="red", linewidth=2,
            label=f"Логнормальный закон\n(μ={mu:.4f}, σ={sigma:.4f})")

    ax.set_xlabel("Коэффициент ошибки τ = Tзаявки / Tфакт")
    ax.set_ylabel("Плотность вероятности")
    ax.set_title(f"Плотность распределения коэффициента ошибки пользователя τ\n"
                 f"(исходные данные acct_0921-0923, n={stats_dict['n_valid']})")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.4)

    fig.tight_layout()
    fig.savefig(outpath, dpi=300)
    plt.close(fig)
    print(f"Сохранено: {outpath}")


def main():
    parser = argparse.ArgumentParser(description="Построение графиков по исходным данным acct_0921-0923")
    parser.add_argument("data_path", help="путь к файлу с учётными записями (формат с разделителем '|')")
    parser.add_argument("--uid", type=int, default=50430, help="UID варианта (по умолчанию 50430)")
    parser.add_argument("--jobname", type=str, default="run_bwa.sh", help="JobName варианта")
    parser.add_argument("--outdir", type=str, default=".", help="каталог для сохранения графиков")
    args = parser.parse_args()

    df = load_data(args.data_path)
    sub = filter_variant(df, args.uid, args.jobname)  # все статусы, без исключений

    os.makedirs(args.outdir, exist_ok=True)

    # график распределения по статусам строится на ПОЛНОМ наборе (включая FAILED) —
    # это нужно, чтобы видеть качество исходных данных в целом
    plot_status_distribution(sub, os.path.join(args.outdir, "status_distribution.png"))

    # для анализа Tфакт / tau исключаем FAILED: такие задачи прерываются аварийно
    # до завершения и не несут полезной информации об ошибке оценки времени
    analysis_set = sub[sub["State_clean"] != "FAILED"].copy()
    n_failed = len(sub) - len(analysis_set)

    stats_dict, valid = compute_statistics(analysis_set)

    print("=" * 60)
    print(f"Всего записей по варианту:      {stats_dict['n_total'] + n_failed}")
    print(f"Исключено FAILED:                {n_failed}")
    print(f"Исключено (некорректные):       {stats_dict['n_excluded']}")
    print(f"Использовано для статистики:    {stats_dict['n_valid']}")
    print(f"Tmin, с:                        {stats_dict['T_min']:.0f}")
    print(f"Tmax, с:                        {stats_dict['T_max']:.0f}")
    print(f"Медиана Tфакт, с:                {stats_dict['T_median']:.0f}")
    print(f"mu (ln tau):                     {stats_dict['mu']:.4f}")
    print(f"sigma (ln tau):                  {stats_dict['sigma']:.4f}")
    print("-" * 60)
    print("Квантили Tфакт, с (пригодятся для подбора коэффициента масштабирования):")
    print(stats_dict["quantiles"].to_string())
    print("=" * 60)

    plot_elapsed_distribution(valid, stats_dict, os.path.join(args.outdir, "elapsed_distribution.png"))
    plot_tau_distribution(valid, stats_dict, os.path.join(args.outdir, "tau_distribution.png"))


if __name__ == "__main__":
    main()