"""
Analyse bystander-eval results and write a viewable report (plots + statistics).

Usage (from Eval_LLMs/):
    pip install pandas numpy statsmodels matplotlib scipy tabulate
    python analyze_results.py evaluation_YYYYMMDD_HHMMSS/          # folder, responses.jsonl or raw_responses.json
    python analyze_results.py evaluation_A/ evaluation_B/          # several runs are combined
    python analyze_results.py evaluation_YYYYMMDD_HHMMSS/ --open   # also open the report in a browser

Outputs go to <first input folder>/analysis/:
    report.html      self-contained report: every plot and table (open in any browser)
    summary.md       the same statistics as Markdown, with the plots linked (VS Code preview shows them)
    *.png            the plots
    by_group_size.csv, regression_<model>.txt

Design notes:
- Score = expected intervention score (1 = non-intervention ... 4 = direct intervention), computed
  from the model's probabilities and the dataset's option_types. A bystander effect shows up as
  a NEGATIVE group-size slope.
- Group size 0 has no other bystanders, so its reaction is "unstated" (old runs label it "n/a";
  that is mapped to "unstated"). When the dataset has an "unstated" level at n >= 1, reaction is a
  3-level factor with "unstated" as reference; otherwise the reaction contrast (ignoring vs
  worried) is estimated on n >= 1 only, so it isn't mixed up with the jump from group 0.
"""
import argparse
import base64
import html
import json
import re
import sys
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

TYPES = ["non_intervention", "hesitation", "indirect_intervention", "direct_intervention"]
TYPE_LABELS = {"non_intervention": "non-intervention", "hesitation": "hesitation",
               "indirect_intervention": "indirect", "direct_intervention": "direct"}
TYPE_COLORS = {"non_intervention": "#9e9e9e", "hesitation": "#f2b134",
               "indirect_intervention": "#4c9be8", "direct_intervention": "#2a7d4f"}
LEVEL_COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e"]
UNSTATED = "unstated"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load(path: Path) -> list[dict]:
    if path.is_dir():
        files = sorted(path.glob("*.jsonl")) or sorted(path.glob("raw_responses.json"))
    else:
        files = [path]
    rows = []
    for f in files:
        if f.suffix == ".jsonl":
            for line in f.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"(skipping malformed line in {f})")
        else:
            data = json.loads(f.read_text())
            rows += [r for rs in data.values() for r in rs] if isinstance(data, dict) else data
    return rows


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if "option_types" not in df:
        sys.exit("These results have no option_types; analyse a run made with matched scenarios.")
    missing = df["option_types"].isna()
    if missing.any():
        print(f"(dropping {missing.sum()} responses without option_types)")
        df = df[~missing]
    df = df.drop_duplicates(["model_name", "scenario_id"], keep="last").reset_index(drop=True)

    df["score"] = df["intervention_score_expected"].astype(float)
    for t in TYPES:
        df[f"p_{t}"] = [sum(p for k, p in pd_.items() if ot.get(k) == t)
                        for pd_, ot in zip(df["probability_distribution"], df["option_types"])]
    for letter in "ABCD":
        df[f"p_at_{letter}"] = [pd_.get(letter, np.nan) for pd_ in df["probability_distribution"]]
    df["dominant_type"] = [ot.get(r) for ot, r in zip(df["option_types"], df["dominant_response"])]
    df["log2_g"] = np.log2(df["group_size"] + 1)
    df["unclear"] = (df["clarity_level"] == "unclear").astype(int)
    df["auth"] = df["authority_present"].astype(bool).astype(int)
    reaction = df.get("bystander_reaction", pd.Series([None] * len(df)))
    df["reaction"] = reaction.fillna(UNSTATED).replace({"n/a": UNSTATED})
    df.loc[df["group_size"] == 0, "reaction"] = UNSTATED
    return df


def reaction_reference(m: pd.DataFrame) -> str:
    """'unstated' if it exists at n >= 1 (3-level design), else 'worried' (old 2-level design)."""
    pos = m[m.group_size > 0]
    if (pos.reaction == UNSTATED).any():
        return UNSTATED
    levels = sorted(pos.reaction.unique())
    return "worried" if "worried" in levels else (levels[0] if levels else UNSTATED)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def fit(df: pd.DataFrame, formula: str):
    n_bases = df["base_id"].nunique()
    model = smf.ols(formula, df)
    # cluster by base story when there are enough clusters; otherwise heteroskedasticity-robust
    if n_bases >= 15:
        return (model.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df["base_id"])[0]}),
                "cluster-robust by base story")
    return model.fit(cov_type="HC1"), f"HC1 (only {n_bases} base stories - treat p-values as optimistic)"


def _reaction_term(ref: str) -> str:
    return f"C(reaction, Treatment('{ref}'))"


TERM_NAMES = {"log2_g": "group size (per doubling of N+1)", "unclear": "unclear vs clear",
              "auth": "authority present"}


def _rename_part(part: str) -> str:
    m = re.match(r"C\(reaction, Treatment\('(\w+)'\)\)\[T\.(\w+)\]", part)
    if m:
        return f"reaction: {m.group(2)} vs {m.group(1)}"
    return TERM_NAMES.get(part, part)


def _rename_term(term: str) -> str:
    """Readable name for a patsy term, e.g. 'log2_g:unclear' -> 'group size (...) x unclear vs clear'."""
    return " x ".join(_rename_part(p) for p in term.split(":"))


def coef_table(res, terms: list[str]) -> pd.DataFrame:
    ci = res.conf_int()
    rows = []
    for t in terms:
        if t in res.params:
            rows.append({"effect": _rename_term(t), "term": t, "estimate": res.params[t],
                         "ci_low": ci.loc[t, 0], "ci_high": ci.loc[t, 1], "p": res.pvalues[t]})
    return pd.DataFrame(rows)


def _terms(res, exclude_base=True) -> list[str]:
    return [t for t in res.params.index if t != "Intercept" and not (exclude_base and t.startswith("C(base_id"))]


def regressions(m: pd.DataFrame) -> dict:
    """Fit the main, reaction and interaction models that the data supports."""
    base_fe = " + C(base_id)" if m["base_id"].nunique() > 1 else ""
    ref = reaction_reference(m)
    pos = m[m.group_size > 0]
    out = {"ref": ref}

    def covariates(d):
        cov = [c for c in ("log2_g", "unclear", "auth") if d[c].nunique() > 1]
        return cov

    # Main model on all rows (incl. group 0). With an 'unstated' level the reaction factor is
    # well defined at every group size, so it can be included here.
    cov = covariates(m)
    main_terms = list(cov)
    if ref == UNSTATED and m.reaction.nunique() > 1:
        main_terms.append(_reaction_term(ref))
    if main_terms:
        res, se = fit(m, "score ~ " + " + ".join(main_terms) + base_fe)
        out["main"] = (res, se, coef_table(res, _terms(res)), "all responses (incl. group 0)")

    # Reaction contrasts on n >= 1, where every reaction level exists
    if pos.reaction.nunique() > 1:
        cov_p = covariates(pos)
        res, se = fit(pos, "score ~ " + " + ".join(cov_p + [_reaction_term(ref)]) + base_fe)
        out["reaction"] = (res, se, coef_table(res, _terms(res)), "responses with n >= 1")

    # Does the group-size slope depend on clarity / authority / reaction?
    d = pos if pos.reaction.nunique() > 1 else m
    if d["log2_g"].nunique() > 1:
        inter = [f"log2_g * {c}" for c in ("unclear", "auth") if d[c].nunique() > 1]
        if d.reaction.nunique() > 1:
            inter.append(f"log2_g * {_reaction_term(ref)}")
        if inter:
            res, se = fit(d, "score ~ " + " + ".join(inter) + base_fe)
            terms = [t for t in _terms(res) if ":" in t]
            label = "responses with n >= 1" if d is pos else "all responses"
            out["interactions"] = (res, se, coef_table(res, terms), label)
    return out


def paired_contrast(m: pd.DataFrame, g_low: int, g_high: int, reaction: str | None) -> dict | None:
    """Within-story paired difference score(g_high) - score(g_low), matching base, clarity, authority.

    reaction=None averages the g_high reactions; otherwise only that reaction level is used
    (group 0 always counts as 'unstated').
    """
    keys = ["base_id", "clarity_level", "authority_present"]
    lo = m[m.group_size == g_low]
    hi = m[m.group_size == g_high]
    if reaction is not None:
        hi = hi[hi.reaction == reaction]
        if g_low > 0:
            lo = lo[lo.reaction == reaction]
    a = lo.groupby(keys)["score"].mean()
    b = hi.groupby(keys)["score"].mean()
    j = pd.concat([a.rename("lo"), b.rename("hi")], axis=1).dropna()
    if len(j) < 2:
        return None
    diff = j.hi - j.lo
    mean, sem = diff.mean(), diff.std(ddof=1) / np.sqrt(len(diff))
    t_p = stats.ttest_rel(j.hi, j.lo).pvalue if diff.std(ddof=1) > 0 else np.nan
    try:
        w_p = stats.wilcoxon(diff).pvalue if (diff != 0).any() else np.nan
    except ValueError:
        w_p = np.nan
    return {"contrast": f"group {g_high} vs {g_low}" + (f" ({reaction})" if reaction else " (reactions averaged)"),
            "n_pairs": len(j), "mean_diff": mean, "ci_low": mean - 1.96 * sem, "ci_high": mean + 1.96 * sem,
            "lower": int((diff < 0).sum()), "higher": int((diff > 0).sum()), "tied": int((diff == 0).sum()),
            "t_test_p": t_p, "wilcoxon_p": w_p}


def describe(row: pd.Series, what: str, unit: str = "") -> str:
    est, lo, hi, p = row["estimate"], row["ci_low"], row["ci_high"], row["p"]
    ci = f"{est:+.3f}{unit} (95% CI {lo:+.3f} to {hi:+.3f}, p = {p:.3g})"
    if lo > 0:
        return f"{what}: scores go **up** by {ci}."
    if hi < 0:
        return f"{what}: scores go **down** by {ci}."
    return f"{what}: no clear effect, {ci}."


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": 0.3, "font.size": 9})
    return plt


def _group_axis(ax, sizes):
    ax.set_xticks(np.log2(np.array(sizes) + 1), [str(s) for s in sizes])
    ax.set_xlabel("other bystanders (log scale)")


def _mean_ci_line(ax, d, value, label, color, offset=0.0, **kw):
    s = d.groupby("group_size")[value].agg(["mean", "sem", "size"])
    x = np.log2(s.index.values + 1) + offset
    yerr = 1.96 * s["sem"].fillna(0)
    ax.errorbar(x, s["mean"], yerr=yerr, marker="o", ms=4, capsize=2, lw=1.5, label=label, color=color, **kw)


def plot_conditions(m, path):
    plt = _plt()
    sizes = sorted(m.group_size.unique())
    panels = [("clarity_level", "Clarity"), ("reaction", "Bystander reaction"), ("authority_present", "Authority figure")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    for ax, (col, title) in zip(axes, panels):
        levels = sorted(m[col].unique(), key=str)
        for i, lvl in enumerate(levels):
            d = m[m[col] == lvl]
            if col == "reaction" and lvl != UNSTATED:
                d = d[d.group_size > 0]
            label = {True: "present", False: "absent"}.get(lvl, str(lvl)) if col == "authority_present" else str(lvl)
            _mean_ci_line(ax, d, "score", label, LEVEL_COLORS[i % len(LEVEL_COLORS)], offset=(i - (len(levels) - 1) / 2) * 0.06)
        _group_axis(ax, sizes)
        ax.set_title(title)
        ax.legend(fontsize=8, frameon=False)
    axes[0].set_ylabel("expected intervention score (1-4)\nhigher = more helping")
    fig.suptitle("Intervention score vs group size (mean ± 95% CI)", fontsize=11)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_types(m, path):
    plt = _plt()
    sizes = sorted(m.group_size.unique())
    clarities = sorted(m.clarity_level.unique())
    fig, axes = plt.subplots(1, len(clarities), figsize=(5.5 * len(clarities), 3.8), sharey=True, squeeze=False)
    for ax, clarity in zip(axes[0], clarities):
        d = m[m.clarity_level == clarity]
        g = d.groupby("group_size")[[f"p_{t}" for t in TYPES]].mean()
        x = np.log2(g.index.values + 1)
        ax.stackplot(x, *[g[f"p_{t}"] for t in TYPES], labels=[TYPE_LABELS[t] for t in TYPES],
                     colors=[TYPE_COLORS[t] for t in TYPES], alpha=0.9)
        _group_axis(ax, sizes)
        ax.set_ylim(0, 1)
        ax.set_title(f"{clarity} scenarios")
    axes[0][0].set_ylabel("mean probability")
    axes[0][-1].legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
    fig.suptitle("How the model splits probability across response types", fontsize=11)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_position(m, path):
    plt = _plt()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1, 1.3]})
    means = [m[f"p_at_{l}"].mean() for l in "ABCD"]
    errs = [1.96 * m[f"p_at_{l}"].sem() for l in "ABCD"]
    ax1.bar(list("ABCD"), means, yerr=errs, capsize=3, color="#7a8fb3")
    ax1.axhline(0.25, color="k", ls="--", lw=1, label="no position bias (0.25)")
    ax1.set_title("Mean probability by option letter")
    ax1.set_ylabel("mean probability")
    ax1.legend(fontsize=8, frameon=False)

    grid = np.full((len(TYPES), 4), np.nan)
    for i, t in enumerate(TYPES):
        for j, l in enumerate("ABCD"):
            vals = [pd_.get(l) for pd_, ot in zip(m["probability_distribution"], m["option_types"]) if ot.get(l) == t]
            if vals:
                grid[i, j] = np.mean(vals)
    im = ax2.imshow(grid, cmap="viridis", aspect="auto", vmin=0, vmax=max(0.01, np.nanmax(grid)))
    ax2.set_xticks(range(4), list("ABCD"))
    ax2.set_yticks(range(len(TYPES)), [TYPE_LABELS[t] for t in TYPES])
    for i in range(len(TYPES)):
        for j in range(4):
            if not np.isnan(grid[i, j]):
                ax2.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center",
                         color="white" if grid[i, j] < 0.6 * np.nanmax(grid) else "black", fontsize=8)
    ax2.set_title("Mean probability of each type at each letter\n(rows should be flat if there is no position bias)")
    ax2.grid(False)
    fig.colorbar(im, ax=ax2, fraction=0.04)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_bases(m, path):
    plt = _plt()
    sizes = sorted(m.group_size.unique())
    fig, ax = plt.subplots(figsize=(7, 4))
    for base_id, d in m.groupby("base_id"):
        s = d.groupby("group_size")["score"].mean()
        ax.plot(np.log2(s.index.values + 1), s.values, color="#888", alpha=0.35, lw=1)
    s = m.groupby("group_size")["score"].mean()
    ax.plot(np.log2(s.index.values + 1), s.values, color="#d62728", lw=2.5, marker="o", label="mean over stories")
    _group_axis(ax, sizes)
    ax.set_ylabel("expected intervention score (1-4)")
    ax.set_title(f"Each base story's curve (grey, n = {m.base_id.nunique()}) and the mean")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_coefficients(tables: list[tuple[str, pd.DataFrame]], path):
    """Forest plot: one panel per regression model, effects with 95% CIs, shared x-axis."""
    plt = _plt()
    tables = [(title, t) for title, t in tables if len(t)]
    if not tables:
        return False
    heights = [len(t) for _, t in tables]
    fig, axes = plt.subplots(len(tables), 1, figsize=(8.5, 0.38 * sum(heights) + 0.9 * len(tables) + 0.6),
                             sharex=True, squeeze=False, gridspec_kw={"height_ratios": heights})
    for ax, (title, t) in zip(axes[:, 0], tables):
        y = np.arange(len(t))[::-1]
        for yi, r in zip(y, t.itertuples()):
            color = "#d62728" if r.ci_high < 0 else ("#2a7d4f" if r.ci_low > 0 else "#555")
            ax.errorbar(r.estimate, yi, xerr=[[r.estimate - r.ci_low], [r.ci_high - r.estimate]],
                        fmt="o", color=color, capsize=3)
        ax.axvline(0, color="k", lw=1)
        ax.set_yticks(y, [e.replace(" (per doubling of N+1)", " (per doubling)") for e in t.effect])
        ax.set_ylim(-0.6, len(t) - 0.4)
        ax.set_title(title, loc="left", fontsize=9, fontweight="bold")
    axes[-1, 0].set_xlabel("effect on intervention score, 95% CI\nred = lowers helping · green = raises it · grey = CI includes 0")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def plot_models(df, path):
    plt = _plt()
    sizes = sorted(df.group_size.unique())
    clarities = sorted(df.clarity_level.unique())
    fig, axes = plt.subplots(1, len(clarities), figsize=(5.5 * len(clarities), 3.8), sharey=True, squeeze=False)
    for ax, clarity in zip(axes[0], clarities):
        for i, (model_name, m) in enumerate(df[df.clarity_level == clarity].groupby("model_name")):
            _mean_ci_line(ax, m, "score", model_name, LEVEL_COLORS[i % len(LEVEL_COLORS)])
        _group_axis(ax, sizes)
        ax.set_title(f"{clarity} scenarios")
    axes[0][0].set_ylabel("expected intervention score (1-4)")
    axes[0][0].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if c in ("p", "t_test_p", "wilcoxon_p"):
            out[c] = out[c].map(lambda v: "" if pd.isna(v) else f"{v:.3g}")
        elif out[c].dtype.kind == "f":
            out[c] = out[c].map(lambda v: "" if pd.isna(v) else f"{v:+.3f}" if c in ("estimate", "ci_low", "ci_high", "mean_diff") else f"{v:.3f}")
    return out


class Report:
    """Collects sections and renders both report.html (images embedded) and summary.md."""

    def __init__(self, out: Path):
        self.out = out
        self.html: list[str] = []
        self.md: list[str] = ["# Bystander eval analysis", ""]

    def h(self, level: int, text: str):
        self.html.append(f"<h{level}>{html.escape(text)}</h{level}>")
        self.md += ["#" * level + " " + text, ""]

    @staticmethod
    def _inline(text: str) -> str:
        """Escape text for HTML and render **bold**."""
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(text))

    def p(self, text: str):
        self.html.append(f"<p>{self._inline(text)}</p>")
        self.md += [text, ""]

    def bullets(self, items: list[str]):
        lis = "".join(f"<li>{self._inline(i)}</li>" for i in items)
        self.html.append(f"<ul>{lis}</ul>")
        self.md += [f"- {i}" for i in items] + [""]

    def table(self, df: pd.DataFrame, index=False):
        shown = _fmt(df)
        self.html.append(shown.to_html(index=index, border=0, classes="tbl", escape=True))
        self.md += [shown.to_markdown(index=index), ""]

    def image(self, path: Path, alt: str):
        if not path.exists():
            return
        data = base64.b64encode(path.read_bytes()).decode()
        self.html.append(f'<figure><img src="data:image/png;base64,{data}" alt="{html.escape(alt)}">'
                         f"<figcaption>{html.escape(alt)}</figcaption></figure>")
        self.md += [f"![{alt}]({path.name})", ""]

    def pre(self, text: str):
        self.html.append(f"<details><summary>Full regression output</summary><pre>{html.escape(text)}</pre></details>")

    def write(self) -> Path:
        css = """
        body{font:14px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:1150px;margin:2em auto;padding:0 1em;color:#222;background:#fff}
        h1{font-size:1.6em}h2{margin-top:2em;border-bottom:1px solid #ddd;padding-bottom:.2em}h3{margin-top:1.5em}
        figure{margin:1em 0}img{max-width:100%;border:1px solid #eee}figcaption{color:#666;font-size:.9em}
        table.tbl{border-collapse:collapse;margin:.5em 0 1em;font-size:13px}
        table.tbl th,table.tbl td{padding:4px 10px;border-bottom:1px solid #e5e5e5;text-align:right}
        table.tbl th:first-child,table.tbl td:first-child{text-align:left}
        pre{background:#f6f8fa;padding:1em;overflow:auto;font-size:12px}.note{color:#666}
        @media (prefers-color-scheme: dark){body{background:#16181c;color:#ddd}img{background:#fff}
        pre{background:#22252b}table.tbl th,table.tbl td{border-color:#333}h2{border-color:#333}}
        """
        page = (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
                f"<title>Bystander eval analysis</title><style>{css}</style></head><body>"
                f"<h1>Bystander eval analysis</h1>{''.join(self.html)}</body></html>")
        (self.out / "report.html").write_text(page, encoding="utf-8")
        (self.out / "summary.md").write_text("\n".join(self.md), encoding="utf-8")
        return self.out / "report.html"


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def analyse_model(model_name: str, m: pd.DataFrame, rep: Report, out: Path) -> pd.DataFrame:
    slug = _slug(model_name)
    rep.h(2, model_name)
    n_bases = m.base_id.nunique()
    reactions = sorted(m[m.group_size > 0].reaction.unique())
    rep.bullets([
        f"{len(m)} responses across {n_bases} base stories and {m.scenario_type.nunique()} scenario type(s): "
        f"{', '.join(sorted(m.scenario_type.unique()))}",
        f"group sizes {sorted(m.group_size.unique())}; reactions at n >= 1: {reactions}",
        f"mean intervention score {m.score.mean():.2f} on a 1-4 scale "
        f"(1 = non-intervention, 2 = hesitation, 3 = indirect, 4 = direct)",
    ])

    regs = regressions(m)

    # Key findings in plain language
    findings = []
    if "main" in regs:
        t = regs["main"][2].set_index("term")
        if "log2_g" in t.index:
            findings.append(describe(t.loc["log2_g"], "Group size (bystander effect = negative)", " per doubling of N+1"))
        if "unclear" in t.index:
            findings.append(describe(t.loc["unclear"], "Unclear vs clear"))
        if "auth" in t.index:
            findings.append(describe(t.loc["auth"], "Authority figure present"))
    if "reaction" in regs:
        t = regs["reaction"][2]
        for r in t[t.term.str.startswith("C(reaction")].itertuples():
            findings.append(describe(pd.Series(r._asdict()), r.effect.replace("reaction: ", "Others ")))
    contrasts = []
    sizes = sorted(m.group_size.unique())
    if 0 in sizes and len(sizes) > 1:
        ref = UNSTATED if regs["ref"] == UNSTATED else None
        for g in [s for s in (1, max(sizes)) if s in sizes and s > 0]:
            c = paired_contrast(m, 0, g, ref)
            if c:
                contrasts.append(c)
        if ref:
            c = paired_contrast(m, 0, max(sizes), None)
            if c:
                contrasts.append(c)
    for c in contrasts[:2]:
        verdict = "lower" if c["ci_high"] < 0 else ("higher" if c["ci_low"] > 0 else "not clearly different")
        findings.append(
            f"Paired within-story, {c['contrast']}: {c['mean_diff']:+.3f} (95% CI {c['ci_low']:+.3f} to "
            f"{c['ci_high']:+.3f}, Wilcoxon p = {c['wilcoxon_p']:.3g}) over {c['n_pairs']} pairs: {verdict}.")
    if n_bases < 15:
        findings.append(f"Only {n_bases} base stories: SEs are HC1, not clustered by story, so p-values are optimistic.")
    rep.h(3, "Key findings")
    rep.bullets(findings or ["Not enough variation in the data to estimate effects."])

    # Plots
    rep.h(3, "Score by condition")
    plot_conditions(m, out / f"conditions_{slug}.png")
    rep.image(out / f"conditions_{slug}.png", "Mean intervention score vs group size, split by clarity, reaction and authority")

    rep.h(3, "Response types")
    plot_types(m, out / f"response_types_{slug}.png")
    rep.image(out / f"response_types_{slug}.png", "Mean probability on each response type vs group size")

    rep.h(3, "Per base story")
    plot_bases(m, out / f"bases_{slug}.png")
    rep.image(out / f"bases_{slug}.png", "Each base story's mean score vs group size")

    # Tables
    g = m.groupby("group_size").agg(
        n=("score", "size"), score=("score", "mean"), score_sem=("score", "sem"),
        p_direct=("p_direct_intervention", "mean"), p_indirect=("p_indirect_intervention", "mean"),
        p_hesitation=("p_hesitation", "mean"), p_non=("p_non_intervention", "mean"))
    rep.h(3, "Means by group size")
    rep.table(g.reset_index())
    pv = m.pivot_table(index="group_size", columns="clarity_level", values="score")
    rep.p("By group size and clarity:")
    rep.table(pv.reset_index())
    pvr = m[m.group_size > 0].pivot_table(index="group_size", columns="reaction", values="score")
    if pvr.shape[1] > 1:
        rep.p("By group size and bystander reaction (n >= 1):")
        rep.table(pvr.reset_index())

    # Regressions
    rep.h(3, "Regressions")
    rep.p("OLS on the expected intervention score with base-story fixed effects. "
          "Group size enters as log2(N+1), so each coefficient is the change per doubling.")
    forest = []
    full_text = []
    for key, title in (("main", "Main effects"), ("reaction", "Reaction contrasts"), ("interactions", "Interactions with group size")):
        if key not in regs:
            continue
        res, se, tbl, sample = regs[key]
        rep.p(f"**{title}** ({sample}; SEs: {se}):")
        rep.table(tbl.drop(columns="term"))
        forest.append((title, tbl))
        full_text.append(f"{title.upper()} ({sample}; SEs: {se})\n{res.summary()}\n")
    if forest and plot_coefficients(forest, out / f"coefficients_{slug}.png"):
        rep.image(out / f"coefficients_{slug}.png", "Regression effects with 95% CIs")
    if full_text:
        (out / f"regression_{slug}.txt").write_text("\n\n".join(full_text))
        rep.pre("\n\n".join(full_text))

    if contrasts:
        rep.h(3, "Paired within-story contrasts")
        rep.p("Same base story, clarity and authority; only the number of other bystanders differs"
              + (" (and, for 'unstated', no reaction sentence is shown at either size)." if regs["ref"] == UNSTATED else "."))
        rep.table(pd.DataFrame(contrasts))

    # Position bias / sanity checks
    rep.h(3, "Position bias and sanity checks")
    counts = m["dominant_response"].value_counts().reindex(list("ABCD"), fill_value=0)
    chi = stats.chisquare(counts.values) if counts.sum() else None
    reasons = [" ".join(r.values()).lower() if isinstance(r, dict) else str(r).lower() for r in m["reasoning"]]
    n_mention = sum(("bystander" in r) or ("diffusion of responsibility" in r) for r in reasons)
    rep.bullets([
        f"top-choice letter counts A/B/C/D: {counts.tolist()}"
        + (f" (chi-square vs uniform p = {chi.pvalue:.3g})" if chi is not None else ""),
        "top-choice response types: " + ", ".join(f"{TYPE_LABELS.get(k, k)} {v}" for k, v in m["dominant_type"].value_counts().items()),
        f"explanations naming the bystander effect / diffusion of responsibility: {n_mention}/{len(m)}",
    ])
    plot_position(m, out / f"position_{slug}.png")
    rep.image(out / f"position_{slug}.png", "Position bias: probability by letter, and by type x letter")

    g = g.reset_index()
    g.insert(0, "model", model_name)
    return g


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyse bystander-eval results")
    parser.add_argument("paths", nargs="+", help="run folder(s), responses.jsonl or raw_responses.json")
    parser.add_argument("--open", action="store_true", help="open report.html in a browser when done")
    args = parser.parse_args(argv)

    rows = [r for p in args.paths for r in load(Path(p))]
    if not rows:
        sys.exit("No responses found.")
    df = to_frame(rows)
    first = Path(args.paths[0])
    out = (first if first.is_dir() else first.parent) / "analysis"
    out.mkdir(exist_ok=True)

    rep = Report(out)
    rep.p(f"Inputs: {', '.join(args.paths)} · {len(df)} responses · {df.model_name.nunique()} model(s). "
          "Score = expected intervention score from the model's option probabilities and the dataset's "
          "option types (1 = non-intervention … 4 = direct). A bystander effect is a negative group-size slope.")

    by_g_all = [analyse_model(name, m, rep, out) for name, m in df.groupby("model_name")]

    if df.model_name.nunique() > 1:
        rep.h(2, "Model comparison")
    plot_models(df, out / "intervention_vs_group_size.png")
    if df.model_name.nunique() > 1:
        rep.image(out / "intervention_vs_group_size.png", "All models: score vs group size")
    pd.concat(by_g_all).to_csv(out / "by_group_size.csv", index=False)

    report = rep.write()
    print("\n".join(rep.md))
    print(f"\nReport: {report.resolve()}")
    print(f"Plots and tables: {out.resolve()}/")
    if args.open:
        webbrowser.open(report.resolve().as_uri())


if __name__ == "__main__":
    main()
